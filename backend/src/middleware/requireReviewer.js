const { createHash, timingSafeEqual } = require("crypto");

// Reviewer authentication for routes that change complaint records.
//
// Configure with REVIEWER_API_KEYS as a comma-separated list of
// "reviewerName:secretKey" pairs, for example:
//   REVIEWER_API_KEYS=asha:4f9c...e1,ravi:b72d...90
// Clients send "Authorization: Bearer <secretKey>". The matching reviewer
// name is attached as req.reviewer and recorded in complaint history, so
// every change is attributable to a person rather than a hardcoded label.

const MIN_KEY_LENGTH = 16;

// Hash before comparing so timingSafeEqual always sees equal-length inputs.
const digest = (value) => createHash("sha256").update(value, "utf8").digest();

const parseReviewerKeys = (rawValue) => {
    const reviewers = [];

    for (const entry of String(rawValue || "").split(",")) {
        const trimmed = entry.trim();
        if (!trimmed) continue;

        const separator = trimmed.indexOf(":");
        const name = separator > 0 ? trimmed.slice(0, separator).trim() : "";
        const key = separator > 0 ? trimmed.slice(separator + 1).trim() : "";

        if (!name || key.length < MIN_KEY_LENGTH) {
            console.warn(
                `Ignoring malformed REVIEWER_API_KEYS entry (expected name:key with a key of at least ${MIN_KEY_LENGTH} characters).`
            );
            continue;
        }

        reviewers.push({ name, keyDigest: digest(key) });
    }

    return reviewers;
};

const findReviewer = (reviewers, presentedKey) => {
    const presentedDigest = digest(presentedKey);
    let match = null;

    // Compare against every key (no early exit) to keep timing uniform.
    for (const reviewer of reviewers) {
        if (timingSafeEqual(reviewer.keyDigest, presentedDigest)) {
            match = reviewer;
        }
    }

    return match;
};

const createRequireReviewer = ({
    reviewerKeys = process.env.REVIEWER_API_KEYS,
    nodeEnv = process.env.NODE_ENV,
} = {}) => {
    const reviewers = parseReviewerKeys(reviewerKeys);
    const isProduction = nodeEnv === "production";

    if (reviewers.length === 0) {
        console.warn(
            isProduction
                ? "REVIEWER_API_KEYS is not configured: complaint updates are disabled."
                : "REVIEWER_API_KEYS is not configured: complaint updates are UNAUTHENTICATED (development mode only)."
        );
    }

    return (req, res, next) => {
        if (reviewers.length === 0) {
            if (isProduction) {
                return res.status(503).json({
                    success: false,
                    message:
                        "Reviewer authentication is not configured on this server.",
                });
            }

            req.reviewer = { name: "UNAUTHENTICATED_DEV" };
            return next();
        }

        const header = req.get("authorization") || "";
        const match = /^Bearer\s+(.+)$/i.exec(header);

        if (!match) {
            return res.status(401).json({
                success: false,
                message: "Reviewer authentication is required.",
            });
        }

        const reviewer = findReviewer(reviewers, match[1].trim());

        if (!reviewer) {
            return res.status(403).json({
                success: false,
                message: "Invalid reviewer key.",
            });
        }

        req.reviewer = { name: reviewer.name };
        return next();
    };
};

module.exports = { createRequireReviewer, parseReviewerKeys };
