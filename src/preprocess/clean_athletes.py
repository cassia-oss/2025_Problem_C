"""
clean_athletes.py — Phase 1, Step 1.1

Input:  data/summerOly_athletes.csv (252,565 rows, 9 columns)
Output: output/cleaned/athletes_clean.csv
Side outputs:
    output/cleaned/dup_medal_conflict.csv  (Type B-P2: original conflict groups before resolution)
    output/cleaned/bp2_audit.csv           (B-P2: every row removed + reason)
    output/cleaned/unknown_noc.csv         (NOC codes not in the mapping table)

Steps 1.1.1 through 1.1.6 per PIPELINE.md Section 1.1.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    ATHLETES_FILE, ATHLETES_CLEAN, CLEANED_DIR,
    NOC_MAPPING, UNKNOWN_NOC, CANCELLED_YEARS, VALID_MEDALS,
    ATHLETE_DEDUP_COLS, ATHLETE_OUTPUT_COLS, OLYMPIC_YEARS,
)
from src.utils.io_utils import read_csv, write_csv


# ------------------------------------------------------------
# STEP 1.1.1 — Handle duplicates
# ------------------------------------------------------------

def classify_duplicates(df: pd.DataFrame) -> tuple:
    """Classify duplicate groups on (Name, NOC, Year, Event) into Types A/B/C.

    Returns:
        type_a_mask: rows in exact full-row duplicates (safe to drop)
        type_b_p1_mask: rows where Medal differs, pattern 'medal vs No medal'
        type_b_p2_mask: rows where two different real medals conflict
        type_c_mask: rows where Team (and possibly other non-Medal cols) vary
        conflict_df: DataFrame of Type B-P2 conflicts for manual review
    """
    dedup_cols = ATHLETE_DEDUP_COLS  # ['Name', 'NOC', 'Year', 'Event']
    dup_mask = df.duplicated(subset=dedup_cols, keep=False)
    dup_df = df[dup_mask].copy()
    dup_df['_group_id'] = dup_df.groupby(dedup_cols).ngroup()

    type_a_groups = set()
    type_b_p1_groups = set()
    type_b_p2_groups = set()
    type_c_groups = set()

    for gid, grp in dup_df.groupby('_group_id'):
        # Columns that vary within this group
        varying = [c for c in grp.columns if grp[c].nunique() > 1]

        if 'Medal' in varying:
            medals = set(grp['Medal'].dropna())
            real_medals = medals - {'No medal', np.nan, None}
            if len(real_medals) >= 2:
                # Two different real medals (e.g. Gold + Silver)
                type_b_p2_groups.add(gid)
            elif len(real_medals) >= 1 and 'No medal' in medals:
                # Medal vs No medal
                type_b_p1_groups.add(gid)
            else:
                # Edge case: all NaN or other weirdness — treat as Type A
                type_a_groups.add(gid)
        elif len(varying) == 0:
            type_a_groups.add(gid)
        else:
            type_c_groups.add(gid)

    # Compute row-level masks
    type_a_mask = dup_df['_group_id'].isin(type_a_groups)
    type_b_p1_mask = dup_df['_group_id'].isin(type_b_p1_groups)
    type_b_p2_mask = dup_df['_group_id'].isin(type_b_p2_groups)
    type_c_mask = dup_df['_group_id'].isin(type_c_groups)

    # Build conflict report for Type B-P2
    conflict_groups = dup_df[type_b_p2_mask]
    if len(conflict_groups) > 0:
        conflict_df = conflict_groups.drop(columns=['_group_id'])
    else:
        conflict_df = pd.DataFrame()

    print(f'  [1.1.1] Duplicates on {dedup_cols}:')
    print(f'    Type A (all identical):      {len(type_a_groups)} groups')
    print(f'    Type B-P1 (medal vs none):   {len(type_b_p1_groups)} groups')
    print(f'    Type B-P2 (medal conflict):  {len(type_b_p2_groups)} groups -> exported')
    print(f'    Type C (Team differs):       {len(type_c_groups)} groups -> kept')

    return type_a_mask, type_b_p1_mask, type_b_p2_mask, type_c_mask, conflict_df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Step 1.1.1: Identify and remove duplicate rows.

    Strategy (per PIPELINE.md + EDA findings):
      - Type A: drop_duplicates on all columns (exact recording errors).
      - Type B-P1: keep the medal row, drop "No medal" rows in the same group.
      - Type B-P2: export the entire duplicate group for manual review,
        then drop *all* rows in those groups from the main DataFrame.
      - Type C: keep all rows (legitimate multi-boat entries in 1900 sailing).
    """
    dedup_cols = ATHLETE_DEDUP_COLS

    type_a_mask, type_b_p1_mask, type_b_p2_mask, type_c_mask, conflict_df = \
        classify_duplicates(df)

    if len(conflict_df) > 0:
        conflict_path = CLEANED_DIR / 'dup_medal_conflict.csv'
        write_csv(conflict_df, conflict_path)
        print(f'    -> {len(conflict_df)} conflict rows saved to {conflict_path}')

    # --- Type A: drop exact full-row duplicates ---
    n_before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    n_type_a = n_before - len(df)
    if n_type_a > 0:
        print(f'    -> Dropped {n_type_a} Type-A rows (exact duplicate on all columns)')

    # --- Type B-P1: keep medal rows, drop "No medal" rows ---
    dup_mask = df.duplicated(subset=dedup_cols, keep=False)
    dup_df = df[dup_mask].copy()
    dup_df['_gid'] = dup_df.groupby(dedup_cols).ngroup()

    drop_indices = []
    for gid, grp in dup_df.groupby('_gid'):
        medals = set(grp['Medal'])
        if len(medals) > 1 and 'No medal' in medals:
            # Keep rows with real medals; drop "No medal" rows
            no_medal_idx = grp[grp['Medal'] == 'No medal'].index
            drop_indices.extend(no_medal_idx)

    if drop_indices:
        df = df.drop(index=drop_indices).reset_index(drop=True)
        print(f'    -> Dropped {len(drop_indices)} Type B-P1 rows (No medal rows where same '
              f'athlete+event has a real medal)')

    # --- Type B-P2: resolve with medal_counts as ground truth ---
    # Strategy (per Cassie):
    #   1. Within each conflict group, keep the HIGHEST medal (Gold > Silver > Bronze).
    #   2. If that causes athletes totals to exceed medal_counts for (NOC, Year),
    #      remove rows to align — prioritising duplicate-Name rows first,
    #      then different-boat entries.
    _resolve_bp2_with_medal_counts(df, dedup_cols)
    print(f'    -> Type B-P2 conflicts resolved against medal_counts')

    # Type C is kept as-is (no action needed)
    return df


def _resolve_bp2_with_medal_counts(df: pd.DataFrame, dedup_cols: list) -> None:
    """Resolve Type B-P2 medal conflicts using medal_counts as constraint.

    For each conflict group (same Name+NOC+Year+Event with 2+ real medals),
    the official medal_counts per-(NOC, Year) totals serve as the constraint:
      - If athletes Gold > official Gold: drop Gold rows in conflict groups
        (keep the Silver/Bronze in those groups instead)
      - Same for Silver and Bronze
      - Remaining conflicts (no constraint violated): keep highest medal

    Mutates df in-place. Exports bp2_audit.csv recording every removal.
    """
    from src.utils.config import MEDAL_COUNTS_FILE, NOC_MAPPING

    medals_raw = read_csv(MEDAL_COUNTS_FILE)
    medals_raw["NOC_clean"] = (
        medals_raw["NOC"].astype(str).str.replace("\xa0", "", regex=False).str.strip()
    )

    # Build (athlete_NOC, Year) -> NOC_in_medal_counts lookup
    mapping = read_csv(NOC_MAPPING)
    noc_year_to_medal_name = {}
    for _, r in mapping.iterrows():
        val = r.get("NOC_in_medal_counts", None)
        if pd.notna(val) and str(val).strip():
            noc_year_to_medal_name[(r["athlete_NOC"], int(r["Year"]))] = str(val).strip()

    # ---- Find ALL conflict groups ----
    medal_rank = {"Gold": 3, "Silver": 2, "Bronze": 1, "No medal": 0}
    dup_mask = df.duplicated(subset=dedup_cols, keep=False)
    dup_df = df[dup_mask].copy()
    dup_df["_gid"] = dup_df.groupby(dedup_cols).ngroup()

    # Identify groups with 2+ real medals
    conflict_groups = set()
    for gid, grp in dup_df.groupby("_gid"):
        real = set(grp["Medal"]) - {"No medal"}
        if len(real) >= 2:
            conflict_groups.add(gid)

    if not conflict_groups:
        print("    [B-P2] No groups with 2+ real medals — nothing to resolve.")
        return

    # ---- Build per-(NOC, Year) official lookup + current counts ----
    conflict_pairs = (
        dup_df[dup_df["_gid"].isin(conflict_groups)][["NOC", "Year"]]
        .drop_duplicates()
    )

    audit_rows = []
    drop_set = set()

    for _, pair in conflict_pairs.iterrows():
        noc = pair["NOC"]
        year = int(pair["Year"])

        # Official target
        medal_name = noc_year_to_medal_name.get((noc, year))
        if medal_name is None:
            continue
        mc = medals_raw[
            (medals_raw["NOC_clean"] == medal_name) & (medals_raw["Year"] == year)
        ]
        if len(mc) == 0:
            continue
        target = {
            "Gold": int(mc["Gold"].values[0]),
            "Silver": int(mc["Silver"].values[0]),
            "Bronze": int(mc["Bronze"].values[0]),
        }

        # Current athletes counts for this (NOC, Year)
        a = df[(df["NOC"] == noc) & (df["Year"] == year)]
        current = {
            "Gold": int((a["Medal"] == "Gold").sum()),
            "Silver": int((a["Medal"] == "Silver").sum()),
            "Bronze": int((a["Medal"] == "Bronze").sum()),
        }

        # Conflict groups for this (NOC, Year)
        conflict_in_pair = dup_df[
            (dup_df["NOC"] == noc)
            & (dup_df["Year"] == year)
            & (dup_df["_gid"].isin(conflict_groups))
        ]

        # ---- Constraint-driven resolution ----
        for medal_type in ["Gold", "Silver", "Bronze"]:
            excess = current[medal_type] - target[medal_type]
            if excess <= 0:
                continue

            # Find conflict groups that HAVE this medal type AND another real medal
            for gid, grp in conflict_in_pair.groupby("_gid"):
                if excess <= 0:
                    break
                if gid in conflict_groups:
                    grp_medals = set(grp["Medal"])
                    other_real = (grp_medals - {"No medal"}) - {medal_type}
                    if medal_type in grp_medals and other_real:
                        # Drop the excess-medal row, keep the other medal
                        victims = grp[grp["Medal"] == medal_type]
                        for _, victim in victims.head(excess).iterrows():
                            drop_set.add(victim.name)
                            other = list(other_real)[0]
                            audit_rows.append({
                                "Name": victim["Name"],
                                "NOC": victim["NOC"],
                                "Year": int(victim["Year"]),
                                "Event": victim["Event"],
                                "dropped_medal": victim["Medal"],
                                "kept_medal": other,
                                "reason": f"G_ath={current['Gold']} vs G_off={target['Gold']} "
                                          f"S_ath={current['Silver']} vs S_off={target['Silver']} "
                                          f"B_ath={current['Bronze']} vs B_off={target['Bronze']}",
                            })
                            current[medal_type] -= 1
                            excess -= 1

    if drop_set:
        df.drop(index=list(drop_set), inplace=True)
        df.reset_index(drop=True, inplace=True)

    # ---- Fallback: remaining conflict groups → keep highest ----
    dup_mask = df.duplicated(subset=dedup_cols, keep=False)
    if dup_mask.any():
        dup_df2 = df[dup_mask].copy()
        dup_df2["_gid2"] = dup_df2.groupby(dedup_cols).ngroup()

        drop_set2 = set()
        for gid, grp in dup_df2.groupby("_gid2"):
            real = set(grp["Medal"]) - {"No medal"}
            if len(real) >= 2:
                best = max(real, key=lambda m: medal_rank[m])
                for _, row in grp.iterrows():
                    if row["Medal"] in real and row["Medal"] != best:
                        drop_set2.add(row.name)
                        audit_rows.append({
                            "Name": row["Name"],
                            "NOC": row["NOC"],
                            "Year": int(row["Year"]),
                            "Event": row["Event"],
                            "dropped_medal": row["Medal"],
                            "kept_medal": best,
                            "reason": "FALLBACK: no constraint violation, kept highest medal",
                        })

        if drop_set2:
            df.drop(index=list(drop_set2), inplace=True)
            df.reset_index(drop=True, inplace=True)
            print(f"    [B-P2] Constraint-driven: dropped {len(drop_set)} rows; "
                  f"fallback (keep highest): dropped {len(drop_set2)} rows")
        else:
            print(f"    [B-P2] Constraint-driven: dropped {len(drop_set)} rows; "
                  f"no fallback needed")
    else:
        print(f"    [B-P2] Constraint-driven: dropped {len(drop_set)} rows; "
              f"no remaining conflicts")

    # ---- Export audit ----
    if audit_rows:
        audit_df = pd.DataFrame(audit_rows)
        audit_path = CLEANED_DIR / "bp2_audit.csv"
        write_csv(audit_df, audit_path)
        print(f"    -> {len(audit_df)} removals audited to {audit_path}")


# ------------------------------------------------------------
# STEP 1.1.2 — Normalize Team names & flag multi-team entries
# ------------------------------------------------------------

def normalize_teams(df: pd.DataFrame) -> pd.DataFrame:
    """Step 1.1.2: Normalize Team names and add is_multi_team flag.

    - Detect dash-suffix pattern (e.g. "United States-1") -> is_multi_team = 1
    - Strip whitespace from Team names
    - Flag rows with encoding artifacts (replacement character U+FFFD)

    Does NOT replace Team names — the NOC mapping table (noc_mapping_v2.csv)
    handles the Team -> canonical_name bridge at query time.
    """
    # --- Detect dash-suffix multi-team pattern ---
    dash_pattern = r'^(.*)-(\d+)$'
    dash_match = df['Team'].str.extract(dash_pattern)
    df['is_multi_team'] = dash_match[1].notna().astype(int)

    n_multi = df['is_multi_team'].sum()
    n_unique = df.loc[df['is_multi_team'] == 1, 'Team'].nunique()
    print(f'  [1.1.2] Multi-team rows: {n_multi} ({n_unique} unique Team names)')

    # --- Strip whitespace ---
    df['Team'] = df['Team'].str.strip()

    # --- Check for encoding artifacts ---
    garbled_mask = df['Team'].str.contains('�', na=False)
    n_garbled = garbled_mask.sum()
    if n_garbled > 0:
        print(f'    WARNING: {n_garbled} rows contain Unicode replacement char (U+FFFD)')
        print(f'    Affected teams: {sorted(df.loc[garbled_mask, "Team"].unique())}')
    else:
        print(f'    No garbled characters detected.')

    return df


# ------------------------------------------------------------
# STEP 1.1.3 — Normalize Medal values
# ------------------------------------------------------------

def normalize_medals(df: pd.DataFrame) -> pd.DataFrame:
    """Step 1.1.3: Normalize Medal column to canonical set.

    Valid values: {'Gold', 'Silver', 'Bronze', 'No medal'}
    Map: 'No Medal', '', NaN -> 'No medal'
    """
    before = df['Medal'].value_counts(dropna=False).to_dict()

    # Fill NaN with 'No medal'
    df['Medal'] = df['Medal'].fillna('No medal')

    # Normalize case/spacing variants
    df['Medal'] = df['Medal'].replace({
        'No Medal': 'No medal',
        '': 'No medal',
        'no medal': 'No medal',
    })

    # Validate
    invalid = set(df['Medal'].unique()) - VALID_MEDALS
    if invalid:
        print(f'    WARNING: Unexpected Medal values remain: {invalid}')
    else:
        print(f'  [1.1.3] Medal values normalized. '
              f'Distribution: {dict(df["Medal"].value_counts())}')

    return df


# ------------------------------------------------------------
# STEP 1.1.4 — Validate NOC codes
# ------------------------------------------------------------

def validate_noc_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Step 1.1.4: Validate that every NOC appears in the mapping table.

    Unknown NOCs are exported to output/cleaned/unknown_noc.csv for review.
    """
    mapping = read_csv(NOC_MAPPING)
    valid_nocs = set(mapping['athlete_NOC'].unique())
    athlete_nocs = set(df['NOC'].unique())

    unknown = athlete_nocs - valid_nocs
    if unknown:
        unknown_rows = df[df['NOC'].isin(unknown)]
        unknown_out = UNKNOWN_NOC
        write_csv(unknown_rows, unknown_out)
        print(f'  [1.1.4] WARNING: {len(unknown)} unknown NOCs ({sorted(unknown)})')
        print(f'    -> {len(unknown_rows)} rows saved to {unknown_out}')
    else:
        print(f'  [1.1.4] All {len(athlete_nocs)} NOC codes validated against mapping.')

    return df


# ------------------------------------------------------------
# STEP 1.1.5 — Validate Year range
# ------------------------------------------------------------

def validate_years(df: pd.DataFrame) -> pd.DataFrame:
    """Step 1.1.5: Validate Year column.

    Year must be a valid Summer Olympics year in OLYMPIC_YEARS.
    Filters out Intercalated Games (1906) and any other non-standard years.
    """
    years_before = set(df['Year'].unique())
    n_before = len(df)
    df = df[df['Year'].isin(OLYMPIC_YEARS)]
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        dropped_years = sorted(years_before - set(OLYMPIC_YEARS))
        print(f'  [1.1.5] Dropped {n_dropped} rows with non-Olympic years: '
              f'{dropped_years}')

    invalid_years = set(df['Year'].unique()) & CANCELLED_YEARS
    out_of_range = df[(df['Year'] < 1896) | (df['Year'] > 2024)]

    if invalid_years:
        n = (df['Year'].isin(invalid_years)).sum()
        print(f'  [1.1.5] WARNING: {n} rows with cancelled years: {invalid_years}')

    if len(out_of_range) > 0:
        print(f'  [1.1.5] WARNING: {len(out_of_range)} rows with Year outside [1896, 2024]')

    if not invalid_years and len(out_of_range) == 0:
        years = sorted(df['Year'].unique())
        print(f'  [1.1.5] Year range OK: {years[0]}–{years[-1]} '
              f'({len(years)} unique Olympiads, dropped {n_dropped})')

    return df


# ------------------------------------------------------------
# STEP 1.1.6 — Write cleaned output
# ------------------------------------------------------------

def write_output(df: pd.DataFrame) -> None:
    """Step 1.1.6: Write cleaned athletes data to CSV.

    Columns: Name, Sex, Team, NOC, Year, City, Sport, Event, Medal, is_multi_team
    """
    # Ensure output columns are in the right order
    df_out = df[ATHLETE_OUTPUT_COLS].copy()
    write_csv(df_out, ATHLETES_CLEAN)
    print(f'  [1.1.6] Cleaned data saved: {ATHLETES_CLEAN}')
    print(f'    Rows: {len(df_out):,}')
    print(f'    Columns: {list(df_out.columns)}')


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print('=' * 60)
    print('clean_athletes.py — Phase 1, Step 1.1')
    print('=' * 60)

    # Load
    print(f'\nLoading: {ATHLETES_FILE}')
    df = read_csv(ATHLETES_FILE)
    print(f'  {len(df):,} rows, {len(df.columns)} columns')

    # Step 1.1.1
    print(f'\n--- Step 1.1.1: Remove duplicates ---')
    df = remove_duplicates(df)

    # Step 1.1.2
    print(f'\n--- Step 1.1.2: Normalize Team names ---')
    df = normalize_teams(df)

    # Step 1.1.3
    print(f'\n--- Step 1.1.3: Normalize Medal values ---')
    df = normalize_medals(df)

    # Step 1.1.4
    print(f'\n--- Step 1.1.4: Validate NOC codes ---')
    df = validate_noc_codes(df)

    # Step 1.1.5
    print(f'\n--- Step 1.1.5: Validate Year range ---')
    df = validate_years(df)

    # Step 1.1.6
    print(f'\n--- Step 1.1.6: Write output ---')
    write_output(df)

    print(f'\nDone. Output: {ATHLETES_CLEAN}')


if __name__ == '__main__':
    main()
