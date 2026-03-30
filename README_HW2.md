# COMPAS Recidivism Analysis — Explainability Audit (Homework 2)

## Purpose

This repository contains the explainability audit of the logistic regression
model built in `Lecture_01_alignment_python_MCHALE.ipynb` (Homework 1). The
model predicts whether a defendant will receive a High vs. Low COMPAS
recidivism risk score (`score_factor_num`) using six predictors derived from
the ProPublica COMPAS dataset.

The goal of this notebook is to apply three post-hoc explainability methods
to that mode, specifically SHAP, LIME, and DiCE and to document what the explanations
reveal about model behavior, where the methods agree and diverge, and what
monitoring is recommended for a court auditor. The notebook also includes a
300 word governance memo addressing my findings.

This work builds directly on Homework 1. All variable names, factor encodings,
and the target variable (`score_factor_num`) are carried over exactly as
defined in `Lecture_01_alignment_python_MCHALE.ipynb`.

---

## Repository Structure

```
.
├── README_HW2.md                              # This file
├── README.md                                  # Homework 1 README
├── Lecture_01_alignment_python_MCHALE.ipynb   # Homework 1 — EDA and model
└── HW2_COMPAS_Explainability.ipynb            # Homework 2 — Explainability audit
```

---

## Python Libraries Used

| Library | Version (recommended) | Purpose |
|---|---|---|
| `pandas` | >= 1.5 | Data loading, filtering, and feature matrix construction |
| `numpy` | >= 1.23 | Numerical operations |
| `matplotlib` | >= 3.6 | Visualizations: SHAP beeswarm, waterfall, LIME bar charts |
| `seaborn` | >= 0.12 | Optional plot styling |
| `statsmodels` | >= 0.13 | Refit of the HW1 logistic regression for summary reference |
| `scipy` | >= 1.9 | Statistical utilities |
| `scikit-learn` | >= 1.1 | Logistic regression refit with `.predict_proba()` interface required by SHAP, LIME, and DiCE; train/test split; one-hot encoding pipeline |
| `shap` | >= 0.42 | Global beeswarm summary plot and per-individual waterfall plots |
| `lime` | >= 0.2 | Local linear approximation explanations for four focal defendants |
| `dice-ml` | >= 0.9 | Diverse counterfactual explanations with immutable feature constraints |

Install all dependencies with:


pip install pandas numpy matplotlib seaborn statsmodels scipy \
            scikit-learn shap lime dice-ml


Or in a Google Colab / Jupyter environment, the core scientific libraries
(`pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `scikit-learn`) are
pre-installed. Install only the missing ones with:

pip install statsmodels shap lime dice-ml


---

## How to Reproduce

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```

2. **Install dependencies** (see above)

3. **Open the HW2 notebook**
   ```bash
   jupyter notebook HW2_COMPAS_Explainability.ipynb
   ```
   Or upload directly to [Google Colab](https://colab.research.google.com/).

4. **Run Cell 1 first** — it installs `shap`, `lime`, and `dice-ml`. In
   Google Colab, restart the runtime after Cell 1 completes before running
   the remaining cells.

5. **Run all remaining cells in order** (`Kernel → Restart & Run All` in
   Jupyter, or `Runtime → Run all` in Colab). The notebook is fully
   self-contained — it rebuilds the HW1 data pipeline from scratch and
   pulls the dataset directly from GitHub. No local data file or prior
   kernel state from HW1 is required.

6. **Output files** saved to the working directory after running:
   - `shap_beeswarm.png` — global beeswarm summary plot
   - `shap_waterfall_4.png` — waterfall plots for four focal defendants
   - `lime_explanations_4.png` — LIME bar charts for four focal defendants

---

## Data Source

The dataset is loaded automatically from ProPublica's public GitHub repository:

```
https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv
```

No manual download is required. The same URL is used in HW1.

---

## Notable Differences Between the HW1 and HW2 Model Implementations

HW1 fits the logistic regression using `statsmodels.formula.api.logit`.
HW2 refits the same model using `sklearn.linear_model.LogisticRegression`
because SHAP, LIME, and DiCE all require a model that exposes a
`.predict_proba()` method, which the statsmodels fitted object does not provide.

### 1. Penalty Parameter
`statsmodels` fits an unpenalised maximum likelihood estimator (MLE) by
default. `sklearn`'s `LogisticRegression` applies L2 regularisation by default.
To approximate the HW1 MLE, HW2 sets `C=1e9` (near-zero L2 penalty). With
this setting, coefficients are numerically very close to the HW1 `model_glm`
summary, but minor floating-point differences may appear.

### 2. Feature Encoding
HW1 uses `pd.Categorical` with explicit reference levels and passes factor
column names directly to the statsmodels formula string (e.g.
`"race_factor + age_factor"`). HW2 one-hot encodes the underlying raw columns
(`race`, `age_cat`, `sex`, `c_charge_degree`) using `pd.get_dummies` with
`drop_first=False`, producing named dummy columns (e.g. `race_African-American`,
`age_cat_Less than 25`) that SHAP and LIME can label directly in their plots.

### 3. Reference Level Handling
In HW1, reference levels are set by ordering the `pd.Categorical` category
list (first category = reference). In HW2's sklearn pipeline, `OneHotEncoder`
with `drop="first"` drops the reference level for model fitting, matching the
implicit baseline used by HW1's statsmodels formula interface.

### 4. Train / Test Split
HW1 fits the model on the full 6,172-row filtered dataset (no held-out set)
because the goal was to reproduce the R script's in-sample coefficients. HW2
introduces an 80/20 stratified train/test split so that SHAP and LIME
explanations are computed on held-out data the model has not seen — reflecting
genuine out-of-sample behavior.

### 5. Model Summary Format
The HW1 statsmodels `.summary()` output includes AIC, BIC, log-likelihood,
and a covariance type note in addition to coefficients. The HW2 sklearn model
does not produce a comparable summary table; instead, `classification_report`
is printed on the test set. The HW1 statsmodels model is also refit in Cell 4
of HW2 solely to display the full summary for reference.

### 6. SHAP Explainer Choice
`shap.LinearExplainer` is used rather than `KernelExplainer` because the
underlying model is a logistic regression. `LinearExplainer` computes exact
Shapley values analytically from the model weights and training feature
covariance — no sampling is required and results are deterministic.
`KernelExplainer` would also work but is slower and approximate.

### 7. DiCE Counterfactual Backend
DiCE is given a sklearn `Pipeline` (preprocessor + logistic regression) rather
than the raw fitted model. This is required because DiCE's random counterfactual
method needs to call the model on original-space (pre-encoded) feature vectors.
The pipeline handles encoding internally, allowing DiCE to propose changes to
human-readable feature values (e.g. `age_cat = "Less than 25"`) rather than
binary dummy columns.

---

## Analytical Pipeline Summary

1. **Reproduce HW1 pipeline** — reload and filter the COMPAS dataset (6,172
   rows); rebuild all HW1 factor columns (`gender_factor`, `age_factor`,
   `race_factor`, `crime_factor`, `score_factor`, `score_factor_num`)
2. **Refit HW1 statsmodels model** — for coefficient reference and comparison
3. **Build sklearn feature matrix** — one-hot encode categorical predictors;
   split 80/20 into train and test sets; fit `LogisticRegression(C=1e9)`
4. **SHAP** — compute `LinearExplainer` values on the test set; produce
   global beeswarm summary and waterfall plots for four focal defendants
5. **LIME** — fit local linear approximations for the same four defendants;
   plot top-10 feature weights; compare SHAP vs LIME top-5 rankings
6. **DiCE** — generate three diverse counterfactuals per defendant with
   `race` and `sex` locked as immutable; flag any constraint violations;
   report minimal feature changes required to flip `score_factor_num`
7. **Governance memo** — 300-word memo summarizing model behavior,
   explanation method limitations, and three monitoring recommendations

---

## Variable Reference

The table below maps every key variable in HW2 back to its origin in HW1.

| HW2 variable / column | HW1 origin | Plain-English description |
|---|---|---|
| `score_factor_num` | HW1 Cell 24 target | **TARGET**: 0 = LowScore, 1 = HighScore |
| `score_factor` | HW1 Cell 5 | Categorical label: LowScore \| HighScore |
| `gender_factor` | HW1 Cell 5 | Defendant sex; ref = Male |
| `age_factor` | HW1 Cell 5 | Age bracket; ref = 25–45 |
| `race_factor` | HW1 Cell 5 | Self-reported race; ref = Caucasian |
| `crime_factor` | HW1 Cell 5 | Charge severity: F = Felony, M = Misdemeanor |
| `priors_count` | HW1 raw column | Number of prior convictions (integer, 0–38) |
| `two_year_recid` | HW1 raw column | Reoffended within 2 years: 0 = No, 1 = Yes |
| `sex` | source of `gender_factor` | Male \| Female |
| `age_cat` | source of `age_factor` | Less than 25 \| 25 - 45 \| Greater than 45 |
| `race` | source of `race_factor` | African-American \| Asian \| Caucasian \| Hispanic \| Native American \| Other |
| `c_charge_degree` | source of `crime_factor` | F (Felony) \| M (Misdemeanor) |
| `score_text` | source of `score_factor` | Low \| Medium \| High (raw COMPAS label) |
