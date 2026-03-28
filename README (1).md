# COMPAS Recidivism Analysis — Python Translation

## Purpose

This repository contains a Python translation of the R-based exploratory data
analysis (EDA) and logistic regression model originally developed by ProPublica
for their investigation into racial bias in the COMPAS recidivism risk scoring
algorithm. The original R workflow was produced as part of Lecture 01 of *The
Alignment Problem* course.

The goal of this translation is to reproduce every analytical step of the
original R script — data loading, cleaning, EDA, modeling, and fairness
diagnostics — using idiomatic Python libraries, and to document any meaningful
differences between the two implementations.

---

## Repository Structure

```
.
├── README.md
└── Lecture_01_alignment_python.ipynb   # Main analysis notebook
```

---

## Python Libraries Used

| Library | Version (recommended) | Purpose |
|---|---|---|
| `pandas` | >= 1.5 | Data loading, filtering, transformation, cross-tabulations |
| `numpy` | >= 1.23 | Numerical operations |
| `matplotlib` | >= 3.6 | Bar chart visualizations (replaces ggplot2 / gridExtra) |
| `seaborn` | >= 0.12 | Optional styling for plots |
| `statsmodels` | >= 0.13 | Logistic regression via `smf.logit` (replaces R's `glm`) |
| `scipy` | >= 1.9 | Statistical utilities |

Install all dependencies with:

```bash
pip install pandas numpy matplotlib seaborn statsmodels scipy
```

Or in a Google Colab / Jupyter environment, all libraries except `statsmodels`
are pre-installed. Install the missing one with:

```bash
pip install statsmodels
```

---

## How to Reproduce

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```

2. **Install dependencies** (see above)

3. **Open the notebook**
   ```bash
   jupyter notebook Lecture_01_alignment_python.ipynb
   ```
   Or upload directly to [Google Colab](https://colab.research.google.com/).

4. **Run all cells in order** (`Kernel → Restart & Run All` in Jupyter, or
   `Runtime → Run all` in Colab). The notebook fetches the dataset directly
   from GitHub at runtime — no local data file is needed.

---

## Data Source

The dataset is loaded automatically from ProPublica's public GitHub repository:

```
https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv
```

No manual download is required.

---

## Notable Differences Between R and Python Implementations

### 1. Dependent Variable for Logistic Regression
R's `glm()` accepts a factor column as the response and automatically treats
the non-reference level as the positive class. `statsmodels.formula.api.logit`
requires a numeric `0`/`1` column. The notebook creates `score_factor_num`
(0 = LowScore, 1 = HighScore) from `score_factor` before fitting the model.

### 2. Reference Level Encoding for Categorical Predictors
R uses `relevel()` to designate a baseline factor level. In Python, the first
category in a `pd.Categorical`'s category list is used as the reference by
`statsmodels`. The notebook sets reference levels by placing the reference
value first in the `categories` list when constructing each `pd.Categorical`.

### 3. Model Summary Output Format
R's `summary.glm()` prints coefficient estimates, standard errors, z-values,
and p-values in a compact table with significance stars. `statsmodels`'
`.summary()` produces a more detailed table that additionally includes
confidence intervals, the log-likelihood, AIC/BIC, and a covariance type note.
Coefficient values and significance levels should match; formatting differs.

### 4. Correlation Function
R's `cor(x, y)` computes Pearson correlation by default. Python's
`pd.Series.corr()` also defaults to Pearson — results are equivalent.

### 5. Date Arithmetic
R computes jail length with `as.numeric(as.Date(out) - as.Date(in))`, which
truncates to whole days at midnight. Python replicates this with
`.dt.normalize()` (floors to midnight) before differencing, then `.dt.days`
to extract the integer day count. Results are equivalent.

### 6. Cross-tabulation Display
R's `xtabs()` prints a formatted contingency table with dimension labels.
`pd.crosstab()` returns a DataFrame with the same values but rendered as a
standard pandas table. Output is functionally identical.

---

## Analytical Pipeline Summary

1. **Load** raw COMPAS data (7,214 rows)
2. **Filter** to analysis-ready rows (±30-day charge window, valid recidivism
   flag, no traffic-only charges, no missing COMPAS score) → 6,172 rows
3. **Transform** datetime columns, encode categorical predictors with explicit
   reference levels
4. **EDA** — demographic breakdowns, score distributions, decile bar charts,
   length-of-stay correlation
5. **Model** — logistic regression predicting High vs. Low COMPAS score from
   gender, age, race, prior counts, charge degree, and two-year recidivism
6. **Evaluate** — overall and per-race confusion matrices; Accuracy, Precision,
   Recall, FPR, FNR; disparity deltas relative to Caucasian baseline

---

## Homework 2 — COMPAS Explainability

### Additional Dependencies

```bash
pip install shap lime dice-ml scikit-learn
```

| Library | Purpose |
|---|---|
| `scikit-learn` | Refits the logistic regression with a `.predict_proba()` interface required by SHAP, LIME, and DiCE |
| `shap` | Global beeswarm summary + individual waterfall plots |
| `lime` | Local linear explanations for four focal individuals |
| `dice-ml` | Diverse counterfactual explanations with immutable feature constraints |

### How to Run HW2

1. Open `HW2_COMPAS_Explainability.ipynb` in Colab or Jupyter
2. Run **Cell 1** first (installs libraries); restart runtime in Colab after
3. Run all remaining cells in order — the notebook is fully self-contained and fetches data from GitHub at runtime
4. Output images (`shap_beeswarm.png`, `shap_waterfall_4.png`, `lime_explanations_4.png`) will be saved in the working directory

### Notable Design Decisions (HW2)

- **sklearn vs statsmodels**: SHAP, LIME, and DiCE all require `.predict_proba()`, which statsmodels' fitted logit object does not expose. The model is refit in sklearn with `C=1e9` (near-zero L2 penalty) to match the unpenalised MLE from HW1 as closely as possible.
- **Immutable features**: `race` and `sex` are excluded from DiCE's `features_to_vary` parameter. Any counterfactual that changes these features would be ethically impermissible and is flagged as a constraint violation.
- **Four focal individuals**: The highest- and lowest-risk defendant in each of the two primary racial groups from the ProPublica analysis (African-American, Caucasian), selected from the held-out test set only.
