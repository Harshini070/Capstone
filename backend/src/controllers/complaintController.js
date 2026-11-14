
const { randomUUID } = require("crypto");

const Complaint = require("../models/Complaint");

const {
    processTeluguComplaint,
    classifyTeluguComplaint,
} = require("../services/nlpService");

const {
    getCategories,
    getCategoryByCode,
    getTaxonomyMetadata,
} = require("../services/taxonomyService");

const ALLOWED_STATUSES = [
    "SUBMITTED",
    "UNDER_REVIEW",
    "IN_PROGRESS",
    "RESOLVED",
    "REJECTED",
];

const ALLOWED_TRANSITIONS = {
    SUBMITTED: ["UNDER_REVIEW", "REJECTED"],
    UNDER_REVIEW: ["IN_PROGRESS", "REJECTED"],
    IN_PROGRESS: ["RESOLVED", "REJECTED"],
    RESOLVED: [],
    REJECTED: [],
};

// complaintId uses 8 hex characters (GH-XXXXXXXX). Collisions are rare but
// become plausible at tens of thousands of records; the unique index rejects
// them, so retry with a freshly generated ID instead of failing the request.
const MAX_COMPLAINT_ID_ATTEMPTS = 5;

const isComplaintIdCollision = (error) =>
    error?.code === 11000 &&
    (error.keyPattern?.complaintId ||
        /complaintId/.test(String(error.message)));

const createWithUniqueComplaintId = async (data) => {
    for (let attempt = 1; ; attempt += 1) {
        try {
            // complaintId is left unset so the schema default generates a new one.
            return await Complaint.create(data);
        } catch (error) {
            if (
                !isComplaintIdCollision(error) ||
                attempt >= MAX_COMPLAINT_ID_ATTEMPTS
            ) {
                throw error;
            }

            console.warn(
                `complaintId collision on attempt ${attempt}; retrying.`
            );
        }
    }
};

// GET: Complaint counts by status across the whole collection
const getComplaintStats = async (req, res, next) => {
    try {
        const grouped = await Complaint.aggregate([
            { $group: { _id: "$status", count: { $sum: 1 } } },
        ]);

        const byStatus = Object.fromEntries(
            ALLOWED_STATUSES.map((status) => [status, 0])
        );

        let total = 0;

        for (const { _id: status, count } of grouped) {
            total += count;

            if (status in byStatus) {
                byStatus[status] = count;
            }
        }

        return res.status(200).json({
            success: true,
            message: "Complaint statistics retrieved successfully.",
            data: { total, byStatus },
        });
    } catch (error) {
        next(error);
    }
};

// GET: Retrieve complaints with pagination
const getAllComplaints = async (req, res, next) => {
    try {
        let { page = "1", limit = "10", status, category } = req.query;

        page = Number(page);
        limit = Number(limit);

        if (
            !Number.isInteger(page) ||
            !Number.isInteger(limit) ||
            page < 1 ||
            limit < 1 ||
            limit > 100
        ) {
            return res.status(400).json({
                success: false,
                message:
                    "Invalid pagination parameters. Page must be at least 1 and limit must be between 1 and 100.",
            });
        }

        const filter = {};

        if (status) {
            const normalizedStatus = status.toUpperCase();

            if (!ALLOWED_STATUSES.includes(normalizedStatus)) {
                return res.status(400).json({
                    success: false,
                    message: "Invalid complaint status filter.",
                });
            }

            filter.status = normalizedStatus;
        }

        if (category) {
            filter.category = category;
        }

        const skip = (page - 1) * limit;

        const [complaints, totalComplaints] = await Promise.all([
            Complaint.find(filter)
                .select(
                    "complaintId title category status language classification createdAt updatedAt"
                )
                .sort({ createdAt: -1, _id: -1 })
                .skip(skip)
                .limit(limit)
                .lean(),

            Complaint.countDocuments(filter),
        ]);

        const totalPages = Math.ceil(totalComplaints / limit);

        return res.status(200).json({
            success: true,
            message: "Complaints retrieved successfully.",
            data: complaints,
            pagination: {
                currentPage: page,
                pageSize: limit,
                totalComplaints,
                totalPages,
                hasNextPage: page < totalPages,
                hasPreviousPage: page > 1,
            },
        });
    } catch (error) {
        next(error);
    }
};

// POST: Submit a new complaint

const submitComplaint = async (req, res, next) => {
    try {
        const { title, description } = req.body;

        if (
            typeof title !== "string" ||
            typeof description !== "string" ||
            !title.trim() ||
            !description.trim()
        ) {
            return res.status(400).json({
                success: false,
                message: "Complaint title and description are required.",
            });
        }

        const recordId = `GH-NLP-${randomUUID()}`;

        // Required preprocessing
        const nlpResult = await processTeluguComplaint({
            recordId,
            title,
            description,
        });

        // Classification is best-effort.
        let classification = null;

        try {
            const result = await classifyTeluguComplaint({
                recordId,
                title,
                description,
            });

            const prediction = result.prediction;

            classification = {
                predictedCategory:
                    prediction?.predicted_category || "UNCLASSIFIED",
                predictionStatus:
                    prediction?.prediction_status || "REVIEW_REQUIRED",
                predictionMethod:
                    prediction?.prediction_method || "RULE_BASED",
                classifierVersion:
                    prediction?.classifier_version || null,
                ruleScore: prediction?.rule_score ?? null,
                scoreMargin: prediction?.score_margin ?? null,
                matchedTerms: prediction?.matched_terms || [],
                confidence: prediction?.confidence ?? null,
                confidenceNote: prediction?.confidence_note || null,
                alternatives: prediction?.alternatives || [],
                taxonomyVersion: result.taxonomy_version || null,
                taxonomyStatus: result.taxonomy_status || null,
                notice: result.notice || null,
                predictedAt: new Date(),
            };
        } catch (classificationError) {
            console.error(
                "Provisional classification unavailable:",
                classificationError.message
            );
        }

        const complaint = await createWithUniqueComplaintId({
            title: title.trim(),
            description: description.trim(),
            language: "te",

            // Never automatically assign an unreviewed prediction.
            category: "UNCLASSIFIED",
            categoryReviewStatus: "NOT_REVIEWED",
            status: "SUBMITTED",

            classification,

            nlpResults: {
                pipelineVersion: nlpResult.pipeline_version,
                normalizedTitle: nlpResult.normalized_title,
                normalizedDescription:
                    nlpResult.normalized_description,
                features: nlpResult.features,
                qualityFlags: nlpResult.quality_flags,
                processedAt: new Date(),
            },
        });

        return res.status(201).json({
            success: true,
            message: "Complaint submitted successfully.",
            data: {
                complaintId: complaint.complaintId,
                status: complaint.status,
                category: complaint.category,
                classification: complaint.classification,
                nlpResults: complaint.nlpResults,
                createdAt: complaint.createdAt,
            },
        });
    } catch (error) {
        next(error);
    }
};


// GET: Return provisional taxonomy categories
const getComplaintCategories = async (req, res, next) => {
    try {
        const categories = getCategories();
        const taxonomy = getTaxonomyMetadata();

        return res.status(200).json({
            success: true,
            message: "Complaint categories retrieved successfully.",
            data: categories,
            taxonomy: {
                registryName: taxonomy.registryName,
                version: taxonomy.version,
                registryStatus: taxonomy.registryStatus,
                totalCategories: taxonomy.totalCategories,
                approvalNotice:
                    "Categories are provisional and must not be treated as approved ground-truth labels.",
            },
        });
    } catch (error) {
        next(error);
    }
};

// PATCH: Manually assign or correct a complaint category
const updateComplaintCategory = async (req, res, next) => {
    try {
        const { complaintId } = req.params;
        const { category, reason } = req.body;

        if (
            typeof complaintId !== "string" ||
            !/^GH-[A-F0-9]{8}$/i.test(complaintId)
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid complaint ID format.",
            });
        }

        if (typeof category !== "string" || !category.trim()) {
            return res.status(400).json({
                success: false,
                message: "A valid category code is required.",
            });
        }

        if (
            reason !== undefined &&
            (typeof reason !== "string" || reason.trim().length > 500)
        ) {
            return res.status(400).json({
                success: false,
                message: "Reason must be a string of at most 500 characters.",
            });
        }

        const categoryCode = category.trim().toUpperCase();
        const categoryDefinition = getCategoryByCode(categoryCode);

        if (!categoryDefinition) {
            return res.status(400).json({
                success: false,
                message: "Unknown or non-assignable category code.",
                requestedCategory: categoryCode,
                allowedCategories: getCategories().map(
                    ({ code, name }) => ({
                        code,
                        name,
                    })
                ),
            });
        }

        const taxonomy = getTaxonomyMetadata();

        const normalizedComplaintId = complaintId.toUpperCase();

        const existingComplaint = await Complaint.findOne({
            complaintId: normalizedComplaintId,
        }).lean();

        if (!existingComplaint) {
            return res.status(404).json({
                success: false,
                message: "Complaint not found.",
            });
        }

        const previousCategory =
            existingComplaint.category || "UNCLASSIFIED";

        const updatedAt = new Date();

        const historyEntry = {
            previousCategory,
            newCategory: categoryCode,
            reviewStatus: "HUMAN_REVIEWED",
            assignmentMethod: "MANUAL",
            taxonomyVersion: String(taxonomy.version || "1.0"),
            reason: typeof reason === "string" ? reason.trim() : "",
            updatedAt,
            updatedBy: req.reviewer?.name || "UNKNOWN_REVIEWER",
        };

        const updatedComplaint = await Complaint.findOneAndUpdate(
            {
                complaintId: normalizedComplaintId,
                category: existingComplaint.category ?? null,
            },
            {
                $set: {
                    category: categoryCode,
                    categoryReviewStatus: "HUMAN_REVIEWED",
                    taxonomyVersion: String(taxonomy.version || "1.0"),
                    categoryAssignmentMethod: "MANUAL",
                },
                $push: {
                    categoryHistory: historyEntry,
                },
            },
            {
                new: true,
                runValidators: true,
            }
        ).lean();

        if (!updatedComplaint) {
            return res.status(409).json({
                success: false,
                message:
                    "Complaint category was changed by another request. Retrieve the latest complaint and try again.",
            });
        }

        return res.status(200).json({
            success: true,
            message: "Complaint category updated successfully.",
            data: {
                complaintId: updatedComplaint.complaintId,
                previousCategory,
                category: updatedComplaint.category,
                categoryName: categoryDefinition.name,
                categoryReviewStatus:
                    updatedComplaint.categoryReviewStatus,
                categoryAssignmentMethod:
                    updatedComplaint.categoryAssignmentMethod,
                taxonomyVersion: updatedComplaint.taxonomyVersion,
                categoryHistory: updatedComplaint.categoryHistory,
                updatedAt: updatedComplaint.updatedAt,
            },
            taxonomy: {
                registryStatus: taxonomy.registryStatus,
                approvalNotice:
                    "This assignment is a human-reviewed selection from a provisional taxonomy; it does not constitute taxonomy approval.",
            },
        });
    } catch (error) {
        next(error);
    }
};

// GET: Retrieve a complaint by ID
const getComplaintById = async (req, res, next) => {
    try {
        const { complaintId } = req.params;

        if (
            typeof complaintId !== "string" ||
            !/^GH-[A-F0-9]{8}$/i.test(complaintId)
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid complaint ID format.",
            });
        }

        const complaint = await Complaint.findOne({
            complaintId: complaintId.toUpperCase(),
        }).lean();

        if (!complaint) {
            return res.status(404).json({
                success: false,
                message: "Complaint not found.",
            });
        }

        return res.status(200).json({
            success: true,
            message: "Complaint retrieved successfully.",
            data: complaint,
        });
    } catch (error) {
        next(error);
    }
};

// PATCH: Update complaint status
const updateComplaintStatus = async (req, res, next) => {
    try {
        const { complaintId } = req.params;
        const { status, reason } = req.body;

        if (
            typeof complaintId !== "string" ||
            !/^GH-[A-F0-9]{8}$/i.test(complaintId)
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid complaint ID format.",
            });
        }

        if (typeof status !== "string") {
            return res.status(400).json({
                success: false,
                message: "A valid complaint status is required.",
            });
        }

        const newStatus = status.toUpperCase();

        if (!ALLOWED_STATUSES.includes(newStatus)) {
            return res.status(400).json({
                success: false,
                message: "Invalid complaint status.",
                allowedStatuses: ALLOWED_STATUSES,
            });
        }

        if (
            reason !== undefined &&
            (typeof reason !== "string" || reason.trim().length > 500)
        ) {
            return res.status(400).json({
                success: false,
                message: "Reason must be a string of at most 500 characters.",
            });
        }

        const normalizedReason =
            typeof reason === "string" ? reason.trim() : "";

        const normalizedComplaintId = complaintId.toUpperCase();

        const existingComplaint = await Complaint.findOne({
            complaintId: normalizedComplaintId,
        }).lean();

        if (!existingComplaint) {
            return res.status(404).json({
                success: false,
                message: "Complaint not found.",
            });
        }

        const previousStatus = existingComplaint.status;

        const permittedStatuses =
            ALLOWED_TRANSITIONS[previousStatus] || [];

        if (!permittedStatuses.includes(newStatus)) {
            return res.status(409).json({
                success: false,
                message: `Status transition from ${previousStatus} to ${newStatus} is not permitted.`,
                currentStatus: previousStatus,
                permittedNextStatuses: permittedStatuses,
            });
        }

        const updatedAt = new Date();

        const transitionEntry = {
            previousStatus,
            newStatus,
            reason: normalizedReason,
            updatedAt,
            updatedBy: req.reviewer?.name || "UNKNOWN_REVIEWER",
        };

        const historyUpdates = [];

        if (
            !Array.isArray(existingComplaint.statusHistory) ||
            existingComplaint.statusHistory.length === 0
        ) {
            historyUpdates.push({
                previousStatus: null,
                newStatus: previousStatus,
                reason:
                    "Initial status recorded during status-history rollout",
                updatedAt: existingComplaint.createdAt || updatedAt,
                updatedBy: "SYSTEM",
            });
        }

        historyUpdates.push(transitionEntry);

        const updatedComplaint = await Complaint.findOneAndUpdate(
            {
                complaintId: normalizedComplaintId,
                status: previousStatus,
            },
            {
                $set: {
                    status: newStatus,
                },
                $push: {
                    statusHistory: {
                        $each: historyUpdates,
                    },
                },
            },
            {
                new: true,
                runValidators: true,
            }
        ).lean();

        if (!updatedComplaint) {
            return res.status(409).json({
                success: false,
                message:
                    "Complaint status was changed by another request. Retrieve the latest complaint and try again.",
            });
        }

        return res.status(200).json({
            success: true,
            message: "Complaint status updated successfully.",
            data: {
                complaintId: updatedComplaint.complaintId,
                previousStatus,
                currentStatus: updatedComplaint.status,
                statusHistory: updatedComplaint.statusHistory,
                updatedAt: updatedComplaint.updatedAt,
            },
        });
    } catch (error) {
        next(error);
    }
};

module.exports = {
    submitComplaint,
    getComplaintById,
    getAllComplaints,
    updateComplaintStatus,
    getComplaintCategories,
    updateComplaintCategory,
    getComplaintStats,
};
