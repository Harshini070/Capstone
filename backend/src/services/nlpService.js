
const axios = require("axios");

const NLP_SERVICE_URL =
    process.env.NLP_SERVICE_URL || "http://127.0.0.1:8000";

const nlpClient = axios.create({
    baseURL: NLP_SERVICE_URL,
    timeout: 15000,
    headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
    },
});

const buildPayload = ({ recordId, title, description }) => ({
    record_id: recordId,
    telugu_title: title,
    telugu_description: description,
});

const createNlpError = (message, statusCode, publicMessage) => {
    const nlpError = new Error(message);
    // Read by errorMiddleware to choose the HTTP response.
    nlpError.statusCode = statusCode;
    nlpError.publicMessage = publicMessage;
    return nlpError;
};

const handleNlpError = (error, operation) => {
    if (error.response) {
        const upstreamStatus = error.response.status;
        const detail =
            error.response.data?.detail ||
            "NLP service rejected the request.";
        const message = `${operation}: ${
            typeof detail === "string" ? detail : JSON.stringify(detail)
        }`;

        // The NLP service rejected the complaint text itself.
        if (upstreamStatus === 422) {
            throw createNlpError(
                message,
                422,
                "The complaint text could not be processed. Please check the title and description."
            );
        }

        throw createNlpError(
            message,
            502,
            "The text-processing service returned an error. Please try again later."
        );
    }

    const reason =
        error.code === "ECONNABORTED"
            ? "request timed out."
            : "unable to connect to NLP service.";

    throw createNlpError(
        `${operation}: ${reason}`,
        503,
        "The text-processing service is temporarily unavailable. Please try again later."
    );
};

const processTeluguComplaint = async (payload) => {
    try {
        const response = await nlpClient.post(
            "/api/v1/nlp/process",
            buildPayload(payload)
        );
        return response.data;
    } catch (error) {
        handleNlpError(error, "NLP preprocessing failed");
    }
};

const classifyTeluguComplaint = async (payload) => {
    try {
        const response = await nlpClient.post(
            "/api/v1/nlp/classify",
            buildPayload(payload)
        );
        return response.data;
    } catch (error) {
        handleNlpError(error, "NLP classification failed");
    }
};

module.exports = {
    processTeluguComplaint,
    classifyTeluguComplaint,
};
