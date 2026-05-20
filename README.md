# LoanVati

**AI-native lending intelligence for faster, explainable credit decisions.**

[![Product Hunt](https://img.shields.io/badge/Product%20Hunt-LoanVati-DA552F?logo=producthunt)](https://www.producthunt.com/products/loanvati)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://react.dev)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()

[**Live Demo**](https://www.producthunt.com/products/loanvati) · [**Product Hunt**](https://www.producthunt.com/products/loanvati) · [**Documentation**](#getting-started)

---

## Why LoanVati

Traditional lending workflows force teams to choose between:

| Challenge | Typical Trade-off |
|-----------|------------------|
| Accurate risk models | Black-box predictions |
| Explainability | Slower decisions |
| Compliance | Manual regulatory checks |
| Speed | Sacrificed accuracy |

**LoanVati combines all four.**

```
Applicant Input → Risk Engine → Explainability → Regulatory Context → Decision Support
```

---

## What LoanVati Does

| Capability | Description |
|------------|-------------|
| **Risk Scoring** | Predict borrower risk with production-grade credit models |
| **Explainable Decisions** | Show why each decision happens using SHAP attribution |
| **AI Lending Reports** | Generate analyst-style summaries on demand |
| **Regulatory Grounding** | RAG layer referencing RBI and Basel guidelines |
| **Workflow Management** | Track applications across the full lending pipeline |

---

## Platform Capabilities

### Decision Intelligence
Real-time ML inference, confidence intervals, and threshold-based routing for automated and semi-automated credit decisions.

### Explainability
Per-prediction SHAP values with feature attribution ranked by impact. Every decision produces a human-readable rationale suitable for audit.

### Compliance Layer
Retrieval-augmented generation over RBI and Basel III/IV reference documents. Decisions are grounded in policy text, not just model outputs.

### Operational Infrastructure
Async FastAPI backend, structured logging, application state management, and a React dashboard for analyst workflows.

---

## Under the Hood

### Model Stack

Trained and evaluated four models, with CatBoost selected for production:

| Model | Role |
|-------|------|
| Logistic Regression | Baseline |
| Random Forest | Ensemble benchmark |
| LightGBM | Gradient boosting candidate |
| **CatBoost** | **Production — best AUC/F1 on holdout** |

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│   React UI  │────▶│                  FastAPI                      │
│  Dashboard  │     │  ┌─────────────┐  ┌──────────┐  ┌─────────┐ │
└─────────────┘     │  │  CatBoost   │  │   SHAP   │  │   RAG   │ │
                    │  │  Inference  │  │ Explainer│  │  Layer  │ │
                    │  └─────────────┘  └──────────┘  └─────────┘ │
                    │         │                              │      │
                    │  ┌──────▼──────────────────────────────▼───┐ │
                    │  │        PostgreSQL + Vector Store         │ │
                    │  └──────────────────────────────────────────┘ │
                    └──────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **ML** | CatBoost, LightGBM, scikit-learn, SHAP |
| **API** | FastAPI, Pydantic, Uvicorn |
| **Frontend** | React 18, Vite, Tailwind CSS |
| **RAG** | LangChain, FAISS, OpenAI Embeddings |
| **Database** | PostgreSQL, SQLAlchemy, Alembic |
| **Infrastructure** | Docker, GitHub Actions, pytest |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment

```bash
cp .env.example .env
```

Key variables:

```env
DATABASE_URL=postgresql://user:password@localhost/loanvati
OPENAI_API_KEY=sk-...
SECRET_KEY=your-secret-key
```

### Run with Docker

```bash
docker-compose up --build
```

---

## Repository Structure

```
loanvati/
├── backend/
│   ├── main.py               # FastAPI entrypoint
│   ├── models/               # CatBoost + training scripts
│   ├── explainability/       # SHAP integration
│   ├── rag/                  # RBI/Basel document retrieval
│   └── api/                  # Route handlers
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── pages/            # Dashboard, application views
│   │   └── services/         # API client
│   └── public/
├── data/                     # Sample datasets (anonymized)
├── notebooks/                # Model training and evaluation
├── docker-compose.yml
└── README.md
```

---

## Roadmap

- [ ] OCR-based document ingestion
- [ ] Cloud deployment (AWS / GCP)
- [ ] Model performance monitoring
- [ ] Credit bureau integrations
- [ ] Role-based access control (RBAC)

---

## Product Hunt

> 🚀 LoanVati is live on Product Hunt — support the launch and share your feedback.

**👉 [producthunt.com/products/loanvati](https://www.producthunt.com/products/loanvati)**

---

## License

MIT — see [LICENSE](LICENSE) for details.
