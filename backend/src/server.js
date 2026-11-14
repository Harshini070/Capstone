
require("dotenv").config();

const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");

const connectDatabase = require("./config/database");
const complaintRoutes = require("./routes/complaintRoutes");
const errorMiddleware = require("./middleware/errorMiddleware");

const app = express();

// Only listed browser origins may call the API (comma-separated).
const allowedOrigins = (
    process.env.CORS_ORIGINS || "http://localhost:5173"
)
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);

app.use(helmet());
app.use(cors({ origin: allowedOrigins }));
app.use(express.json({ limit: "1mb" }));
app.use(morgan("dev"));

app.get("/health", (req, res) => {
    res.status(200).json({
        service: "GrievanceHub Backend",
        status: "healthy",
        timestamp: new Date().toISOString(),
    });
});

app.use("/api/v1/complaints", complaintRoutes);

app.use(errorMiddleware);

const PORT = process.env.PORT || 5000;

const startServer = async () => {
    try {
        await connectDatabase();

        app.listen(PORT, () => {
            console.log(
                `GrievanceHub backend running on port ${PORT}`
            );
        });
    } catch (error) {
        console.error("Backend startup failed.");
        process.exit(1);
    }
};

startServer();
