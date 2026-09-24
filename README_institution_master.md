# institution_master.py

## Purpose

Joins the two finished tables into one master file, one row per listed
institution: the call report table from
`listed_institutions_products.py` (deposits, deposit fees, auto loans,
mortgage servicing, credit card items, group percentages) and the HMDA
table from `hmda_2025_lender_originations.py` (2025 origination counts
and volumes for 1-4 unit properties). No raw data is re-read; the
script runs in seconds.

## Requirements

Python 3.8+, pandas. Both upstream scripts must have been run first.

## Configuration

Three paths at the top of the script:

- `CALL_REPORT_CSV`: path to `listed_institutions_products.csv`.
- `HMDA_CSV`: path to `lender_originations_1to4_2025.csv` (typically in
  the HMDA project's `tables` folder).
- `OUT_CSV`: where to write `institution_master.csv`.

Use raw-string Windows paths (r"C:\...") when the files live in
different folders.

## Join logic

The join key is RSSD, constructed differently on each side:

Institution side. Banks match on `institution_id`, which is the bank's
RSSD. Credit unions match on the `cu_rssd` column, because their
`institution_id` is the NCUA charter number, a different numbering
system; `cu_rssd` was populated by the upstream script from the FOICU
crosswalk.

HMDA side. Rows without a real RSSD (blank, zero, or negative
placeholders, which are the nonbank lenders) are dropped before
joining. Because more than one LEI can carry the same RSSD, HMDA rows
are aggregated to one row per RSSD first: counts and volumes are
summed, lender names are concatenated into `hmda_lender_names`, and
`n_leis_matched` records how many LEIs rolled up. Without this step
the join would duplicate institution rows.

The merge is a left join from the institution table, so every listed
institution keeps its row whether or not it matched HMDA data.

## Output

`institution_master.csv`: all columns from the call report table,
followed by:

- `match_rssd`: the key used for the join
- `n_leis_matched`: number of HMDA LEIs aggregated into the row (blank
  = no HMDA match)
- `hmda_lender_names`: names of the matched HMDA filer(s)
- `hmda_orig_count_1unit` .. `hmda_orig_count_4unit`,
  `hmda_orig_volume_1unit` .. `hmda_orig_volume_4unit`,
  `hmda_orig_count_1to4_total`, `hmda_orig_volume_1to4_total`

The console prints match counts by institution type, rows aggregated
from multiple LEIs, and the five largest institutions by assets with no
HMDA match.

## Interpreting non-matches

A blank HMDA section does not always mean zero mortgage activity:

- Institutions below HMDA filing thresholds do not file at all; this
  accounts for most unmatched smaller institutions.
- Trust, custody, card, and wholesale-funded banks legitimately have no
  reportable origination business (for example custody banks and card
  monolines commonly appear unmatched).
- Some organizations originate through a separate affiliate charter
  whose LEI carries a different RSSD (for example a parent's lending
  running through a "private bank" affiliate). The volume then sits on
  a different row or outside the listed roster entirely. The
  largest-unmatched printout is the shortlist to review for this
  pattern; the CFPB HMDA data browser resolves any name in seconds.

If a mapping override becomes necessary, the clean pattern is a
two-column CSV (listed RSSD, HMDA RSSD) applied to `match_rssd` before
the merge.

## Time-frame note

The HMDA columns are calendar-2025 origination flows. The call report
columns mix a 6/30/2026 point-in-time balance sheet and a
trailing-four-quarter fee window ending 6/30/2026. The periods overlap
but do not align; the file supports cross-sectional comparison, and any
write-up should state the windows.

## Troubleshooting

- KeyError on a column name: the upstream CSVs changed shape; confirm
  both were produced by the current script versions.
- All credit unions unmatched: the call report CSV predates the
  `cu_rssd` column; rerun `listed_institutions_products.py`.
- Duplicate institution rows: should not occur given the per-RSSD
  aggregation; if seen, check for duplicate rows in the upstream
  institution CSV.
