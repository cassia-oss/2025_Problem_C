"""
Compare athletes-derived medal counts with official medal_counts
on a common key: (canonical_name, Year).

Both sources are mapped to canonical_name via noc_mapping_v2:
  - athletes:  athlete_NOC -> canonical_name (already done in clean_medal_counts.py)
  - official:  NOC_name -> canonical_name (via NOC_in_medal_counts bridge)

Output: output/cleaned/medal_counts_compare.csv
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.utils.config import MEDAL_COUNTS_FILE, MEDAL_COUNTS_CLEAN, NOC_MAPPING, CLEANED_DIR

print("=" * 60)
print("1. Load sources")
print("=" * 60)

ath_derived = pd.read_csv(MEDAL_COUNTS_CLEAN)
official_raw = pd.read_csv(MEDAL_COUNTS_FILE)
mapping = pd.read_csv(NOC_MAPPING)

print(f"  Athletes-derived: {len(ath_derived):,} rows")
print(f"  Official raw:     {len(official_raw):,} rows")
print(f"  NOC mapping:      {len(mapping):,} rows")

# ============================================================
# 2. Build reverse map: (NOC_in_medal_counts, Year) -> canonical_name
# ============================================================

print()
print("=" * 60)
print("2. Map official NOC names -> canonical_name")
print("=" * 60)

# First clean official NOC names
official = official_raw.copy()
official["NOC_raw"] = official["NOC"].astype(str).str.replace("\xa0", "", regex=False).str.strip()
official["Year"] = official["Year"].astype(int)

# Build reverse map from mapping
reverse_map = {}
for _, r in mapping.iterrows():
    noc_in_mc = r["NOC_in_medal_counts"]
    if pd.isna(noc_in_mc) or str(noc_in_mc).strip() == "":
        continue
    key = (str(noc_in_mc).strip(), int(r["Year"]))
    canonical = r["canonical_name"]
    if pd.isna(canonical) or str(canonical).strip() == "":
        continue
    if key not in reverse_map:
        reverse_map[key] = str(canonical).strip()

print(f"  Reverse map entries: {len(reverse_map):,}")

# Apply to official table
def lookup_canonical_official(row):
    key = (row["NOC_raw"], int(row["Year"]))
    return reverse_map.get(key)

official["canonical_name"] = official.apply(lookup_canonical_official, axis=1)

n_unmapped = official["canonical_name"].isna().sum()
print(f"  Official rows mapped: {(~official['canonical_name'].isna()).sum():,}")
print(f"  Official rows unmapped: {n_unmapped:,}")

if n_unmapped > 0:
    unmapped = official[official["canonical_name"].isna()]
    print(f"\n  Unmapped official rows:")
    for _, r in unmapped.iterrows():
        print(f"    {r['NOC_raw']:40s} Year={int(r['Year'])}  "
              f"G={int(r['Gold'])} S={int(r['Silver'])} B={int(r['Bronze'])}")

# Aggregate official by canonical_name (in case multiple NOC names map to same canonical)
official_agg = (
    official.groupby(["canonical_name", "Year"], dropna=True)
    .agg(Gold_off=("Gold", "sum"),
         Silver_off=("Silver", "sum"),
         Bronze_off=("Bronze", "sum"),
         Total_off=("Total", "sum"))
    .reset_index()
)
print(f"\n  Official after canonical aggregation: {len(official_agg):,} rows")

# ============================================================
# 3. Join & compare
# ============================================================

print()
print("=" * 60)
print("3. Compare on (canonical_name, Year)")
print("=" * 60)

merged = ath_derived.merge(
    official_agg,
    left_on=["NOC", "Year"],
    right_on=["canonical_name", "Year"],
    how="outer",
    indicator=True,
)

# Fill NaN for non-overlapping rows
for col in ["Gold", "Silver", "Bronze", "Total"]:
    merged[f"{col}_ath"] = merged[col].fillna(0).astype(int)
for col in ["Gold_off", "Silver_off", "Bronze_off", "Total_off"]:
    merged[col] = merged[col].fillna(0).astype(int)

# Drop redundant columns
merged = merged.drop(columns=["Gold", "Silver", "Bronze", "Total"])

# Compute diffs
for col in ["Gold", "Silver", "Bronze", "Total"]:
    a = merged[f"{col}_ath"]
    b = merged[f"{col}_off"]
    merged[f"diff_{col}"] = a - b

merged["abs_diff_sum"] = (
    merged["diff_Gold"].abs()
    + merged["diff_Silver"].abs()
    + merged["diff_Bronze"].abs()
)

# Classify
def classify(row):
    if row["_merge"] == "left_only":
        return "ONLY_IN_ATHLETES"
    if row["_merge"] == "right_only":
        return "ONLY_IN_OFFICIAL"
    if row["abs_diff_sum"] == 0:
        return "MATCH"
    return "DIFFER"

merged["match_status"] = merged.apply(classify, axis=1)

# ============================================================
# 4. Summary
# ============================================================

print(f"\n  Total rows: {len(merged):,}")

print(f"\n  By match_status:")
for status, grp in merged.groupby("match_status"):
    pct = len(grp) / len(merged) * 100
    total_medal_diff = int(grp["abs_diff_sum"].sum())
    print(f"    {status:20s}: {len(grp):5d}  ({pct:5.1f}%)  "
          f"total_medal_diff={total_medal_diff}")

# Match rate
compared = merged[merged["match_status"] != "NO_MEDALS"]
n_compared = len(compared)
n_match = (compared["match_status"] == "MATCH").sum()
print(f"\n  Match rate (excl. NO_MEDALS): {n_match}/{n_compared} = "
      f"{n_match/n_compared*100:.1f}%")

# ---- DIFFER detail ----
differ = merged[merged["match_status"] == "DIFFER"]
print(f"\n  DIFFER: {len(differ)} rows")
if len(differ) > 0:
    print(f"  Top 20 by abs_diff_sum:")
    top = differ.nlargest(20, "abs_diff_sum")
    for _, r in top.iterrows():
        print(
            f"    {r['NOC']:30s} {int(r['Year'])}  "
            f"ath=(G:{int(r['Gold_ath']):3d} S:{int(r['Silver_ath']):3d} "
            f"B:{int(r['Bronze_ath']):3d} T:{int(r['Total_ath']):4d})  "
            f"off=(G:{int(r['Gold_off']):3d} S:{int(r['Silver_off']):3d} "
            f"B:{int(r['Bronze_off']):3d} T:{int(r['Total_off']):4d})  "
            f"diff=(G:{int(r['diff_Gold']):+d} S:{int(r['diff_Silver']):+d} "
            f"B:{int(r['diff_Bronze']):+d})"
        )

    print(f"\n  DIFFER by Year:")
    for year, grp in differ.groupby("Year"):
        print(f"    {int(year)}: {len(grp):3d} rows, absolute_medal_diff={int(grp['abs_diff_sum'].sum())}")

# ---- ONLY_IN_ATHLETES ----
only_ath = merged[merged["match_status"] == "ONLY_IN_ATHLETES"]
print(f"\n  ONLY_IN_ATHLETES: {len(only_ath)} rows")
if len(only_ath) > 0:
    for _, r in only_ath.iterrows():
        print(f"    {r['NOC']:30s} Y={int(r['Year'])}  "
              f"G={int(r['Gold_ath'])} S={int(r['Silver_ath'])} B={int(r['Bronze_ath'])}")

# ---- ONLY_IN_OFFICIAL ----
only_off = merged[merged["match_status"] == "ONLY_IN_OFFICIAL"]
print(f"\n  ONLY_IN_OFFICIAL: {len(only_off)} rows")
if len(only_off) > 0:
    for _, r in only_off.iterrows():
        print(f"    {r['canonical_name']:30s} Y={int(r['Year'])}  "
              f"G={int(r['Gold_off'])} S={int(r['Silver_off'])} B={int(r['Bronze_off'])}")

# ---- NO_MEDALS ----
no_med = merged[merged["match_status"] == "NO_MEDALS"]
if len(no_med) > 0:
    print(f"\n  NO_MEDALS (zero medals): {len(no_med)} rows")

# ============================================================
# 5. Save
# ============================================================

out_cols = [
    "NOC", "canonical_name", "Year",
    "Gold_ath", "Silver_ath", "Bronze_ath", "Total_ath",
    "Gold_off", "Silver_off", "Bronze_off", "Total_off",
    "diff_Gold", "diff_Silver", "diff_Bronze", "diff_Total",
    "abs_diff_sum", "match_status",
]
merged = merged[out_cols].sort_values(["Year", "NOC"]).reset_index(drop=True)

OUT = CLEANED_DIR / "medal_counts_compare.csv"
merged.to_csv(OUT, index=False)
print(f"\n  Saved: {OUT}")

print("\nDone.")
