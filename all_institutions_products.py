import zipfile
import os
import glob
import pandas as pd

# =====================================================================
# CONFIG
# =====================================================================
# Folder holding all the zip files. Output CSV is written here too.
# Example: DATA_DIR = r"C:\Users\Will\Documents\callreports"
DATA_DIR = "."

# Six quarters, oldest first: (bank_date, ncua_date, column_label)
PERIODS = [
    ("03312025", "2025-03", "20250331"),
    ("06302025", "2025-06", "20250630"),
    ("09302025", "2025-09", "20250930"),
    ("12312025", "2025-12", "20251231"),
    ("03312026", "2026-03", "20260331"),
    ("06302026", "2026-06", "20260630"),
]

CURRENT = "20260630"
# YTD quarters needed for trailing-4-quarter fees:
# TTM = YTD current + YTD prior Q4 - YTD same quarter last year
TTM_LABELS = {"20250630", "20251231", "20260630"}

BANK_FEE_CODES = ["RIAD4080", "RIADH032", "RIADH033", "RIADH034"]

# Current-quarter product fields
BANK_CURRENT_CODES = [
    "RCON2200",              # total domestic deposits
    "RCONK137",              # consumer auto loans outstanding
    "RCONB804", "RCONB805",  # 1-4 family serviced for others (RC-S M2a/M2b)
]
CU_CURRENT_CODES = [
    "ACCT_018",              # total shares and deposits
    "ACCT_385", "ACCT_370",  # new + used vehicle loans outstanding
    "ACCT_779A",             # RE loans sold but serviced by the CU
]


def extract(zip_name, folder):
    if not os.path.exists(folder):
        with zipfile.ZipFile(zip_name, "r") as z:
            z.extractall(folder)


def scan_load(folder, sep, key, codes, skip_desc_row):
    """Pull key + requested codes from whichever files in folder hold them."""
    data = None
    found = set()
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        try:
            header = pd.read_csv(path, sep=sep, nrows=0)
        except Exception:
            continue
        new = [c for c in codes if c in header.columns and c not in found]
        if not new or key not in header.columns:
            continue
        df = pd.read_csv(path, sep=sep,
                         skiprows=[1] if skip_desc_row else None,
                         low_memory=False, usecols=[key] + new)
        for c in new:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        found.update(new)
        data = df if data is None else data.merge(df, on=key, how="outer")
        if found == set(codes):
            break
    missing = set(codes) - found
    if missing:
        print(f"WARNING {folder}: codes not found: {sorted(missing)}")
        for c in missing:
            data[c] = pd.NA
    return data


# =====================================================================
# 1. Banks
# =====================================================================
bank_frames = []
bank_names = {}

for bank_date, _, label in PERIODS:
    folder = os.path.join(DATA_DIR, f"ffiec_{bank_date}")
    extract(os.path.join(DATA_DIR,
            f"FFIEC CDR Call Bulk All Schedules {bank_date}.zip"), folder)

    codes = ["RCFD2170", "RCON2170"]
    if label in TTM_LABELS:
        codes += BANK_FEE_CODES
    if label == CURRENT:
        codes += BANK_CURRENT_CODES

    q = scan_load(folder, "\t", "IDRSSD", codes, skip_desc_row=True)

    q[f"total_assets_{label}"] = (
        q["RCFD2170"].fillna(q["RCON2170"]) * 1000   # thousands -> dollars
    )
    keep = ["IDRSSD", f"total_assets_{label}"]
    for c in codes:
        if c in ("RCFD2170", "RCON2170"):
            continue
        q = q.rename(columns={c: f"{c}_{label}"})
        keep.append(f"{c}_{label}")
    bank_frames.append(q[keep])

    por_matches = glob.glob(os.path.join(folder, "*POR*"))
    if por_matches:
        por = pd.read_csv(por_matches[0], sep="\t", low_memory=False)
        bank_names.update(
            dict(zip(por["IDRSSD"], por["Financial Institution Name"])))
    else:
        print(f"WARNING: no POR file found in {folder}")

banks = bank_frames[0]
for f in bank_frames[1:]:
    banks = banks.merge(f, on="IDRSSD", how="outer")

# Trailing-4-quarter fees (YTD arithmetic), converted to dollars
banks["total_fees_ttm_4q"] = (
    banks["RIAD4080_20260630"]
    + banks["RIAD4080_20251231"]
    - banks["RIAD4080_20250630"]
) * 1000

for c in ["RIADH032", "RIADH033", "RIADH034"]:
    banks[f"{c}_TTM"] = (
        banks[f"{c}_20260630"]
        + banks[f"{c}_20251231"]
        - banks[f"{c}_20250630"]
    ) * 1000

# Current-quarter product totals, converted to dollars
banks["total_deposits_20260630"] = banks["RCON2200_20260630"] * 1000
banks["auto_loans_20260630"] = banks["RCONK137_20260630"] * 1000
# Mortgage servicing UPB = RC-S M2a + M2b; NaN only if BOTH missing
banks["mtg_servicing_upb_20260630"] = (
    banks[["RCONB804_20260630", "RCONB805_20260630"]]
    .sum(axis=1, min_count=1) * 1000
)

banks = banks.rename(columns={"IDRSSD": "institution_id"})
banks["institution_name"] = banks["institution_id"].map(bank_names)
banks["institution_type"] = "Bank"

# =====================================================================
# 2. Credit unions
# =====================================================================
cu_frames = []
cu_names = {}

for _, ncua_date, label in PERIODS:
    folder = os.path.join(DATA_DIR, f"ncua_{ncua_date}")
    extract(os.path.join(DATA_DIR,
            f"call-report-data-{ncua_date}.zip"), folder)

    codes = ["ACCT_010"]
    if label in TTM_LABELS:
        codes += ["ACCT_131"]
    if label == CURRENT:
        codes += CU_CURRENT_CODES

    q = scan_load(folder, ",", "CU_NUMBER", codes, skip_desc_row=False)

    q = q.rename(columns={"ACCT_010": f"total_assets_{label}"})
    keep = ["CU_NUMBER", f"total_assets_{label}"]
    for c in codes:
        if c == "ACCT_010":
            continue
        q = q.rename(columns={c: f"{c}_{label}"})
        keep.append(f"{c}_{label}")
    cu_frames.append(q[keep])

    foicu_matches = glob.glob(os.path.join(folder, "*FOICU*"))
    if foicu_matches:
        foicu = pd.read_csv(foicu_matches[0], sep=",", low_memory=False)
        cu_names.update(dict(zip(foicu["CU_NUMBER"], foicu["CU_NAME"])))
    else:
        print(f"WARNING: no FOICU file found in {folder}")

cus = cu_frames[0]
for f in cu_frames[1:]:
    cus = cus.merge(f, on="CU_NUMBER", how="outer")

# NCUA values are already dollars; ACCT_131 is YTD like RIAD items
cus["total_fees_ttm_4q"] = (
    cus["ACCT_131_20260630"]
    + cus["ACCT_131_20251231"]
    - cus["ACCT_131_20250630"]
)

# Current-quarter product totals (already dollars)
cus["total_deposits_20260630"] = cus["ACCT_018_20260630"]
# Auto = new + used vehicle; NaN only if BOTH missing
cus["auto_loans_20260630"] = (
    cus[["ACCT_385_20260630", "ACCT_370_20260630"]]
    .sum(axis=1, min_count=1)
)
cus["mtg_servicing_upb_20260630"] = cus["ACCT_779A_20260630"]

cus = cus.rename(columns={"CU_NUMBER": "institution_id"})
cus["institution_name"] = cus["institution_id"].map(cu_names)
cus["institution_type"] = "Credit Union"

# =====================================================================
# 3. Combine; shares vs COMBINED bank + CU denominators
# =====================================================================
combined = pd.concat([banks, cus], ignore_index=True)

for col, pct in [
    ("total_deposits_20260630", "pct_of_total_deposits"),
    ("auto_loans_20260630", "pct_of_total_auto_loans"),
    ("mtg_servicing_upb_20260630", "pct_of_total_mtg_servicing"),
]:
    denom = combined[col].sum()
    combined[pct] = combined[col] / denom * 100

asset_cols = [f"total_assets_{label}" for _, _, label in PERIODS]
final_cols = (
    ["institution_id", "institution_name", "institution_type"]
    + asset_cols
    + ["total_fees_ttm_4q",
       "RIADH032_TTM", "RIADH033_TTM", "RIADH034_TTM",
       "total_deposits_20260630", "pct_of_total_deposits",
       "auto_loans_20260630", "pct_of_total_auto_loans",
       "mtg_servicing_upb_20260630", "pct_of_total_mtg_servicing"]
)

for c in final_cols:
    if c not in combined.columns:
        combined[c] = pd.NA
combined = combined[final_cols].sort_values(asset_cols[-1],
                                            ascending=False)

out_path = os.path.join(DATA_DIR, "all_institutions_products.csv")
combined.to_csv(out_path, index=False)

is_bank = combined["institution_type"] == "Bank"
print(f"Saved {len(combined)} institutions to {out_path}")
print(f"  {is_bank.sum()} banks, {(~is_bank).sum()} credit unions")
for pct in ["pct_of_total_deposits", "pct_of_total_auto_loans",
            "pct_of_total_mtg_servicing"]:
    print(f"  {pct} sums to {combined[pct].sum():.1f} (should be ~100)")
print(combined.head(10).to_string(index=False))
