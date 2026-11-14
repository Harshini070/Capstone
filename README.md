# GrievanceHub

A modular, Telugu-first research framework and complaint-management
prototype for Hyderabad municipal grievances.

## Research objective

Develop a reproducible framework for analyzing and categorizing authentic
Telugu municipal complaints.

## Research principles

- Authentic Telugu complaints are the primary target.
- Translated and synthetic data must be labeled separately.
- Source permissions and provenance must be documented.
- Personally identifiable information must be protected.
- Raw datasets and record-level outputs must not be committed to Git.
- Model evaluation must be reproducible.

## Current status

| Phase | Status |
|---|---|
| 1–2. Source discovery, governance, corpus preparation | Complete |
| 3. Dataset quality and preprocessing | Complete |
| 4. Telugu NLP pipeline foundation | Complete |
| 5. Translation-artifact cleanup, quality and eligibility audit | In progress |

The working corpus is 15,374 Bengaluru complaints machine-translated into
Telugu. It is **not** authentic GHMC data. The Phase 5 eligibility audit
(`reports/phase5_training_eligibility_audit.json`) cleared **0** records for
model training: all records still await manual privacy review, and most
contain translation artifacts. The category taxonomy is
`PROVISIONAL_NOT_APPROVED`.

Milestone reports are in [docs/research/](docs/research/).

## Architecture

```
React (frontend/, :5173)
   │  REST
   ▼
Express + MongoDB (backend/, :5000)
   │  POST /api/v1/nlp/process   (required)
   │  POST /api/v1/nlp/classify  (best-effort)
   ▼
FastAPI NLP service (nlp-service/, :8000)
   │  imports
   ▼
src/grievancehub/nlp/   normalization, tokenization, features,
                        quality checks, provisional rule classifier
```

New complaints are stored with `category: "UNCLASSIFIED"`. The rule-based
suggestion is stored separately in `classification` and never becomes the
assigned category automatically: a reviewer must assign it.

The classifier is transparent Telugu phrase matching (longest match wins,
no double counting). It abstains when no rule matches or the evidence is
ambiguous. Rule scores are **not** probabilities, and `confidence` is always
`null`.

## Repository layout

| Path | Contents |
|---|---|
| `src/grievancehub/nlp/` | Telugu NLP library and rule classifier |
| `nlp-service/` | FastAPI wrapper around the library |
| `backend/` | Express API, MongoDB models, reviewer authentication |
| `frontend/` | React + Vite dashboard |
| `scripts/` | Reproducible research pipeline steps (phases 1–5) |
| `configs/` | Corpus config and provisional taxonomy mapping |
| `docs/` | Protocols, governance, annotation guidelines, milestones |
| `reports/` | Aggregate (non-record-level) research outputs |
| `data/` | Local only; ignored by Git |
| `tests/` | Python tests |

## Running locally

Prerequisites: Python 3.11, Node.js 20+, and a MongoDB instance (local or
Atlas).

**1. Python environment** (from the repository root)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Only for scripts/translate_telugu_queue.py:
# pip install -r requirements-translation.txt
```

**2. NLP service**

```powershell
cd nlp-service
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/docs

**3. Backend**

```powershell
cd backend
Copy-Item .env.example .env   # then set MONGODB_URI and REVIEWER_API_KEYS
npm install
npm run dev
```

**4. Frontend**

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open http://localhost:5173.

## Reviewer authentication

Changing a complaint's status or category requires a reviewer key. Set
`REVIEWER_API_KEYS` in `backend/.env` as comma-separated `name:key` pairs
(keys of at least 16 characters):

```
REVIEWER_API_KEYS=asha:<key>,ravi:<key>
```

Generate a key with
`node -e "console.log(require('crypto').randomBytes(24).toString('hex'))"`.
Reviewers enter their key in the complaint detail view. Their name is
recorded in the status and category history.

If no keys are configured, updates are allowed without authentication when
`NODE_ENV=development` (recorded as `UNAUTHENTICATED_DEV`) and refused in
production.

Reading complaints (`GET` routes) does not require authentication yet.
Restrict network access to the backend accordingly.

## Tests

```powershell
# Python (from the repository root)
python -m unittest discover -s tests -t . -v

# Backend
cd backend
npm test
```
