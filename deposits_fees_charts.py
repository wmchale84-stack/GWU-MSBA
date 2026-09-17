import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# CONFIG
# =====================================================================
DATA_DIR = "."
INPUT_FILE = "listed_institutions_products.csv"  # or all_institutions_products.csv

# Okabe-Ito palette (course standard)
BLUE = "#0072B2"      # banks
ORANGE = "#E69F00"    # credit unions
GRAY = "#8f9aa6"      # context / guide lines

plt.rcParams.update({"font.size": 10, "axes.titlesize": 11,
                     "axes.spines.top": False, "axes.spines.right": False})

# =====================================================================
# Load and clean
# =====================================================================
df = pd.read_csv(os.path.join(DATA_DIR, INPUT_FILE))
d = df[["institution_id", "institution_name", "institution_type",
        "total_deposits_20260630", "total_fees_ttm_4q"]].copy()
n_start = len(d)
d = d.dropna(subset=["total_deposits_20260630", "total_fees_ttm_4q"])
d = d[(d["total_deposits_20260630"] > 0) & (d["total_fees_ttm_4q"] > 0)]
n = len(d)
n_excl = n_start - n

d["fee_bp"] = d["total_fees_ttm_4q"] / d["total_deposits_20260630"] * 10000
banks = d[d["institution_type"] == "Bank"]
cus = d[d["institution_type"] == "Credit Union"]

# Numbers for the finding-titles
logx = np.log10(d["total_deposits_20260630"])
logy = np.log10(d["total_fees_ttm_4q"])
slope, intercept = np.polyfit(logx, logy, 1)
r = np.corrcoef(logx, logy)[0, 1]
med_bp = d["fee_bp"].median()
q10, q90 = d["fee_bp"].quantile([0.10, 0.90])
spread = q90 / q10

# =====================================================================
# Figure 1 (main): log-log scatter with constant-yield guide line
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.scatter(banks["total_deposits_20260630"], banks["total_fees_ttm_4q"],
           s=28, color=BLUE, alpha=0.75, label="Banks", zorder=3)
ax.scatter(cus["total_deposits_20260630"], cus["total_fees_ttm_4q"],
           s=28, color=ORANGE, alpha=0.85, label="Credit unions", zorder=3)

# Guide line: what fees would be if every institution earned the
# group-median fee yield. Distance above/below the line = pricing
# intensity, not size.
xs = np.logspace(np.log10(d["total_deposits_20260630"].min()),
                 np.log10(d["total_deposits_20260630"].max()), 50)
ax.plot(xs, xs * med_bp / 10000, color=GRAY, lw=1.2, ls="--", zorder=2)
ax.text(xs[-1], xs[-1] * med_bp / 10000,
        f"  median yield\n  ({med_bp:.0f} bp)", color=GRAY,
        fontsize=8.5, va="center")

# Direct-label the three largest deposit holders
for _, row in d.nlargest(3, "total_deposits_20260630").iterrows():
    ax.annotate(str(row["institution_name"])[:22],
                (row["total_deposits_20260630"], row["total_fees_ttm_4q"]),
                textcoords="offset points", xytext=(6, -4), fontsize=8,
                color="#444444")

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Total deposits, 6/30/2026 (dollars, log scale)")
ax.set_ylabel("Deposit fees, trailing 4 quarters (dollars, log scale)")
ax.set_title(f"Fees rise {slope:.2f}-for-1 with deposit size "
             f"(log-log slope; r = {r:.2f})", loc="left")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(DATA_DIR, "fig1_deposits_vs_fees.png"), dpi=300)

# =====================================================================
# Figure 2: fee intensity (bp) vs size
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.scatter(banks["total_deposits_20260630"], banks["fee_bp"],
           s=28, color=BLUE, alpha=0.75, label="Banks", zorder=3)
ax.scatter(cus["total_deposits_20260630"], cus["fee_bp"],
           s=28, color=ORANGE, alpha=0.85, label="Credit unions", zorder=3)
ax.axhline(med_bp, color=GRAY, lw=1.2, ls="--", zorder=2)
ax.text(ax.get_xlim()[1], med_bp, f"  median {med_bp:.0f} bp",
        color=GRAY, fontsize=8.5, va="center")
ax.set_xscale("log")
ax.set_xlabel("Total deposits, 6/30/2026 (dollars, log scale)")
ax.set_ylabel("Fees per $ of deposits (basis points)")
ax.set_title(f"Similar-sized institutions differ {spread:.0f}x in fee "
             "intensity (90th vs 10th percentile)", loc="left")
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(os.path.join(DATA_DIR, "fig2_fee_intensity.png"), dpi=300)

# =====================================================================
# Figure 3 (only if the group is small enough to read names):
# ranked fee-yield bars from zero
# =====================================================================
if n <= 40:
    rk = d.sort_values("fee_bp", ascending=True)
    colors = [BLUE if t == "Bank" else ORANGE
              for t in rk["institution_type"]]
    fig, ax = plt.subplots(figsize=(7.5, 0.28 * n + 1.2))
    ax.barh(rk["institution_name"].astype(str).str[:28], rk["fee_bp"],
            color=colors)
    ax.axvline(med_bp, color=GRAY, lw=1.2, ls="--")
    ax.set_xlabel("Fees per $ of deposits (basis points)")
    ax.set_xlim(0, None)   # bars start at zero (course standard)
    top_name = rk.iloc[-1]["institution_name"]
    ax.set_title(f"{str(top_name)[:30]} leads the group at "
                 f"{rk['fee_bp'].max():.0f} bp; group median "
                 f"{med_bp:.0f} bp", loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(DATA_DIR, "fig3_fee_yield_ranked.png"),
                dpi=300)
    fig3_note = "fig3_fee_yield_ranked.png"
else:
    fig3_note = (f"skipped (group has {n} institutions; ranked bars "
                 "unreadable past ~40)")

# =====================================================================
# Captions in the course formula, with real N filled in
# =====================================================================
src = ("FFIEC Call Reports (RIAD4080, RCON2200) and NCUA 5300s "
       "(ACCT_131, ACCT_018)")
print("=" * 70)
print("PASTE-READY CAPTIONS")
print("=" * 70)
print(f"Figure 1. Fees are the trailing four quarters ended 6/30/2026; "
      f"deposits are the 6/30/2026 point-in-time balance. Both axes "
      f"log. One dot per institution. Source: {src}. {n} institutions "
      f"stand behind it ({n_excl} excluded for missing or zero "
      f"values).")
print()
print(f"Figure 2. Fee intensity is trailing-four-quarter fees divided "
      f"by 6/30/2026 deposits, in basis points. Source: {src}. {n} "
      f"institutions stand behind it.")
print()
if n <= 40:
    print(f"Figure 3. Bars start at zero and are ordered by fee yield. "
          f"Source: {src}. {n} institutions stand behind it.")
print()
print(f"Computed for the memo: log-log slope {slope:.2f}, r {r:.2f}, "
      f"median yield {med_bp:.0f} bp, 90/10 spread {spread:.1f}x")
print(f"Figure 3: {fig3_note}")
