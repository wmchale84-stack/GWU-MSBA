# hmda_2025_lender_originations.py

## Purpose

Aggregates the 2025 HMDA Loan/Application Register (LAR) to one row per
mortgage lender, with the count and dollar volume of originated loans
on 1-4 unit properties, broken out by number of units (1, 2, 3, 4) and
totaled. Lender name, RSSD ID, and tax ID are attached from the HMDA
Panel file when present. Covers every HMDA filer, banks, credit unions,
and nonbanks alike.

## Requirements

Python 3.8+, pandas. Memory use is flat regardless of file size because
aggregation happens inside each read chunk; the national LAR (roughly
13.5 million rows for 2025) processes in a few minutes.

## Input files

The script uses the folder layout of the base ETL: a `Data` subfolder
under the working directory, with `tables` created for output.

1. 2025 LAR file: `2025_lar.csv` or the pipe-delimited `2025_lar.txt`
   (converted to CSV automatically on first run), in `Data/` or the
   working directory. Source: FFIEC HMDA data publication
   (ffiec.cfpb.gov/data-publication), 2025 national loan-level dataset.
2. Optional: the 2025 HMDA Panel file, from the same publication page.
   Any CSV or pipe-delimited text file with "panel" in its name, placed
   in `Data/` or the working directory, is detected automatically. The
   panel supplies lender names, tax IDs, and RSSD IDs; without it the
   output is LEI-only.

## Definitions and filters

- Origination means `action_taken == 1` (loan originated) only.
  "Approved, not accepted" (code 2) is excluded because it never
  funded; codes 3-8 are excluded as non-originations.
- 1-4 family means `total_units` in {"1", "2", "3", "4"}. The field is
  text because values above 4 are ranges ("5-24"). Both site-built and
  manufactured homes are included; filter `derived_dwelling_category`
  upstream if site-built only is wanted.
- `loan_amount` is in actual dollars but is disclosed rounded to the
  midpoint of a $10,000 bucket, so lender dollar sums are approximate
  by construction. Fine for ranking and shares; not exact volume.
- Lender means LEI, the legal entity. Affiliated lenders (a bank and
  its mortgage subsidiary) file under separate LEIs and appear as
  separate rows.

## Panel merge details

Column detection on the panel file is by name: the LEI column, a
column containing "name", a column containing "rssd" (preferring the
respondent-level column over any containing "parent" or "topholder"),
and a column containing "tax". The panel is often Latin-1 encoded; the
reader tries UTF-8 and falls back to Latin-1 automatically. The console
prints which panel columns were mapped.

## Output

`tables/lender_originations_1to4_2025.csv`, one row per LEI, sorted by
total volume descending:

- `lei`, `lender_name`, `rssd`, `tax_id` (the last three only when a
  panel file was merged)
- `orig_count_1unit` .. `orig_count_4unit` and
  `orig_volume_1unit` .. `orig_volume_4unit`: origination count and
  dollar volume per unit category
- `orig_count_1to4_total`, `orig_volume_1to4_total`: sums across the
  four categories (blank only if all four are blank)

The console prints raw rows seen, originations kept, and the top ten
lenders.

## Caveats

- Nonbank lenders have no Federal Reserve RSSD; the panel carries a
  placeholder (blank, 0, or -1) for them. Tax ID is the identifier
  that populates for nonbanks.
- A blank `lender_name` on a row means the LEI filed LAR data but is
  absent from the panel file downloaded, which occasionally happens
  with late registrants.
- Depository lenders' RSSD in the panel is usually the filing bank's
  but can occasionally be a holding-company RSSD; expect a handful of
  near-misses when joining to bank-level data.
- Blank unit columns for a lender mean no originations in that bucket,
  which is common: 1-unit properties carry the overwhelming majority
  of count and volume.

## Troubleshooting

- UnicodeDecodeError on the panel read: handled automatically by the
  Latin-1 fallback; if it recurs with a different error, print
  `panel_matches` to confirm the glob did not pick up a zip or Excel
  file containing "panel" in its name.
- FileNotFoundError at startup: place `2025_lar.csv` or
  `2025_lar.txt` in `Data/` under the working directory.
- Memory pressure: lower `CHUNK_SIZE` (default 500,000 rows).
