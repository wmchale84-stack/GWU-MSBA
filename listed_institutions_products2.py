import zipfile
import os
import glob
import pandas as pd

# =====================================================================
# CONFIG
# =====================================================================
# Folder holding all the zip files, the institution list, and outputs.
# Example: DATA_DIR = r"C:\Users\Will\Documents\callreports"
DATA_DIR = "."

# CSV in DATA_DIR listing the institutions to keep.
#   Preferred: columns institution_id[, institution_type]
#   (institution_type = "Bank" or "Credit Union"; recommended because
#   bank RSSD IDs and NCUA charter numbers are separate numbering
#   systems and can collide)
#   Also accepted: a plain headerless list of ID numbers.
LIST_FILE = "institution_list.csv"

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

# RIAD4080 = total service charges on deposit accounts.
# H032/H033/H034/H035 = RI Memo 15.a-15.d breakout (consumer overdraft,
# consumer maintenance, consumer ATM, all other). The four components
# reconcile to RIAD4080 for banks >$1B that report them.
BANK_FEE_CODES = ["RIAD4080", "RIADH032", "RIADH033", "RIADH034",
                  "RIADH035"]
FEE_COMPONENTS = ["RIADH032", "RIADH033", "RIADH034", "RIADH035"]

# Current-quarter product fields
BANK_CURRENT_CODES = [
    "RCON2200",              # total domestic deposits
    "RCONK137",              # consumer auto loans outstanding
    "RCONB804", "RCONB805",  # 1-4 family serviced for others (RC-S M2a/M2b)
    "RCONB538",              # credit card loans outstanding (RC-C 6.a)
    "RCONB575",              # credit cards past due 30-89, accruing (RC-N 5.a)
    "RCONB576",              # credit cards past due 90+, accruing (RC-N 5.a)
    "RCONB577",              # credit cards nonaccrual (RC-N 5.a)
]
CU_CURRENT_CODES = [
    "ACCT_018",              # total shares and deposits
    "ACCT_385", "ACCT_370",  # new + used vehicle loans outstanding
    "ACCT_779A",             # RE loans sold but serviced by the CU
    "ACCT_396",              # unsecured credit card loans outstanding
    "ACCT_397",              # all other unsecured loans/lines of credit
    "ACCT_045B",             # delinquent credit card loans, reportable total
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


def load_id_list(path):
    """Read the institution list. Returns a dataframe with institution_id
    and, if provided, institution_type."""
    df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}
    if "institution_id" in cols:
        out = pd.DataFrame({
            "institution_id": pd.to_numeric(df[cols["institution_id"]],
                                            errors="coerce")
        })
        if "institution_type" in cols:
            out["institution_type"] = (
                df[cols["institution_type"]].astype(str).str.strip()
            )
    else:
        # Headerless list of numbers: first row was read as the header
        df = pd.read_csv(path, header=None)
        out = pd.DataFrame({
            "institution_id": pd.to_numeric(df[0], errors="coerce")
        })
    out = out.dropna(subset=["institution_id"])
    out["institution_id"] = out["institution_id"].astype("int64")
    return out.drop_duplicates()


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

for c in FEE_COMPONENTS:
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
# Credit card items
banks["cc_loans_20260630"] = banks["RCONB538_20260630"] * 1000
banks["cc_past_due_30_89_20260630"] = banks["RCONB575_20260630"] * 1000
banks["cc_past_due_90plus_20260630"] = banks["RCONB576_20260630"] * 1000
banks["cc_nonaccrual_20260630"] = banks["RCONB577_20260630"] * 1000

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
# Credit card items. NCUA reportable delinquency begins at 60 days,
# so the delinquent total is NOT comparable to the banks' 30-89 bucket.
cus["cc_loans_20260630"] = cus["ACCT_396_20260630"]
cus["other_unsecured_loc_20260630"] = cus["ACCT_397_20260630"]
cus["cc_delinquent_total_20260630"] = cus["ACCT_045B_20260630"]

cus = cus.rename(columns={"CU_NUMBER": "institution_id"})
cus["institution_name"] = cus["institution_id"].map(cu_names)
cus["institution_type"] = "Credit Union"

# =====================================================================
# 3. Combine, then FILTER to the supplied institution list
# =====================================================================
combined = pd.concat([banks, cus], ignore_index=True)
combined["institution_id"] = pd.to_numeric(
    combined["institution_id"], errors="coerce").astype("Int64")

id_list = load_id_list(os.path.join(DATA_DIR, LIST_FILE))
print(f"Institution list: {len(id_list)} unique IDs loaded")

if "institution_type" in id_list.columns:
    keep_keys = set(zip(id_list["institution_id"],
                        id_list["institution_type"]))
    mask = combined.apply(
        lambda r: (r["institution_id"], r["institution_type"]) in keep_keys,
        axis=1)
    group = combined[mask].copy()
else:
    keep_ids = set(id_list["institution_id"])
    group = combined[combined["institution_id"].isin(keep_ids)].copy()
    # Flag any ID that matched both a bank and a credit union
    dup = group.groupby("institution_id")["institution_type"].nunique()
    collisions = dup[dup > 1].index.tolist()
    if collisions:
        print("WARNING: these IDs matched BOTH a bank and a credit union "
              "(add an institution_type column to your list to "
              f"disambiguate): {collisions}")

# Report listed IDs not found in the data
found_ids = set(group["institution_id"])
not_found = sorted(set(id_list["institution_id"]) - found_ids)
if not_found:
    print(f"NOTE: {len(not_found)} listed IDs not found in the data: "
          f"{not_found}")

# =====================================================================
# 4. Percentages WITHIN the listed group only
# =====================================================================
for col, pct in [
    ("total_deposits_20260630", "pct_of_group_deposits"),
    ("auto_loans_20260630", "pct_of_group_auto_loans"),
    ("mtg_servicing_upb_20260630", "pct_of_group_mtg_servicing"),
    ("cc_loans_20260630", "pct_of_group_credit_card"),
]:
    denom = group[col].sum()
    group[pct] = group[col] / denom * 100 if denom else pd.NA

asset_cols = [f"total_assets_{label}" for _, _, label in PERIODS]
fee_ttm_cols = [f"{c}_TTM" for c in FEE_COMPONENTS]
final_cols = (
    ["institution_id", "institution_name", "institution_type"]
    + asset_cols
    + ["total_fees_ttm_4q"]
    + fee_ttm_cols
    + ["total_deposits_20260630", "pct_of_group_deposits",
       "auto_loans_20260630", "pct_of_group_auto_loans",
       "mtg_servicing_upb_20260630", "pct_of_group_mtg_servicing",
       "cc_loans_20260630", "pct_of_group_credit_card",
       "cc_past_due_30_89_20260630", "cc_past_due_90plus_20260630",
       "cc_nonaccrual_20260630",
       "other_unsecured_loc_20260630", "cc_delinquent_total_20260630"]
)

for c in final_cols:
    if c not in group.columns:
        group[c] = pd.NA
group = group[final_cols].sort_values(asset_cols[-1], ascending=False)

out_path = os.path.join(DATA_DIR, "listed_institutions_products.csv")
group.to_csv(out_path, index=False)

is_bank = group["institution_type"] == "Bank"
print(f"Saved {len(group)} institutions to {out_path}")
print(f"  {is_bank.sum()} banks, {(~is_bank).sum()} credit unions")
for pct in ["pct_of_group_deposits", "pct_of_group_auto_loans",
            "pct_of_group_mtg_servicing", "pct_of_group_credit_card"]:
    print(f"  {pct} sums to {group[pct].sum():.1f} (should be ~100)")

# Reconciliation: H032+H033+H034+H035 vs RIAD4080 (TTM basis)
rec = group.loc[is_bank, fee_ttm_cols + ["total_fees_ttm_4q"]].dropna()
if len(rec):
    diff = (rec[fee_ttm_cols].sum(axis=1)
            - rec["total_fees_ttm_4q"]).abs()
    ok = (diff <= 2000).sum()
    print(f"  Fee reconciliation: {ok} of {len(rec)} reporting banks "
          "have components summing to the total (within rounding)")
print(group.to_string(index=False))
