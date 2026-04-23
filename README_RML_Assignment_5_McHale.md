# Responsible Machine Learning - COMPAS ML Security Audit (Homework 5) - William McHale

## Purpose

This repository contains the ML security audit of the logistic regression and
gradient-boosted tree models built in the Lecture 05 live-coding session. Both
models predict two-year recidivism (`two_year_recid`) using seven predictors derived
from the ProPublica COMPAS dataset.

The goal of this notebook is to implement three full adversarial attack pipelines —
PGD evasion, label-flip data poisoning, and shadow-model membership inference —
measure their impact on fairness and privacy metrics, and produce audit-level findings
with concrete governance recommendations. All attacks are implemented from scratch using
only standard scientific Python libraries; no external adversarial ML library is required.

This work builds directly on Homeworks 1–4 and the Lecture 05 live-coding notebook.
The data pipeline, feature set, and model architecture are reproduced inline and match
the Lecture 05 Cell 1 setup exactly.

**NIST reference:** Vassilev et al. (2024). *Adversarial Machine Learning: A Taxonomy
and Terminology of Attacks and Mitigations.* NIST AI 100-2e2023.
https://doi.org/10.6028/NIST.AI.100-2e2023

---

## Repository Structure

```
.
├── README_HW5.md                                                    # This file
├── README_HW4.md                                                    # Homework 4 README
├── README_HW3.md                                                    # Homework 3 README
├── README_HW2.md                                                    # Homework 2 README
├── README.md                                                        # Homework 1 README
├── Lecture_01_alignment_python_MCHALE.ipynb                        # HW1 — EDA and model
├── HW2_COMPAS_Explainability_HW2_McHale_2026_03_29.ipynb           # HW2 — Explainability
├── RML_HW3_COMPAS_Disparate_Impact_Audit_McHale_2026_04_05.ipynb   # HW3 — Disparate impact
├── RML_HW4_Python_Coding_Audit_McHale_2026_04_13.ipynb             # HW4 — Robustness
└── RML_HW5_ML_Security_Audit_McHale_2026_04_30.ipynb               # HW5 — This notebook
```

---

## Python Libraries Used

| Library | Version (recommended) | Purpose |
|---|---|---|
| `pandas` | >= 1.5 | Data manipulation, filtering, groupby |
| `numpy` | >= 1.23 | Numerical operations, finite-difference gradients, PSI |
| `matplotlib` | >= 3.6 | All visualisations: ROC curves, histograms, bar charts |
| `scikit-learn` | >= 1.1 | LogisticRegression, GradientBoostingClassifier, DecisionTreeClassifier, StandardScaler, train_test_split, StratifiedShuffleSplit, roc_auc_score, RocCurveDisplay |

All libraries are pre-installed in Google Colab. No additional installation is required.

---

## How to Reproduce

1. **Clone the repository**
   ```
   git clone https://github.com/wmchade84-stack/GWU-MSBA.git
   cd GWU-MSBA
   ```

2. **Open the HW5 notebook**
   ```
   jupyter notebook RML_HW5_ML_Security_Audit_McHale_2026_04_30.ipynb
   ```
   Or upload directly to [Google Colab](https://colab.research.google.com/).

3. **Run all cells in order** (`Kernel → Restart & Run All` in Jupyter, or
   `Runtime → Run all` in Colab). The GBT numerical-gradient PGD sweep in
   Part 1 takes approximately 1–2 minutes. All other cells run in under
   30 seconds. The notebook is fully self-contained — it loads the COMPAS
   dataset directly from ProPublica's GitHub. No local data files or prior
   notebook state are required.

4. **Output files** saved to the working directory after running:
   - `pgd_evasion_audit.png` — PGD FPR, AIR, and ΔFPR curves for both models (Part 1)
   - `poisoning_audit.png` — AUC, AIR, and PSI degradation curves for both poison variants (Part 2)
   - `mi_roc_confgap.png` — MI ROC curves and confidence-gap histograms for LR and GBT (Part 3)
   - `mi_regularisation_sweep.png` — MI AUC and AIR vs L2 regularisation strength C (Part 3)

---

## Data Source

The dataset is loaded automatically from ProPublica's public GitHub repository:

```
https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv
```

No manual download is required. HW5 uses a different feature set and target variable
from HW1–HW4 to match the Lecture 05 notebook exactly (see Notable Differences below).

---

## Notable Differences from Prior Homeworks

### 1. Feature Set
HW1–HW4 used `gender_factor`, `age_factor`, `race_factor`, `priors_count`,
`crime_factor`, and `two_year_recid` as predictors. HW5 uses the Lecture 05 feature
set: `age`, `priors_count`, `juv_fel_count`, `juv_misd_count`, `juv_other_count`,
`c_charge_degree`, and `sex`, one-hot encoded via `pd.get_dummies` with `drop_first=True`.
This matches the Lecture 05 Cell 1 setup exactly so attack results are directly
comparable to the live-coding outputs discussed in class.

### 2. Target Variable
HW1–HW4 predicted `score_factor_num` (High vs Low COMPAS score). HW5 predicts
`two_year_recid` (actual two-year reoffending outcome: 0 = No, 1 = Yes), matching
the Lecture 05 setup.

### 3. Train / Test Split
HW5 uses a 70/30 stratified split (`test_size=0.3`) matching Lecture 05 Cell 1,
versus the 80/20 split used in HW4.

### 4. Model Architecture
HW5 uses raw sklearn estimators (`LogisticRegression`, `GradientBoostingClassifier`)
with a `StandardScaler` applied separately, rather than the `ColumnTransformer +
Pipeline` wrapper used in HW4. This matches the Lecture 05 notebook and simplifies
the PGD gradient computation, which requires direct access to model coefficients.

### 5. Attack Implementations
All three attack pipelines are implemented from scratch without external libraries.
The PGD attack uses the exact `sign(w)` gradient formula from Lecture 05 Cell 3 for
the LR, and a finite-difference numerical gradient approximation for the GBT. The
label-flip poisoning function is reproduced from Lecture 05 Cell 5 and extended with
a `target_race` parameter to support both AA-targeted and CA-targeted variants. The
membership inference pipeline is reproduced from Lecture 05 Cell 7 and applied to
both LR and GBT targets, with an additional L2 regularisation sweep.

---

## Analytical Pipeline Summary

1. **Setup** — load and filter COMPAS; one-hot encode `c_charge_degree` and `sex`;
   70/30 stratified split; `StandardScaler`; fit `lr` and `gbt`; establish clean-model
   fairness baseline (FPR by race, AIR)
2. **Part 1 — PGD Evasion** — white-box PGD on LR (`sign(w)` gradient, 40 iterations);
   finite-difference PGD on GBT (20 iterations); ε ∈ {0.0, 0.25, 0.5, 1.0, 2.0};
   FPR by race, AIR, and ΔFPR per ε; six-panel visualisation saved as PNG
3. **Part 2 — Poisoning Loop** — `poison_label_flip()` with `target_race` ∈
   {African-American, Caucasian}; poison rates 0–30%; AUC, AIR, FPR by race, and PSI
   per rate; stealth zone identification; three-panel visualisation saved as PNG
4. **Part 3 — Membership Inference** — 10 shadow GBT models via `StratifiedShuffleSplit`;
   `DecisionTreeClassifier(max_depth=6)` meta-classifier; MI AUC and generalisation gap
   for LR and GBT; confidence-gap histograms; L2 regularisation sweep
   C ∈ {0.01, 0.1, 1.0, 10.0}; four-panel visualisation saved as PNG
5. **Part 4 — Reflection** — highest-risk finding identified with quantified evidence;
   proactive mitigation (cryptographic data provenance, NIST AI 100-2 §4.1); reactive
   mitigation (AIR-anchored fairness monitoring); disparate impact of each mitigation

---

## Variable Reference

| Variable | Source | Description |
|---|---|---|
| `X, y, race` | HW5 Cell 0 | Full feature matrix, labels, and race array |
| `Xs_tr / Xs_te` | HW5 Cell 0 | StandardScaler-transformed train/test features |
| `y_tr / y_te` | HW5 Cell 0 | Target vectors (70/30 stratified split) |
| `r_tr / r_te` | HW5 Cell 0 | Race labels aligned to train/test splits |
| `lr` | HW5 Cell 0 | Fitted `LogisticRegression(max_iter=1000)` |
| `gbt` | HW5 Cell 0 | Fitted `GradientBoostingClassifier(n_estimators=200, max_depth=4)` |
| `BASELINE_AA` | HW5 Cell 0 | Clean LR FPR for African-American defendants (0.281) |
| `BASELINE_CA` | HW5 Cell 0 | Clean LR FPR for Caucasian defendants (0.143) |
| `BASELINE_AIR` | HW5 Cell 0 | Clean LR AIR = FPR_AA / FPR_CA = 1.961 |
| `df_pgd_lr / df_pgd_gbt` | HW5 Part 1 | PGD results table per ε for LR and GBT |
| `df_poison_aa / df_poison_ca` | HW5 Part 2 | Poisoning sweep results per rate for each variant |
| `meta_clf` | HW5 Part 3 | Trained shadow-model meta-classifier |
| `df_reg` | HW5 Part 3 | L2 regularisation sweep results (MI AUC, AIR, gen gap per C) |
