import pandas as pd
import sqlite3

# --- 1. Banks (FFIEC): values in THOUSANDS, so convert to dollars ---
con_bank = sqlite3.connect("call_report.db")

bank_query = """
SELECT
    rc.IDRSSD                                       AS institution_id,
    por."Financial Institution Name"                AS institution_name,
    COALESCE(rc.RCFD2170, rc.RCON2170) * 1000       AS total_assets_dollars
FROM call_report_rc  rc
JOIN call_report_por por
    ON rc.IDRSSD = por.IDRSSD
WHERE COALESCE(rc.RCFD2170, rc.RCON2170) > 10000000
"""

banks = pd.read_sql(bank_query, con_bank)
banks["institution_type"] = "Bank"

# --- 2. Credit unions (NCUA): values already in dollars ---
con_cu = sqlite3.connect("ncua_call_report.db")

cu_query = """
SELECT
    fs.CU_NUMBER      AS institution_id,
    foicu.CU_NAME     AS institution_name,
    fs.ACCT_010       AS total_assets_dollars
FROM ncua_fs220  fs
JOIN ncua_foicu  foicu
    ON fs.CU_NUMBER = foicu.CU_NUMBER
WHERE fs.ACCT_010 > 10000000000
"""

cus = pd.read_sql(cu_query, con_cu)
cus["institution_type"] = "Credit Union"

# --- 3. Combine, sort, display ---
combined = pd.concat([banks, cus], ignore_index=True)
combined = combined.sort_values("total_assets_dollars", ascending=False)

print(f"{len(combined)} institutions over $10 billion "
      f"({len(banks)} banks, {len(cus)} credit unions)")
print(combined.to_string(index=False))

# --- 4. Save to CSV ---
combined.to_csv("institutions_over_10b.csv", index=False)
print("Saved to institutions_over_10b.csv")
