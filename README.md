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
| 5. AI-assisted corpus review | Gate 2 complete (engineering, S1–S3 run); Gate 3 (AI review) not started |
| ML training (Part F) | Not started; needs separate approval |

The working corpus is **a translated experimental corpus derived from
Bengaluru/BBMP municipal complaint data**: 15,374 records machine-translated
into Telugu. It is **not** authentic Hyderabad/GHMC citizen complaint data.
Under the historical audit policy, 0 records are cleared for model training.
The category taxonomy is `PROVISIONAL_NOT_APPROVED`.

Milestone reports are in [docs/research/](docs/research/). The running log of
every major step and decision is
[GrievanceHub_Phase5_Development_Log.md](docs/research/GrievanceHub_Phase5_Development_Log.md).

## Phase 5: AI-assisted corpus review

**Disclosure:** corpus review in Phase 5 is done by an AI model
(`review_method = AI_ASSISTED`). There is no human annotation. Two AI passes
measure self-consistency only, not ground truth. The protocol is in
[GrievanceHub_Phase5_AI_Review_Protocol.md](docs/research/GrievanceHub_Phase5_AI_Review_Protocol.md).

| Stage | Script | Output (record-level outputs are Git-ignored) |
|---|---|---|
| S1 Rebuild review sample | `scripts/phase5_build_review_sample_v2.py` | `data/interim/review/phase5_review_sample_v2.csv` |
| S2 Automated screens | `scripts/phase5_corpus_screens.py` | `corpus_screens.csv`, `reports/phase5_review/screens_summary.json` |
| S3 Label-noise detection | `scripts/phase5_label_noise_detection.py` | `label_noise_flags.csv`, `label_noise_summary.json`, `mapping_concentration.csv` |
| S4–S6 Review batches | `scripts/phase5_review_batches.py` | `review_queue.csv`, batch files, `review_pass1.csv`, `review_pass2.csv` |
| S7 Consistency | `scripts/phase5_review_consistency.py` | `review_final.csv`, `consistency_report.json` |
| S8 Eligibility, dataset v3 | `scripts/phase5_apply_review_decisions.py` | `data/processed/translated_bengaluru_reviewed_v3.csv`, `eligibility_summary.json` |
| S9 Statistics | `scripts/phase5_review_statistics.py validate` / `estimate` | `statistics_validation.json`, `population_estimates.csv` |

Eligibility audit: `python scripts/phase5_training_eligibility_audit.py`
(historical default policy, unchanged) or `--policy ai_assisted_v1` (reads
dataset v3).

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
