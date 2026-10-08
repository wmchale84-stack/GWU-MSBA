# HMDA Analysis - Clean, Annotated Workflow
# Reconstructed from the working HMDA notebook/screenshots.
#
# Purpose:
#   - load HMDA LAR and institution/reference data
#   - inspect and normalize fields
#   - aggregate records to lender/LEI level
#   - merge readable institution names
#   - calculate lender-level measures
#   - validate and export a clean CSV

from pathlib import Path
import pandas as pd
import numpy as np

# =============================================================================
# 1. CONFIGURATION
# =============================================================================
DATA_DIR = Path(r"C:\path\to\hmda\data")
LAR_FILE = DATA_DIR / "hmda_lar.csv"
INSTITUTION_FILE = DATA_DIR / "hmda_institutions.csv"
OUTPUT_FILE = DATA_DIR / "hmda_lender_analysis.csv"

# =============================================================================
# 2. HELPERS
# =============================================================================
def find_column(df, candidates, required=True):
    """Return the first matching column, allowing minor naming differences."""
    normalized = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower().replace(" ", "_")
        if key in normalized:
            return normalized[key]
    if required:
        raise KeyError("Required column not found. Tried: " + ", ".join(candidates))
    return None

def numeric(series):
    """Convert text to numeric; invalid/suppressed values become missing."""
    return pd.to_numeric(series, errors="coerce")

def safe_ratio(num, den):
    """Divide without producing infinite values when denominator is zero."""
    return num / den.replace(0, np.nan)

# =============================================================================
# 3. VERIFY AND LOAD FILES
# =============================================================================
for path in (LAR_FILE, INSTITUTION_FILE):
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

# Read identifiers as text so leading zeroes are preserved.
lar = pd.read_csv(LAR_FILE, dtype=str, low_memory=False)
inst = pd.read_csv(INSTITUTION_FILE, dtype=str, low_memory=False)

print(f"LAR rows: {len(lar):,}")
print(f"Institution rows: {len(inst):,}")
print("\nLAR columns:")
print(lar.columns.tolist())
print("\nInstitution columns:")
print(inst.columns.tolist())

# =============================================================================
# 4. LOCATE ANALYTICAL FIELDS
# =============================================================================
lar_lei = find_column(lar, ["lei"])
inst_lei = find_column(inst, ["lei"])
inst_name = find_column(
    inst, ["respondent_name", "institution_name", "legal_name", "name"]
)

loan_amount = find_column(lar, ["loan_amount", "loan_amount_000s"], required=False)
action_taken = find_column(lar, ["action_taken"], required=False)
origination_charges = find_column(lar, ["origination_charges"], required=False)
loan_costs = find_column(lar, ["total_loan_costs", "total_loan_cost"], required=False)
points_fees = find_column(lar, ["total_points_and_fees", "points_and_fees"], required=False)
interest_rate = find_column(lar, ["interest_rate"], required=False)
rate_spread = find_column(lar, ["rate_spread"], required=False)

# =============================================================================
# 5. STANDARDIZE LEI AND BUILD INSTITUTION LOOKUP
# =============================================================================
lar[lar_lei] = lar[lar_lei].astype("string").str.strip()
inst[inst_lei] = inst[inst_lei].astype("string").str.strip()

institution_lookup = (
    inst[[inst_lei, inst_name]]
    .dropna(subset=[inst_lei])
    .drop_duplicates(subset=[inst_lei])
    .rename(columns={inst_lei: "lei", inst_name: "institution_name"})
)

# =============================================================================
# 6. CLEAN NUMERIC FIELDS
# =============================================================================
for col in [
    loan_amount, action_taken, origination_charges, loan_costs,
    points_fees, interest_rate, rate_spread
]:
    if col is not None:
        lar[col] = numeric(lar[col])

# =============================================================================
# 7. CREATE RECORD-LEVEL FLAGS
# =============================================================================
# HMDA action_taken code 1 denotes an originated loan.
if action_taken is not None:
    lar["originated_flag"] = (lar[action_taken] == 1).astype(int)
else:
    lar["originated_flag"] = 1

lar["application_record"] = 1

# =============================================================================
# 8. AGGREGATE TO ONE ROW PER LENDER / LEI
# =============================================================================
grouped = lar.groupby(lar_lei, dropna=False)

summary = (
    grouped.agg(
        applications=("application_record", "sum"),
        originations=("originated_flag", "sum")
    )
    .reset_index()
    .rename(columns={lar_lei: "lei"})
)

if loan_amount is not None:
    temp = (
        grouped[loan_amount]
        .agg(total_loan_amount="sum",
             average_loan_amount="mean",
             median_loan_amount="median")
        .reset_index()
        .rename(columns={lar_lei: "lei"})
    )
    summary = summary.merge(temp, on="lei", how="left")

# Add optional pricing/cost measures only when present in the source file.
for source, output in [
    (origination_charges, "avg_origination_charges"),
    (loan_costs, "avg_total_loan_costs"),
    (points_fees, "avg_points_and_fees"),
    (interest_rate, "avg_interest_rate"),
    (rate_spread, "avg_rate_spread"),
]:
    if source is not None:
        temp = (
            grouped[source].mean().reset_index(name=output)
            .rename(columns={lar_lei: "lei"})
        )
        summary = summary.merge(temp, on="lei", how="left")

# =============================================================================
# 9. DERIVED MEASURES
# =============================================================================
summary["origination_rate"] = safe_ratio(
    summary["originations"], summary["applications"]
)
summary["origination_rate_pct"] = 100 * summary["origination_rate"]

# =============================================================================
# 10. MERGE INSTITUTION NAME
# =============================================================================
result = summary.merge(
    institution_lookup, on="lei", how="left", validate="many_to_one"
)

first = ["lei", "institution_name"]
result = result[first + [c for c in result.columns if c not in first]]

# =============================================================================
# 11. VALIDATION
# =============================================================================
print("\nVALIDATION")
print("-" * 70)
print(f"Unique LEIs in LAR: {lar[lar_lei].nunique(dropna=True):,}")
print(f"Lender rows: {len(result):,}")
print(f"Unmatched institution names: {result['institution_name'].isna().sum():,}")
print(f"Applications represented: {result['applications'].sum():,}")
print(f"Original LAR rows: {len(lar):,}")

if result["lei"].duplicated().any():
    raise ValueError("Duplicate LEIs remain in final output.")

# =============================================================================
# 12. REVIEW AND EXPORT
# =============================================================================
result = result.sort_values(
    ["applications", "originations"], ascending=[False, False]
).reset_index(drop=True)

print("\nTop lenders:")
print(result.head(20).to_string(index=False))

result.to_csv(OUTPUT_FILE, index=False)
print(f"\nHMDA output written to: {OUTPUT_FILE}")
