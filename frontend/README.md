# GrievanceHub Frontend

React + Vite operations dashboard for the existing GrievanceHub Express/MongoDB backend.

## Features
- Dashboard metrics and recent complaint list
- Complaint search and status/category filters
- Telugu-first complaint submission
- Complaint detail drawer with status history
- Status transition updates
- Manual category assignment with rationale
- Backend health and provisional taxonomy indicators

## Run locally
1. Start MongoDB.
2. Start the backend from `backend/` using `npm install` (first time) and `npm run dev`.
3. Confirm the backend is reachable at `http://localhost:5000/health`.
4. Open a second terminal in `frontend/`:
   ```powershell
   Copy-Item .env.example .env
   npm install
   npm run dev
   ```
5. Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

## API contract expected
- `GET /health`
- `GET /api/v1/complaints?page=1&limit=100`
- `GET /api/v1/complaints/categories`
- `POST /api/v1/complaints`
- `GET /api/v1/complaints/:complaintId`
- `PATCH /api/v1/complaints/:complaintId/status`
- `PATCH /api/v1/complaints/:complaintId/category`

Set `VITE_API_BASE_URL` in `.env` if the backend is hosted elsewhere.

## Important research/demo labels
- Taxonomy is provisional, not an approved municipal standard.
- Category changes through this interface are manual assignments, not ML predictions.
- NLP preprocessing is not a trained classifier.
- The current reconstructed corpus is Bengaluru-derived machine-translated Telugu, not authentic GHMC Telugu complaints.
