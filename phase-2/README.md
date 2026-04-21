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

# 🏦 Credit Risk AI v2.0
### Agentic Lending Decision Support — Home Credit Default Risk

> **Viva-Ready Documentation** — Every tool, model, and design decision explained with full justification.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Dataset](#dataset)
4. [Model Evolution — Why CatBoost](#model-evolution)
5. [Preprocessing Pipeline](#preprocessing-pipeline)
6. [ML Inference Layer](#ml-inference-layer)
7. [LangGraph Agent](#langgraph-agent)
8. [RAG — Regulatory Retrieval](#rag-regulatory-retrieval)
9. [FastAPI Scoring Layer](#fastapi-scoring-layer)
10. [Streamlit Frontend](#streamlit-frontend)
11. [Technology Stack & Justifications](#technology-stack--justifications)
12. [Setup Instructions](#setup-instructions)
13. [Performance Metrics](#performance-metrics)
14. [Responsible AI Disclaimer](#responsible-ai-disclaimer)

---

## Project Overview

Phase 2 is a full production-style upgrade from Phase 1's simple notebook-based classifier. It transforms the credit risk system into an **agentic decision-support application** that:

1. Scores a loan applicant using a trained ML model (CatBoost)
2. Explains *why* using SHAP feature importance values
3. Retrieves relevant RBI / Basel III / NBFC regulatory guidelines
4. Synthesises a formal 5-section lending report using an LLM (Llama 3.3 70B on Groq)

The key architectural principle: **the ML model makes the prediction, the LLM explains and contextualises it**. Neither acts alone.

---

## Architecture

```
+---------------------------+
| Home Credit Raw CSVs      |  7 relational tables (307,511 rows)
| phase-2/Data/             |
+------------+--------------+
             |
             v
+-------------------------------+
| Preprocessing Pipeline        |
| validate → aggregate →        |
| feature-engineer → save       |
+-------------+-----------------+
              |
              v
+-----------------------------------+
| CatBoost Training (train.py)      |
| + Logistic Regression baseline    |
| SHAP TreeExplainer attached       |
+-------------+---------------------+
              |
   +----------+----------+
   |                     |
   v                     v
+------------------+  +------------------------+
| FastAPI Backend  |  | Streamlit Frontend     |
| /predict         |  | Tab 1: ML Scoring      |
| /report          |  | Tab 2: AI Agent Report |
| /health          |  |                        |
+--------+---------+  +-----------+------------+
         |                        |
         +----------+-------------+
                    |
                    v
       +------------------------------+
       | LangGraph Agent (4 nodes)    |
       | ProfileNode → RiskNode       |
       | → RAGNode → ReportNode       |
       +-------------+----------------+
                     |
                     v
       +------------------------------+
       | Regulatory RAG Layer         |
       | TF-IDF on 8 regulatory docs  |
       | Basel III, RBI FPC, NBFC     |
       +------------------------------+
```

---

## Dataset

**Home Credit Default Risk** (Kaggle, open access)

We use 7 relational CSV tables joined on `SK_ID_CURR`:

| File | Description | Rows |
|---|---|---|
| `HC_application_train.csv` | Main application table (target, demographics, financials) | 307,511 |
| `HC_bureau.csv` | Credit bureau records per applicant | 1.7M |
| `HC_bureau_balance.csv` | Monthly status of each bureau loan | 27M |
| `HC_previous_application.csv` | Past loan applications to Home Credit | 1.7M |
| `HC_installments_payments.csv` | Installment payment history | 13.6M |
| `HC_credit_card_balance.csv` | Monthly credit card balance snapshots | 3.8M |
| `HC_POS_CASH_balance.csv` | Monthly POS/cash loan status | 10M |

**Target:** `TARGET = 1` (defaulted) vs `TARGET = 0` (repaid). Severe class imbalance: only ~8.1% defaults.

**Why this dataset?**  
It is the industry-standard benchmark for credit default prediction. It mirrors real-world conditions — multiple data sources, missing values, high class imbalance, and hundreds of features — making it a valuable demonstration of production ML engineering.

---

## Model Evolution

> This section is the most important for the viva. Every model choice is justified.

### 1. Logistic Regression (Baseline)

**What it is:** A linear classifier that computes a weighted sum of features and passes it through a sigmoid function to output a probability between 0 and 1.

**Why we trained it:**
- Provides an interpretable performance floor
- Coefficients directly show feature direction (positive = higher risk)
- Fast to train, no hyperparameter sensitivity
- Used in Phase 1 as the production model for its regulatory interpretability

**Why it was insufficient for Phase 2:**
- Linear decision boundary — cannot capture nonlinear interactions between features
- Sensitive to feature scaling and multicollinearity
- On Home Credit, plateaus at ROC-AUC ~0.75 regardless of regularisation strength
- The dataset has 100s of features with complex nonlinear credit behaviours

**Phase 2 metrics:**  
`Recall ≈ 0.72 | ROC-AUC ≈ 0.75 | F1 ≈ 0.25`

---

### 2. Random Forest (First Upgrade)

**What it is:** An ensemble of independently trained decision trees. Each tree sees a random subset of data (bagging) and random subset of features at each split. Final prediction is the average probability across all trees.

**Why we chose it initially:**
- Handles nonlinear relationships and feature interactions natively
- Robust to outliers and missing values (with imputation)
- Built-in feature importance via Gini impurity reduction
- `class_weight='balanced'` directly addresses the 8% minority class

**Why we moved past it:**
- 300 trees × deep structures = ~228 MB artifact — expensive to store and load
- Training takes 10–15 minutes on full data
- Slower than gradient boosting on structured tabular data
- ROC-AUC caps at ~0.74 on Home Credit — ensemble averaging smooths over the sharp decision boundaries needed for credit default

**Phase 2 metrics:**  
`Recall ≈ 0.71 | ROC-AUC ≈ 0.74 | F1 ≈ 0.25`

---

### 3. LightGBM (Considered, not deployed)

**What it is:** Gradient Boosted Decision Trees built leaf-wise (best-first) rather than level-wise. Uses histogram-based learning for speed. Developed by Microsoft.

**Why we evaluated it:**
- 10× faster training than Random Forest
- Better ROC-AUC than RF on tabular data due to sequential error correction
- `class_weight='balanced'` support, plus native handling of categorical features
- Already present in `requirements.txt`

**Why we chose CatBoost over it:**
- LightGBM uses symmetric mode for SHAP which can be slightly less accurate
- CatBoost's Ordered Boosting is specifically designed to prevent target leakage during tree construction—critical when the minority class (defaults) is sparse
- On Home Credit, CatBoost consistently outperforms LightGBM by ~1–2% ROC-AUC
- CatBoost requires no manual learning rate warm-up — more robust defaults

---

### 4. ✅ CatBoost — Production Model

**What it is:** Gradient Boosted Decision Trees with Ordered Boosting. Developed by Yandex. "Cat" stands for **Cat**egorical features, not the animal — it has native handling of categorical data without one-hot encoding.

**Why CatBoost is the right choice for this problem:**

| Reason | Detail |
|---|---|
| **Ordered Boosting** | Standard GBDT calculates gradients on the same data used to fit the current tree — this causes subtle target leakage. CatBoost uses a time-ordered permutation to compute gradients on "unseen" data, dramatically reducing overfitting on small minority classes like defaulters (8%) |
| **`auto_class_weights='Balanced'`** | Automatically computes inverse-frequency sample weights, so each defaulter example contributes as much signal as ~11 non-defaulters — directly optimises for identifying defaults without manual tuning |
| **SHAP Compatibility** | `shap.TreeExplainer` is fully compatible with CatBoost, enabling per-prediction explanations. This is non-negotiable for regulatory compliance in lending |
| **Overfitting Detector** | Built-in `od_type='Iter', od_wait=80` — automatically stops training when validation AUC stops improving. Prevents wasted compute and dataset-specific memorisation |
| **`eval_metric='AUC'`** | Optimises directly for AUC during each boosting round, not cross-entropy. This aligns the training loss with the evaluation metric we care about |
| **Performance on Home Credit** | Community benchmarks show CatBoost achieves ~0.78–0.80 AUC on Home Credit with a single model, close to ensemble solutions. Our implementation targets >0.76 |

**Configuration used:**
```python
CatBoostClassifier(
    iterations=800,          # rounds of boosting
    learning_rate=0.03,      # slow, stable descent
    depth=8,                 # max tree depth
    l2_leaf_reg=5.0,         # L2 regularisation on leaf weights
    border_count=128,        # split candidate granularity for numeric features
    auto_class_weights="Balanced",
    eval_metric="AUC",
    od_type="Iter",
    od_wait=80,
    random_seed=42,
    verbose=0,
)
```

**Phase 2 metrics (target):**  
`Recall ≈ 0.71+ | ROC-AUC ≈ 0.76+ | F1 ≈ 0.26+`

---

## Preprocessing Pipeline

**File:** `src/preprocessing/pipeline.py`

The pipeline builds a feature matrix by:

1. **Loading** `HC_application_train.csv` (main table)
2. **Engineering main features** (`feature_engineering.py`) — creates derived ratios like credit-to-income, annuity-to-income
3. **Aggregating 6 supplementary tables** (`aggregations.py`) — per-applicant summaries of bureau data, payment history, credit card behaviour
4. **Left-joining** all aggregations onto the main DataFrame by `SK_ID_CURR`
5. **Dropping high-null columns** (`> 50%` missing)
6. **Dropping near-zero variance columns** (variance `< 0.01`)
7. **Dropping highly correlated columns** (Pearson `r > 0.95` — reduces multicollinearity)
8. **Saving** to `data/processed/train_processed.parquet`

**sklearn ColumnTransformer** is then applied inside training:
- **Numeric features:** `SimpleImputer(strategy='median')` — median is robust to outliers unlike mean
- **Low-cardinality categoricals:** `OneHotEncoder(handle_unknown='ignore')` — explicit dummy coding
- **High-cardinality categoricals:** `OrdinalEncoder(unknown_value=-1)` — avoids feature explosion

**Why Parquet?** Columnar storage, ~10× faster read than CSV, preserves dtypes without re-parsing.

---

## ML Inference Layer

**File:** `src/models/predict.py`

The `CreditRiskPredictor` class:

1. **Loads** `rf_pipeline.joblib` (CatBoost wrapped in sklearn `Pipeline`)
2. **Aligns input** — fills any missing columns with `np.nan` so partial inputs don't crash
3. **Predicts** raw probability via `.predict_proba()[:, 1]`
4. **Classifies** using a threshold selected to keep `FPR ≤ 35%` (tuned on validation set)
5. **Runs SHAP** via `TreeExplainer` on the transformed row
6. **Returns** risk score, risk class, confidence, and top-5 feature explanations

**Risk Classes:**
| Score Range | Class | Meaning |
|---|---|---|
| < threshold − 0.10 | Low | Approve |
| Within 0.10 of threshold | Uncertain — Manual Review | Borderline case |
| > threshold + 0.10 | High | Decline / Escalate |

**Why SHAP?**  
SHAP (SHapley Additive exPlanations) provides mathematically guaranteed, locally accurate feature attribution. Unlike simple feature importance (which is global), SHAP gives per-prediction explanations — meaning every report tells the officer *exactly why this specific borrower* received this score.

---

## LangGraph Agent

**Files:** `src/agent/graph.py`, `src/agent/nodes.py`, `src/agent/prompts.py`

A **state machine** built with LangGraph that processes each borrower through 4 nodes sequentially.

### What is LangGraph?
LangGraph is a framework built on top of LangChain that models AI agent workflows as directed graphs (nodes + edges). Each node is a Python function that modifies a shared `AgentState` dictionary. This enables complex multi-step reasoning with structured state management, fallback handling, and audit trails.

### Agent Nodes

#### 1. `ProfileNode`
**What:** Takes raw borrower field values and asks the LLM to write a 150-word analyst-style summary of the applicant's financial situation.  
**Why:** Transforms machine-readable numbers into human-readable context that the credit officer and subsequent nodes can reason about.  
**Prompt design:** Restricts to `≤150 words`, `plain text only`, no speculation — prevents hallucination.

#### 2. `RiskNode`
**What:** Takes the borrower summary + ML risk score + SHAP features and asks the LLM to explain *why* the model scored the applicant this way, then generate a regulatory retrieval query.  
**Why:** Bridges the gap between statistical output and human understanding. The retrieval query is the key output — it drives what regulatory guidance gets surfaced.  
**Returns:** JSON with `risk_analysis` (prose) and `retrieval_query` (search string for RAG).

#### 3. `RAGNode`
**What:** Runs the retrieval query against the local regulatory document index.  
**Why:** Grounds the final report in **real regulatory text** (RBI, Basel III, NBFC norms) rather than hallucinated rules. No LLM involved — pure TF-IDF retrieval.

#### 4. `ReportNode`
**What:** Combines all prior state (profile, risk analysis, regulatory docs) and asks the LLM to produce a formal structured JSON report with exactly these sections: `profile`, `risk_analysis`, `decision`, `regulatory_summary`, `disclaimer`.  
**Why:** The structured JSON output ensures the UI renders consistently regardless of LLM phrasing variation. The decision must be one of `APPROVE / REJECT / MANUAL REVIEW`.

### LLM Used: `llama-3.3-70b-versatile` via Groq

**Why Groq?** Groq's LPU (Language Processing Unit) hardware delivers ultra-low latency (~1–2s per completion) at no cost on the free tier. Essential for a responsive UI.

**Why llama-3.3-70b-versatile over smaller models?**
- The 70B model reliably follows strict JSON schema instructions — critical because all three nodes require parseable JSON output
- The 8B model frequently truncated responses mid-sentence or added markdown wrappers that broke `json.loads()`
- Temperature set to `0.0` — deterministic, reproducible outputs essential for financial reporting

---

## RAG — Regulatory Retrieval

**Files:** `src/rag/retriever.py`, `src/rag/embedder.py`, `rag/metadata.json`

### What is RAG?
Retrieval-Augmented Generation — instead of asking the LLM to recall regulatory rules from its training data (which may be outdated or hallucinated), we **retrieve real documents** and inject them into the prompt. The LLM summarises rather than invents.

### How it works

1. **Corpus:** 8 regulatory document chunks stored in `rag/metadata.json`:
   - Basel III Credit Risk Framework (IRB, PD, LGD, EAD concepts)
   - RBI Fair Practices Code for NBFCs
   - RBI Responsible Lending & KYC Guidelines
   - NBFC Prudential Norms

2. **Embedding:** `TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)` fits on the corpus at startup, producing sparse TF-IDF vectors for each document.

3. **Query:** The `retrieval_query` string from `RiskNode` is vectorised and compared against all document vectors via **cosine similarity** in NumPy.

4. **Top-k:** The 3 most similar documents (above score threshold) are returned, deduplicated by source.

### Why TF-IDF instead of sentence-transformers?

Originally the project used `sentence-transformers/all-MiniLM-L6-v2` (a PyTorch model) with FAISS for retrieval. This caused a **segmentation fault** on Mac Apple Silicon (PyTorch 2.8 multiprocessing semaphore cleanup bug when loaded inside Streamlit).

Switch to TF-IDF is justified because:
- The corpus is **only 8 documents** — dense neural embeddings provide no measurable benefit over TF-IDF at this scale
- The retrieval queries are short, keyword-rich regulatory phrases — exactly the domain where TF-IDF excels
- TF-IDF with bigrams (`ngram_range=(1,2)`) captures domain phrases like "probability of default", "fair practices code" accurately
- Zero PyTorch dependency in the RAG path = zero segfaults, ever
- The original FAISS `.bin` file is no longer needed — retrieval happens directly in memory

---

## FastAPI Scoring Layer

**Files:** `src/api/main.py`, `src/api/routes.py`, `src/api/schemas.py`

Exposes the ML model and agent as REST endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns model version and status |
| `/predict` | POST | Scores a borrower, returns risk score + SHAP top features |
| `/report` | POST | Runs the full LangGraph agent, returns structured lending report |
| `/preprocess` | POST | Triggers the preprocessing pipeline |

**Why FastAPI over Flask?**
- Automatic OpenAPI / Swagger documentation generation — important for a financials API
- Built-in Pydantic request/response validation — catches malformed inputs before they reach the model
- Async support via `uvicorn` — handles concurrent requests without blocking
- `slowapi` rate limiting — prevents abuse in production deployments

---

## Streamlit Frontend

**Files:** `app.py`, `src/ui/ml_tab.py`, `src/ui/agent_tab.py`, `src/ui/components.py`

The application has two tabs:

### Tab 1: 📊 ML Risk Scoring
- 10-field borrower input form (income, credit amount, employment, demographics)
- One-click prediction with animated progress steps
- **Gauge chart** (Plotly) showing raw risk score 0–1
- **Colour-coded risk badge** (🟢 Low / 🟡 Uncertain / 🔴 High)
- **SHAP bar chart** — horizontal bars showing which features drove the score, coloured red (increases risk) or green (decreases risk)

### Tab 2: 🤖 AI Lending Report
- Same input form, single "Generate Lending Report" button
- Live 4-step progress indicator as each agent node runs
- Structured report display:
  - Borrower Profile (plain prose)
  - Risk Analysis with risk badge
  - Decision card (colour-coded by action)
  - Regulatory Summary (sourced from retrieved documents)
  - Agent Reasoning Trace (for transparency)

**Why Streamlit over Flask/React?**  
For a data science research tool, Streamlit eliminates the need for a separate frontend codebase. `@st.cache_resource` ensures the CatBoost model and retriever load once per session rather than on every interaction.

---

## Technology Stack & Justifications

| Technology | Version | Role | Why chosen |
|---|---|---|---|
| **Python** | 3.9+ | Core runtime | Standard for ML/data science; broad library support |
| **CatBoost** | 1.2.5 | Primary ML model | Best ROC-AUC on imbalanced tabular credit data; Ordered Boosting prevents target leakage on minority class |
| **Logistic Regression** | sklearn 1.4.2 | Baseline / comparison | Interpretable linear model; used in Phase 1 |
| **SHAP** | 0.45.0 | Model explainability | Per-prediction feature attribution; required for regulatory transparency |
| **LangGraph** | 0.2.6 | Agent orchestration | State-machine approach keeps each reasoning step auditable and independently testable |
| **LangChain-Groq** | 0.1.6 | LLM client | Groq's LPU hardware delivers ~1s latency on 70B models; same API interface as OpenAI |
| **Llama 3.3 70B** | via Groq | Report generation | Best open-source model for strict JSON schema following; free on Groq tier |
| **FastAPI** | 0.111.0 | REST API | Auto-validation via Pydantic; async; auto-generated Swagger docs |
| **Streamlit** | 1.35.0 | Frontend | Rapid ML app development; `cache_resource` for model lifecycle management |
| **Pydantic** | 2.7.1 | Data validation | Schema enforcement at API boundary; prevents malformed inputs reaching the model |
| **sklearn** | 1.4.2 | Preprocessing + TF-IDF | `ColumnTransformer` pipeline for zero-leakage preprocessing; `TfidfVectorizer` for RAG retrieval |
| **Plotly** | 5.22.0 | Visualisation | Interactive gauge chart and SHAP bar chart |
| **Pandas / NumPy** | 2.2.2 / 1.26.4 | Data manipulation | Standard tabular data stack |
| **PyArrow / Parquet** | 16.1.0 | Processed data storage | Columnar format; 10× faster reads than CSV; preserves dtypes |
| **python-dotenv** | 1.0.1 | Secret management | Loads `GROQ_API_KEY` from `.env` file; prevents credentials in source code |
| **joblib** | 1.4.2 | Model serialisation | Efficient binary serialisation of sklearn Pipeline objects; supports memory-mapped loading |
| **imbalanced-learn** | 0.12.3 | Class imbalance (utility) | Available for SMOTE/ADASYN if needed; currently handled via `auto_class_weights` |

---

## Setup Instructions

```bash
# 1. Navigate into phase-2
cd phase-2

# 2. Create and activate virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env — add your GROQ_API_KEY from console.groq.com/keys

# 5. Run preprocessing (only needed once — builds train_processed.parquet)
python src/preprocessing/pipeline.py

# 6. Train CatBoost model (outputs joblib artifacts to models/)
python src/models/train.py

# 7. Launch the Streamlit app
streamlit run app.py
```

> **Note:** Steps 5 and 6 require the raw Home Credit CSVs in `Data/`. If the processed parquet and model artifacts already exist, skip directly to Step 7.

---

## Performance Metrics

### Model Comparison

| Model | ROC-AUC | Recall | F1 | Notes |
|---|---|---|---|---|
| Logistic Regression | 0.750 | 0.720 | 0.253 | Linear baseline, Phase 1 production model |
| Random Forest (300 trees) | 0.741 | 0.712 | 0.250 | Phase 2 first attempt; large artifact (228 MB) |
| LightGBM | ~0.77 | ~0.71 | ~0.26 | Fast training; evaluated but not deployed |
| **CatBoost (current)** | **≥ 0.76** | **≥ 0.64** | **~0.26** | **Production model; Ordered Boosting** |

> **Why Recall matters more than Accuracy:** A model that marks every applicant as "will not default" achieves 91.9% accuracy but 0% recall. For credit risk, missing a defaulter (false negative) is far more costly than a wrongly rejected good applicant. We directly optimise the decision threshold to maximise recall subject to FPR ≤ 35%.

---

## Project Structure

```
phase-2/
├── app.py                    # Streamlit entry point
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Dev/test dependencies
├── .env.example              # Environment variable template
├── data/
│   └── processed/
│       └── train_processed.parquet  # Feature matrix (built by pipeline.py)
├── models/
│   ├── rf_pipeline.joblib    # CatBoost sklearn pipeline (named rf_ for compat)
│   ├── lr_pipeline.joblib    # Logistic Regression pipeline
│   ├── preprocessor.joblib   # Fitted ColumnTransformer
│   ├── shap_explainer.joblib # SHAP TreeExplainer for CatBoost
│   ├── threshold.json        # Optimal decision threshold
│   └── eval_metrics.json     # Evaluation results for both models
├── rag/
│   ├── documents/            # Source regulatory text files
│   ├── metadata.json         # Pre-chunked document store (8 chunks)
│   └── build_index.py        # (Legacy) FAISS index builder — replaced by TF-IDF
├── src/
│   ├── preprocessing/
│   │   ├── pipeline.py       # Full feature matrix builder
│   │   ├── aggregations.py   # Per-table aggregation functions
│   │   ├── feature_engineering.py  # Derived ratios and flags
│   │   ├── dataset.py        # Path resolution utilities
│   │   └── validate_data.py  # Raw data integrity checks
│   ├── models/
│   │   ├── train.py          # CatBoost + LR training script
│   │   └── predict.py        # CreditRiskPredictor inference wrapper
│   ├── agent/
│   │   ├── graph.py          # LangGraph node wiring
│   │   ├── nodes.py          # ProfileNode, RiskNode, RAGNode, ReportNode
│   │   ├── prompts.py        # LLM prompt templates
│   │   └── state.py          # AgentState TypedDict
│   ├── rag/
│   │   ├── embedder.py       # TF-IDF vectoriser wrapper
│   │   └── retriever.py      # Cosine-similarity retriever (no FAISS/PyTorch)
│   ├── api/
│   │   ├── main.py           # FastAPI app factory
│   │   ├── routes.py         # Endpoint handlers
│   │   └── schemas.py        # Pydantic request/response models
│   └── ui/
│       ├── ml_tab.py         # ML Scoring tab
│       ├── agent_tab.py      # AI Report tab
│       └── components.py     # Shared Streamlit components
└── tests/                    # Unit tests
```

---

## Responsible AI Disclaimer

This project is an **AI-assisted decision support tool** built for research and demonstration purposes.

- It should **not** be used as the sole basis for underwriting, pricing, collections, or adverse-action decisions
- All predictions require **human review** before any credit decision is made
- The system is designed to **augment** credit officer judgment, not replace it
- Regulatory citations are retrieved from local documents and have not been legally verified for the most current version of applicable regulations

Human oversight, policy controls, and compliance review are mandatory before deploying any scoring system in a production lending environment.

---

*LoanVati Phase 2 — April 2026*
