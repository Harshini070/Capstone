// Decide which browser origins may call the API.
//
// - CORS_ORIGINS set: exactly those origins (comma-separated).
// - Not set, development: localhost, 127.0.0.1 and private-network
//   addresses (so the Vite "Network" URL works from a phone on the LAN).
// - Not set, production: http://localhost:5173 only.

const PRODUCTION_DEFAULT = ["http://localhost:5173"];

const isLocalOrPrivateHost = (hostname) =>
    hostname === "localhost" ||
    hostname === "[::1]" ||
    /^127\./.test(hostname) ||
    /^10\./.test(hostname) ||
    /^192\.168\./.test(hostname) ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(hostname);

const parseOrigins = (value) =>
    String(value || "")
        .split(",")
        .map((origin) => origin.trim().replace(/\/$/, ""))
        .filter(Boolean);

const createCorsOriginCheck = ({ corsOrigins, nodeEnv } = {}) => {
    const configured = parseOrigins(corsOrigins);
    const isProduction = nodeEnv === "production";

    const isAllowed = (origin) => {
        if (configured.length) {
            return configured.includes(origin);
        }

        if (isProduction) {
            return PRODUCTION_DEFAULT.includes(origin);
        }

        try {
            const { protocol, hostname } = new URL(origin);
            return /^https?:$/.test(protocol) && isLocalOrPrivateHost(hostname);
        } catch {
            return false;
        }
    };

    // Signature expected by the cors package. Requests without an Origin
    // header (curl, server-to-server) are not browser CORS requests.
    return (origin, callback) => callback(null, !origin || isAllowed(origin));
};

module.exports = { createCorsOriginCheck };
