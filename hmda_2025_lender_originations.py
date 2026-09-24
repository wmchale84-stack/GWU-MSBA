import os
import csv
import glob
import pandas as pd

# =====================================================================
# 0. Paths (same layout as the base ETL)
# =====================================================================
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "Data")
TABLES_DIR = os.path.join(BASE_DIR, "tables")
os.makedirs(TABLES_DIR, exist_ok=True)

# =====================================================================
# 1. Resolve the 2025 LAR file (convert pipe-delimited txt if needed)
# =====================================================================
raw_candidates = [
    os.path.join(DATA_DIR, "2025_lar.csv"),
    os.path.join(BASE_DIR, "2025_lar.csv"),
]
txt_candidates = [
    os.path.join(DATA_DIR, "2025_lar.txt"),
    os.path.join(BASE_DIR, "2025_lar.txt"),
]

RAW_PATH = next((p for p in raw_candidates if os.path.exists(p)), None)
TXT_PATH = next((p for p in txt_candidates if os.path.exists(p)), None)

if RAW_PATH is None and TXT_PATH is not None:
    RAW_PATH = os.path.join(os.path.dirname(TXT_PATH), "2025_lar.csv")
    print(f"Converting text file to CSV: {TXT_PATH} -> {RAW_PATH}")
    with open(TXT_PATH, "r", newline="") as fin, \
         open(RAW_PATH, "w", newline="") as fout:
        reader = csv.reader(fin, delimiter="|")
        writer = csv.writer(fout)
        writer.writerows(reader)

if RAW_PATH is None:
    raise FileNotFoundError(
        "Could not find 2025_lar.csv or 2025_lar.txt in Code/ or "
        "Code/Data/. Place the raw 2025 HMDA file there first.")

print(f"Using raw file: {RAW_PATH}")

# =====================================================================
# 2. Chunked aggregation
#    Originations only (action_taken == 1); 1-4 unit properties.
#    Aggregate inside each chunk so memory stays flat.
# =====================================================================
KEEP_COLS = ["lei", "action_taken", "total_units", "loan_amount"]
UNIT_VALUES = ["1", "2", "3", "4"]
CHUNK_SIZE = 500_000

partials = []
total_raw = 0
total_kept = 0

for chunk in pd.read_csv(RAW_PATH, usecols=KEEP_COLS,
                         low_memory=False, chunksize=CHUNK_SIZE):
    total_raw += len(chunk)

    chunk = chunk[chunk["action_taken"] == 1]
    chunk["total_units"] = chunk["total_units"].astype(str).str.strip()
    chunk = chunk[chunk["total_units"].isin(UNIT_VALUES)]
    chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"],
                                         errors="coerce")
    total_kept += len(chunk)

    part = (chunk.groupby(["lei", "total_units"])
                 .agg(n=("loan_amount", "size"),
                      vol=("loan_amount", "sum"))
                 .reset_index())
    partials.append(part)
    print(f"  Processed {total_raw:,} rows | kept {total_kept:,}",
          end="\r")

agg = (pd.concat(partials, ignore_index=True)
         .groupby(["lei", "total_units"])
         .agg(n=("n", "sum"), vol=("vol", "sum"))
         .reset_index())
print(f"\nDone. Raw rows seen: {total_raw:,}; "
      f"originations kept (1-4 units): {total_kept:,}")

# =====================================================================
# 3. Pivot wide: per lender, count + volume for units 1..4 and total
# =====================================================================
wide_n = agg.pivot(index="lei", columns="total_units", values="n")
wide_v = agg.pivot(index="lei", columns="total_units", values="vol")

out = pd.DataFrame(index=wide_n.index)
for u in UNIT_VALUES:
    out[f"orig_count_{u}unit"] = wide_n.get(u)
    out[f"orig_volume_{u}unit"] = wide_v.get(u)

count_cols = [f"orig_count_{u}unit" for u in UNIT_VALUES]
vol_cols = [f"orig_volume_{u}unit" for u in UNIT_VALUES]
out["orig_count_1to4_total"] = out[count_cols].sum(axis=1, min_count=1)
out["orig_volume_1to4_total"] = out[vol_cols].sum(axis=1, min_count=1)

out = out.reset_index()

# =====================================================================
# 4. Optional: lender names from the HMDA Panel file, if present
# =====================================================================
panel_matches = (glob.glob(os.path.join(DATA_DIR, "*panel*"))
                 + glob.glob(os.path.join(BASE_DIR, "*panel*")))
panel_matches = [p for p in panel_matches
                 if p.lower().endswith((".csv", ".txt"))]
if panel_matches:
    ppath = panel_matches[0]
    sep = "|" if ppath.lower().endswith(".txt") else ","
    try:
        panel = pd.read_csv(ppath, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        print("Panel file is not UTF-8; retrying with latin-1 encoding")
        panel = pd.read_csv(ppath, sep=sep, low_memory=False,
                            encoding="latin-1")
    lei_col = next((c for c in panel.columns
                    if str(c).strip().lower() == "lei"), None)
    name_col = next((c for c in panel.columns
                     if "name" in str(c).lower()), None)
    if lei_col and name_col:
        names = (panel[[lei_col, name_col]]
                 .drop_duplicates(subset=lei_col)
                 .rename(columns={lei_col: "lei",
                                  name_col: "lender_name"}))
        out = out.merge(names, on="lei", how="left")
        out = out[["lei", "lender_name"]
                  + [c for c in out.columns
                     if c not in ("lei", "lender_name")]]
        print(f"Lender names merged from: {os.path.basename(ppath)}")
    else:
        print(f"Panel file found ({os.path.basename(ppath)}) but lei/"
              "name columns not identified; output is LEI-only.")
else:
    print("No HMDA panel file found in Data/; output is LEI-only. "
          "Download the 2025 panel file to add lender names.")

# =====================================================================
# 5. Sort and save
# =====================================================================
out = out.sort_values("orig_volume_1to4_total", ascending=False)

out_path = os.path.join(TABLES_DIR, "lender_originations_1to4_2025.csv")
out.to_csv(out_path, index=False)
print(f"Saved {len(out):,} lenders to {out_path}")
print(out.head(10).to_string(index=False))
