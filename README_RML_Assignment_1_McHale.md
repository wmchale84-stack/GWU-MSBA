# COMPAS Recidivism Analysis — Python Translation & READ ME - Responsible Machine Learning - McHale - 2026.03.28

## Purpose

This repository contains a Python translation of the R-based exploratory data
analysis (EDA) and logistic regression model originally developed by ProPublica
for their investigation into racial bias in the COMPAS recidivism risk scoring
algorithm. The original R workflow was produced as part of Lecture 01.

The goal of this translation is to reproduce each step of the
original R script from data loading, cleaning, EDA, modeling, and fairness
diagnostics. To do this, I am using various Python libraries, and have tried to document any meaningful
differences between the two approaches.

---

## Repository Structure

```
.
├── README_RML_Assignment_1_McHale_2026.03.28.md
└── CODE_RML_Assignment_1_MCHALE_2026.03.28.ipynb   # Main analysis notebook
```

---

## Python Libraries Used

| Library | Purpose |
| `pandas` | Data loading, filtering, transformation, cross-tabulations |
| `numpy` | Numerical operations |
| `matplotlib` | Bar chart visualizations (replaces ggplot2 / gridExtra) |
| `seaborn` | Optional styling for plots |
| `statsmodels` | Logistic regression via `smf.logit` (replaces R's `glm`) |
| `scipy` | Statistical utilities |

Install all dependencies with:


pip install pandas numpy matplotlib seaborn statsmodels scipy

Or in a Google Colab / Jupyter environment, all libraries except `statsmodels`
are pre-installed. Install the missing one with:

pip install statsmodels

---

## How to Reproduce

1. **Clone the repository**
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>

2. **Install dependencies** (see above)

3. **Open the notebook**
   jupyter notebook Lecture_01_alignment_python.ipynb

   Or upload directly to [Google Colab](https://colab.research.google.com/).

4. **Run all cells in order** (`Kernel → Restart & Run All` in Jupyter, or
   `Runtime → Run all` in Colab). The notebook fetches the dataset directly
   from GitHub at runtime.

---

## Data Source

The dataset is loaded automatically from ProPublica's public GitHub repository:


https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv

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
