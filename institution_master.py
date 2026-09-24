import os
import pandas as pd

# =====================================================================
# CONFIG - set these three paths
# =====================================================================
# Call report output (from listed_institutions_products.py)
CALL_REPORT_CSV = r"listed_institutions_products.csv"
# HMDA output (from hmda_2025_lender_originations.py)
HMDA_CSV = r"lender_originations_1to4_2025.csv"
# Where to write the combined master file
OUT_CSV = r"institution_master.csv"

# =====================================================================
# 1. Load both tables
# =====================================================================
inst = pd.read_csv(CALL_REPORT_CSV)
hmda = pd.read_csv(HMDA_CSV)
print(f"Call report table: {len(inst)} institutions")
print(f"HMDA table: {len(hmda)} lenders")

# =====================================================================
# 2. Prepare HMDA: keep rows with a real RSSD, aggregate to one row
#    per RSSD (multiple LEIs can share one)
# =====================================================================
hmda["rssd"] = pd.to_numeric(hmda.get("rssd"), errors="coerce")
h = hmda[hmda["rssd"].notna() & (hmda["rssd"] > 0)].copy()
h["rssd"] = h["rssd"].astype("int64")
print(f"HMDA lenders with a real RSSD: {len(h)} "
      f"(dropped {len(hmda) - len(h)} nonbank/placeholder rows)")

num_cols = [c for c in h.columns
            if c.startswith("orig_count_") or c.startswith("orig_volume_")]

agg_spec = {c: (c, "sum") for c in num_cols}
h_agg = (h.groupby("rssd")
          .agg(n_leis_matched=("lei", "nunique"),
               hmda_lender_names=("lender_name",
                                  lambda s: "; ".join(
                                      sorted(set(s.dropna().astype(str))))),
               **agg_spec)
          .reset_index())
h_agg = h_agg.rename(columns={c: f"hmda_{c}" for c in num_cols})

# =====================================================================
# 3. Build the match key on the institution table:
#    banks -> institution_id (bank RSSD); CUs -> cu_rssd (from FOICU)
# =====================================================================
inst["match_rssd"] = pd.to_numeric(
    inst["institution_id"], errors="coerce")
is_cu = inst["institution_type"] == "Credit Union"
if "cu_rssd" in inst.columns:
    inst.loc[is_cu, "match_rssd"] = pd.to_numeric(
        inst.loc[is_cu, "cu_rssd"], errors="coerce")
else:
    print("WARNING: cu_rssd column not found; credit unions will not "
          "match HMDA data.")
inst["match_rssd"] = inst["match_rssd"].astype("Int64")

# =====================================================================
# 4. Left join and save
# =====================================================================
master = inst.merge(h_agg, left_on="match_rssd", right_on="rssd",
                    how="left").drop(columns=["rssd"])

master.to_csv(OUT_CSV, index=False)

has_hmda = master["n_leis_matched"].notna()
by_type = master.groupby("institution_type")[
    "n_leis_matched"].apply(lambda s: s.notna().sum())
print(f"Saved {len(master)} institutions to {OUT_CSV}")
print(f"  {has_hmda.sum()} matched to HMDA origination data:")
for t, n in by_type.items():
    total = (master["institution_type"] == t).sum()
    print(f"    {t}: {n} of {total}")
multi = master[master["n_leis_matched"] > 1]
if len(multi):
    print(f"  {len(multi)} institutions aggregated from multiple LEIs "
          "(see n_leis_matched / hmda_lender_names)")
big_unmatched = master[~has_hmda].nlargest(
    5, "total_assets_20260630")[["institution_name",
                                 "institution_type"]]
if len(big_unmatched):
    print("  Largest institutions with NO HMDA match (check for "
          "affiliate-LEI filing):")
    print(big_unmatched.to_string(index=False))
