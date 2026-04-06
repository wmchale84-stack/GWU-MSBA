# Responsible Machine Learning - COMPAS Disparate Impact Audit (Homework 3) - William McHale

## Purpose

This repository contains the disparate impact audit of the logistic regression
model built in `Lecture_01_alignment_python_MCHALE.ipynb` (Homework 1) and
explained in `HW2_COMPAS_Explainability_HW2_McHale_2026_03_29.ipynb` (Homework 2).
The model predicts whether a defendant will receive a High vs. Low COMPAS
recidivism risk score (`score_factor_num`) using six predictors derived from
the ProPublica COMPAS dataset.

The goal of this notebook is to apply four quantitative fairness metrics across
racial groups and intersectional (race × sex) subgroups, produce a
publication-quality figure, and close with a 300-word compliance memo addressed
to a hypothetical regulator. The notebook uses `solas_disparity` to independently
verify the manual AIR and SMD calculations and confirm both approaches produce
identical results.

This work builds directly on Homework 2. The cleaned COMPAS dataframe (`df`)
is loaded by downloading the HW2 notebook from its public GitHub URL and
running it directly, so no local file upload is required.

---

## Repository Structure

```
.
├── README_HW3.md                                          # This file
├── README_HW2.md                                          # Homework 2 README
├── README.md                                              # Homework 1 README
├── Lecture_01_alignment_python_MCHALE.ipynb               # HW1 — EDA and model
├── HW2_COMPAS_Explainability_HW2_McHale_2026_03_29.ipynb  # HW2 — Explainability
└── RML_HW3_COMPAS_Disparate_Impact_Audit_McHale_2026_04_05.ipynb  # HW3 — This notebook
```

---

## Python Libraries Used

| Library | Version (recommended) | Purpose |
|---|---|---|
| `pandas` | >= 1.5 | Data manipulation, groupby aggregations, cross-tabulations |
| `numpy` | >= 1.23 | Numerical operations, Cohen's d pooled standard deviation |
| `matplotlib` | >= 3.6 | Publication-quality grouped bar chart |
| `scipy` | >= 1.9 | `proportions_ztest` for statistical significance testing |
| `statsmodels` | >= 0.13 | `proportions_ztest` imported via `statsmodels.stats.proportion` |
| `solas_disparity` | latest | Independent AIR and SMD verification |

Install all dependencies with:

```
pip install pandas numpy matplotlib scipy statsmodels solas-ai-disparity
```

In a Google Colab or Jupyter environment, `pandas`, `numpy`, `matplotlib`,
`scipy`, and `statsmodels` are pre-installed. Install only the missing one with:

```
!pip install solas-ai-disparity --quiet
```

---

## How to Reproduce

1. **Clone the repository**
   ```
   git clone https://github.com/wmchale84-stack/GWU-MSBA.git
   cd GWU-MSBA
   ```

2. **Install dependencies** (see above)

3. **Open the HW3 notebook**
   ```
   jupyter notebook RML_HW3_COMPAS_Disparate_Impact_Audit_McHale_2026_04_05.ipynb
   ```
   Or upload directly to [Google Colab](https://colab.research.google.com/).

4. **Run Cell 0 first** — it installs `solas-ai-disparity`. In Google Colab,
   restart the runtime after Cell 0 completes before running the remaining cells.

5. **Run all remaining cells in order** (`Kernel → Restart & Run All` in
   Jupyter, or `Runtime → Run all` in Colab). The notebook downloads the HW2
   notebook from GitHub and executes it to build `df` — no local file upload
   is required beyond the HW3 notebook itself.

6. **Output file** saved to the working directory after running:
   - `fpr_fnr_by_race.png` — publication-quality grouped FPR/FNR bar chart

---

## Data Source

`df` is loaded by downloading the HW2 notebook from its public GitHub URL and
running it with `%run`:

```
https://raw.githubusercontent.com/wmchale84-stack/GWU-MSBA/main/HW2_COMPAS_Explainability_HW2_McHale_2026_03_29.ipynb
```

That notebook in turn loads the raw COMPAS dataset from ProPublica's public
GitHub repository:

```
https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv
```

No manual data download is required at any step.

---

## Notable Differences from Lecture 03 Code

HW3 is based on the Lecture 03 live coding notebook but corrects several bugs
and adds features not present in the original.

### 1. Indentation Bugs Fixed
The Lecture 03 `error_rates()` function had `tp`, `tn`, `fp`, `fn`, and
`results.append()` de-indented outside the `for grp, g in df.groupby(...)` loop,
which caused all metrics to be computed only for the last group. The same bug
affected `smd()` where `sc = g[score_col]` and subsequent lines were outside
the loop. Both functions are correctly indented inside their respective loops
in this notebook.

### 2. solas_disparity Import
The Lecture 03 code included a commented-out pip install line and no working
import. HW3 installs `solas-ai-disparity` in Cell 0 and imports
`solas_disparity as sd`. The AIR and SMD functions are called using
`sd.adverse_impact_ratio()` and `sd.standardized_mean_difference()` with
binary indicator columns for each racial group, matching the API's requirement
that each reference group appear only once.

### 3. Data Loading via GitHub
Rather than using a locally uploaded file, HW3 downloads the HW2 notebook
directly from its public GitHub URL using `urllib.request.urlretrieve` and
runs it with `%run HW2.ipynb`. This makes the notebook fully reproducible
without any manual file uploads.

### 4. FPR Z-Test Added
The Lecture 03 code only tested the overall selection rate difference. HW3 adds
a separate two-proportion z-test specifically on false positive rates
(non-recidivists who were flagged high-risk), which is the metric central to the
ProPublica racial bias finding.

### 5. high_risk Alias
`high_risk` is created as an alias for `score_factor_num` in Cell 1 to match
the variable naming convention used in Lecture 03, while keeping the connection
to the HW1 and HW2 target variable explicit throughout.

---

## Analytical Pipeline Summary

1. **Install** — `solas-ai-disparity` via `!pip install`
2. **Load data** — download HW2 notebook from GitHub; `%run HW2.ipynb`; create `high_risk` alias for `score_factor_num`
3. **AIR and ME** — manual `selection_rate()` function; EEOC 80% Rule flag per group
4. **Z-test (selection rate)** — two-proportion z-test on high-risk rates: African-American vs Caucasian
5. **solas_disparity verification** — `sd.adverse_impact_ratio()` and `sd.standardized_mean_difference()` confirm manual results
6. **Intersectional AIR** — race × sex subgroups; worst-group identification and interpretation
7. **SMD** — Cohen's d on `decile_score` by race; magnitude labelling (small / medium / large / very large)
8. **FPR and FNR** — `error_rates()` function; per-race confusion matrix metrics
9. **Z-test (FPR)** — two-proportion z-test on false positive rates: African-American vs Caucasian
10. **Bar chart** — publication-quality grouped FPR/FNR chart sorted by FPR; saved as PNG
11. **Compliance memo** — 300-word memo with word count assertion

---

## Variable Reference

| Variable | Source | Description |
|---|---|---|
| `df` | HW2 Cell 3 | Filtered COMPAS dataframe (6,172 rows) |
| `score_factor_num` | HW2 Cell 3 | TARGET: 0 = LowScore, 1 = HighScore |
| `high_risk` | HW3 Cell 1 | Alias for `score_factor_num`; matches Lecture 03 naming |
| `race_factor` | HW2 Cell 3 | Self-reported race as `pd.Categorical`; ref = Caucasian |
| `gender_factor` | HW2 Cell 3 | Defendant sex; ref = Male |
| `decile_score` | raw column | Continuous COMPAS score (1–10); used for SMD |
| `two_year_recid` | raw column | Actual reoffending within 2 years: 0 = No, 1 = Yes |
| `sir` | HW3 Cell 2 | Selection rate, AIR, and ME table by race |
| `smd_tbl` | HW3 Cell 6 | Cohen's d table by race |
| `er` | HW3 Cell 7 | FPR, FNR, and accuracy table by race |

---

## Expected Output Values

These are the approximate values the notebook should produce, consistent with
the ProPublica analysis and the HW1 logistic regression:

| Metric | African-American | Caucasian |
|---|---|---|
| Selection rate (`high_risk`) | ~0.576 | ~0.331 |
| AIR (vs Caucasian) | ~1.74 | 1.000 |
| FPR | ~0.448 | ~0.234 |
| FNR | ~0.280 | ~0.477 |
| Mean decile score | ~5.33 | ~3.73 |
| SMD (Cohen's d) | ~0.67 — large | reference |

The AIR for African-American defendants (~1.74) substantially exceeds 1.0,
indicating over-flagging relative to Caucasian defendants. The EEOC 80% Rule
flags groups whose selection rate falls *below* 80% of the reference group.
Here the disparity runs in the opposite direction — African-American defendants
are flagged at a much *higher* rate than Caucasian defendants, indicating adverse
impact in the form of over-surveillance rather than under-selection.
