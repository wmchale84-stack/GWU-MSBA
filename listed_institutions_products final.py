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

# Write intermediate tables for manual checking into DATA_DIR/audit/.
# Set to False once the pipeline is verified.
AUDIT = True

# CSV in DATA_DIR listing the institutions to keep.
# The script looks for: an ID column whose name contains "rssd" or "id",
# and a type column whose name contains "type" or "bank or cu"
# (values like Bank / bank / CU / Credit Union all work).
# Bank rows match on bank RSSD (IDRSSD). Credit union rows match on
# EITHER the NCUA charter number or the credit union's RSSD; the
# RSSD-to-charter crosswalk is built from the FOICU file.
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
    "RCFDB538", "RCONB538",  # credit card loans (consolidated / domestic)
    "RCONB575",              # credit cards past due 30-89, accruing (RC-N 5.a)
    "RCONB576",              # credit cards past due 90+, accruing (RC-N 5.a)
    "RCONB577",              # credit cards nonaccrual (RC-N 5.a)
]
CU_CURRENT_CODES = [
    "ACCT_018",              # total shares and deposits
    "ACCT_385", "ACCT_370",  # new + used vehicle loans outstanding
    "ACCT_779A",             # RE loans sold but serviced by the CU
    "ACCT_396",              # unsecured credit card loans outstanding
    "ACCT_024B",             # delinquent credit cards (confirm bucket in AcctDesc)
    "ACCT_045B",             # delinquent credit cards (confirm bucket in AcctDesc)
]

AUDIT_DIR = os.path.join(DATA_DIR, "audit")


def save_audit(df, name):
    """Write an intermediate table for manual checking."""
    if not AUDIT:
        return
    os.makedirs(AUDIT_DIR, exist_ok=True)
    path = os.path.join(AUDIT_DIR, name)
    df.to_csv(path, index=False)
    print(f"  [audit] {name}: {len(df)} rows x {df.shape[1]} cols")


def extract(zip_name, folder):
    if not os.path.exists(folder):
        with zipfile.ZipFile(zip_name, "r") as z:
            z.extractall(folder)


def scan_load(folder, sep, key, codes, skip_desc_row):
    """Pull key + requested codes from whichever files in folder hold
    them. Column-name matching is CASE-INSENSITIVE; requested code names
    are used for the output columns regardless of the file's casing."""
    data = None
    found = set()
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        try:
            header = pd.read_csv(path, sep=sep, nrows=0)
        except Exception:
            continue
        lookup = {c.upper(): c for c in header.columns}
        if key.upper() not in lookup:
            continue
        new = [c for c in codes
               if c.upper() in lookup and c not in found]
        if not new:
            continue
        actual_key = lookup[key.upper()]
        actual_cols = [lookup[c.upper()] for c in new]
        df = pd.read_csv(path, sep=sep,
                         skiprows=[1] if skip_desc_row else None,
                         low_memory=False,
                         usecols=[actual_key] + actual_cols)
        df = df.rename(columns={lookup[c.upper()]: c for c in new})
        df = df.rename(columns={actual_key: key})
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


def norm_type(s):
    """Normalize institution-type strings: bank/BANK -> Bank;
    cu, credit union, creditunion -> Credit Union."""
    t = str(s).strip().lower().replace("_", " ").replace("-", " ")
    if t in ("cu", "credit union", "creditunion"):
        return "Credit Union"
    if t == "bank":
        return "Bank"
    return str(s).strip()


def load_id_list(path):
    """Read the institution list. Finds the ID column (name contains
    'rssd' or 'id') and the type column (name contains 'type' or
    'bank or cu'). Falls back to a headerless single-column list."""
    df = pd.read_csv(path)
    id_col = None
    type_col = None
    for c in df.columns:
        cl = str(c).lower().strip()
        if id_col is None and ("rssd" in cl or "id" in cl):
            id_col = c
        if type_col is None and ("type" in cl or
                                 ("bank" in cl and "cu" in cl)):
            type_col = c
    if id_col is None:
        # Headerless list of numbers: first row was read as the header
        df = pd.read_csv(path, header=None)
        out = pd.DataFrame({
            "institution_id": pd.to_numeric(df[0], errors="coerce")
        })
    else:
        out = pd.DataFrame({
            "institution_id": pd.to_numeric(df[id_col], errors="coerce")
        })
        if type_col is not None:
            out["institution_type"] = df[type_col].map(norm_type)
        print(f"List columns used: id = '{id_col}'"
              + (f", type = '{type_col}'" if type_col else
                 " (no type column found)"))
    out = out.dropna(subset=["institution_id"])
    out["institution_id"] = out["institution_id"].astype("int64")
    return out.drop_duplicates()


# =====================================================================
# 1. Banks: per-quarter pulls (audit step 1)
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
    q = q[keep]
    save_audit(q, f"step1_bank_raw_{label}.csv")
    bank_frames.append(q)

    por_matches = glob.glob(os.path.join(folder, "*POR*"))
    if por_matches:
        por = pd.read_csv(por_matches[0], sep="\t", low_memory=False)
        bank_names.update(
            dict(zip(por["IDRSSD"], por["Financial Institution Name"])))
    else:
        print(f"WARNING: no POR file found in {folder}")

# ---- audit step 2: six quarters merged, before calculations ----
banks = bank_frames[0]
for f in bank_frames[1:]:
    banks = banks.merge(f, on="IDRSSD", how="outer")
save_audit(banks, "step2_banks_merged.csv")

# ---- calculations ----
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

banks["total_deposits_20260630"] = banks["RCON2200_20260630"] * 1000
banks["auto_loans_20260630"] = banks["RCONK137_20260630"] * 1000
banks["mtg_servicing_upb_20260630"] = (
    banks[["RCONB804_20260630", "RCONB805_20260630"]]
    .sum(axis=1, min_count=1) * 1000
)
banks["cc_loans_20260630"] = (
    banks["RCFDB538_20260630"].fillna(banks["RCONB538_20260630"]) * 1000
)
banks["cc_past_due_30_89_20260630"] = banks["RCONB575_20260630"] * 1000
banks["cc_past_due_90plus_20260630"] = banks["RCONB576_20260630"] * 1000
banks["cc_nonaccrual_20260630"] = banks["RCONB577_20260630"] * 1000

banks = banks.rename(columns={"IDRSSD": "institution_id"})
banks["institution_name"] = banks["institution_id"].map(bank_names)
banks["institution_type"] = "Bank"
banks["cu_rssd"] = pd.NA
save_audit(banks, "step3_banks_calculated.csv")

# =====================================================================
# 2. Credit unions: per-quarter pulls (audit step 4)
# =====================================================================
cu_frames = []
cu_names = {}
cu_rssd_map = {}     # CU_NUMBER -> RSSD, from FOICU (latest wins)

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
    q = q[keep]
    save_audit(q, f"step4_cu_raw_{label}.csv")
    cu_frames.append(q)

    foicu_matches = glob.glob(os.path.join(folder, "*FOICU*"))
    if foicu_matches:
        foicu = pd.read_csv(foicu_matches[0], sep=",", low_memory=False)
        cu_names.update(dict(zip(foicu["CU_NUMBER"], foicu["CU_NAME"])))
        # Crosswalk: FOICU carries each CU's RSSD alongside its charter
        rssd_cols = [c for c in foicu.columns
                     if "rssd" in str(c).lower()]
        if rssd_cols:
            rssd_vals = pd.to_numeric(foicu[rssd_cols[0]],
                                      errors="coerce")
            cu_rssd_map.update(
                dict(zip(foicu["CU_NUMBER"], rssd_vals)))
        else:
            print(f"WARNING: no RSSD column found in FOICU for {label}")
    else:
        print(f"WARNING: no FOICU file found in {folder}")

# ---- audit step 5: six quarters merged, before calculations ----
cus = cu_frames[0]
for f in cu_frames[1:]:
    cus = cus.merge(f, on="CU_NUMBER", how="outer")
save_audit(cus, "step5_cus_merged.csv")

# ---- calculations ----
cus["total_fees_ttm_4q"] = (
    cus["ACCT_131_20260630"]
    + cus["ACCT_131_20251231"]
    - cus["ACCT_131_20250630"]
)

cus["total_deposits_20260630"] = cus["ACCT_018_20260630"]
cus["auto_loans_20260630"] = (
    cus[["ACCT_385_20260630", "ACCT_370_20260630"]]
    .sum(axis=1, min_count=1)
)
cus["mtg_servicing_upb_20260630"] = cus["ACCT_779A_20260630"]
# NCUA reportable delinquency begins at 60 days; ACCT_024B / ACCT_045B
# kept under their account codes; confirm buckets in AcctDesc.
cus["cc_loans_20260630"] = cus["ACCT_396_20260630"]

cus = cus.rename(columns={"CU_NUMBER": "institution_id"})
cus["institution_name"] = cus["institution_id"].map(cu_names)
cus["institution_type"] = "Credit Union"
cus["cu_rssd"] = cus["institution_id"].map(cu_rssd_map).astype("Int64")
save_audit(cus, "step6_cus_calculated.csv")

# =====================================================================
# 3. Combine (audit step 7), then FILTER to the supplied list.
#    Banks match on RSSD (IDRSSD). Credit unions match on charter
#    number OR RSSD via the FOICU crosswalk.
# =====================================================================
combined = pd.concat([banks, cus], ignore_index=True)
combined["institution_id"] = pd.to_numeric(
    combined["institution_id"], errors="coerce").astype("Int64")
save_audit(combined, "step7_combined_all.csv")

id_list = load_id_list(os.path.join(DATA_DIR, LIST_FILE))
print(f"Institution list: {len(id_list)} unique IDs loaded")

has_type = "institution_type" in id_list.columns
if has_type:
    bank_ids = set(id_list.loc[
        id_list["institution_type"] == "Bank", "institution_id"])
    cu_ids = set(id_list.loc[
        id_list["institution_type"] == "Credit Union", "institution_id"])
else:
    bank_ids = set(id_list["institution_id"])
    cu_ids = set(id_list["institution_id"])

is_bank_row = combined["institution_type"] == "Bank"
bank_mask = is_bank_row & combined["institution_id"].isin(bank_ids)
cu_charter_mask = (~is_bank_row
                   & combined["institution_id"].isin(cu_ids))
cu_rssd_mask = (~is_bank_row & combined["cu_rssd"].notna()
                & combined["cu_rssd"].isin(cu_ids))
group = combined[bank_mask | cu_charter_mask | cu_rssd_mask].copy()
group["matched_on"] = "bank RSSD"
group.loc[cu_charter_mask[group.index], "matched_on"] = "CU charter"
group.loc[cu_rssd_mask[group.index]
          & ~cu_charter_mask[group.index], "matched_on"] = "CU RSSD"

if not has_type:
    dup = group.groupby("institution_id")["institution_type"].nunique()
    collisions = dup[dup > 1].index.tolist()
    if collisions:
        print("WARNING: these IDs matched BOTH a bank and a credit union "
              "(your list's type column was not detected; check its "
              f"header): {collisions}")

# ---- audit step 8: match report, one row per listed ID ----
matched_ids = set(group["institution_id"].dropna())
matched_rssds = set(group["cu_rssd"].dropna())
report = id_list.copy()
report["status"] = report["institution_id"].apply(
    lambda i: "matched" if (i in matched_ids or i in matched_rssds)
    else "NOT FOUND")
name_by_key = {}
for _, r in group.iterrows():
    name_by_key[r["institution_id"]] = r["institution_name"]
    if pd.notna(r["cu_rssd"]):
        name_by_key[r["cu_rssd"]] = r["institution_name"]
report["matched_name"] = report["institution_id"].map(name_by_key)
save_audit(report, "step8_list_match_report.csv")

not_found = report[report["status"] == "NOT FOUND"]
if len(not_found):
    nf_ids = sorted(not_found["institution_id"].tolist())
    print(f"NOTE: {len(not_found)} listed IDs not found: {nf_ids[:20]}"
          + (" ..." if len(nf_ids) > 20 else ""))

print("Match summary by key:")
print(group["matched_on"].value_counts().to_string())

# ---- audit step 9: filtered group before percentage columns ----
save_audit(group, "step9_group_filtered.csv")

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
    ["institution_id", "cu_rssd", "institution_name", "institution_type",
     "matched_on"]
    + asset_cols
    + ["total_fees_ttm_4q"]
    + fee_ttm_cols
    + ["total_deposits_20260630", "pct_of_group_deposits",
       "auto_loans_20260630", "pct_of_group_auto_loans",
       "mtg_servicing_upb_20260630", "pct_of_group_mtg_servicing",
       "cc_loans_20260630", "pct_of_group_credit_card",
       "cc_past_due_30_89_20260630", "cc_past_due_90plus_20260630",
       "cc_nonaccrual_20260630",
       "ACCT_024B_20260630", "ACCT_045B_20260630"]
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

rec = group.loc[is_bank, fee_ttm_cols + ["total_fees_ttm_4q"]].dropna()
if len(rec):
    diff = (rec[fee_ttm_cols].sum(axis=1)
            - rec["total_fees_ttm_4q"]).abs()
    ok = (diff <= 2000).sum()
    print(f"  Fee reconciliation: {ok} of {len(rec)} reporting banks "
          "have components summing to the total (within rounding)")
print(group.head(15).to_string(index=False))
