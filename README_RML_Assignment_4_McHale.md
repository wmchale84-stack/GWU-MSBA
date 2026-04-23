# Responsible Machine Learning - COMPAS Robustness and Generalization Audit (Homework 4) - William McHale

## Purpose

This repository contains the robustness and generalization audit of the logistic
regression and gradient-boosted tree models built in the Lecture 04 live-coding session.
Both models predict whether a defendant will receive a High vs. Low COMPAS recidivism
risk score (`score_binary`) using six predictors derived from the ProPublica COMPAS dataset.

The goal of this notebook is to apply five audit techniques introduced in Lecture 04 —
distribution drift detection, generalization gap analysis, spurious-correlation probing,
stress testing, and slice-based evaluation — and to document what each reveals about
model fragility, fairness, and deployment risk. The notebook is fully self-contained:
it rebuilds the data pipeline and both models from scratch so it runs end-to-end without
any prior notebook state or file upload.

This work builds directly on Homeworks 1–3. All variable names, factor encodings, and
the target variable (`score_binary`) are carried over as defined in those notebooks.

---

## Repository Structure

```
.
├── README_HW4.md                                                    # This file
├── README_HW3.md                                                    # Homework 3 README
├── README_HW2.md                                                    # Homework 2 README
├── README.md                                                        # Homework 1 README
├── Lecture_01_alignment_python_MCHALE.ipynb                        # HW1 — EDA and model
├── HW2_COMPAS_Explainability_HW2_McHale_2026_03_29.ipynb           # HW2 — Explainability
├── RML_HW3_COMPAS_Disparate_Impact_Audit_McHale_2026_04_05.ipynb   # HW3 — Disparate impact
└── RML_HW4_Python_Coding_Audit_McHale_2026_04_13.ipynb             # HW4 — This notebook
```

---

## Python Libraries Used

| Library | Version (recommended) | Purpose |
|---|---|---|
| `pandas` | >= 1.5 | Data manipulation, groupby aggregations, cross-tabulations |
| `numpy` | >= 1.23 | Numerical operations, PSI and MMD computations |
| `matplotlib` | >= 3.6 | All visualisations: histograms, bar charts, ICE curves |
| `scipy` | >= 1.9 | `ks_2samp` for KS distribution tests |
| `scikit-learn` | >= 1.1 | LogisticRegression, GradientBoostingClassifier, StandardScaler, OneHotEncoder, ColumnTransformer, Pipeline, train_test_split, permutation_importance, roc_auc_score, confusion_matrix |

All libraries are pre-installed in Google Colab. No additional installation is required.

---

## How to Reproduce

1. **Clone the repository**
   ```
   git clone https://github.com/wmchade84-stack/GWU-MSBA.git
   cd GWU-MSBA
   ```

2. **Open the HW4 notebook**
   ```
   jupyter notebook RML_HW4_Python_Coding_Audit_McHale_2026_04_13.ipynb
   ```
   Or upload directly to [Google Colab](https://colab.research.google.com/).

3. **Run all cells in order** (`Kernel → Restart & Run All` in Jupyter, or
   `Runtime → Run all` in Colab). The notebook is fully self-contained — it
   loads the COMPAS dataset directly from ProPublica's GitHub and rebuilds
   both models from scratch. No local data files or prior notebook state
   are required.

4. **Output files** saved to the working directory after running:
   - `score_drift.png` — train vs test score distribution histograms (Part A)
   - `ice_priors_count.png` — ICE curves for `priors_count` (Part D)
   - `slice_fpr_fnr_by_race.png` — grouped FPR/FNR bar chart by race (Part E)

---

## Data Source

The dataset is loaded automatically from ProPublica's public GitHub repository:

```
https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv
```

No manual download is required. The same URL and filtering criteria are used across
HW1–HW4.

---

## Notable Differences from Prior Homeworks

HW1–HW3 used a `statsmodels` logistic regression and `pd.Categorical` factor columns
passed through a formula string. HW4 rebuilds both models using `sklearn` Pipelines
with `StandardScaler` and `OneHotEncoder`, matching the Lecture 04 live-coding notebook
exactly so that all helper functions (`psi_numeric`, `mmd_rbf`, `permutation_importance`,
`pairwise_swap_shift`, `slice_metrics`, etc.) work without modification.

### 1. Two Models
HW1–HW3 audited the logistic regression exclusively. HW4 audits both the logistic
regression (`lr_pipeline`) and the gradient-boosted tree (`gbt_pipeline`,
`GradientBoostingClassifier(n_estimators=200, max_depth=4)`) side by side across
all five audit parts, enabling direct comparison of their robustness profiles.

### 2. Self-Contained Pipeline
HW3 loaded `df` by downloading and executing the HW2 notebook via `%run`. HW4
rebuilds the full data pipeline inline so the notebook does not depend on any
other notebook being present in the Colab session.

### 3. sklearn ColumnTransformer Encoding
HW1–HW3 used `pd.get_dummies` for one-hot encoding and passed raw arrays to sklearn
models. HW4 wraps preprocessing and the classifier in a single `Pipeline` with a
`ColumnTransformer`, which is required for `permutation_importance` to operate
correctly on the original feature names.

### 4. Train / Test Split Ratio
HW1–HW3 used an 80/20 stratified split. HW4 uses the same 80/20 split, consistent
with the Lecture 04 live-coding notebook.

---

## Analytical Pipeline Summary

1. **Data pipeline** — load and filter COMPAS (6,172 rows); rebuild factor columns;
   fit `StandardScaler + OneHotEncoder` preprocessing; 80/20 stratified train/test
   split; fit `lr_pipeline` and `gbt_pipeline`
2. **Helper functions** — `psi_numeric()`, `mmd_rbf()`, `evaluate_classifier()`,
   `permutation_importance_table()`, `pairwise_swap_shift()`, `slice_metrics()`,
   `stress_test_priors()`, `plot_ice_numeric()`, `global_sensitivity_index()`
   reproduced directly from the Lecture 04 live-coding notebook
3. **Part A — Distribution Drift** — PSI and KS on `priors_count` and
   `two_year_recid`; MMD² on encoded feature space; train vs test score
   distribution histograms for both models
4. **Part B — Generalization** — train/test accuracy, AUC, log loss, and Brier
   score gaps for both models; permutation importance on train vs test to diagnose
   feature-level overfitting
5. **Part C — Spurious-Correlation Probe** — counterfactual swaps on `race_factor`
   (African-American ↔ Caucasian), `gender_factor` (Female ↔ Male), and
   `crime_factor` (F ↔ M); mean absolute probability shift per swap per model
6. **Part D — Robustness** — stress test on `priors_count` with δ ∈ {0, 2, 5, 10};
   ICE curves for both models; global sensitivity index
7. **Part E — Slice-Based Evaluation** — accuracy, AUC, Brier, FPR, and FNR by
   `race_factor`, `gender_factor`, and `age_factor` for both models; grouped FPR/FNR
   bar chart saved as PNG

---

## Variable Reference

| Variable | Source | Description |
|---|---|---|
| `df` | HW4 Cell 2 | Filtered COMPAS dataframe (6,172 rows) |
| `score_binary` | HW4 Cell 2 | TARGET: 0 = LowScore, 1 = HighScore |
| `X_train / X_test` | HW4 Cell 2 | Raw feature matrices (80/20 stratified split) |
| `y_train / y_test` | HW4 Cell 2 | Target vectors |
| `lr_pipeline` | HW4 Cell 2 | Fitted sklearn LogisticRegression Pipeline |
| `gbt_pipeline` | HW4 Cell 2 | Fitted sklearn GradientBoostingClassifier Pipeline |
| `numeric_features` | HW4 Cell 2 | `['priors_count', 'two_year_recid']` |
| `categorical_features` | HW4 Cell 2 | `['gender_factor', 'age_factor', 'race_factor', 'crime_factor']` |
| `models` | HW4 Cell 2 | Dict mapping model name to fitted pipeline |
| `input_drift_table` | HW4 Part A | PSI and KS results per numeric feature |
| `generalization_table` | HW4 Part B | Train/test metric gaps per model |
| `sensitivity_table` | HW4 Part D | Global sensitivity index per model |
