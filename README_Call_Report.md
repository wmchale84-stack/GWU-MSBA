# FFIEC Bank + NCUA Credit Union Call Report Product Analysis

## Purpose

This project builds a combined bank and credit-union product dataset for
a specified list of institutions.

It uses the **FFIEC Call Report bulk All Schedules files for banks** and
the **NCUA Call Report files for credit unions**, retains six quarters
of total assets, calculates selected current-period product balances,
calculates trailing-four-quarter fee measures, matches the results to a
supplied institution list, and produces group-level product shares.

The cleaned script is:

`call_report_analysis.py`

The final analytical output is:

`listed_institutions_products.csv`

## Source of This Version

This version is a documented rewrite of the working
`listed_institutions_products final.py` analysis. The analytical
formulas, FFIEC MDRM codes, NCUA account codes, institution-matching
logic, audit outputs, and final output fields have been preserved.

## Analysis Period

The script uses six quarters:

  Quarter End   FFIEC bank date   NCUA date
  ------------- ----------------- -----------
  2025 Q1       `03312025`        `2025-03`
  2025 Q2       `06302025`        `2025-06`
  2025 Q3       `09302025`        `2025-09`
  2025 Q4       `12312025`        `2025-12`
  2026 Q1       `03312026`        `2026-03`
  2026 Q2       `06302026`        `2026-06`

The current-quarter product measures are based on **June 30, 2026**.

## Required Inputs

Place the input files in `DATA_DIR`.

### Institution list

`institution_list.csv`

The working configuration expects:

``` text
rssd
bank or cu
```

The loader also attempts to detect reasonable ID/type column names
automatically.

### FFIEC bank files

For each bank quarter, the script expects a ZIP named like:

``` text
FFIEC CDR Call Bulk All Schedules 03312025.zip
FFIEC CDR Call Bulk All Schedules 06302025.zip
...
FFIEC CDR Call Bulk All Schedules 06302026.zip
```

The ZIPs are extracted into quarter-specific `ffiec_...` folders.

The script scans the tab-delimited schedule files for the requested MDRM
fields and joins them by `IDRSSD`.

### NCUA credit-union files

For each credit-union quarter, the script expects a ZIP named like:

``` text
call-report-data-2025-03.zip
call-report-data-2025-06.zip
...
call-report-data-2026-06.zip
```

The ZIPs are extracted into quarter-specific `ncua_...` folders.

The script scans the comma-delimited files for requested NCUA account
codes and joins them by `CU_NUMBER`.

## Important FFIEC Form Note

The bank side uses the **FFIEC CDR Call Bulk All Schedules** download
and retrieves the required MDRM fields by `IDRSSD`.

The script itself does **not** contain a separate filter that limits
records to a particular Call Report form number. Therefore, although the
analysis includes the bank Call Report data and fields used for the
intended FFIEC 041 analysis, the code should not be described as
programmatically excluding institutions solely because they file another
Call Report form. The bulk schedules and availability of the requested
MDRMs determine what is loaded.

## Bank Measures

### Total assets

For every quarter, the script requests:

-   `RCFD2170`
-   `RCON2170`

It uses consolidated `RCFD2170` when available and falls back to
domestic `RCON2170`.

``` text
Total Assets = RCFD2170, otherwise RCON2170
```

Bank Call Report values are multiplied by **1,000** because these fields
are reported in thousands of dollars.

### Deposit-account service charges

The analysis uses:

-   `RIAD4080` --- total service charges on deposit accounts
-   `RIADH032`
-   `RIADH033`
-   `RIADH034`
-   `RIADH035`

The H032--H035 fields are the four Memo 15.a--15.d components used in
the working analysis:

-   consumer overdraft-related fees
-   consumer account maintenance fees
-   consumer ATM fees
-   all other deposit-account service charges

For reporting banks, the components can be reconciled to total service
charges.

### Trailing-four-quarter fee calculation

The source fields are year-to-date income-statement values, so the
script constructs the trailing four quarters as:

``` text
TTM =
2026 Q2 YTD
+ 2025 Q4 YTD
- 2025 Q2 YTD
```

For total fees:

``` text
RIAD4080_20260630
+ RIAD4080_20251231
- RIAD4080_20250630
```

The same formula is applied separately to H032--H035.

The result is multiplied by 1,000 to convert bank values to dollars.

## Current Bank Product Fields

For June 30, 2026, the script retrieves:

  MDRM         Use in analysis
  ------------ ------------------------------------------------
  `RCON2200`   Total domestic deposits
  `RCONK137`   Consumer auto loans outstanding
  `RCONB804`   1--4 family mortgage servicing component
  `RCONB805`   1--4 family mortgage servicing component
  `RCFDB538`   Consolidated credit-card loans
  `RCONB538`   Domestic credit-card loans fallback
  `RCONB575`   Credit cards past due 30--89 days and accruing
  `RCONB576`   Credit cards past due 90+ days and accruing
  `RCONB577`   Credit cards in nonaccrual status

Mortgage servicing UPB is:

``` text
RCONB804 + RCONB805
```

Credit-card loans use:

``` text
RCFDB538
```

with:

``` text
RCONB538
```

as the fallback when the consolidated field is missing.

## Credit-Union Measures

### Total assets

For each of the six quarters:

`ACCT_010`

### Deposit/share fee measure

For the periods required to construct trailing-four-quarter fees:

`ACCT_131`

The credit-union TTM calculation is:

``` text
ACCT_131_20260630
+ ACCT_131_20251231
- ACCT_131_20250630
```

### Current credit-union product fields

For June 30, 2026:

  -----------------------------------------------------------------------
  NCUA account                        Use in analysis
  ----------------------------------- -----------------------------------
  `ACCT_018`                          Total shares and deposits

  `ACCT_385`                          Vehicle-loan component

  `ACCT_370`                          Vehicle-loan component

  `ACCT_779A`                         Real-estate loans sold but serviced
                                      by the CU

  `ACCT_396`                          Unsecured credit-card loans
                                      outstanding

  `ACCT_024B`                         Credit-card delinquency field
                                      retained under account code

  `ACCT_045B`                         Credit-card delinquency field
                                      retained under account code
  -----------------------------------------------------------------------

Auto loans are calculated as:

``` text
ACCT_385 + ACCT_370
```

The working code intentionally does **not** rename `ACCT_024B` and
`ACCT_045B` to specific delinquency buckets. Their exact bucket
definitions should be confirmed against the applicable `AcctDesc` before
relabeling.

## Credit-Union RSSD Crosswalk

The script reads the quarterly `FOICU` file.

It uses:

-   `CU_NUMBER` for the credit-union charter
-   `CU_NAME` for the institution name
-   the RSSD field found in FOICU for the charter-to-RSSD crosswalk

This allows a credit union in the supplied institution list to be
matched either by its charter number or by RSSD.

## Institution Matching

After the bank and credit-union data are calculated, they are
concatenated.

Banks are matched using:

``` text
Bank -> IDRSSD
```

Credit unions can match using:

``` text
Credit Union -> CU_NUMBER
```

or:

``` text
Credit Union -> RSSD from FOICU
```

The final data includes a `matched_on` field showing whether the row
matched through:

-   `bank RSSD`
-   `CU charter`
-   `CU RSSD`

If the institution list does not include a detected bank/CU type field,
the script warns when the same numeric ID matches both a bank and a
credit union.

## Group Product Percentages

Percentages are calculated **only after filtering to the supplied
institution list**.

For each product:

``` text
Institution Product Balance
----------------------------- × 100
Sum for Matched Institution Group
```

The output contains:

-   `pct_of_group_deposits`
-   `pct_of_group_auto_loans`
-   `pct_of_group_mtg_servicing`
-   `pct_of_group_credit_card`

Each percentage column should sum to approximately **100%** across the
matched group.

These measures are therefore **shares within the selected institution
group**, not shares of the entire U.S. banking or credit-union market.

## Audit Files

When:

``` python
AUDIT = True
```

the script writes intermediate CSVs into:

``` text
DATA_DIR/audit/
```

The audit sequence is:

1.  `step1_bank_raw_[quarter].csv`
2.  `step2_banks_merged.csv`
3.  `step3_banks_calculated.csv`
4.  `step4_cu_raw_[quarter].csv`
5.  `step5_cus_merged.csv`
6.  `step6_cus_calculated.csv`
7.  `step7_combined_all.csv`
8.  `step8_list_match_report.csv`
9.  `step9_group_filtered.csv`

These files make it possible to trace a final value back through each
stage of the pipeline.

## Final Output

The script writes:

`listed_institutions_products.csv`

The output contains institution identifiers, institution names/types,
six quarters of total assets, fee measures, current product balances,
product shares, and credit-card delinquency fields.

Key columns include:

``` text
institution_id
cu_rssd
institution_name
institution_type
matched_on
total_assets_20250331
total_assets_20250630
total_assets_20250930
total_assets_20251231
total_assets_20260331
total_assets_20260630
total_fees_ttm_4q
RIADH032_TTM
RIADH033_TTM
RIADH034_TTM
RIADH035_TTM
total_deposits_20260630
pct_of_group_deposits
auto_loans_20260630
pct_of_group_auto_loans
mtg_servicing_upb_20260630
pct_of_group_mtg_servicing
cc_loans_20260630
pct_of_group_credit_card
cc_past_due_30_89_20260630
cc_past_due_90plus_20260630
cc_nonaccrual_20260630
ACCT_024B_20260630
ACCT_045B_20260630
```

## Validation Checks

The working script performs several useful checks.

### Missing MDRM/account codes

If a requested field is not found in the extracted schedule files, the
script prints a warning and creates the field as missing rather than
silently substituting another measure.

### Institution-list match report

`step8_list_match_report.csv` identifies every supplied institution ID
as:

``` text
matched
```

or:

``` text
NOT FOUND
```

### Product-share reconciliation

The script prints the sum of each group percentage column. Each should
be approximately:

``` text
100.0
```

### Bank fee reconciliation

For banks with all required fields, the script compares:

``` text
RIADH032_TTM
+ RIADH033_TTM
+ RIADH034_TTM
+ RIADH035_TTM
```

against:

``` text
total_fees_ttm_4q
```

A difference of no more than **\$2,000** is treated as reconciled to
allow for reporting/rounding differences.

## Running the Script

Required Python package:

``` bash
pip install pandas
```

Set:

``` python
DATA_DIR = r"C:\your\callreport\folder"
```

Place the FFIEC ZIP files, NCUA ZIP files, and `institution_list.csv` in
that folder.

Then run:

``` bash
python call_report_analysis.py
```

During validation, leave:

``` python
AUDIT = True
```

Once the workflow is established and the audit files are no longer
needed for every run, it can be changed to:

``` python
AUDIT = False
```

## Interpretation Notes

Bank and credit-union reporting systems are not identical. The script
intentionally maps conceptually similar products into common final
columns, but users should retain the underlying regulatory definitions
when interpreting comparisons.

In particular:

-   FFIEC bank fields reported in thousands are converted to dollars.
-   NCUA values are used as supplied in the NCUA data.
-   Bank fee components are available only for institutions that report
    the relevant memo items.
-   Bank and CU mortgage-servicing definitions are based on the exact
    fields selected in the working analysis and should not be assumed to
    represent every possible servicing category.
-   NCUA reportable delinquency conventions differ from the bank Call
    Report convention.
-   Group percentages describe only the supplied institution group.
-   Missing values should not automatically be interpreted as zero.

## Reproducibility

For a reproducible run, retain together:

1.  `call_report_analysis.py`
2.  `README_Call_Report.md`
3.  `institution_list.csv`
4.  the six FFIEC bulk ZIP files
5.  the six NCUA Call Report ZIP files
6.  the generated audit folder
7.  `listed_institutions_products.csv`

This preserves the complete path from the regulatory source files to the
final institution/product comparison dataset.
