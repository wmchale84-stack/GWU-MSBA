# HMDA Lender Analysis

## Purpose

This project converts HMDA Loan/Application Register (LAR) data into a
clean lender-level analytical file. It rewrites the exploratory HMDA
notebook into a readable, reproducible workflow with explicit loading,
cleaning, aggregation, validation, and export steps.

## Files

-   `hmda_analysis.py` --- annotated analysis script
-   HMDA LAR CSV --- record-level application/loan data
-   HMDA institution/reference CSV --- LEI and institution information
-   `hmda_lender_analysis.csv` --- final lender-level output

## Analytical Grain

The final output contains **one row per lender/LEI**. LEI is retained as
the stable institution identifier and the institution/reference file
supplies the readable institution name.

## Workflow

``` text
HMDA LAR
   |
   v
schema inspection and cleaning
   |
   v
record-level analytical flags
   |
   v
aggregation by LEI
   |
   +---- HMDA institution/reference file
   |
   v
lender-level measures
   |
   v
validation
   |
   v
hmda_lender_analysis.csv
```

## Measures

Where the corresponding source fields are available, the script creates:

-   applications
-   originations
-   origination rate
-   total loan amount
-   average loan amount
-   median loan amount
-   average origination charges
-   average total loan costs
-   average points and fees
-   average interest rate
-   average rate spread

HMDA `action_taken = 1` is treated as an originated loan.

## Annual File Differences

HMDA public-file layouts can differ across years. The script uses
candidate column-name lists instead of assuming every release uses
exactly the same schema. Required identifiers fail clearly when missing;
optional measures are included only when their fields exist.

## Numeric Cleaning

Potential numeric fields are converted with:

``` python
pd.to_numeric(..., errors="coerce")
```

Blank, suppressed, or otherwise nonnumeric values therefore become
missing rather than being incorrectly treated as zero.

## Institution Merge

The LAR is aggregated by LEI and then joined to the
institution/reference file. The script validates the merge as
many-to-one and reports LEIs that do not obtain an institution-name
match.

## Validation

The script reports:

-   LAR row count
-   unique LEIs
-   lender rows produced
-   unmatched institution names
-   applications represented in the output
-   duplicate LEIs

The aggregated application count should reconcile to the LAR records
included in the analysis.

## Running

Install dependencies:

``` bash
pip install pandas numpy
```

Update the configuration:

``` python
DATA_DIR = Path(r"C:\path\to\hmda\data")
LAR_FILE = DATA_DIR / "hmda_lar.csv"
INSTITUTION_FILE = DATA_DIR / "hmda_institutions.csv"
```

Then run:

``` bash
python hmda_analysis.py
```

## Interpretation

HMDA is application-level mortgage data. Lender counts, averages, and
shares describe activity represented in HMDA and should not
automatically be interpreted as institution-wide market share,
profitability, credit quality, or compliance performance. Comparisons
should consider lender size, geography, product mix, applicant
populations, and reporting coverage.
