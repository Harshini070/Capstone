const test = require("node:test");
const assert = require("node:assert/strict");

const {
    createRequireReviewer,
    parseReviewerKeys,
} = require("../src/middleware/requireReviewer");
const errorMiddleware = require("../src/middleware/errorMiddleware");
const { classifyError } = errorMiddleware;

const KEY_A = "a".repeat(32);
const KEY_B = "b".repeat(32);

// Minimal Express req/res doubles.
const makeReq = (authorization) => ({
    get: (name) =>
        name.toLowerCase() === "authorization" ? authorization : undefined,
});

const makeRes = () => {
    const res = { statusCode: 200, body: undefined, headersSent: false };
    res.status = (code) => {
        res.statusCode = code;
        return res;
    };
    res.json = (body) => {
        res.body = body;
        return res;
    };
    return res;
};

const run = (middleware, req) => {
    const res = makeRes();
    let nextCalled = false;
    middleware(req, res, () => {
        nextCalled = true;
    });
    return { res, nextCalled };
};

// Silence configuration warnings during tests.
test.beforeEach(() => {
    test.mock.method(console, "warn", () => {});
});
test.afterEach(() => test.mock.restoreAll());

test("parseReviewerKeys skips malformed and short entries", () => {
    const reviewers = parseReviewerKeys(
        `asha:${KEY_A}, nokey, ravi:short, :${KEY_B}`
    );
    assert.deepEqual(
        reviewers.map((r) => r.name),
        ["asha"]
    );
});

test("valid key attaches the matching reviewer name", () => {
    const mw = createRequireReviewer({
        reviewerKeys: `asha:${KEY_A},ravi:${KEY_B}`,
        nodeEnv: "production",
    });
    const req = makeReq(`Bearer ${KEY_B}`);
    const { nextCalled } = run(mw, req);
    assert.equal(nextCalled, true);
    assert.equal(req.reviewer.name, "ravi");
});

test("missing Authorization header returns 401", () => {
    const mw = createRequireReviewer({ reviewerKeys: `asha:${KEY_A}` });
    const { res, nextCalled } = run(mw, makeReq(undefined));
    assert.equal(nextCalled, false);
    assert.equal(res.statusCode, 401);
});

test("wrong key returns 403", () => {
    const mw = createRequireReviewer({ reviewerKeys: `asha:${KEY_A}` });
    const { res, nextCalled } = run(mw, makeReq(`Bearer ${KEY_B}`));
    assert.equal(nextCalled, false);
    assert.equal(res.statusCode, 403);
});

test("no keys configured: allowed in development, refused in production", () => {
    const dev = createRequireReviewer({ reviewerKeys: "", nodeEnv: "development" });
    const devReq = makeReq(undefined);
    assert.equal(run(dev, devReq).nextCalled, true);
    assert.equal(devReq.reviewer.name, "UNAUTHENTICATED_DEV");

    const prod = createRequireReviewer({ reviewerKeys: "", nodeEnv: "production" });
    const { res, nextCalled } = run(prod, makeReq(undefined));
    assert.equal(nextCalled, false);
    assert.equal(res.statusCode, 503);
});

test("classifyError maps known error types to status codes", () => {
    const nlpDown = Object.assign(new Error("connect ECONNREFUSED"), {
        statusCode: 503,
        publicMessage: "unavailable",
    });
    assert.deepEqual(classifyError(nlpDown), {
        status: 503,
        message: "unavailable",
    });

    const validation = Object.assign(new Error("bad"), {
        name: "ValidationError",
        errors: { title: { message: "Path `title` is required." } },
    });
    assert.equal(classifyError(validation).status, 400);
    assert.deepEqual(classifyError(validation).details, [
        "Path `title` is required.",
    ]);

    assert.equal(classifyError({ code: 11000 }).status, 409);
    // express.json() errors carry statusCode too; the specific message wins.
    assert.deepEqual(
        classifyError({ type: "entity.parse.failed", statusCode: 400 }),
        { status: 400, message: "Request body is not valid JSON." }
    );
    assert.equal(classifyError(new Error("boom")).status, 500);
});

test("errorMiddleware never exposes internal error messages", () => {
    test.mock.method(console, "error", () => {});
    const res = makeRes();
    errorMiddleware(new Error("secret connection string"), {}, res, () => {});
    assert.equal(res.statusCode, 500);
    assert.equal(res.body.message, "An internal server error occurred.");
    assert.doesNotMatch(JSON.stringify(res.body), /secret/);
});
