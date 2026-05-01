# LoanVati Phase 3

Phase 3 is a self-contained MVP product app:

- `backend/` - FastAPI, PostgreSQL, JWT auth, applicant pipeline APIs, ML/report integration.
- `frontend/` - Vite React app converted from the Stitch prototype and wired to real APIs.
- `LV-MD/` - source PRD/design/prototype references.

## Backend

```bash
cd phase-3/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set `DATABASE_URL`, `JWT_SECRET`, and optionally `GROQ_API_KEY` in `.env`.

Run migrations:

```bash
DATABASE_URL=postgresql://loanvati:loanvati@localhost:5432/loanvati alembic upgrade head
```

Start FastAPI:

```bash
DATABASE_URL=postgresql://loanvati:loanvati@localhost:5432/loanvati \
JWT_SECRET=change-me \
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd phase-3/frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

Open `http://localhost:5173`.

## Verification

```bash
cd phase-3/backend
DATABASE_URL=postgresql://loanvati:loanvati@localhost:5432/loanvati_test \
JWT_SECRET=test-secret \
python -m pytest tests/test_phase3_product_logic.py

cd ../frontend
npm test
npm run build
```
