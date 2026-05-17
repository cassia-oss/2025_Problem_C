"""
build_discipline_map.py - Phase 1, Step 1.7

Input:  output/cleaned/athletes_clean.csv, output/cleaned/programs_clean.csv
Output: output/cleaned/athlete_discipline_map.csv

Purpose:
  Map every unique (Sport, Event) pair in athletes_clean to an IOC discipline
  Code from programs_clean. This mapping is required by discipline_index.py
  (Section 2.2) to compute discipline-level advantage scores.

Mapping approach (see PIPELINE Section 1.7):
  1. Normalize Sport names between athletes_clean and programs_clean
  2. Single-discipline sports -> direct match
  3. Multi-discipline sports -> keyword extraction from Event string
  4. Year-based inference fallback
  5. Manual review export for unmapped rows

Discipline resolution rules are imported from src.utils.discipline_resolver
so that the mapping table is the single source of truth for Phase 2.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    ATHLETES_CLEAN, PROGRAMS_CLEAN,
    ATHLETE_DISCIPLINE_MAP, DISCIPLINE_MAP_REVIEW,
)
from src.utils.io_utils import read_csv, write_csv
from src.utils.discipline_resolver import (
    SPORT_NAME_NORMALIZE,
    get_single_disc_sports,
    make_athlete_keyword,
    resolve_discipline_with_method,
)


def build_discipline_map(ath: pd.DataFrame, prog: pd.DataFrame) -> tuple:
    """Build athlete Sport/Event -> discipline Code mapping."""
    single_disc_sports = get_single_disc_sports(prog)

    pairs = ath[['Sport', 'Event']].drop_duplicates().copy()
    pairs['athlete_keyword'] = pairs['Event'].apply(make_athlete_keyword)
    print(f"  Unique (Sport, Event) pairs: {len(pairs):,}")

    mappings = []
    stats = {
        'sub_sport': 0,
        'single_disc': 0,
        'keyword': 0,
        'default': 0,
        'year_infer': 0,
        'manual_review': 0,
        'excluded': 0,
        'unmapped': 0,
    }

    for _, row in pairs.iterrows():
        athlete_sport = str(row['Sport']).strip()
        event = str(row['Event']).strip()
        athlete_keyword = row['athlete_keyword']

        lookup_sport = athlete_sport.split(', ')[0].strip()
        norm_sport = SPORT_NAME_NORMALIZE.get(lookup_sport, lookup_sport)

        discipline, code, match_method = resolve_discipline_with_method(
            athlete_sport, event, single_disc_sports
        )
        stats[match_method] = stats.get(match_method, 0) + 1

        mappings.append({
            'athlete_Sport': athlete_sport,
            'athlete_keyword': athlete_keyword,
            'programs_Sport': norm_sport if norm_sport is not None else '',
            'programs_Discipline': discipline if discipline else (
                'EXCLUDED' if match_method == 'excluded' else ''
            ),
            'Code': code if code else '',
            'match_method': match_method,
        })

    result = pd.DataFrame(mappings).drop_duplicates().reset_index(drop=True)
    return result, stats


def year_based_fallback(result: pd.DataFrame, ath: pd.DataFrame,
                        prog: pd.DataFrame) -> tuple:
    """Step 1.7.5: infer a code only when all observed years imply one option."""
    unresolved = result[
        (result['Code'] == '') & (result['match_method'] != 'excluded')
    ].copy()
    if len(unresolved) == 0:
        return result, 0

    print(f"\n  Year-based fallback: {len(unresolved)} unmapped rows")

    prog_year = (
        prog[prog['EventCount'] > 0]
        .groupby(['Sport', 'Year'])
        .apply(lambda g: list(zip(g['Discipline'], g['Code'])))
        .to_dict()
    )

    ath_keys = ath[['Sport', 'Event', 'Year']].copy()
    ath_keys['athlete_keyword'] = ath_keys['Event'].apply(make_athlete_keyword)
    years_by_key = (
        ath_keys.groupby(['Sport', 'athlete_keyword'])['Year']
        .apply(lambda s: sorted({int(y) for y in s.dropna()}))
        .to_dict()
    )

    n_inferred = 0
    for idx, row in unresolved.iterrows():
        athlete_sport = row['athlete_Sport']
        athlete_keyword = row['athlete_keyword']
        norm_sport = row['programs_Sport']
        years = years_by_key.get((athlete_sport, athlete_keyword), [])

        options = set()
        for year in years:
            options.update(prog_year.get((norm_sport, year), []))

        if len(options) == 1:
            disc, code = next(iter(options))
            result.loc[idx, 'programs_Discipline'] = disc
            result.loc[idx, 'Code'] = code
            result.loc[idx, 'match_method'] = 'year_infer'
            n_inferred += 1
            print(f"    {athlete_sport:30s} -> {disc:20s} {code}")

    return result, n_inferred


def main():
    print('=' * 60)
    print('build_discipline_map.py - Phase 1, Step 1.7')
    print('=' * 60)

    print(f"\nLoading athletes_clean: {ATHLETES_CLEAN}")
    ath = read_csv(ATHLETES_CLEAN)
    print(f"  {len(ath):,} rows, {ath['Sport'].nunique()} unique sports")

    print(f"\nLoading programs_clean: {PROGRAMS_CLEAN}")
    prog = read_csv(PROGRAMS_CLEAN)
    print(f"  {len(prog):,} rows")

    print(f"\n--- Building discipline map ---")
    result, stats = build_discipline_map(ath, prog)

    result, inferred = year_based_fallback(result, ath, prog)
    stats['year_infer'] = inferred
    stats['unmapped'] = int(
        ((result['Code'] == '') & (result['match_method'] != 'excluded')).sum()
    )

    still_unmapped = result[
        (result['Code'] == '') & (result['match_method'] != 'excluded')
    ].copy()
    if len(still_unmapped) > 0:
        print(f"\n  *** {len(still_unmapped)} pairs still unmapped - write to review ***")
        result.loc[still_unmapped.index, 'match_method'] = 'manual_review'
        still_unmapped = result.loc[still_unmapped.index]
        stats['manual_review'] = len(still_unmapped)
        review_cols = [
            'athlete_Sport', 'athlete_keyword', 'programs_Sport',
            'programs_Discipline', 'Code', 'match_method'
        ]
        write_csv(still_unmapped[review_cols], DISCIPLINE_MAP_REVIEW)
        print(f"  Saved: {DISCIPLINE_MAP_REVIEW}")

    print(f"\n--- Mapping stats ---")
    print(f"  Total unique (Sport, Event) pairs: {len(result):,}")
    for method in [
        'sub_sport', 'single_disc', 'keyword', 'default',
        'year_infer', 'manual_review', 'excluded', 'unmapped'
    ]:
        count = stats.get(method, 0)
        if count > 0:
            print(f"    {method}: {count:,}")

    out_cols = [
        'athlete_Sport', 'athlete_keyword', 'programs_Sport',
        'programs_Discipline', 'Code', 'match_method'
    ]
    write_csv(result[out_cols], ATHLETE_DISCIPLINE_MAP)
    print(f"\n  Saved: {ATHLETE_DISCIPLINE_MAP}")
    print(f"  Rows: {len(result):,}")

    valid = result['match_method'] != 'excluded'
    code_coverage = (result.loc[valid, 'Code'] != '').mean()
    print(f"  Code coverage (excl. excluded): {code_coverage:.1%}")


if __name__ == '__main__':
    main()
