// Map known error types to accurate HTTP responses. Internal details are
// logged server-side only; clients receive a safe, generic message.
const classifyError = (error) => {
    // Body-parser errors also carry a statusCode, so check them first to
    // return a specific message.
    // Malformed JSON body (raised by express.json()).
    if (error.type === "entity.parse.failed") {
        return { status: 400, message: "Request body is not valid JSON." };
    }

    if (error.type === "entity.too.large") {
        return { status: 413, message: "Request body is too large." };
    }

    // Errors raised deliberately with a status (e.g. NLP service failures).
    if (Number.isInteger(error.statusCode)) {
        return {
            status: error.statusCode,
            message:
                error.publicMessage ||
                (error.statusCode < 500
                    ? "The request could not be processed."
                    : "An internal server error occurred."),
        };
    }

    // Mongoose schema validation failures.
    if (error.name === "ValidationError") {
        return {
            status: 400,
            message: "Complaint data failed validation.",
            details: Object.values(error.errors || {}).map(
                (fieldError) => fieldError.message
            ),
        };
    }

    if (error.name === "CastError") {
        return { status: 400, message: "Invalid value in request." };
    }

    // MongoDB duplicate key.
    if (error.code === 11000) {
        return {
            status: 409,
            message: "A record with the same identifier already exists.",
        };
    }

    return { status: 500, message: "An internal server error occurred." };
};

const errorMiddleware = (error, req, res, next) => {
    if (res.headersSent) {
        return next(error);
    }

    const { status, message, details } = classifyError(error);

    if (status >= 500) {
        console.error("API Error:", error);
    } else {
        console.warn(`API Error (${status}):`, error.message);
    }

    const body = { success: false, message };

    if (details && details.length) {
        body.details = details;
    }

    return res.status(status).json(body);
};

module.exports = errorMiddleware;
module.exports.classifyError = classifyError;
