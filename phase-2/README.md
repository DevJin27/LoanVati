---
title: Credit Risk AI v2.0
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
license: mit
---

# Credit Risk AI v2.0
Production-style credit risk scoring and agentic lending decision support built on the Home Credit Default Risk dataset.

## Live Demo Links
- Hugging Face Spaces: `TBD`
- Streamlit Community Cloud: `TBD`

## Architecture Diagram
```text
                   +----------------------+
                   | Home Credit Raw CSVs |
                   |   phase-2/Data       |
                   +----------+-----------+
                              |
                              v
                 +---------------------------+
                 | Preprocessing Pipeline    |
                 | validate -> aggregate ->  |
                 | feature engineer -> save  |
                 +-------------+-------------+
                               |
                               v
                +-----------------------------+
                | RF / LR Training Artifacts  |
                | pipelines, threshold, SHAP  |
                +-------------+---------------+
                              |
              +---------------+----------------+
              |                                |
              v                                v
   +------------------------+      +------------------------+
   | FastAPI Scoring Layer  |      | Streamlit Frontend     |
   | predict / report /     |      | ML tab + Agent tab     |
   | preprocess / health    |      |                        |
   +-----------+------------+      +-----------+------------+
               |                                   |
               +----------------+------------------+
                                |
                                v
                   +-----------------------------+
                   | LangGraph Lending Agent     |
                   | profile -> risk -> RAG ->   |
                   | structured report           |
                   +-------------+---------------+
                                 |
                                 v
                   +-----------------------------+
                   | Regulatory RAG Layer        |
                   | txt docs -> embeddings ->   |
                   | FAISS retrieval             |
                   +-----------------------------+
```

## Setup Instructions
```bash
cd phase-2
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt
python src/preprocessing/pipeline.py && python src/models/train.py && streamlit run app.py
```

## API Keys
Copy `.env.example` to `.env`, then fill in:
- `GROQ_API_KEY`
- `API_SECRET_KEY`

The app and API load these values with `python-dotenv`. Never commit the real `.env`.

## ML Performance
| Model | Recall | ROC-AUC | F1 |
| --- | ---: | ---: | ---: |
| Random Forest | 0.7126 | 0.7415 | 0.2502 |
| Logistic Regression | 0.7200 | 0.7501 | 0.2527 |

## Agent Workflow
1. `ProfileNode` summarizes borrower context from the supplied applicant fields.
2. `RiskNode` explains the ML score using SHAP signals and generates a regulatory retrieval query.
3. `RAGNode` fetches the most relevant regulatory guidance from the local FAISS index.
4. `ReportNode` produces a five-section structured lending report with citations and disclaimer text.

Data flows from the predictor into the graph as `risk_score`, `risk_class`, and `top_features`, then each node appends to a shared `AgentState` audit trail.

## Dataset Instructions
1. Download the Home Credit Default Risk CSV files.
2. Place them in `phase-2/Data ` using the preserved names already mapped by the project:
   - `HC_application_train.csv`
   - `HC_bureau.csv`
   - `HC_bureau_balance.csv`
   - `HC_previous_application.csv`
   - `HC_installments_payments.csv`
   - `HC_credit_card_balance.csv`
   - `HC_POS_CASH_balance.csv`
   - `HomeCredit_columns_description.csv`
   - `HC_sample_submission.csv`
3. Run `python src/preprocessing/validate_data.py` before rebuilding the feature matrix.

## Project Structure
```text
phase-2/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── data/
│   └── processed/
├── models/
├── rag/
│   ├── documents/
│   ├── build_index.py
│   └── metadata.json
├── src/
│   ├── preprocessing/
│   ├── models/
│   ├── agent/
│   ├── rag/
│   ├── api/
│   └── ui/
└── tests/
```

## Responsible AI Disclaimer
This project is an AI-assisted decision support tool for research and demonstration. It should not be used as the sole basis for underwriting, pricing, collections, or customer adverse-action decisions without human review, policy controls, and compliance oversight.
