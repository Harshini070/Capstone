
const express = require("express");

const {
    submitComplaint,
    getComplaintById,
    getAllComplaints,
    updateComplaintStatus,
    getComplaintCategories,
    updateComplaintCategory,
    getComplaintStats,
} = require("../controllers/complaintController");
const { createRequireReviewer } = require("../middleware/requireReviewer");

const router = express.Router();
const requireReviewer = createRequireReviewer();

// Static paths must come before /:complaintId
router.get("/categories", getComplaintCategories);
router.get("/stats", getComplaintStats);

// Complaint collection
router.get("/", getAllComplaints);
router.post("/", submitComplaint);

// Manual category assignment (reviewers only)
router.patch(
    "/:complaintId/category",
    requireReviewer,
    updateComplaintCategory
);

// Complaint status update (reviewers only)
router.patch(
    "/:complaintId/status",
    requireReviewer,
    updateComplaintStatus
);

// Retrieve individual complaint
router.get("/:complaintId", getComplaintById);

module.exports = router;
