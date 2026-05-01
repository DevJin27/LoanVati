# LoanVati v3.0 — Product Requirements Document
**For:** Codex (backend / ML development)  
**Companion doc:** `design.md` (Stitch UI)  
**Status:** Active — build from existing capstone codebase  
**Last updated:** May 2026

---

## 1. Context & Codebase State

LoanVati v2.0 is a working capstone project. The core ML pipeline and agent are functional. This PRD describes what to **fix, extend, and add** to turn it into a shippable product. Do not rewrite what works.

### What exists and is usable

| Module | Path | State |
|---|---|---|
| CatBoost classifier | `src/models/train.py`, `models/rf_pipeline.joblib` | Working. Keep. |
| SHAP explainer | `models/shap_explainer.joblib` | Working. Keep. |
| LangGraph 4-node agent | `src/agent/graph.py`, `nodes.py` | Working but report output is unreliable. Fix. |
| TF-IDF RAG retriever | `src/rag/retriever.py`, `embedder.py` | Working. Extend corpus. |
| FastAPI backend | `src/api/main.py`, `routes.py` | Working. Extend with new routes. |
| Streamlit frontend | `app.py`, `src/ui/` | **Replace entirely.** Do not extend. |

### What needs to be built from scratch

- Auth system (JWT)
- Applicant history / pipeline tracker (DB layer)
- "Fix It" coaching feature (feature perturbation)
- Outcome logging + self-training loop
- Billing integration (Razorpay)
- Production web frontend (handed to Stitch)

---

## 2. Immediate Fixes (Ship First)

These block quality. Fix before any new features.

### 2.1 Report Quality — LangGraph Node Hardening

**Problem:** ReportNode frequently produces malformed JSON. Root causes:
- Groq occasionally returns partial completions when context is long
- No retry or validation between nodes — a bad `RiskNode` output silently corrupts `ReportNode`
- RAG chunks are too long (~800 tokens each), consuming context budget

**Fix in `src/agent/nodes.py`:**

Each node must wrap its LLM call in a retry loop with JSON validation:

```python
import json, time

MAX_RETRIES = 3

def call_with_retry(chain, input_data, required_keys: list[str]) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            raw = chain.invoke(input_data)
            # Strip markdown fences if present
            text = raw.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            parsed = json.loads(text.strip())
            # Validate required keys exist
            missing = [k for k in required_keys if k not in parsed]
            if missing:
                raise ValueError(f"Missing keys: {missing}")
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError("All retries failed")
```

**Fix in `src/agent/prompts.py`:**

Every node system prompt must include an explicit JSON schema example. Add to each prompt:

```
CRITICAL: Respond ONLY with valid JSON. No markdown, no explanation, no preamble.
Your response must be parseable by json.loads().

Example of the exact format required:
{
  "risk_analysis": "...",
  "retrieval_query": "..."
}
```

**Fix in `src/rag/embedder.py`:**

Rechunk regulatory documents to max 300 tokens per chunk. Update `rag/metadata.json`. Overlap between chunks: 50 tokens. This prevents ReportNode from receiving wall-of-text context.

### 2.2 Model Temperature Fix

In `src/agent/nodes.py`, confirm all three LLM-using nodes have `temperature=0`. If any node is using a non-zero temperature, reports will be non-deterministic in structure.

---

## 3. RAG Corpus Expansion — CIBIL & Bureau Documents

**File to update:** `rag/metadata.json`  
**Retriever:** No changes needed — TF-IDF reindexes on startup

Add the following 6 document chunks to the corpus. Source text must be paraphrased from public RBI/CIBIL documentation (do not reproduce verbatim):

| ID | Title | Key content to cover |
|---|---|---|
| `cibil_score_guide` | CIBIL Score Ranges & Interpretation | 300–900 scale; 750+ = low risk; 650–749 = medium; below 650 = high risk; factors: repayment history (35%), credit exposure (30%), credit type mix (25%), recent inquiries (10%) |
| `cibil_ntc_guidelines` | New to Credit (NTC) Borrowers | Thin-file risk; how lenders evaluate applicants with <6 months bureau history; alternative data signals; RBI guidance on financial inclusion for NTC segments |
| `rbi_credit_info_act` | RBI Master Direction — Credit Information Companies | CIC regulation framework; permissible uses of credit data; rights of borrowers to dispute; lender obligations when using bureau reports |
| `cibil_dispute_norms` | CIBIL Dispute & Correction Process | 30-day resolution timeline; impact of disputes on lending decisions; interim lending guidance |
| `rbi_provisioning_norms` | RBI Provisioning Norms for NPAs | NPA classification (90-day default rule); standard / substandard / doubtful / loss asset categories; provisioning percentages; relevance to credit decisions |
| `rbi_digital_lending` | RBI Digital Lending Guidelines 2022 | KYC via video; digital sanction letter requirements; cooling-off period; grievance redressal for digital loans |

Each chunk in `metadata.json` should follow the existing schema:
```json
{
  "id": "cibil_score_guide",
  "title": "CIBIL score ranges and interpretation",
  "source": "TransUnion CIBIL / RBI Credit Information Framework",
  "content": "...(paraphrased, max 300 tokens)..."
}
```

After adding, run `python -c "from src.rag.embedder import build_index; build_index()"` to verify the new chunks index without error.

---

## 4. Self-Training Feedback Loop

This is the most architecturally significant new feature. Read the full spec before building any part.

### 4.1 The Selection Bias Problem

When LoanVati scores an applicant low and the DSA skips them, no outcome is ever collected. If you naively train on only the outcomes you observe, the model only learns from cases it was already confident about. Over time it becomes overconfident and stops correcting its errors.

**Mitigation — two design constraints that must be enforced:**

1. **Override logging:** When a DSA submits an applicant despite a High risk score, log this as an override event. These are the most valuable training examples — they directly test the model's confidence.

2. **Rejection reason capture:** Lender rejections must be classified as `credit_risk` or `other` at logging time. Only `credit_risk` rejections feed into training. A rejection because the lender's product doesn't match the applicant's geography is not a credit signal.

### 4.2 Database Schema

Add the following tables to the application database (PostgreSQL recommended; SQLite acceptable for early MVP).

```sql
-- Applicants screened by a DSA
CREATE TABLE applicants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dsa_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    
    -- Input features (same fields as /predict endpoint)
    income FLOAT,
    credit_amount FLOAT,
    annuity FLOAT,
    employment_years FLOAT,
    age_years FLOAT,
    family_size INT,
    education TEXT,
    income_type TEXT,
    housing_type TEXT,
    occupation TEXT,
    
    -- LoanVati output
    risk_score FLOAT,
    risk_class TEXT,  -- 'Low' | 'Uncertain' | 'High'
    model_version TEXT,  -- e.g. 'catboost_v1.2'
    shap_top_features JSONB,  -- [{feature, value, shap_value}, ...]
    
    -- DSA decision
    dsa_decision TEXT,  -- 'submitted' | 'skipped' | 'submitted_override'
    -- 'submitted_override' = DSA submitted despite High score
    
    -- Lender outcome (filled in later)
    lender_outcome TEXT,  -- 'approved' | 'rejected_credit' | 'rejected_other' | NULL
    lender_name TEXT,
    outcome_logged_at TIMESTAMP,
    
    -- Training flag
    include_in_training BOOLEAN DEFAULT FALSE
    -- Set to TRUE only when: dsa_decision IN ('submitted','submitted_override')
    -- AND lender_outcome IN ('approved','rejected_credit')
);

-- Model version registry
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT UNIQUE NOT NULL,
    trained_at TIMESTAMP DEFAULT now(),
    training_sample_count INT,
    roc_auc FLOAT,
    recall FLOAT,
    notes TEXT,
    artifact_path TEXT  -- path to .joblib file
);

-- Retraining job log
CREATE TABLE training_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_at TIMESTAMP DEFAULT now(),
    triggered_by TEXT,  -- 'schedule' | 'manual'
    new_labels_used INT,
    base_model_version TEXT,
    output_model_version TEXT,
    status TEXT  -- 'running' | 'completed' | 'failed'
);
```

### 4.3 New API Endpoints

Add to `src/api/routes.py`:

**`POST /applicants`** — Create applicant record when DSA runs a score
```json
Request: {
  "income": 150000, "credit_amount": 500000,
  ... (all input fields),
  "risk_score": 0.72, "risk_class": "High",
  "model_version": "catboost_v1.2",
  "shap_top_features": [...]
}
Response: { "applicant_id": "uuid" }
```

**`PATCH /applicants/{id}/decision`** — Log DSA's decision
```json
Request: { "decision": "submitted" | "skipped" | "submitted_override" }
```

**`PATCH /applicants/{id}/outcome`** — Log lender outcome
```json
Request: {
  "lender_outcome": "approved" | "rejected_credit" | "rejected_other",
  "lender_name": "HDFC Bank"
}
```
On receipt: set `include_in_training = TRUE` if outcome is `approved` or `rejected_credit`.

**`GET /applicants`** — Paginated list for DSA dashboard
```
Query params: ?page=1&limit=20&risk_class=High&outcome=approved
```

**`GET /applicants/{id}`** — Full applicant detail with report

**`POST /admin/retrain`** — Trigger retraining job (admin only)

### 4.4 Retraining Pipeline

Create `src/models/retrain.py`:

```python
"""
Retraining pipeline. Combines original Home Credit processed data
with new labelled applicant outcomes.

MUST be run as an offline batch job, not during a live request.
Trigger: manual admin action OR scheduled (e.g. monthly cron)
         when new_label_count >= 200
"""

def load_new_labels(db_session) -> pd.DataFrame:
    """
    Pull applicants where include_in_training=TRUE
    and not already used in a prior training run.
    Maps lender_outcome to TARGET: approved=0, rejected_credit=1
    """
    ...

def combine_with_base_data(new_labels: pd.DataFrame) -> pd.DataFrame:
    """
    Load train_processed.parquet (original 307k rows).
    Append new_labels, aligning columns.
    New labels are upweighted 3x via sample_weight to reflect
    real-world distribution (they are recent, domain-matched data).
    """
    ...

def retrain_catboost(df: pd.DataFrame, base_model_version: str) -> str:
    """
    Retrain with same hyperparameters as original.
    Evaluate on a held-out validation set (always from original data
    to avoid contamination from the selection bias).
    If new model ROC-AUC < current production model ROC-AUC - 0.02,
    REJECT the new model and log a warning. Do not auto-deploy.
    Returns new version string.
    """
    ...
```

**Critical guardrail:** The validation set used to evaluate the new model must come from the original Home Credit data only, never from the collected outcomes. This prevents the selection bias from corrupting the evaluation metric.

### 4.5 Model Versioning

When a new model is deployed, store the version string in `models/active_version.json`:
```json
{ "version": "catboost_v1.3", "deployed_at": "2026-05-15T10:00:00Z" }
```

Every `/predict` response should include `model_version` so each applicant record knows which model scored it.

---

## 5. "Fix It" Coaching Feature

**New file:** `src/models/coaching.py`

Given a scored applicant, perturb individual features and repredict to find actionable improvements.

```python
def generate_coaching_tips(
    applicant_row: dict,
    predictor: CreditRiskPredictor,
    max_tips: int = 3
) -> list[dict]:
    """
    For each SHAP-identified risk driver:
    1. Perturb the feature value toward a better range
       (e.g. reduce CREDIT_INCOME_RATIO by 10%, 20%, 30%)
    2. Repredict risk score
    3. If score improvement > 0.05, add as a coaching tip

    Only surface tips for features the applicant can actually change:
    - Actionable: credit_amount, annuity, loan term
    - Not actionable: age, gender, education (do NOT suggest these)

    Returns list of:
    {
      "feature": "credit_income_ratio",
      "current_value": 0.72,
      "suggested_value": 0.55,
      "score_improvement": 0.09,
      "human_tip": "Reducing the loan amount from ₹5L to ₹3.8L would move this applicant from High to Uncertain risk."
    }
    """
```

**New endpoint:** `POST /coaching`
```json
Request: { "applicant_id": "uuid" }
Response: { "tips": [...], "current_score": 0.72, "best_achievable_score": 0.51 }
```

The `human_tip` string is generated by calling the LLM with the perturbation data — not by the coaching function itself. Add a `CoachingNode` to the LangGraph agent or call it independently.

---

## 6. Auth & User Management

Use JWT (PyJWT). No OAuth for MVP.

**Tables:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'dsa',  -- 'dsa' | 'admin'
    created_at TIMESTAMP DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE report_quota (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    plan TEXT DEFAULT 'free',  -- 'free' | 'growth' | 'team'
    reports_used_this_month INT DEFAULT 0,
    reports_limit INT DEFAULT 10,  -- 10 for free, NULL for paid
    period_reset_at TIMESTAMP
);
```

**Endpoints:**
- `POST /auth/register`
- `POST /auth/login` → returns `{ access_token, token_type }`
- `GET /auth/me`
- All other endpoints require `Authorization: Bearer <token>` header

Quota check middleware: on each `/predict` or `/report` call, verify `reports_used_this_month < reports_limit` (null limit = unlimited).

---

## 7. Billing — Razorpay Integration

**New file:** `src/api/billing.py`

**Plans:**
| Plan | Monthly price | Report limit | Razorpay plan ID |
|---|---|---|---|
| Free | ₹0 | 10/month | — |
| Growth | ₹799 | Unlimited | `plan_growth` |
| Team | ₹1,999 | Unlimited, 5 seats | `plan_team` |
| Pay-per-report | — | +1 per purchase (₹49) | `plan_ppr` |

**Endpoints:**
- `POST /billing/create-order` — creates Razorpay order, returns `order_id`
- `POST /billing/verify-payment` — verifies Razorpay signature, upgrades plan in DB
- `GET /billing/status` — returns current plan, usage, next reset date

Razorpay credentials stored in `.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.

---

## 8. Environment Variables

`.env.example` should include:
```
GROQ_API_KEY=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
DATABASE_URL=postgresql://...
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
MODEL_VERSION=catboost_v1.2
```

---

## 9. Dependencies to Add

Add to `requirements.txt`:
```
psycopg2-binary>=2.9
sqlalchemy>=2.0
alembic>=1.13
PyJWT>=2.8
razorpay>=1.4
python-multipart>=0.0.9
```

---

## 10. Priority Order

Build in this sequence. Each phase is independently deployable.

**Phase 1 — Fix & stabilise (Week 1)**
- LangGraph retry + validation logic
- Prompt schema enforcement in all nodes
- RAG rechunking to 300 tokens
- CIBIL document additions to corpus

**Phase 2 — Database + Auth (Week 1–2)**
- PostgreSQL schema (users, applicants, quota)
- JWT auth endpoints
- Quota middleware on /predict and /report
- Applicant CRUD endpoints

**Phase 3 — Feedback loop (Week 2–3)**
- Outcome logging endpoints (PATCH /decision, PATCH /outcome)
- `include_in_training` flag logic
- `retrain.py` pipeline (offline, not triggered automatically yet)
- Admin `/admin/retrain` endpoint

**Phase 4 — Coaching (Week 3)**
- `coaching.py` feature perturbation
- `POST /coaching` endpoint
- LLM-generated `human_tip` strings

**Phase 5 — Billing (Week 4)**
- Razorpay integration
- Plan upgrade/downgrade
- Quota reset cron job (monthly)

---

## 11. What Not to Build

- Do not build a new frontend — that is Stitch's job. Expose clean JSON APIs only.
- Do not integrate real CIBIL/Experian bureau APIs — use manual input for MVP.
- Do not implement true online learning (incremental CatBoost updates) — batch retraining only.
- Do not build multi-lender matching — defer post-revenue.
- Do not add SMOTE/ADASYN — `auto_class_weights='Balanced'` is sufficient.

---

## 12. Testing Requirements

Each new module must have a corresponding test file in `tests/`:

- `tests/test_agent_retry.py` — verify ReportNode recovers from malformed LLM output
- `tests/test_coaching.py` — verify perturbation produces valid tip structure
- `tests/test_outcome_logging.py` — verify `include_in_training` flag logic (credit rejection → TRUE, other rejection → FALSE)
- `tests/test_retrain_guardrail.py` — verify retraining rejects a model that degrades more than 0.02 AUC

---

*LoanVati v3.0 PRD — generated May 2026*
