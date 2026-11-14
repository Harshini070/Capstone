import React, { useEffect, useMemo, useState } from "react";
import { api, getReviewerKey, setReviewerKey } from "./services/api";

const STATUS_OPTIONS = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "IN_PROGRESS",
  "RESOLVED",
  "REJECTED",
];

const STATUS_LABELS = {
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Under review",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
  REJECTED: "Rejected",
};

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getPrediction(complaint) {
  return complaint?.classification?.predictedCategory || "Not available";
}

function getCategoryName(category) {
  if (typeof category === "string") return category;

  return category?.name || category?.category || category?.id || "";
}

// The backend only accepts category codes (e.g. SOLID_WASTE), not names.
function getCategoryCode(category) {
  if (typeof category === "string") return category;

  return category?.code || "";
}

function StatusBadge({ status }) {
  const value = status || "SUBMITTED";

  return (
    <span className={`status-badge ${value.toLowerCase()}`}>
      {STATUS_LABELS[value] || value}
    </span>
  );
}

function MetricCard({ title, value, description }) {
  return (
    <div className="metric-card">
      <p>{title}</p>
      <h2>{value}</h2>
      <span>{description}</span>
    </div>
  );
}

function SectionHeading({ title, description, action }) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      {action}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("dashboard");

  const [complaints, setComplaints] = useState([]);
  const [categories, setCategories] = useState([]);
  const [statusCounts, setStatusCounts] = useState(null);
  const [reviewerKey, setReviewerKeyState] = useState(getReviewerKey);
  const [selected, setSelected] = useState(null);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);

  const [backendStatus, setBackendStatus] = useState("Checking");

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [form, setForm] = useState({
    title: "",
    description: "",
  });

  const [newComplaint, setNewComplaint] = useState(null);

  const [statusDraft, setStatusDraft] = useState("");
  const [statusReason, setStatusReason] = useState("");

  const [categoryDraft, setCategoryDraft] = useState("");
  const [categoryReason, setCategoryReason] = useState("");

  // Load complaints, categories and backend health
  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [
        complaintResponse,
        categoryResponse,
        healthResponse,
      ] = await Promise.all([
        api.getComplaints(),
        api.getCategories(),
        api.health(),
      ]);

      setComplaints(complaintResponse.data || []);
      setCategories(categoryResponse.data || []);

      setBackendStatus(healthResponse.status || "Online");
    } catch (err) {
      setError(err.message);
      setBackendStatus("Offline");
    } finally {
      setLoading(false);
    }

    // Totals across all complaints, not just the 100 loaded for the list.
    // Optional: an older backend without /stats falls back to local counts.
    try {
      const statsResponse = await api.getStats();
      setStatusCounts(statsResponse.data || null);
    } catch {
      setStatusCounts(null);
    }
  }

  function handleReviewerKeyChange(value) {
    setReviewerKeyState(value);
    setReviewerKey(value.trim());
  }

  useEffect(() => {
    loadData();
  }, []);

  // Search and filter complaints
  const filteredComplaints = useMemo(() => {
    return complaints.filter((complaint) => {
      const query = search.trim().toLowerCase();

      const matchesSearch =
        !query ||
        [
          complaint.complaintId,
          complaint.title,
          complaint.category,
          complaint.status,
          getPrediction(complaint),
        ].some((value) =>
          String(value || "").toLowerCase().includes(query)
        );

      const matchesStatus =
        statusFilter === "ALL" ||
        complaint.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [complaints, search, statusFilter]);

  // Dashboard statistics
  const stats = useMemo(() => {
    if (statusCounts?.byStatus) {
      const counts = statusCounts.byStatus;

      return {
        total: statusCounts.total ?? 0,
        submitted: counts.SUBMITTED ?? 0,
        active: (counts.UNDER_REVIEW ?? 0) + (counts.IN_PROGRESS ?? 0),
        resolved: counts.RESOLVED ?? 0,
      };
    }

    return {
      total: complaints.length,

      submitted: complaints.filter(
        (item) => item.status === "SUBMITTED"
      ).length,

      active: complaints.filter(
        (item) =>
          item.status === "UNDER_REVIEW" ||
          item.status === "IN_PROGRESS"
      ).length,

      resolved: complaints.filter(
        (item) => item.status === "RESOLVED"
      ).length,
    };
  }, [complaints, statusCounts]);

  // Open complaint details
  async function openComplaint(id) {
    setDetailLoading(true);
    setSelected(null);
    setMessage("");

    try {
      const response = await api.getComplaint(id);
      const complaint = response.data;

      setSelected(complaint);

      setStatusDraft(complaint.status || "SUBMITTED");
      setCategoryDraft(complaint.category || "");

      setStatusReason("");
      setCategoryReason("");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setDetailLoading(false);
    }
  }

  // Submit a new complaint
  async function handleSubmit(event) {
    event.preventDefault();

    if (!form.title.trim() || !form.description.trim()) {
      setError("Please enter both the title and description.");
      return;
    }

    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await api.submitComplaint({
        title: form.title.trim(),
        description: form.description.trim(),
      });

      setNewComplaint(response.data);

      setForm({
        title: "",
        description: "",
      });

      setPage("success");

      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  // Update complaint status
  async function handleStatusUpdate() {
    if (!selected || !statusDraft) return;

    setSaving(true);
    setMessage("");

    try {
      await api.updateStatus(selected.complaintId, {
        status: statusDraft,
        reason: statusReason,
      });

      setMessage("Complaint status updated.");

      await openComplaint(selected.complaintId);
      await loadData();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Assign complaint category
  async function handleCategoryUpdate() {
    if (!selected || !categoryDraft) return;

    setSaving(true);
    setMessage("");

    try {
      await api.updateCategory(selected.complaintId, {
        category: categoryDraft,
        reason:
          categoryReason ||
          "Category assigned through the GrievanceHub dashboard.",
      });

      setMessage("Category assignment updated.");

      await openComplaint(selected.complaintId);
      await loadData();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Navigation
  function navigate(nextPage) {
    setPage(nextPage);
    setError("");
    setMessage("");
    setSelected(null);
  }

  return (
    <div className="app">

      {/* HEADER */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-logo">G</div>

          <div>
            <h1>GrievanceHub</h1>
            <p>Municipal Complaint Management</p>
          </div>
        </div>

        <div className="connection">
          <span
            className={`connection-dot ${
              backendStatus === "Offline" ? "offline" : ""
            }`}
          />

          Backend: {backendStatus}
        </div>
      </header>

      <div className="layout">

        {/* SIDEBAR */}

        <aside className="sidebar">
          <p className="sidebar-label">MENU</p>

          <button
            className={
              page === "dashboard"
                ? "nav-button active"
                : "nav-button"
            }
            onClick={() => navigate("dashboard")}
          >
            <span>▦</span>
            Dashboard
          </button>

          <button
            className={
              page === "complaints"
                ? "nav-button active"
                : "nav-button"
            }
            onClick={() => navigate("complaints")}
          >
            <span>☷</span>
            Complaints
          </button>

          <button
            className={
              page === "submit"
                ? "nav-button active"
                : "nav-button"
            }
            onClick={() => navigate("submit")}
          >
            <span>＋</span>
            Submit complaint
          </button>

          <div className="sidebar-note">
            <strong>GrievanceHub</strong>

            <p>
              A modular AI framework for Telugu municipal
              complaint management.
            </p>
          </div>
        </aside>

        {/* MAIN CONTENT */}

        <main className="main-content">

          {error && (
            <div className="alert error-alert">
              {error}

              <button onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}

          {message && (
            <div className="alert success-alert">
              {message}

              <button onClick={() => setMessage("")}>
                ×
              </button>
            </div>
          )}

          {/* DASHBOARD */}

          {page === "dashboard" && (
            <>
              <SectionHeading
                title="Dashboard"
                description="Overview of municipal complaints and their current status."
                action={
                  <button
                    className="secondary-button"
                    onClick={loadData}
                  >
                    Refresh
                  </button>
                }
              />

              <div className="metric-grid">
                <MetricCard
                  title="Total complaints"
                  value={stats.total}
                  description="All registered complaints"
                />

                <MetricCard
                  title="Submitted"
                  value={stats.submitted}
                  description="Awaiting review"
                />

                <MetricCard
                  title="Active complaints"
                  value={stats.active}
                  description="Under review or in progress"
                />

                <MetricCard
                  title="Resolved"
                  value={stats.resolved}
                  description="Marked as resolved"
                />
              </div>

              <section className="panel">
                <SectionHeading
                  title="Recent complaints"
                  description="Latest complaint records."
                  action={
                    <button
                      className="text-button"
                      onClick={() => navigate("complaints")}
                    >
                      View all
                    </button>
                  }
                />

                <ComplaintTable
                  rows={complaints.slice(0, 5)}
                  loading={loading}
                  onOpen={openComplaint}
                />
              </section>

              <section className="panel">
                <SectionHeading
                  title="Registered categories"
                  description="Categories provided by the backend taxonomy registry."
                />

                <div className="category-list">
                  {categories.length === 0 ? (
                    <p className="muted">
                      No categories available.
                    </p>
                  ) : (
                    categories.map((item, index) => (
                      <span
                        className="category-chip"
                        key={index}
                      >
                        {getCategoryName(item)}
                      </span>
                    ))
                  )}
                </div>
              </section>
            </>
          )}

          {/* COMPLAINT LIST */}

          {page === "complaints" && (
            <>
              <SectionHeading
                title="Complaints"
                description="Search and review submitted municipal complaints."
                action={
                  <button
                    className="primary-button"
                    onClick={() => navigate("submit")}
                  >
                    + New complaint
                  </button>
                }
              />

              <section className="panel">
                <div className="toolbar">
                  <input
                    className="search-input"
                    placeholder="Search by ID, title or category..."
                    value={search}
                    onChange={(event) =>
                      setSearch(event.target.value)
                    }
                  />

                  <select
                    value={statusFilter}
                    onChange={(event) =>
                      setStatusFilter(event.target.value)
                    }
                  >
                    <option value="ALL">All statuses</option>

                    {STATUS_OPTIONS.map((status) => (
                      <option key={status} value={status}>
                        {STATUS_LABELS[status]}
                      </option>
                    ))}
                  </select>
                </div>

                <ComplaintTable
                  rows={filteredComplaints}
                  loading={loading}
                  onOpen={openComplaint}
                />
              </section>
            </>
          )}

          {/* SIMPLE CITIZEN SUBMISSION FORM */}

          {page === "submit" && (
            <>
              <SectionHeading
                title="Submit a Complaint"
                description="Please provide the details of your complaint."
              />

              <section className="panel form-panel">
                <form onSubmit={handleSubmit}>

                  <label>
                    Complaint Title

                    <input
                      type="text"
                      placeholder="Enter complaint title"
                      value={form.title}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          title: event.target.value,
                        })
                      }
                      required
                    />
                  </label>

                  <label>
                    Complaint Description

                    <textarea
                      rows="6"
                      placeholder="Describe your issue here..."
                      value={form.description}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          description: event.target.value,
                        })
                      }
                      required
                    />
                  </label>

                  <button
                    className="primary-button"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting
                      ? "Submitting..."
                      : "Submit Complaint"}
                  </button>

                </form>
              </section>
            </>
          )}

          {/* SUBMISSION SUCCESS */}

          {page === "success" && newComplaint && (
            <section className="panel success-panel">

              <div className="success-icon">✓</div>

              <h2>Complaint submitted</h2>

              <p>Your complaint has been received.</p>

              <div className="reference-box">
                <span>COMPLAINT REFERENCE</span>

                <strong>
                  {newComplaint.complaintId || "Created"}
                </strong>
              </div>

              <PredictionDetails
                complaint={newComplaint}
              />

              <div className="button-row">
                <button
                  className="primary-button"
                  onClick={() => navigate("complaints")}
                >
                  View complaints
                </button>

                <button
                  className="secondary-button"
                  onClick={() => navigate("submit")}
                >
                  Submit another
                </button>
              </div>
            </section>
          )}

          {loading && page === "dashboard" && (
            <p className="loading-message">
              Loading dashboard data...
            </p>
          )}

          <footer className="footer">
            GrievanceHub · Telugu Municipal Complaint Management
          </footer>

        </main>
      </div>

      {/* DETAIL LOADING */}

      {detailLoading && (
        <div className="modal-backdrop">
          <div className="modal">
            Loading complaint details...
          </div>
        </div>
      )}

      {/* COMPLAINT DETAILS */}

      {selected && (
        <div
          className="modal-backdrop"
          onClick={() => setSelected(null)}
        >
          <section
            className="detail-modal"
            onClick={(event) => event.stopPropagation()}
          >

            <div className="modal-header">
              <div>
                <span className="muted">
                  COMPLAINT DETAILS
                </span>

                <h2>{selected.complaintId}</h2>
              </div>

              <button
                className="close-button"
                onClick={() => setSelected(null)}
              >
                ×
              </button>
            </div>

            <div className="detail-content">

              <h3>{selected.title}</h3>

              <p className="description">
                {selected.description}
              </p>

              <div className="detail-grid">

                <div>
                  <span>Assigned category</span>

                  <strong>
                    {selected.category || "UNCLASSIFIED"}
                  </strong>
                </div>

                <div>
                  <span>Status</span>

                  <StatusBadge status={selected.status} />
                </div>

                <div>
                  <span>Language</span>

                  <strong>
                    {selected.language || "Not specified"}
                  </strong>
                </div>

                <div>
                  <span>Created</span>

                  <strong>
                    {formatDate(selected.createdAt)}
                  </strong>
                </div>

              </div>

              {/* AI CLASSIFICATION */}

              <PredictionDetails complaint={selected} />

              {/* REVIEWER KEY */}

              <div className="detail-section">
                <h3>Reviewer key</h3>

                <input
                  type="password"
                  autoComplete="off"
                  placeholder="Required to update status or category"
                  value={reviewerKey}
                  onChange={(event) =>
                    handleReviewerKeyChange(event.target.value)
                  }
                />

                <p className="muted">
                  Kept only for this browser tab. Your reviewer name is
                  recorded with each change.
                </p>
              </div>

              {/* STATUS UPDATE */}

              <div className="detail-section">
                <h3>Update status</h3>

                <select
                  value={statusDraft}
                  onChange={(event) =>
                    setStatusDraft(event.target.value)
                  }
                >
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_LABELS[status]}
                    </option>
                  ))}
                </select>

                <textarea
                  rows="2"
                  placeholder="Reason for status update (optional)"
                  value={statusReason}
                  onChange={(event) =>
                    setStatusReason(event.target.value)
                  }
                />

                <button
                  className="primary-button"
                  onClick={handleStatusUpdate}
                  disabled={saving || statusDraft === selected.status}
                >
                  {saving ? "Saving..." : "Save status"}
                </button>
              </div>

              {/* CATEGORY ASSIGNMENT */}

              <div className="detail-section">
                <h3>Assign category</h3>

                <select
                  value={categoryDraft}
                  onChange={(event) =>
                    setCategoryDraft(event.target.value)
                  }
                >
                  <option value="">
                    Select a category
                  </option>

                  {categories.map((item) => {
                    const code = getCategoryCode(item);

                    return (
                      <option key={code} value={code}>
                        {getCategoryName(item)}
                      </option>
                    );
                  })}
                </select>

                <textarea
                  rows="2"
                  placeholder="Reason for category assignment (optional)"
                  value={categoryReason}
                  onChange={(event) =>
                    setCategoryReason(event.target.value)
                  }
                />

                <button
                  className="primary-button"
                  onClick={handleCategoryUpdate}
                  disabled={saving || !categoryDraft}
                >
                  {saving ? "Saving..." : "Save category"}
                </button>
              </div>

            </div>
          </section>
        </div>
      )}

    </div>
  );
}

// COMPLAINT TABLE

function ComplaintTable({ rows, loading, onOpen }) {
  if (loading) {
    return (
      <p className="loading-message">
        Loading complaints...
      </p>
    );
  }

  if (!rows.length) {
    return (
      <div className="empty-state">
        No complaints found.
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table>

        <thead>
          <tr>
            <th>Reference</th>
            <th>Complaint</th>
            <th>Assigned category</th>
            <th>AI prediction</th>
            <th>Status</th>
            <th>Date</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((complaint) => (
            <tr
              key={complaint._id || complaint.complaintId}
              onClick={() =>
                onOpen(complaint.complaintId)
              }
            >
              <td className="reference-cell">
                {complaint.complaintId}
              </td>

              <td className="title-cell">
                {complaint.title}
              </td>

              <td>
                {complaint.category || "UNCLASSIFIED"}
              </td>

              <td>
                {getPrediction(complaint)}
              </td>

              <td>
                <StatusBadge status={complaint.status} />
              </td>

              <td>
                {formatDate(complaint.createdAt)}
              </td>
            </tr>
          ))}
        </tbody>

      </table>
    </div>
  );
}

// AI CLASSIFICATION DETAILS

function PredictionDetails({ complaint }) {
  const prediction = complaint?.classification;

  if (!prediction) {
    return (
      <div className="prediction-box">
        <h3>AI Classification</h3>
        <p>No category prediction available.</p>
      </div>
    );
  }

  return (
    <div className="prediction-box">
      <div className="prediction-heading">
        <h3>AI Classification</h3>
        <span className="provisional-label">
          Provisional
        </span>
      </div>

      <div className="prediction-main">
        <span>Suggested category</span>
        <strong>
          {prediction.predictedCategory || "UNCLASSIFIED"}
        </strong>
      </div>

      <p className="prediction-warning">
        This category is automatically suggested and is subject
        to administrative review.
      </p>
    </div>
  );
}