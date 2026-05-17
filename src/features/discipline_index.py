"""
discipline_index.py - Phase 2, Step 2.2

Input:  output/cleaned/athletes_clean.csv
        output/cleaned/athlete_discipline_map.csv
        output/cleaned/noc_mapping_v2.csv
        output/cleaned/programs_clean.csv
Output: output/features/discipline_index.csv

Formula (see PIPELINE Section 2.2):
  1. Map athletes to IOC discipline Codes via athlete_discipline_map
  2. Count medals per (NOC, Code, Year) after team-event dedup
  3. Normalize: score = (Gold/TotalGold) * 1.0 + (Silver/TotalSilver) * 0.6
                         + (Bronze/TotalBronze) * 0.4
     where totals are per-discipline-Year across ALL countries
  4. Weighted T_score with 3-Olympiad window (w0=1.0, w1=0.7, w2=0.5)
     Only uses data available at that Year (no future leakage).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    ATHLETES_CLEAN, ATHLETE_DISCIPLINE_MAP, NOC_MAPPING, PROGRAMS_CLEAN,
    DISCIPLINE_INDEX, MEDAL_WEIGHTS, OLYMPIC_YEARS,
)
from src.utils.io_utils import read_csv, write_csv
from src.utils.discipline_resolver import make_athlete_keyword

# Weights for 3-Olympiad window
W_CURRENT = 1.0
W_LAG1 = 0.7
W_LAG2 = 0.5


def load_data():
    """Load and prepare all input data."""
    print(f"\nLoading athletes_clean: {ATHLETES_CLEAN}")
    ath = read_csv(ATHLETES_CLEAN)
    print(f"  {len(ath):,} rows")

    print(f"Loading athlete_discipline_map: {ATHLETE_DISCIPLINE_MAP}")
    disc_map = read_csv(ATHLETE_DISCIPLINE_MAP)
    print(f"  {len(disc_map):,} rows")

    print(f"Loading NOC mapping: {NOC_MAPPING}")
    noc_map = read_csv(NOC_MAPPING)
    print(f"  {len(noc_map):,} rows")

    print(f"Loading programs_clean: {PROGRAMS_CLEAN}")
    prog = read_csv(PROGRAMS_CLEAN)
    print(f"  {len(prog):,} rows")

    return ath, disc_map, noc_map, prog


def build_canonical_lookup(noc_map: pd.DataFrame) -> dict:
    """Build (athlete_NOC, Year) -> canonical_name lookup."""
    lookup = {}
    for _, r in noc_map.iterrows():
        key = (str(r['athlete_NOC']).strip(), int(r['Year']))
        val = str(r.get('canonical_name', '')).strip()
        if val and pd.notna(r.get('canonical_name')) and key not in lookup:
            lookup[key] = val
    return lookup


def attach_discipline_map(ath: pd.DataFrame, disc_map: pd.DataFrame) -> pd.DataFrame:
    """Join athletes_clean to athlete_discipline_map via (Sport, athlete_keyword)."""
    ath = ath.copy()
    ath['athlete_keyword'] = ath['Event'].apply(make_athlete_keyword)

    map_cols = [
        'athlete_Sport', 'athlete_keyword',
        'programs_Discipline', 'Code', 'match_method'
    ]
    mapping = disc_map[map_cols].drop_duplicates()

    dup = mapping.duplicated(subset=['athlete_Sport', 'athlete_keyword']).sum()
    if dup > 0:
        raise ValueError(f"athlete_discipline_map has {dup} duplicate mapping keys")

    merged = ath.merge(
        mapping,
        left_on=['Sport', 'athlete_keyword'],
        right_on=['athlete_Sport', 'athlete_keyword'],
        how='left',
    )
    merged['Discipline'] = merged['programs_Discipline'].fillna('')
    merged['Code'] = merged['Code'].fillna('')

    matched = (merged['Code'] != '').sum()
    print(f"\n  Discipline-map join coverage: {matched:,}/{len(merged):,} "
          f"({matched/len(merged)*100:.1f}%)")
    return merged


def compute_medal_counts(ath: pd.DataFrame, canon_lookup: dict) -> pd.DataFrame:
    """Count medals per (canonical_name, Code, Year, Medal), keeping 0-medal participation."""
    ath = ath[ath['Code'] != ''].copy()
    print(f"\n  Athletes with valid discipline Code: {len(ath):,}")

    # Team-event dedup: keep one per (NOC, Year, Event, Medal)
    dedup = ath.drop_duplicates(subset=['NOC', 'Year', 'Event', 'Medal'])
    dedup['athlete_NOC'] = dedup['NOC']

    # All participating NOC-discipline-year rows, including countries with no medal.
    participation = (
        dedup.groupby(['athlete_NOC', 'Code', 'Discipline', 'Year'])
        .size()
        .reset_index(name='n_participations')
        .drop(columns='n_participations')
    )

    has_medal = dedup[dedup['Medal'] != 'No medal'].copy()
    counts = (
        has_medal.groupby(['athlete_NOC', 'Code', 'Discipline', 'Year', 'Medal'])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ['Gold', 'Silver', 'Bronze']:
        if col not in counts.columns:
            counts[col] = 0

    merged = participation.merge(
        counts,
        on=['athlete_NOC', 'Code', 'Discipline', 'Year'],
        how='left',
    )
    for col in ['Gold', 'Silver', 'Bronze']:
        merged[col] = merged[col].fillna(0).astype(int)

    merged['canonical_name'] = merged.apply(
        lambda r: canon_lookup.get((str(r['athlete_NOC']).strip(), int(r['Year'])),
                                   str(r['athlete_NOC'])),
        axis=1,
    )

    result = merged[
        ['canonical_name', 'Discipline', 'Code', 'Year', 'Gold', 'Silver', 'Bronze']
    ].copy()
    result['Total'] = result['Gold'] + result['Silver'] + result['Bronze']

    print(f"  Participation rows (NOC-Discipline-Year): {len(result):,}")
    print(f"  Zero-medal participation rows: {(result['Total'] == 0).sum():,}")
    print(f"  Total medals: G={int(result['Gold'].sum()):,} "
          f"S={int(result['Silver'].sum()):,} "
          f"B={int(result['Bronze'].sum()):,}")
    return result


def compute_discipline_totals(medals: pd.DataFrame) -> pd.DataFrame:
    """Compute total medals per (Code, Year) across all countries."""
    totals = medals.groupby(['Code', 'Year']).agg(
        Gold_total=('Gold', 'sum'),
        Silver_total=('Silver', 'sum'),
        Bronze_total=('Bronze', 'sum'),
    ).reset_index()
    print(f"\n  Discipline-Year totals: {len(totals):,} rows")
    return totals


def compute_normalized_scores(medals: pd.DataFrame,
                              totals: pd.DataFrame) -> pd.DataFrame:
    """Compute normalized score per (canonical_name, Code, Year)."""
    merged = medals.merge(totals, on=['Code', 'Year'], how='left')

    def safe_div(num, denom):
        """Safe division: 0/0 = 0, x/0 = 0."""
        mask = denom > 0
        result = np.zeros(len(num))
        result[mask] = num[mask] / denom[mask]
        return result

    merged['gold_score'] = safe_div(
        merged['Gold'].values, merged['Gold_total'].values
    ) * MEDAL_WEIGHTS['Gold']
    merged['silver_score'] = safe_div(
        merged['Silver'].values, merged['Silver_total'].values
    ) * MEDAL_WEIGHTS['Silver']
    merged['bronze_score'] = safe_div(
        merged['Bronze'].values, merged['Bronze_total'].values
    ) * MEDAL_WEIGHTS['Bronze']

    merged['score'] = (
        merged['gold_score'] + merged['silver_score'] + merged['bronze_score']
    )

    result = merged[['canonical_name', 'Discipline', 'Code', 'Year', 'score']].copy()
    print(f"  Normalized scores: {len(result):,} rows")
    return result


def compute_t_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Compute T_score with 3-Olympiad weighted window."""
    olympic_years = sorted(OLYMPIC_YEARS)
    year_to_prev = {}
    year_to_prev2 = {}
    for i, y in enumerate(olympic_years):
        if i >= 1:
            year_to_prev[y] = olympic_years[i - 1]
        if i >= 2:
            year_to_prev2[y] = olympic_years[i - 2]

    score_lookup = {}
    for _, r in scores.iterrows():
        key = (r['canonical_name'], r['Code'], int(r['Year']))
        score_lookup[key] = r['score']

    rows = []
    for _, r in scores.iterrows():
        cname = r['canonical_name']
        code = r['Code']
        year = int(r['Year'])
        current_score = r['score']

        lag1_score = None
        lag2_score = None

        prev_year = year_to_prev.get(year)
        if prev_year is not None:
            lag1_score = score_lookup.get((cname, code, prev_year))

        prev2_year = year_to_prev2.get(year)
        if prev2_year is not None:
            lag2_score = score_lookup.get((cname, code, prev2_year))

        numerator = W_CURRENT * current_score
        denominator = W_CURRENT
        n_used = 1

        if lag1_score is not None:
            numerator += W_LAG1 * lag1_score
            denominator += W_LAG1
            n_used += 1

        if lag2_score is not None:
            numerator += W_LAG2 * lag2_score
            denominator += W_LAG2
            n_used += 1

        t_score = numerator / denominator if denominator > 0 else np.nan

        rows.append({
            'canonical_name': cname,
            'Discipline': r['Discipline'],
            'Code': code,
            'Year': year,
            'score_current': round(current_score, 6),
            'score_lag1': round(lag1_score, 6) if lag1_score is not None else np.nan,
            'score_lag2': round(lag2_score, 6) if lag2_score is not None else np.nan,
            'T_score': round(t_score, 6),
            'n_years_used': n_used,
        })

    result = pd.DataFrame(rows)
    result = result.sort_values(['canonical_name', 'Code', 'Year']).reset_index(drop=True)
    print(f"\n  T_score rows: {len(result):,}")
    print(f"  T_score range: [{result['T_score'].min():.4f}, "
          f"{result['T_score'].max():.4f}]")
    return result


def validate(result: pd.DataFrame) -> None:
    """Run integrity checks."""
    print(f"\n  Validation:")
    n_nan_t = result['T_score'].isna().sum()
    print(f"    NaN T_score: {n_nan_t}")

    dup = result.duplicated(subset=['canonical_name', 'Code', 'Year']).sum()
    print(f"    Duplicate keys: {dup}")
    if dup > 0:
        print(f"    WARNING: {dup} duplicate keys found!")

    bad_years = set(result['Year'].unique()) - set(OLYMPIC_YEARS)
    if bad_years:
        print(f"    Bad years: {sorted(bad_years)}")


def main():
    print('=' * 60)
    print('discipline_index.py - Phase 2, Step 2.2')
    print('=' * 60)

    ath, disc_map, noc_map, prog = load_data()

    print(f"\n--- Building canonical name lookup ---")
    canon_lookup = build_canonical_lookup(noc_map)
    print(f"  {len(canon_lookup):,} entries")

    print(f"\n--- Joining athlete_discipline_map ---")
    ath = attach_discipline_map(ath, disc_map)

    print(f"\n--- Computing medal counts by discipline ---")
    medals = compute_medal_counts(ath, canon_lookup)

    totals = compute_discipline_totals(medals)

    print(f"\n--- Computing normalized scores ---")
    scores = compute_normalized_scores(medals, totals)

    print(f"\n--- Computing T_scores (3-Olympiad window) ---")
    result = compute_t_scores(scores)

    validate(result)

    out_cols = [
        'canonical_name', 'Discipline', 'Code', 'Year',
        'score_current', 'score_lag1', 'score_lag2',
        'T_score', 'n_years_used'
    ]
    out = result[out_cols]
    write_csv(out, DISCIPLINE_INDEX)
    print(f"\n--- Output ---")
    print(f"  Saved: {DISCIPLINE_INDEX}")
    print(f"  Rows:  {len(out):,}")
    print(f"  Countries: {out['canonical_name'].nunique():,}")
    print(f"  Disciplines: {out['Code'].nunique()}")
    print(f"  Years: {int(out['Year'].min())}-{int(out['Year'].max())}")


if __name__ == '__main__':
    main()
