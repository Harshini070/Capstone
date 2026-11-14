const test = require("node:test");
const assert = require("node:assert/strict");

const { createCorsOriginCheck } = require("../src/config/cors");

const allows = (check, origin) => {
    let result;
    check(origin, (error, allowed) => {
        assert.equal(error, null);
        result = allowed;
    });
    return result;
};

test("development default allows local and private-network origins", () => {
    const check = createCorsOriginCheck({ nodeEnv: "development" });
    assert.equal(allows(check, "http://localhost:5173"), true);
    assert.equal(allows(check, "http://127.0.0.1:5173"), true);
    assert.equal(allows(check, "http://192.168.1.20:5173"), true);
    assert.equal(allows(check, "http://172.20.0.5:5173"), true);
    assert.equal(allows(check, "https://evil.example"), false);
    assert.equal(allows(check, "http://172.32.0.1:5173"), false);
});

test("production default allows only localhost:5173", () => {
    const check = createCorsOriginCheck({ nodeEnv: "production" });
    assert.equal(allows(check, "http://localhost:5173"), true);
    assert.equal(allows(check, "http://192.168.1.20:5173"), false);
});

test("CORS_ORIGINS overrides defaults exactly", () => {
    const check = createCorsOriginCheck({
        corsOrigins: "https://grievancehub.example/, http://localhost:4000",
        nodeEnv: "development",
    });
    assert.equal(allows(check, "https://grievancehub.example"), true);
    assert.equal(allows(check, "http://localhost:4000"), true);
    assert.equal(allows(check, "http://localhost:5173"), false);
});

test("requests without an Origin header are allowed", () => {
    const check = createCorsOriginCheck({ nodeEnv: "production" });
    assert.equal(allows(check, undefined), true);
});
