# listed_institutions_products.py

## Purpose

Builds a single table, one row per institution, for a user-supplied list
of banks and credit unions. For each institution it pulls from the FFIEC
bank Call Report and the NCUA 5300 credit union call report:

- Total assets for six quarters (3/31/2025 through 6/30/2026)
- Deposit fee income for the trailing four quarters, with the consumer
  fee breakout for banks
- Point-in-time totals (6/30/2026) for deposits, consumer auto loans,
  mortgage servicing UPB, and credit card balances and delinquency
- Percentage-of-group columns for deposits, auto, mortgage servicing,
  and credit cards, denominated by the listed population only

It also writes numbered intermediate tables to an audit folder so each
pipeline step can be checked manually.

## Requirements

Python 3.8+, pandas. Run in Jupyter with `%run
listed_institutions_products.py` or from the command line. Roughly 2 to
3 GB of disk is needed for the extracted quarterly files.

## Input files

All inputs live in one folder, set by `DATA_DIR` at the top of the
script.

1. Six FFIEC bulk zips, one per quarter, from the FFIEC Central Data
   Repository public site (cdr.ffiec.gov, Bulk Data Download, "Call
   Reports -- Single Period", tab-delimited). Expected names:
   `FFIEC CDR Call Bulk All Schedules MMDDYYYY.zip` for 03312025,
   06302025, 09302025, 12312025, 03312026, 06302026.
2. Six NCUA quarterly zips from NCUA.gov (Analysis, Credit Union and
   Corporate Call Report Data). Expected names:
   `call-report-data-YYYY-MM.zip` for 2025-03 through 2026-06.
3. `institution_list.csv`, the roster of institutions to keep. Set
   `LIST_ID_COL` to the exact header of the RSSD column and
   `LIST_TYPE_COL` to the exact header of the type column (values such
   as Bank, bank, CU, Credit Union are all accepted; set to None if the
   file has no type column). IDs are RSSDs for both banks and credit
   unions; credit union RSSDs are translated to NCUA charter numbers
   automatically using the FOICU file (see Matching logic).

The script extracts each zip into `ffiec_<date>` / `ncua_<date>`
subfolders on first run and skips extraction when a folder already
exists.

## Configuration variables

- `DATA_DIR`: folder holding the zips, the list file, and all outputs.
- `AUDIT`: True writes step tables to `DATA_DIR/audit/`; set False once
  verified.
- `LIST_FILE`, `LIST_ID_COL`, `LIST_TYPE_COL`: roster file and its
  column headers.
- `PERIODS`: the six quarters as (bank_date, ncua_date, column_label).
  To move the window forward, update all three parts of each tuple and
  download the matching zips.
- `CURRENT`: the label of the point-in-time quarter (last entry of
  PERIODS).
- `TTM_LABELS`: the three quarters whose year-to-date values feed the
  trailing-four-quarter fee calculation.
- `BANK_FEE_CODES`, `BANK_CURRENT_CODES`, `CU_CURRENT_CODES`: the field
  lists pulled from each source. Adding a code here is all that is
  needed to pull a new field; the loader finds it in whichever schedule
  file carries it.

## Source fields

Bank (FFIEC Call Report; values reported in thousands of dollars):

- RCFD2170 / RCON2170: total assets, consolidated / domestic-office.
- RIAD4080: service charges on deposit accounts (Schedule RI item 5.b),
  year-to-date.
- RIADH032, RIADH033, RIADH034, RIADH035: RI Memorandum 15.a-15.d
  breakout of RIAD4080 (consumer overdraft charges, consumer monthly
  maintenance charges, consumer ATM fees, all other service charges).
  Reported only by banks over $1 billion in assets that offer consumer
  deposit products; the four components sum to RIAD4080 for reporters.
- RCON2200: total deposits in domestic offices (Schedule RC item 13.a).
- RCONK137: consumer automobile loans outstanding (RC-C Part I item
  6.c). Excludes motorcycles, RVs, boats (item 6.d), auto leases (item
  10.a), and commercial or floor-plan vehicle lending.
- RCONB804 / RCONB805: outstanding principal balance of closed-end 1-4
  family residential mortgages serviced for others, with / without
  recourse (RC-S Memorandum 2.a / 2.b).
- RCFDB538 / RCONB538: credit card loans outstanding (RC-C item 6.a).
- RCONB575 / RCONB576 / RCONB577: credit cards past due 30-89 days
  still accruing / past due 90+ days still accruing / nonaccrual
  (RC-N item 5.a columns A, B, C).

Credit union (NCUA 5300; values reported in actual dollars):

- ACCT_010: total assets.
- ACCT_131: total fee income, year-to-date. Broader than the banks'
  deposit service charges; see Caveats.
- ACCT_018: total shares and deposits.
- ACCT_385 / ACCT_370: new / used vehicle loans outstanding.
- ACCT_779A: outstanding balance of real estate loans sold but serviced
  by the credit union.
- ACCT_396: unsecured credit card loans outstanding.
- ACCT_024B / ACCT_045B: delinquent credit card loan accounts, carried
  under their account codes; confirm each bucket's definition in the
  quarter's AcctDesc file.

## Derived columns and formulas

All dollar outputs are in actual dollars; bank values are multiplied by
1,000 during processing.

- `total_assets_<label>`: COALESCE(RCFD2170, RCON2170) x 1000 for
  banks (consolidated where reported, domestic otherwise); ACCT_010 for
  credit unions.
- `total_fees_ttm_4q`: trailing four quarters of fee income ending
  6/30/2026. RIAD and ACCT income fields are year-to-date and reset
  each January, so
  TTM = YTD(6/30/2026) + YTD(12/31/2025) - YTD(6/30/2025).
  Banks use RIAD4080; credit unions use ACCT_131.
- `RIADH032_TTM` .. `RIADH035_TTM`: same formula per component; banks
  only.
- `total_deposits_20260630`: RCON2200 x 1000 (banks) / ACCT_018 (CUs).
- `auto_loans_20260630`: RCONK137 x 1000 (banks) / ACCT_385 + ACCT_370
  (CUs; blank only when both are missing).
- `mtg_servicing_upb_20260630`: (RCONB804 + RCONB805) x 1000 (blank
  only when both are missing) / ACCT_779A.
- `cc_loans_20260630`: COALESCE(RCFDB538, RCONB538) x 1000 / ACCT_396.
- `pct_of_group_*`: institution value divided by the sum of that value
  across the matched roster, x 100. Denominators are the listed group
  only, not the full market. Each percentage column sums to
  approximately 100 across the output; the run summary prints the sums.

## Matching logic

Bank RSSD IDs and NCUA charter numbers are independent numbering
systems and can collide, and a credit union's RSSD is not its charter
number. The script therefore matches:

- Bank rows on IDRSSD equal to a listed ID typed Bank.
- Credit union rows on either the NCUA charter number or the credit
  union's RSSD, using an RSSD-to-charter crosswalk built from the FOICU
  file. The `matched_on` output column records which key matched.

`audit/step8_list_match_report.csv` lists every roster ID with its
match status and matched name.

## Outputs

- `listed_institutions_products.csv`: the final table, one row per
  matched institution, sorted by 6/30/2026 assets.
- `audit/step1_bank_raw_<label>.csv` (x6) and
  `audit/step4_cu_raw_<label>.csv` (x6): each quarter's pull as loaded.
- `audit/step2_banks_merged.csv`, `audit/step5_cus_merged.csv`: six
  quarters joined, before calculations.
- `audit/step3_banks_calculated.csv`, `audit/step6_cus_calculated.csv`:
  after TTM arithmetic and dollar conversion.
- `audit/step7_combined_all.csv`: full bank + CU universe before
  filtering (~8,700 rows).
- `audit/step8_list_match_report.csv`: roster match report.
- `audit/step9_group_filtered.csv`: the filtered group before
  percentage columns.

The run summary prints row counts per audit file, match counts by key,
percentage-column sums, and a fee reconciliation check
(H032+H033+H034+H035 versus RIAD4080 on a TTM basis for banks
reporting all four).

## Caveats

- ACCT_131 is total credit union fee income of every kind, broader than
  the banks' deposit service charges, so cross-type fee comparisons
  overstate credit union deposit-fee intensity.
- RCON2200 is domestic-office deposits; foreign-office deposits at the
  largest banks are excluded.
- The H-series consumer fee components are blank for banks under $1
  billion; blank does not mean zero.
- NCUA reportable delinquency begins at 60 days past due, so the credit
  union delinquency accounts are not comparable to the banks' 30-89 day
  bucket.
- Small banks filing the FFIEC 051 report a combined servicing figure
  (RCONFT12) instead of B804/B805 and show blank mortgage servicing
  here.
- Blank percentage inputs shrink that product's group denominator,
  which inflates remaining institutions' shares; review blanks before
  quoting shares in a small group.
- Institutions chartered mid-window show blank TTM fees (the formula
  needs the 2025 YTD values); institutions that stopped filing show
  blanks in later quarters. Both are correct behavior.

## Troubleshooting

- "codes not found" warning: the field is absent from that quarter's
  files under any casing. For NCUA fields, open the quarter's
  AcctDesc.txt (the data dictionary shipped in each zip) and search the
  description text for the item; put the live account code into
  `CU_CURRENT_CODES`.
- Zero or partial roster matches: the run prints the list file's
  columns, the raw type values, and a parsed preview. A KeyError at
  startup means `LIST_ID_COL` or `LIST_TYPE_COL` does not match the
  file's headers.
- FileNotFoundError on a zip: the file name or date portion differs
  from the `PERIODS` naming; match the names exactly or edit PERIODS.
