
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000"
).replace(/\/$/, "");

// Reviewer key for status/category updates. Kept in sessionStorage so it
// is cleared when the tab closes and is never built into the bundle.
const REVIEWER_KEY_STORAGE = "grievancehub.reviewerKey";

export function getReviewerKey() {
  try {
    return sessionStorage.getItem(REVIEWER_KEY_STORAGE) || "";
  } catch {
    return "";
  }
}

export function setReviewerKey(key) {
  try {
    if (key) {
      sessionStorage.setItem(REVIEWER_KEY_STORAGE, key);
    } else {
      sessionStorage.removeItem(REVIEWER_KEY_STORAGE);
    }
  } catch {
    // Storage unavailable (private mode); key lasts for this page only.
  }
}

function reviewerHeaders() {
  const key = getReviewerKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const result = await response.json().catch(() => ({}));

  if (!response.ok || result.success === false) {
    throw new Error(
      result.message || `Request failed with status ${response.status}`
    );
  }

  return result;
}

export const api = {
  health: () => request("/health"),

  getComplaints: (page = 1, limit = 100) =>
    request(`/api/v1/complaints?page=${page}&limit=${limit}`),

  getCategories: () =>
    request("/api/v1/complaints/categories"),

  getStats: () =>
    request("/api/v1/complaints/stats"),

  getComplaint: (id) =>
    request(`/api/v1/complaints/${encodeURIComponent(id)}`),

  submitComplaint: (data) =>
    request("/api/v1/complaints", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateStatus: (id, data) =>
    request(`/api/v1/complaints/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      headers: reviewerHeaders(),
      body: JSON.stringify(data),
    }),

  updateCategory: (id, data) =>
    request(`/api/v1/complaints/${encodeURIComponent(id)}/category`, {
      method: "PATCH",
      headers: reviewerHeaders(),
      body: JSON.stringify(data),
    }),
};
