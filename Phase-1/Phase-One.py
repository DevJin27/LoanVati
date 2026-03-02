#!/usr/bin/env python
# coding: utf-8

# # Credit Risk Modelling — Refactored Pipeline
# 
# **Dataset:** Bank of Baroda internal data (`case_study1.csv`) + CIBIL bureau data (`case_study2.csv`)
# 
# **Target:** `Approved_Flag` — Multiclass (P1, P2, P3, P4)
# 
# **Sections:**
# 1. Imports
# 2. Configuration
# 3. Data Loading & EDA Charts
# 4. Preprocessing
# 5. Feature Engineering & Selection Diagnostics
# 6. Model Training
# 7. Evaluation & Charts (Confusion Matrices, ROC-AUC)
# 8. Utilities (`predict()`)
# 9. Gradio UI (Live Inference Interface)
# 

# ## 1. Imports

# In[1]:


# Install all required packages into the active kernel
import sys
get_ipython().system('{sys.executable} -m pip install --quiet matplotlib seaborn scipy statsmodels scikit-learn xgboost')
print('All packages ready.')


# In[2]:


# ── Standard Library ──────────────────────────────────────────────────────────
import warnings
warnings.filterwarnings('ignore')

# ── Core Data & Numerics ──────────────────────────────────────────────────────
import numpy as np
import pandas as pd

# ── Visualisation ─────────────────────────────────────────────────────────────
import matplotlib.pyplot as plt
import seaborn as sns

# ── Statistics ────────────────────────────────────────────────────────────────
from scipy.stats import chi2_contingency, f_oneway
from statsmodels.stats.outliers_influence import variance_inflation_factor

# ── Scikit-learn ──────────────────────────────────────────────────────────────
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
)

# ── XGBoost ───────────────────────────────────────────────────────────────────
import xgboost as xgb

print('All imports successful.')


# ## 2. Configuration

# In[3]:


# ── Central config — edit only here ──────────────────────────────────────────
CONFIG = {
    # File paths
    'PATH_CASE1': 'data/case_study1.csv',
    'PATH_CASE2': 'data/case_study2.csv',

    # Dataset constants
    'MERGE_KEY':           'PROSPECTID',
    'TARGET':              'Approved_Flag',
    'SENTINEL_VALUE':      -99999.000,
    'NULL_DROP_THRESHOLD': 10_000,       # drop df2 cols with > this many nulls

    # Feature selection thresholds
    'PVALUE_THRESHOLD': 0.05,
    'VIF_THRESHOLD':    6.0,

    # Train / test split
    'TEST_SIZE':     0.20,
    'RANDOM_STATE':  42,

    # Columns that need standard scaling (continuous, wide-range numerics)
    'COLS_TO_SCALE': [
        'Age_Oldest_TL', 'Age_Newest_TL', 'time_since_recent_payment',
        'max_recent_level_of_deliq', 'recent_level_of_deliq',
        'time_since_recent_enq', 'NETMONTHLYINCOME', 'Time_With_Curr_Empr',
    ],

    # Ordinal mapping for EDUCATION
    'EDUCATION_MAP': {
        'SSC': 1, '12TH': 2, 'GRADUATE': 3,
        'UNDER GRADUATE': 3, 'POST-GRADUATE': 4,
        'PROFESSIONAL': 3, 'OTHERS': 1,
    },

    # Columns to one-hot encode
    'OHE_COLS': ['MARITALSTATUS', 'GENDER', 'last_prod_enq2', 'first_prod_enq2'],

    # ── GridSearchCV param grids ──────────────────────────────────────────────
    'PARAM_GRID_LR': {
        'C':        [0.01, 0.1, 1, 10],
        'solver':   ['lbfgs', 'saga'],
        'max_iter': [500, 1000],
    },
    'PARAM_GRID_DT': {
        'max_depth':        [5, 10, 20, None],
        'min_samples_split': [2, 5, 10],
        'criterion':        ['gini', 'entropy'],
    },
    'PARAM_GRID_RF': {
        'n_estimators': [100, 200],
        'max_depth':    [None, 10, 20],
    },
    'PARAM_GRID_XGB': {
        'n_estimators':  [100, 200],
        'max_depth':     [3, 5],
        'learning_rate': [0.1, 0.2],
    },

    'CV_FOLDS': 3,
}

print('Configuration loaded.')


# ## 3. Data Loading

# In[4]:


def load_data(path1: str, path2: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load two CSV files into independent DataFrames.

    Parameters
    ----------
    path1 : str  Path to the first CSV (BoB internal data).
    path2 : str  Path to the second CSV (CIBIL bureau data).

    Returns
    -------
    (df1, df2) : tuple of DataFrames
    """
    df1 = pd.read_csv(path1)
    df2 = pd.read_csv(path2)
    print(f'Loaded df1: {df1.shape}  |  df2: {df2.shape}')
    return df1.copy(), df2.copy()


# ── Execute ───────────────────────────────────────────────────────────────────
df1_raw, df2_raw = load_data(CONFIG['PATH_CASE1'], CONFIG['PATH_CASE2'])


# ## 4. Preprocessing

# In[ ]:


def clean_df1(df: pd.DataFrame, sentinel: float = -99999.0) -> pd.DataFrame:
    """
    Clean BoB internal data (df1).

    Steps
    -----
    1. Replace sentinel value with NaN.
    2. Drop all rows with any remaining NaN.

    Parameters
    ----------
    df       : Raw df1 DataFrame.
    sentinel : Numeric sentinel representing missing data (default -99999.0).

    Returns
    -------
    Cleaned DataFrame.
    """
    df = df.replace(sentinel, np.nan)
    before = len(df)
    df = df.dropna()
    print(f'df1 cleaned: {before} → {len(df)} rows ({before - len(df)} dropped)')
    return df


def clean_df2(
    df: pd.DataFrame,
    sentinel: float = -99999.0,
    null_threshold: int = 10_000,
) -> pd.DataFrame:
    """
    Clean CIBIL bureau data (df2).

    Steps
    -----
    1. Replace sentinel value with NaN.
    2. Drop columns where null count exceeds `null_threshold`.
    3. Drop rows with any remaining NaN.

    Parameters
    ----------
    df              : Raw df2 DataFrame.
    sentinel        : Numeric sentinel (default -99999.0).
    null_threshold  : Max allowed nulls per column before dropping (default 10 000).

    Returns
    -------
    Cleaned DataFrame.
    """
    df = df.replace(sentinel, np.nan)

    # Drop columns with too many missing values
    high_null_cols = [c for c in df.columns if df[c].isnull().sum() > null_threshold]
    df = df.drop(columns=high_null_cols)
    print(f'df2: dropped {len(high_null_cols)} high-null columns: {high_null_cols}')

    before = len(df)
    df = df.dropna()
    print(f'df2 cleaned: {before} → {len(df)} rows ({before - len(df)} dropped)')
    return df


def merge_datasets(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    on_col: str = 'PROSPECTID',
) -> pd.DataFrame:
    """
    Inner-merge the two cleaned datasets on `on_col`.

    Parameters
    ----------
    df1    : Cleaned BoB internal DataFrame.
    df2    : Cleaned CIBIL bureau DataFrame.
    on_col : Column to merge on (default 'PROSPECTID').

    Returns
    -------
    Merged DataFrame.
    """
    df = pd.merge(df1, df2, on=on_col)
    print(f'Merged shape: {df.shape}  |  Remaining NaNs: {df.isna().sum().sum()}')
    return df


# ── Execute ───────────────────────────────────────────────────────────────────
df1_clean = clean_df1(df1_raw, sentinel=CONFIG['SENTINEL_VALUE'])
df2_clean = clean_df2(
    df2_raw,
    sentinel=CONFIG['SENTINEL_VALUE'],
    null_threshold=CONFIG['NULL_DROP_THRESHOLD'],
)
df = merge_datasets(df1_clean, df2_clean, on_col=CONFIG['MERGE_KEY'])


# ## 3b. Exploratory Data Analysis (EDA)

# In[ ]:


CLASS_LABELS = ["P1", "P2", "P3", "P4"]  # defined here for EDA (before feature eng section)

# ── EDA Charts ───────────────────────────────────────────────────────────────
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np

# Style
plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#e6edf3",
    "xtick.color": "#848d97", "ytick.color": "#848d97",
    "text.color": "#e6edf3", "grid.color": "#21262d",
    "figure.dpi": 120, "font.family": "DejaVu Sans",
})
PALETTE = ["#238636", "#1f6feb", "#f78166", "#d29922"]  # P1 P2 P3 P4

fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor("#0d1117")
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

# ── 1. Class distribution bar ──────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
vc = df[CONFIG["TARGET"]].value_counts().reindex(CLASS_LABELS)
bars = ax1.bar(CLASS_LABELS, vc.values, color=PALETTE, edgecolor="#30363d", linewidth=0.8)
ax1.set_title("Class Distribution", fontsize=13, fontweight="bold", color="#58a6ff")
ax1.set_ylabel("Count", fontsize=10)
for bar, v in zip(bars, vc.values):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
             f"{v:,}", ha="center", fontsize=9, color="#e6edf3")
ax1.grid(axis="y", alpha=0.3)

# ── 2. Class distribution pie ─────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
labels_pct = [f"{l} ({v/vc.sum()*100:.1f}%)" for l, v in zip(CLASS_LABELS, vc.values)]
wedges, _ = ax2.pie(vc.values, colors=PALETTE, startangle=90,
                    wedgeprops=dict(edgecolor="#0d1117", linewidth=2))
ax2.legend(wedges, labels_pct, loc="center left", bbox_to_anchor=(0.85, 0.5),
           fontsize=8, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
ax2.set_title("Class Imbalance", fontsize=13, fontweight="bold", color="#58a6ff")

# ── 3. Net Monthly Income by class boxplot ────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
income_data = [df.loc[df[CONFIG["TARGET"]] == l, "NETMONTHLYINCOME"].dropna().values
               for l in CLASS_LABELS]
bp = ax3.boxplot(income_data, patch_artist=True, notch=False,
                 medianprops=dict(color="#e6edf3", linewidth=2),
                 whiskerprops=dict(color="#848d97"), capprops=dict(color="#848d97"),
                 flierprops=dict(marker="o", color="#848d97", alpha=0.3, markersize=3))
for patch, color in zip(bp["boxes"], PALETTE):
    patch.set_facecolor(color); patch.set_alpha(0.8)
ax3.set_xticklabels(CLASS_LABELS)
ax3.set_title("Monthly Income by Risk Class", fontsize=13, fontweight="bold", color="#58a6ff")
ax3.set_ylabel("Net Monthly Income (₹)", fontsize=10)
ax3.grid(axis="y", alpha=0.3)

# ── 4. Age of Oldest TL by class violin ───────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0])
for i, (lbl, color) in enumerate(zip(CLASS_LABELS, PALETTE)):
    data = df.loc[df[CONFIG["TARGET"]] == lbl, "Age_Oldest_TL"].dropna().values
    parts = ax4.violinplot(data, positions=[i], widths=0.7,
                           showmedians=True, showextrema=False)
    for pc in parts["bodies"]:
        pc.set_facecolor(color); pc.set_alpha(0.75)
    parts["cmedians"].set_color("#e6edf3"); parts["cmedians"].set_linewidth(2)
ax4.set_xticks(range(4)); ax4.set_xticklabels(CLASS_LABELS)
ax4.set_title("Age of Oldest Trade Line", fontsize=13, fontweight="bold", color="#58a6ff")
ax4.set_ylabel("Months", fontsize=10)
ax4.grid(axis="y", alpha=0.3)

# ── 5. Max delinquency heatmap-style count ─────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
cross = pd.crosstab(df[CONFIG["TARGET"]], df["max_recent_level_of_deliq"].clip(upper=6))
cross = cross.reindex(CLASS_LABELS)
sns.heatmap(cross, ax=ax5, cmap="Blues", fmt="d", annot=True,
            linewidths=0.5, linecolor="#0d1117",
            cbar_kws={"shrink": 0.8},
            annot_kws={"fontsize": 8})
ax5.set_title("Max Delinquency vs. Risk Class", fontsize=13, fontweight="bold", color="#58a6ff")
ax5.set_xlabel("Max Delinquency Level (capped at 6)", fontsize=9)
ax5.set_ylabel("Risk Class", fontsize=9)

# ── 6. Correlation heatmap (numerical selected features, top 12) ────────────
ax6 = fig.add_subplot(gs[1, 2])
num_candidates = [c for c in df.select_dtypes(include="number").columns
                  if c != CONFIG["TARGET"]][:12]
corr = df[num_candidates].corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, ax=ax6, cmap="coolwarm", center=0, mask=mask,
            square=True, linewidths=0.3, linecolor="#0d1117",
            cbar_kws={"shrink": 0.7}, annot=False)
ax6.set_title("Feature Correlation (top 12 num)", fontsize=13, fontweight="bold", color="#58a6ff")
ax6.tick_params(labelsize=7, labelrotation=45)

plt.suptitle("Exploratory Data Analysis", fontsize=17, fontweight="bold",
             color="#58a6ff", y=1.01)
plt.savefig("eda_charts.png", bbox_inches="tight", facecolor="#0d1117")
plt.show()
print("EDA charts saved.")


# ## 5. Feature Engineering

# In[ ]:


# ── 5a. Identify column types ─────────────────────────────────────────────────
cat_cols = df.select_dtypes(include='object').columns.tolist()
num_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()

# Remove ID and target from working lists
cat_cols = [c for c in cat_cols if c != CONFIG['TARGET']]
num_cols = [c for c in num_cols if c != CONFIG['MERGE_KEY']]

print(f'Categorical features : {len(cat_cols)} → {cat_cols}')
print(f'Numerical features   : {len(num_cols)}')


# In[ ]:


def select_categorical_features(
    df: pd.DataFrame,
    cat_cols: list[str],
    target: str,
    threshold: float = 0.05,
) -> list[str]:
    """
    Select categorical features using the Chi-Square test of independence.

    Null Hypothesis (H0): No association between feature and target.
    Decision rule: Reject H0 when p-value ≤ threshold (feature is significant).

    Parameters
    ----------
    df       : Merged DataFrame.
    cat_cols : List of candidate categorical column names.
    target   : Name of the target column.
    threshold: Significance level (default 0.05).

    Returns
    -------
    List of significant categorical feature names.
    """
    kept = []
    print(f"{'Feature':<30} {'p-value':>12} {'Significant':>12}")
    print('-' * 56)
    for col in cat_cols:
        _, pval, _, _ = chi2_contingency(pd.crosstab(df[col], df[target]))
        significant = pval <= threshold
        if significant:
            kept.append(col)
        print(f"{col:<30} {pval:>12.4f} {'✓' if significant else '✗':>12}")
    print(f'\nKept {len(kept)} / {len(cat_cols)} categorical features.')
    return kept


# ── Execute ───────────────────────────────────────────────────────────────────
kept_cat = select_categorical_features(
    df, cat_cols, target=CONFIG['TARGET'], threshold=CONFIG['PVALUE_THRESHOLD']
)


# In[ ]:


def select_numerical_features_vif(
    df: pd.DataFrame,
    num_cols: list[str],
    threshold: float = 6.0,
) -> list[str]:
    """
    Iteratively remove numerical features with high Variance Inflation Factor (VIF).

    VIF measures multicollinearity: a VIF > threshold means the feature is
    strongly predictable from other features. We drop the worst offender
    each iteration until all VIFs are below the threshold.

    Parameters
    ----------
    df        : Merged DataFrame.
    num_cols  : List of candidate numerical column names.
    threshold : Maximum acceptable VIF (default 6.0).

    Returns
    -------
    List of low-multicollinearity numerical feature names.
    """
    cols = [c for c in num_cols if df[c].std() > 0]  # drop zero-variance cols

    iteration = 0
    while True:
        X = df[cols].values
        vifs = [variance_inflation_factor(X, i) for i in range(len(cols))]
        max_vif = max(vifs)

        if max_vif <= threshold:
            break  # all remaining features are below the threshold

        # Drop the feature with the highest VIF
        drop_idx = vifs.index(max_vif)
        print(f'Iter {iteration}: Dropping "{cols[drop_idx]}" (VIF={max_vif:.2f})')
        cols.pop(drop_idx)
        iteration += 1

    print(f'\nRetained {len(cols)} numerical features after VIF filtering.')
    return cols


# ── Execute ───────────────────────────────────────────────────────────────────
vif_passed = select_numerical_features_vif(
    df, num_cols, threshold=CONFIG['VIF_THRESHOLD']
)


# In[ ]:


def select_numerical_features_anova(
    df: pd.DataFrame,
    num_cols: list[str],
    target: str,
    class_labels: list[str],
    threshold: float = 0.05,
) -> list[str]:
    """
    Select numerical features using a one-way ANOVA F-test against the target.

    ANOVA is preferred over correlation here because the target has ≥ 3 categories,
    and we want to capture non-linear mean differences across groups.

    Parameters
    ----------
    df           : Merged DataFrame (VIF-filtered subset).
    num_cols     : Candidate numerical columns (post-VIF).
    target       : Name of the target column.
    class_labels : Ordered list of class labels, e.g. ['P1','P2','P3','P4'].
    threshold    : Significance level (default 0.05).

    Returns
    -------
    List of significant numerical feature names.
    """
    kept = []
    for col in num_cols:
        groups = [df.loc[df[target] == lbl, col].tolist() for lbl in class_labels]

        # ANOVA requires at least 2 samples per group
        if any(len(g) < 2 for g in groups):
            continue

        _, pval = f_oneway(*groups)
        if pval <= threshold:
            kept.append(col)

    print(f'Retained {len(kept)} / {len(num_cols)} numerical features after ANOVA.')
    return kept


# Target class labels are fixed for this dataset
CLASS_LABELS = ['P1', 'P2', 'P3', 'P4']

# ── Execute ───────────────────────────────────────────────────────────────────
kept_num = select_numerical_features_anova(
    df, vif_passed, target=CONFIG['TARGET'],
    class_labels=CLASS_LABELS, threshold=CONFIG['PVALUE_THRESHOLD']
)

# Combine selected features and trim the main DataFrame
selected_features = kept_num + kept_cat
df = df[selected_features + [CONFIG['TARGET']]]
print(f'Final feature set size: {len(selected_features)}  |  df shape: {df.shape}')


# ## 5b. Feature Selection Diagnostics

# In[ ]:


# ── Ensure CLASS_LABELS is available ───────────────────────────────────
if "CLASS_LABELS" not in dir():
    CLASS_LABELS = ["P1", "P2", "P3", "P4"]

# ── Feature Selection Charts ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#161b22")

# ── 1. Chi-square p-values ─────────────────────────────────────────────────
pvals_cat = {}
for col in cat_cols:
    _, pv, _, _ = chi2_contingency(pd.crosstab(df[col], df[CONFIG["TARGET"]]))
    pvals_cat[col] = pv
chi_df = pd.Series(pvals_cat).sort_values()
colors_chi = ["#238636" if p < 0.05 else "#f78166" for p in chi_df]
axes[0].barh(chi_df.index, chi_df.values, color=colors_chi, edgecolor="#30363d")
axes[0].axvline(0.05, color="#f78166", linestyle="--", linewidth=1.5, label="α = 0.05")
axes[0].set_title("Chi-Square p-values\n(Categorical Features)", fontsize=12,
                   fontweight="bold", color="#58a6ff")
axes[0].set_xlabel("p-value", fontsize=10)
axes[0].legend(fontsize=9, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
axes[0].tick_params(colors="#848d97")

# ── 2. VIF (on post-ANOVA numeric features) ────────────────────────────────
from statsmodels.stats.outliers_influence import variance_inflation_factor
vif_cols = [c for c in kept_num if df[c].std() > 0][:15]
X_vif = df[vif_cols].dropna().values
vif_vals = [variance_inflation_factor(X_vif, i) for i in range(len(vif_cols))]
vif_series = pd.Series(vif_vals, index=vif_cols).sort_values(ascending=False)
colors_vif = ["#f78166" if v > 6 else "#238636" for v in vif_series]
axes[1].barh(vif_series.index, vif_series.values, color=colors_vif, edgecolor="#30363d")
axes[1].axvline(6, color="#f78166", linestyle="--", linewidth=1.5, label="VIF = 6")
axes[1].set_title("Variance Inflation Factor\n(Selected Numeric Features)", fontsize=12,
                   fontweight="bold", color="#58a6ff")
axes[1].set_xlabel("VIF", fontsize=10)
axes[1].legend(fontsize=9, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
axes[1].tick_params(colors="#848d97")

# ── 3. ANOVA p-values ──────────────────────────────────────────────────────
from scipy.stats import f_oneway
pvals_num = {}
for col in vif_passed[:20]:
    groups = [df.loc[df[CONFIG["TARGET"]] == l, col].dropna().values for l in CLASS_LABELS]
    if all(len(g) >= 2 for g in groups):
        _, pv = f_oneway(*groups)
        pvals_num[col] = pv
anova_df = pd.Series(pvals_num).sort_values()
colors_anova = ["#238636" if p < 0.05 else "#f78166" for p in anova_df]
axes[2].barh(anova_df.index, anova_df.values, color=colors_anova, edgecolor="#30363d")
axes[2].axvline(0.05, color="#f78166", linestyle="--", linewidth=1.5, label="α = 0.05")
axes[2].set_title("ANOVA p-values\n(Numerical Features)", fontsize=12,
                   fontweight="bold", color="#58a6ff")
axes[2].set_xlabel("p-value", fontsize=10)
axes[2].legend(fontsize=9, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
axes[2].tick_params(colors="#848d97")

plt.suptitle("Feature Selection Diagnostics", fontsize=15, fontweight="bold",
             color="#58a6ff", y=1.02)
plt.tight_layout()
plt.savefig("feature_selection_charts.png", bbox_inches="tight", facecolor="#0d1117")
plt.show()
print("Feature selection charts saved.")


# In[ ]:


def encode_features(
    df: pd.DataFrame,
    education_map: dict,
    ohe_cols: list[str],
) -> pd.DataFrame:
    """
    Encode categorical features prior to modelling.

    Two strategies are applied:
    - Ordinal encoding  : EDUCATION (natural hierarchy: SSC < 12TH < GRADUATE ...)
    - One-hot encoding  : Remaining nominal categoricals (no natural order)

    Parameters
    ----------
    df           : Feature-selected DataFrame (including target column).
    education_map: Dict mapping raw EDUCATION strings to integer ranks.
    ohe_cols     : Columns to one-hot encode.

    Returns
    -------
    Encoded DataFrame (target column included).
    """
    df = df.copy()

    # Ordinal encode EDUCATION (only if the column is present after feature selection)
    if 'EDUCATION' in df.columns:
        df['EDUCATION'] = df['EDUCATION'].map(education_map).astype(int)

    # One-hot encode nominal categoricals that survived feature selection
    cols_present = [c for c in ohe_cols if c in df.columns]
    df = pd.get_dummies(df, columns=cols_present)

    print(f'Encoding complete. Shape after OHE: {df.shape}')
    return df


def scale_features(
    df: pd.DataFrame,
    cols_to_scale: list[str],
) -> tuple[pd.DataFrame, StandardScaler, list[str]]:
    """
    Fit and apply StandardScaler to the specified continuous columns.

    Only columns actually present in `df` are scaled (guards against
    columns dropped during feature selection).

    Parameters
    ----------
    df            : Encoded DataFrame.
    cols_to_scale : Candidate columns for scaling.

    Returns
    -------
    (scaled_df, fitted_scaler, scaled_col_names)
    """
    df = df.copy()
    cols_present = [c for c in cols_to_scale if c in df.columns]

    scaler = StandardScaler()
    df[cols_present] = scaler.fit_transform(df[cols_present])

    print(f'Scaled {len(cols_present)} columns: {cols_present}')
    return df, scaler, cols_present


# ── Execute ───────────────────────────────────────────────────────────────────
df_encoded = encode_features(
    df,
    education_map=CONFIG['EDUCATION_MAP'],
    ohe_cols=CONFIG['OHE_COLS'],
)

df_encoded, fitted_scaler, scaled_cols = scale_features(
    df_encoded,
    cols_to_scale=CONFIG['COLS_TO_SCALE'],
)

print(f'\nFinal encoded shape: {df_encoded.shape}')
print(f'Target distribution:\n{df_encoded[CONFIG["TARGET"]].value_counts()}')


# In[ ]:


# ── Prepare X, y, label encoding, and train/test split ───────────────────────
TARGET = CONFIG['TARGET']

X = df_encoded.drop(columns=[TARGET])
y = df_encoded[TARGET]

# Encode string labels to integers (required by XGBoost; consistent for all models)
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)   # P1→0, P2→1, P3→2, P4→3

# Single train/test split — shared across all models for a fair comparison
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=CONFIG['TEST_SIZE'],
    random_state=CONFIG['RANDOM_STATE'],
    stratify=y_encoded,   # preserves class proportions in both sets
)

# Store column order for use in predict()
FEATURE_COLUMNS = X.columns.tolist()

print(f'X_train: {X_train.shape}  |  X_test: {X_test.shape}')
print(f'Classes: {label_encoder.classes_}')


# ## 6. Model Training

# In[ ]:


def train_with_grid_search(
    estimator,
    param_grid: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv: int = 3,
    scoring: str = 'accuracy',
    model_name: str = '',
):
    """
    Wrap any sklearn-compatible estimator in GridSearchCV and return the best model.

    Parameters
    ----------
    estimator  : Unfitted sklearn estimator.
    param_grid : Hyperparameter search space.
    X_train    : Training features.
    y_train    : Training labels.
    cv         : Number of cross-validation folds.
    scoring    : Scoring metric for GridSearchCV.
    model_name : Human-readable name for logging.

    Returns
    -------
    best_estimator : Fitted best model from GridSearchCV.
    """
    grid = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        cv=cv,
        scoring=scoring,
        n_jobs=-1,
        refit=True,
    )
    grid.fit(X_train, y_train)
    print(f'[{model_name}] Best params : {grid.best_params_}')
    print(f'[{model_name}] CV accuracy : {grid.best_score_:.4f}')
    return grid.best_estimator_


# In[ ]:


# ── 6a. Logistic Regression ───────────────────────────────────────────────────
# Multiclass multinomial LR with GridSearchCV over regularisation strength (C)
# and solver. This model is ALSO used as the final production predict() model.
print('Training Logistic Regression...')
lr_model = train_with_grid_search(
    estimator=LogisticRegression(random_state=CONFIG['RANDOM_STATE']),
    param_grid=CONFIG['PARAM_GRID_LR'],
    X_train=X_train,
    y_train=y_train,
    cv=CONFIG['CV_FOLDS'],
    model_name='Logistic Regression',
)


# In[ ]:


# ── 6b. Decision Tree ─────────────────────────────────────────────────────────
print('Training Decision Tree...')
dt_model = train_with_grid_search(
    estimator=DecisionTreeClassifier(random_state=CONFIG['RANDOM_STATE']),
    param_grid=CONFIG['PARAM_GRID_DT'],
    X_train=X_train,
    y_train=y_train,
    cv=CONFIG['CV_FOLDS'],
    model_name='Decision Tree',
)


# In[ ]:


# ── 6c. Random Forest ─────────────────────────────────────────────────────────
print('Training Random Forest...')
rf_model = train_with_grid_search(
    estimator=RandomForestClassifier(random_state=CONFIG['RANDOM_STATE']),
    param_grid=CONFIG['PARAM_GRID_RF'],
    X_train=X_train,
    y_train=y_train,
    cv=CONFIG['CV_FOLDS'],
    model_name='Random Forest',
)


# In[ ]:


# ── 6d. XGBoost ───────────────────────────────────────────────────────────────
# XGBoost requires integer-encoded labels (already done via LabelEncoder)
print('Training XGBoost...')
xgb_model = train_with_grid_search(
    estimator=xgb.XGBClassifier(
        objective='multi:softmax',
        num_class=len(CLASS_LABELS),
        random_state=CONFIG['RANDOM_STATE'],
        eval_metric='mlogloss',
    ),
    param_grid=CONFIG['PARAM_GRID_XGB'],
    X_train=X_train,
    y_train=y_train,
    cv=CONFIG['CV_FOLDS'],
    model_name='XGBoost',
)


# ## 7. Evaluation

# In[ ]:


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    model_name: str,
) -> dict:
    """
    Evaluate a fitted classifier on the test set.

    Metrics computed
    ----------------
    - Accuracy
    - Macro-averaged Precision, Recall, F1-score
    - Per-class Precision, Recall, F1-score

    Parameters
    ----------
    model      : Fitted sklearn-compatible classifier.
    X_test     : Test features.
    y_test     : True integer-encoded labels.
    model_name : Label used in the comparison table.

    Returns
    -------
    Dict with keys: model, accuracy, macro_precision, macro_recall, macro_f1,
    plus per-class precision/recall/f1.
    """
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average=None
    )
    macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='macro'
    )

    result = {
        'Model':           model_name,
        'Accuracy':        round(acc, 4),
        'Macro Precision': round(macro_prec, 4),
        'Macro Recall':    round(macro_rec, 4),
        'Macro F1':        round(macro_f1, 4),
    }

    # Per-class metrics (P1..P4)
    for i, label in enumerate(CLASS_LABELS):
        result[f'{label} Precision'] = round(prec[i], 4)
        result[f'{label} Recall']    = round(rec[i], 4)
        result[f'{label} F1']        = round(f1[i], 4)

    return result


def print_comparison_table(results: list[dict]) -> pd.DataFrame:
    """
    Print a formatted model comparison table and return it as a DataFrame.

    Parameters
    ----------
    results : List of dicts returned by evaluate_model().

    Returns
    -------
    Summary DataFrame (sorted by Accuracy descending).
    """
    summary_cols = ['Model', 'Accuracy', 'Macro Precision', 'Macro Recall', 'Macro F1']
    detail_cols  = [f'{lbl} {m}' for lbl in CLASS_LABELS for m in ('Precision', 'Recall', 'F1')]

    df_results = pd.DataFrame(results).sort_values('Accuracy', ascending=False)

    print('=' * 80)
    print('MODEL COMPARISON SUMMARY')
    print('=' * 80)
    print(df_results[summary_cols].to_string(index=False))
    print('\n' + '─' * 80)
    print('PER-CLASS BREAKDOWN')
    print('─' * 80)
    print(df_results[['Model'] + detail_cols].to_string(index=False))
    print('=' * 80)

    return df_results


# ── Execute ───────────────────────────────────────────────────────────────────
model_registry = {
    'Logistic Regression': lr_model,
    'Decision Tree':       dt_model,
    'Random Forest':       rf_model,
    'XGBoost':             xgb_model,
}

results = [
    evaluate_model(model, X_test, y_test, name)
    for name, model in model_registry.items()
]

comparison_df = print_comparison_table(results)


# In[ ]:


# ── Detailed classification report for each model ─────────────────────────────
for name, model in model_registry.items():
    y_pred = model.predict(X_test)
    print(f'\n{"─" * 50}')
    print(f'Classification Report — {name}')
    print('─' * 50)
    print(
        classification_report(
            y_test, y_pred,
            target_names=label_encoder.classes_,
        )
    )


# ## 7b. Evaluation Charts

# In[ ]:


# ── Local imports/constants to keep this cell independent ──────────────
import matplotlib.gridspec as gridspec
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize
PALETTE = ["#238636", "#1f6feb", "#f78166", "#d29922"]  # P1 P2 P3 P4

# ── Evaluation Charts ─────────────────────────────────────────────────────────

fig = plt.figure(figsize=(20, 14))
fig.patch.set_facecolor("#0d1117")
gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.5, wspace=0.4)

model_items = list(model_registry.items())

# ── 1–4. Confusion matrices for all 4 models ──────────────────────────────
for idx, (name, model) in enumerate(model_items):
    ax = fig.add_subplot(gs[0, idx])
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, ax=ax, cmap="Blues", fmt="d", annot=True,
                xticklabels=CLASS_LABELS, yticklabels=CLASS_LABELS,
                linewidths=0.5, linecolor="#0d1117",
                cbar=False, annot_kws={"fontsize": 9})
    ax.set_title(name, fontsize=11, fontweight="bold", color="#58a6ff")
    ax.set_xlabel("Predicted", fontsize=9)
    ax.set_ylabel("Actual", fontsize=9)
    ax.tick_params(colors="#848d97")
    ax.set_facecolor("#161b22")

# ── 5. Model comparison bar chart ─────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 0:2])
metrics_to_plot = ["Accuracy", "Macro Precision", "Macro Recall", "Macro F1"]
x = np.arange(len(metrics_to_plot))
bar_w = 0.18
colors_bar = ["#58a6ff", "#238636", "#d29922", "#f78166"]
for i, (name, model) in enumerate(model_items):
    row = comparison_df[comparison_df["Model"] == name].iloc[0]
    vals = [row[m] for m in metrics_to_plot]
    bars = ax5.bar(x + i * bar_w, vals, bar_w, label=name,
                   color=colors_bar[i], edgecolor="#0d1117", alpha=0.9)
ax5.set_xticks(x + bar_w * 1.5)
ax5.set_xticklabels(metrics_to_plot, fontsize=10)
ax5.set_ylim(0, 1.15)
ax5.set_title("Model Performance Comparison", fontsize=13, fontweight="bold", color="#58a6ff")
ax5.set_ylabel("Score", fontsize=10)
ax5.legend(fontsize=9, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
ax5.grid(axis="y", alpha=0.3)
ax5.set_facecolor("#161b22")

# ── 6. ROC-AUC curves (OvR — Logistic Regression) ─────────────────────────
ax6 = fig.add_subplot(gs[1, 2:4])
y_bin = label_binarize(y_test, classes=[0, 1, 2, 3])
y_score = lr_model.predict_proba(X_test)
roc_colors = PALETTE
for i, (lbl, col) in enumerate(zip(CLASS_LABELS, roc_colors)):
    fpr, tpr, _ = roc_curve(y_bin[:, i], y_score[:, i])
    roc_auc = auc(fpr, tpr)
    ax6.plot(fpr, tpr, color=col, lw=2, label=f"{lbl} (AUC = {roc_auc:.3f})")
ax6.plot([0, 1], [0, 1], "k--", lw=1, color="#848d97")
ax6.set_xlim([0, 1]); ax6.set_ylim([0, 1.05])
ax6.set_xlabel("False Positive Rate", fontsize=10)
ax6.set_ylabel("True Positive Rate", fontsize=10)
ax6.set_title("ROC-AUC Curves — Logistic Regression (OvR)", fontsize=13,
              fontweight="bold", color="#58a6ff")
ax6.legend(fontsize=9, labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
ax6.grid(alpha=0.3)
ax6.set_facecolor("#161b22")

plt.suptitle("Model Evaluation", fontsize=17, fontweight="bold", color="#58a6ff", y=1.01)
plt.savefig("evaluation_charts.png", bbox_inches="tight", facecolor="#0d1117")
plt.show()
print("Evaluation charts saved.")


# ## 8. Utilities — `predict()`

# In[ ]:


def predict(raw_input: dict) -> dict:
    """
    Production inference function using the trained Logistic Regression model.

    Even if another model achieved higher accuracy during evaluation,
    this function intentionally uses Logistic Regression because:
    - It produces well-calibrated probabilities.
    - It is interpretable and auditable in a credit risk context.

    Pipeline applied (mirrors training)
    ------------------------------------
    1. Build a single-row DataFrame from `raw_input`.
    2. Ordinal-encode EDUCATION using CONFIG['EDUCATION_MAP'].
    3. One-hot encode nominal categoricals (CONFIG['OHE_COLS']).
    4. Align columns to the training feature set (fills missing OHE columns
       with 0 and drops any extra columns).
    5. Standard-scale continuous columns using the fitted scaler.
    6. Run inference with lr_model.

    Parameters
    ----------
    raw_input : dict
        Keys must match the original pre-encoded feature names.
        Example:
        {
            'Age_Oldest_TL': 120,
            'NETMONTHLYINCOME': 50000,
            'EDUCATION': 'GRADUATE',
            'GENDER': 'M',
            'MARITALSTATUS': 'Married',
            'last_prod_enq2': 'PL',
            'first_prod_enq2': 'PL',
            ... (all selected features)
        }

    Returns
    -------
    dict with keys:
        'prediction'  : Predicted class label (e.g. 'P2').
        'probability' : Dict mapping each class label to its predicted probability.

    Raises
    ------
    ValueError if raw_input is empty or missing critical keys.
    """
    if not raw_input:
        raise ValueError('raw_input must not be empty.')

    # 1. Build a one-row DataFrame
    df_input = pd.DataFrame([raw_input])

    # 2. Ordinal-encode EDUCATION
    if 'EDUCATION' in df_input.columns:
        df_input['EDUCATION'] = df_input['EDUCATION'].map(
            CONFIG['EDUCATION_MAP']
        ).fillna(1).astype(int)

    # 3. One-hot encode nominal categoricals
    ohe_cols_present = [c for c in CONFIG['OHE_COLS'] if c in df_input.columns]
    df_input = pd.get_dummies(df_input, columns=ohe_cols_present)

    # 4. Align to training feature order (add missing, drop extra)
    df_input = df_input.reindex(columns=FEATURE_COLUMNS, fill_value=0)

    # 5. Scale continuous columns using the fitted scaler
    cols_to_scale_present = [c for c in scaled_cols if c in df_input.columns]
    df_input[cols_to_scale_present] = fitted_scaler.transform(
        df_input[cols_to_scale_present]
    )

    # 6. Predict with Logistic Regression (production model)
    pred_encoded = lr_model.predict(df_input)[0]
    pred_label   = label_encoder.inverse_transform([pred_encoded])[0]
    proba        = lr_model.predict_proba(df_input)[0]

    return {
        'prediction':  pred_label,
        'probability': {
            cls: round(float(p), 4)
            for cls, p in zip(label_encoder.classes_, proba)
        },
    }


print('predict() function defined and ready.')


# In[ ]:


# ── Demo: run predict() on a sample row from the test set ─────────────────────
import random

# Pick a random row from the original (pre-encoded) df that was in the test set
# We use X_test index to retrieve the raw features before scaling/encoding
sample_idx = X_test.index[0]

# Reconstruct raw input from the encoded test row
# (In a real system, raw_input would come directly from the API / form)
sample_raw = X_test.loc[sample_idx].to_dict()

# NOTE: Since the data is already encoded at this stage, we pass it directly.
# In production, raw string inputs (e.g. EDUCATION='GRADUATE') would be passed.
df_single   = pd.DataFrame([sample_raw]).reindex(columns=FEATURE_COLUMNS, fill_value=0)
pred_enc    = lr_model.predict(df_single)[0]
pred_label  = label_encoder.inverse_transform([pred_enc])[0]
true_label  = label_encoder.inverse_transform([y_test[0]])[0]
proba       = lr_model.predict_proba(df_single)[0]

print('\n── predict() Demo Output ──────────────────────────')
print(f'  True label      : {true_label}')
print(f'  Predicted label : {pred_label}')
print(f'  Probabilities   :')
for cls, p in zip(label_encoder.classes_, proba):
    print(f'      {cls}: {p:.4f}')


# ## 9. Gradio UI

# In[ ]:


# ── Install Gradio into the active kernel ────────────────────────────────────
import sys
get_ipython().system('{sys.executable} -m pip install --quiet gradio')
print('Gradio ready.')


# In[ ]:


import gradio as gr

# ── Gradio wrapper ────────────────────────────────────────────────────────────
def gr_predict(education, marital, last_prod, first_prod,
               income, age_oldest_tl, age_newest_tl,
               time_since_payment, time_since_enq, time_with_empr,
               max_deliq, recent_deliq):
    try:
        raw = {
            "EDUCATION":                 education,
            "MARITALSTATUS":             marital,
            "GENDER":                    "M",          # default; not in mockup
            "last_prod_enq2":            last_prod,
            "first_prod_enq2":           first_prod,
            "NETMONTHLYINCOME":          income,
            "Age_Oldest_TL":             age_oldest_tl,
            "Age_Newest_TL":             age_newest_tl,
            "time_since_recent_payment": time_since_payment,
            "time_since_recent_enq":     time_since_enq,
            "Time_With_Curr_Empr":       time_with_empr,
            "max_recent_level_of_deliq": max_deliq,
            "recent_level_of_deliq":     recent_deliq,
        }
        result = predict(raw)
        pred   = result["prediction"]

        label_map = {
            "P1": ("P1 — Top Tier",      "Approve",             "🟢"),
            "P2": ("P2 — Good",          "Approve (Conditional)","🔵"),
            "P3": ("P3 — Marginal",      "Manual Review",        "🟡"),
            "P4": ("P4 — High Risk",     "Decline",              "🔴"),
        }
        desc, rec, dot = label_map.get(pred, (pred, "Unknown", "⚪"))

        pred_text = f"PREDICTION: {desc} {dot}"
        rec_text  = f"Recommendation: {rec}"
        return pred_text, rec_text
    except Exception as e:
        return f"Error: {e}", ""


DARK_CSS = """
body, .gradio-container {
    background: #0d1117 !important;
    font-family: 'Segoe UI', system-ui, sans-serif;
}

/* ── Main header ── */
#live-header {
    text-align: center;
    padding: 28px 0 18px 0;
}
#live-header h1 {
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    color: #e6edf3;
    text-shadow: 0 0 30px rgba(88,166,255,0.25);
    margin: 0;
}

/* ── Cards ── */
.card {
    background: rgba(22, 27, 34, 0.85) !important;
    border: 1px solid rgba(48, 54, 61, 0.95) !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
    backdrop-filter: blur(8px);
}
.card-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #8b949e;
    margin-bottom: 14px;
}

/* ── Inputs ── */
label span, .gr-form label {
    color: #848d97 !important;
    font-size: 0.78rem !important;
}
input[type=number], select, .gr-dropdown select {
    background: rgba(13,17,23,0.9) !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}
input[type=range] {
    accent-color: #58a6ff;
}

/* ── Output box ── */
#output-box {
    background: rgba(22, 27, 34, 0.9) !important;
    border: 1px solid #30363d !important;
    border-radius: 14px !important;
    padding: 18px 28px !important;
    text-align: center;
    margin-top: 12px;
}
#pred-line {
    font-size: 1.25rem;
    font-weight: 700;
    color: #e6edf3;
    letter-spacing: 0.04em;
}
#rec-line {
    font-size: 1.05rem;
    color: #8b949e;
    margin-top: 6px;
}

/* ── Button ── */
#predict-btn {
    display: none !important;
}

/* ── Sliders ── */
.gr-slider input { accent-color: #58a6ff; }
"""

prod_choices = ["AL", "CC", "ConsumerLoan", "HL", "PL", "others"]
edu_choices  = ["SSC", "12TH", "GRADUATE", "UNDER GRADUATE",
                "POST-GRADUATE", "PROFESSIONAL", "OTHERS"]
mar_choices  = ["Married", "Single", "Others"]

with gr.Blocks(css=DARK_CSS, title="Live Inference Interface") as demo:

    gr.HTML('''
    <div id="live-header">
      <h1>LIVE INFERENCE INTERFACE</h1>
    </div>
    ''')

    with gr.Row(equal_height=True):

        # ── Personal Info ────────────────────────────────────────────────
        with gr.Column(elem_classes="card"):
            gr.HTML('<div class="card-title">PERSONAL INFO</div>')
            education = gr.Dropdown(edu_choices, label="Education",
                                    value="POST-GRADUATE")
            marital   = gr.Dropdown(mar_choices, label="Marital Status",
                                    value="Married")
            income    = gr.Number(label="Net Monthly Income", value=8500,
                                  precision=0)

        # ── Credit Profile ───────────────────────────────────────────────
        with gr.Column(elem_classes="card"):
            gr.HTML('<div class="card-title">CREDIT PROFILE</div>')
            last_prod     = gr.Dropdown(prod_choices, label="Last Product Enquiry",
                                        value="CC")
            first_prod    = gr.Dropdown(prod_choices, label="First Product Enquiry",
                                        value="HL")
            age_oldest_tl = gr.Slider(0, 300, value=240, step=1,
                                      label="Age of Oldest TL")
            age_newest_tl = gr.Slider(0, 120, value=12, step=1,
                                      label="Age of Newest TL")

        # ── Delinquency ──────────────────────────────────────────────────
        with gr.Column(elem_classes="card"):
            gr.HTML('<div class="card-title">DELINQUENCY</div>')
            time_since_payment = gr.Slider(0, 120, value=0, step=1,
                                           label="Months Since Last Payment")
            time_since_enq     = gr.Slider(0, 60,  value=3, step=1,
                                           label="Months Since Last Enquiry")
            time_with_empr     = gr.Slider(0, 300, value=60, step=1,
                                           label="Months With Employer")
            max_deliq          = gr.Slider(0, 10,  value=0, step=1,
                                           label="Max Delinquency Level")
            recent_deliq       = gr.Slider(0, 10,  value=0, step=1,
                                           label="Recent Delinquency Level")

    # ── Prediction output ────────────────────────────────────────────────────
    pred_text = gr.Textbox(visible=False)
    rec_text  = gr.Textbox(visible=False)

    out_html = gr.HTML('<div id="output-box">'
                       '<div id="pred-line">Adjust inputs above · prediction appears here</div>'
                       '<div id="rec-line"></div></div>')

    def update_output(education, marital, last_prod, first_prod,
                      income, age_oldest_tl, age_newest_tl,
                      time_since_payment, time_since_enq, time_with_empr,
                      max_deliq, recent_deliq):
        p, r = gr_predict(education, marital, last_prod, first_prod,
                          income, age_oldest_tl, age_newest_tl,
                          time_since_payment, time_since_enq, time_with_empr,
                          max_deliq, recent_deliq)
        return (f'<div id="output-box">'
                f'<div id="pred-line">{p}</div>'
                f'<div id="rec-line">{r}</div></div>')

    all_inputs = [education, marital, last_prod, first_prod,
                  income, age_oldest_tl, age_newest_tl,
                  time_since_payment, time_since_enq, time_with_empr,
                  max_deliq, recent_deliq]

    for inp in all_inputs:
        inp.change(fn=update_output, inputs=all_inputs, outputs=out_html)

demo.launch(server_port=7860, show_error=True)

