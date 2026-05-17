"""
clean_medal_counts.py — Phase 1, Step 1.2

Input:  output/cleaned/athletes_clean.csv
        output/cleaned/noc_mapping_v2.csv
Output: output/cleaned/medal_counts_clean.csv

Approach:
  Derive medal counts from athletes_clean, grouped by canonical_name
  from the NOC mapping table. canonical_name is the project-wide
  unified country identifier and is always populated.

  One medal per (NOC, Year, Event, Medal) after team-event dedup.
  All (NOC, Year) participation pairs are included; non-medalists
  get Gold=Silver=Bronze=Total=0.

  The official summerOly_medal_counts.csv is NOT used as input —
  it serves as a comparison reference via audit_medal_compare.py.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    ATHLETES_CLEAN, MEDAL_COUNTS_CLEAN, NOC_MAPPING,
)
from src.utils.io_utils import read_csv, write_csv


def build_canonical_name_map(mapping: pd.DataFrame) -> dict:
    """Build (athlete_NOC, Year) -> canonical_name lookup.

    canonical_name is always populated (unlike NOC_in_medal_counts).
    Returns a dict and a set of (NOC, Year) keys where canonical_name
    was missing (should be empty).
    """
    name_map = {}
    missing = []

    for _, r in mapping.iterrows():
        key = (r["athlete_NOC"], int(r["Year"]))
        val = r.get("canonical_name", None)

        if pd.isna(val) or str(val).strip() == "":
            missing.append(key)
        else:
            # Store the first valid canonical_name for this key
            if key not in name_map:
                name_map[key] = str(val).strip()

    return name_map, missing


def build_medal_counts(ath: pd.DataFrame,
                       name_map: dict) -> pd.DataFrame:
    """Derive medal counts from athletes, grouped by canonical_name.

    Steps:
      1. Team-event dedup on (NOC, Year, Event, Medal)
      2. Count medals per (NOC, Year, Medal)
      3. Map NOC -> canonical_name via name_map
      4. Build full panel with zero-fill for non-medalists
      5. Sort and rank
    """
    # ---- Step 1: dedup ----
    dedup = ath.drop_duplicates(subset=["NOC", "Year", "Event", "Medal"])

    # ---- Step 2: count medals per (NOC, Year) ----
    has_medal = dedup[dedup["Medal"] != "No medal"]
    counts = (
        has_medal.groupby(["NOC", "Year", "Medal"])
        .size()
        .unstack(fill_value=0)
    )
    for col in ["Gold", "Silver", "Bronze"]:
        if col not in counts.columns:
            counts[col] = 0
    counts["Total"] = counts["Gold"] + counts["Silver"] + counts["Bronze"]
    counts = counts.reset_index()
    counts = counts.rename(columns={"NOC": "athlete_NOC"})
    counts = counts[["athlete_NOC", "Year",
                      "Gold", "Silver", "Bronze", "Total"]]

    # ---- Step 3: map to canonical_name ----
    def get_canonical(noc, year):
        key = (noc, int(year))
        val = name_map.get(key)
        if val is None:
            # Fallback: use NOC code itself (shouldn't happen if mapping is complete)
            print(f"    WARNING: no canonical_name for ({noc}, {int(year)}) — using NOC code")
            return noc
        return val

    counts["NOC"] = counts.apply(
        lambda r: get_canonical(r["athlete_NOC"], r["Year"]), axis=1
    )

    # ---- Step 4: build full panel (all participation pairs) ----
    all_pairs = (
        dedup[["NOC", "Year"]]
        .drop_duplicates()
        .rename(columns={"NOC": "athlete_NOC"})
    )

    panel = all_pairs.merge(counts, on=["athlete_NOC", "Year"], how="left")
    for col in ["Gold", "Silver", "Bronze", "Total"]:
        panel[col] = panel[col].fillna(0).astype(int)

    # Map canonical_name for zero-medal rows too
    panel["NOC"] = panel.apply(
        lambda r: get_canonical(r["athlete_NOC"], r["Year"]), axis=1
    )

    # ---- Step 5: rank within each Year ----
    panel = panel.sort_values(
        ["Year", "Total", "Gold", "Silver", "Bronze"],
        ascending=[True, False, False, False, False]
    )
    panel["Rank"] = panel.groupby("Year")["Total"].rank(
        method="min", ascending=False
    ).astype(int)

    return panel


def validate(df: pd.DataFrame) -> None:
    """Run integrity checks on the output."""
    n_total = len(df)
    n_null_noc = df["NOC"].isna().sum()
    n_empty_noc = (df["NOC"].astype(str).str.strip() == "").sum()
    n_dup = df.duplicated(subset=["NOC", "Year"]).sum()
    gold_plus_silver_plus_bronze = (df["Gold"] + df["Silver"] + df["Bronze"])
    n_bad_total = (gold_plus_silver_plus_bronze != df["Total"]).sum()

    print(f"\n  Validation:")
    print(f"    Rows:                {n_total:,}")
    print(f"    Null NOC:            {n_null_noc}")
    print(f"    Empty NOC:           {n_empty_noc}")
    print(f"    Duplicate (NOC,Year): {n_dup}")
    print(f"    Total != G+S+B:      {n_bad_total}")

    issues = []
    if n_null_noc > 0 or n_empty_noc > 0:
        issues.append("EMPTY NOC — output rejected")
    if n_dup > 0:
        issues.append(f"DUPLICATE KEY ({n_dup} rows) — output rejected")
    if n_bad_total > 0:
        issues.append(f"TOTAL MISMATCH ({n_bad_total} rows)")

    if issues:
        print(f"\n  *** INTEGRITY CHECK FAILED ***")
        for i in issues:
            print(f"    {i}")
        raise AssertionError(" | ".join(issues))
    else:
        print(f"    All checks passed.")


def main():
    print("=" * 60)
    print("clean_medal_counts.py — Phase 1, Step 1.2")
    print("=" * 60)

    print(f"\nLoading athletes_clean: {ATHLETES_CLEAN}")
    ath = read_csv(ATHLETES_CLEAN)
    print(f"  {len(ath):,} rows")

    print(f"Loading NOC mapping: {NOC_MAPPING}")
    mapping = read_csv(NOC_MAPPING)

    # Build canonical name map
    print(f"\n--- Building canonical_name map ---")
    name_map, missing = build_canonical_name_map(mapping)
    print(f"  Map entries: {len(name_map):,}")
    print(f"  Missing canonical_name: {len(missing)}")
    if missing:
        for m in sorted(missing, key=lambda x: (x[1], x[0]))[:10]:
            print(f"    {m}")
        if len(missing) > 10:
            print(f"    ... and {len(missing) - 10} more")

    # Build medal counts
    print(f"\n--- Building medal counts ---")
    result = build_medal_counts(ath, name_map)

    # Validate
    validate(result)

    # Write output
    out_cols = ["NOC", "Year", "Gold", "Silver", "Bronze", "Total", "Rank"]
    out = result[out_cols].sort_values(["Year", "Rank"]).reset_index(drop=True)

    write_csv(out, MEDAL_COUNTS_CLEAN)
    print(f"\n--- Output ---")
    print(f"  Saved: {MEDAL_COUNTS_CLEAN}")
    print(f"  Rows:  {len(out):,}")
    print(f"  NOC:   {out['NOC'].nunique():,} canonical names")
    print(f"  Years: {int(out['Year'].min())} – {int(out['Year'].max())}")
    print(f"  Medals: G={int(out['Gold'].sum()):,} "
          f"S={int(out['Silver'].sum()):,} "
          f"B={int(out['Bronze'].sum()):,} "
          f"T={int(out['Total'].sum()):,}")

    # Quick stats
    print(f"\n  Top-10 by total medals (all-time):")
    all_time = out.groupby("NOC")[["Gold", "Silver", "Bronze", "Total"]].sum()
    all_time = all_time.sort_values("Total", ascending=False)
    for noc, row in all_time.head(10).iterrows():
        print(f"    {noc:30s}  G={int(row['Gold']):4d}  "
              f"S={int(row['Silver']):4d}  B={int(row['Bronze']):4d}  "
              f"T={int(row['Total']):4d}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
