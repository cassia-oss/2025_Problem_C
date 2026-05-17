"""
clean_programs.py — Phase 1, Step 1.3

Input:  data/summerOly_programs.csv
Output: output/cleaned/programs_clean.csv

Steps 1.3.1 through 1.3.4 per PIPELINE.md:
  1.3.1  Melt from wide to long format
  1.3.2  Handle bullet (•) values → is_demo flag
  1.3.3  Drop cancelled years (1916, 1940, 1944)
  1.3.4  Handle special characters in Sport/Discipline names
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import PROGRAMS_FILE, PROGRAMS_CLEAN, CANCELLED_YEARS, OLYMPIC_YEARS
from src.utils.io_utils import read_csv, write_csv


def load_and_melt() -> pd.DataFrame:
    """Step 1.3.1: Load wide-format programs data and melt to long format.

    The raw CSV has columns: Sport, Discipline, Code, Sports Governing Body,
    then one column per Olympic year (1896, 1900, ..., 2024).
    """
    df = read_csv(PROGRAMS_FILE, encoding='ISO-8859-1')
    print(f'  Raw shape: {df.shape}')

    # Identify year columns (numeric column names, excluding first 4)
    id_cols = ['Sport', 'Discipline', 'Code', 'Sports Governing Body']
    year_cols = [c for c in df.columns if c not in id_cols]

    # Clean year column names: strip '1906*' -> 1906, convert to int
    year_map = {}
    for c in year_cols:
        clean = str(c).replace('*', '').strip()
        year_map[c] = int(clean)

    df = df.rename(columns=year_map)
    year_cols_clean = list(year_map.values())

    # Melt
    df_long = df.melt(
        id_vars=id_cols,
        value_vars=year_cols_clean,
        var_name='Year',
        value_name='EventCount_raw'
    )
    df_long['Year'] = df_long['Year'].astype(int)

    # Drop summary rows (Total events / Total disciplines / Total sports)
    df_long = df_long[~df_long['Sport'].str.contains('Total', case=False, na=False)]
    df_long = df_long.dropna(subset=['Sport'])
    df_long = df_long[df_long['Sport'].str.strip() != '']

    print(f'  Long format: {len(df_long):,} rows')
    return df_long


def parse_event_count(val):
    """Step 1.3.2: Parse a single cell value into (EventCount, is_demo, status_code).

    Per data_dictionary.csv, the raw data uses these special markers:
      - Bullet (•) — demonstration/unofficial sport. The bullet character
        was corrupted to '?' during encoding, producing values like
        '?0', '?4', '??0', '??1'.
      - [s3] footnote — cancelled due to bad weather (1896 sailing/rowing).
      - [s5] footnote — moved to Winter Olympics (pre-1924 ice sports).

    Returns (EventCount, is_demo, status_code).
    """
    if pd.isna(val):
        return 0, 0, "official"

    s = str(val).strip()

    # ---- Demo/unofficial sports: bullet corrupted to ? ----
    # '?0' or '??0' → 0 events, demo
    # '?4' → 4 events, demo  (extract the number!)
    # '??1' → 1 event, demo  (extract the number!)
    if s in ("?0", "??0"):
        return 0, 1, "demo"
    if s in ("?4", "??1"):
        nums = re.findall(r"\d+", s)
        return int(nums[0]), 1, "demo"

    # ---- Cancelled due to weather (S3 footnote) ----
    if s == "0[s3]":
        return 0, 0, "cancelled_weather"

    # ---- Moved to Winter Olympics (S5 footnote) ----
    if "winter" in s.lower():
        return 0, 0, "winter_transfer"

    # ---- Plain numeric ----
    try:
        count = int(float(s))
        return count, 0, "official"
    except (ValueError, TypeError):
        pass

    # ---- Catch-all for any unrecognized non-numeric ----
    nums = re.findall(r"\d+", s)
    if nums:
        return int(nums[0]), 0, "unrecognized"
    return 0, 0, "unrecognized"


def clean_programs() -> pd.DataFrame:
    """Main cleaning pipeline for programs data."""
    df = load_and_melt()

    # Parse EventCount
    parsed = df['EventCount_raw'].apply(parse_event_count)
    df['EventCount'] = parsed.apply(lambda x: x[0])
    df['is_demo'] = parsed.apply(lambda x: x[1])
    df['status_code'] = parsed.apply(lambda x: x[2])

    n_demo = df['is_demo'].sum()
    print(f'  Demonstration entries (is_demo=1): {n_demo} rows')
    print(f'  Status code distribution:')
    for code, count in df['status_code'].value_counts().items():
        print(f'    {code}: {count}')

    # Step 1.3.3: Drop cancelled years and non-Olympic years (e.g., 1906)
    n_before = len(df)
    df = df[~df['Year'].isin(CANCELLED_YEARS)]
    df = df[df['Year'].isin(OLYMPIC_YEARS)]
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        print(f'  Dropped {n_dropped} rows (cancelled years + non-Olympic years)')

    # Step 1.3.4: Clean special characters in Sport/Discipline names
    df['Sport'] = df['Sport'].str.strip()
    df['Discipline'] = df['Discipline'].str.strip().fillna('')

    # Check for encoding artifacts
    for col in ['Sport', 'Discipline']:
        garbled = df[df[col].str.contains('�', na=False)]
        if len(garbled) > 0:
            print(f'  WARNING: {len(garbled)} rows with U+FFFD in {col}: '
                  f'{sorted(garbled[col].unique())}')
        else:
            print(f'  No encoding artifacts in {col}')

    # Drop Sports Governing Body (not needed downstream)
    df = df.drop(columns=['Sports Governing Body', 'EventCount_raw'])

    # Reorder columns
    df = df[['Sport', 'Discipline', 'Code', 'Year', 'EventCount', 'is_demo', 'status_code']]
    df = df.sort_values(['Sport', 'Discipline', 'Year']).reset_index(drop=True)

    return df


def summarize(df: pd.DataFrame) -> None:
    """Print summary statistics."""
    print(f'\n--- Summary ---')
    print(f'  Unique Sports: {df["Sport"].nunique()}')
    print(f'  Unique Disciplines: {df["Discipline"].nunique()}')
    print(f'  Unique Codes: {df["Code"].nunique()}')
    print(f'  Year range: {df["Year"].min()} – {df["Year"].max()}')
    print(f'  Total event-entries: {df["EventCount"].sum():,}')
    print(f'  Demo entries: {df["is_demo"].sum()}')
    print(f'  Rows with EventCount=0: {(df["EventCount"] == 0).sum()}')
    print(f'  Status codes: {dict(df["status_code"].value_counts())}')

    # Top sports by event count
    print(f'\n  Top 10 sports by total event-entries:')
    top = df.groupby('Sport')['EventCount'].sum().sort_values(ascending=False).head(10)
    for sport, count in top.items():
        print(f'    {sport:25s} {int(count):,}')


def main():
    print('=' * 60)
    print('clean_programs.py — Phase 1, Step 1.3')
    print('=' * 60)

    print(f'\nLoading: {PROGRAMS_FILE}')

    print(f'\n--- Step 1.3.1–1.3.4: Melt, parse, clean ---')
    df = clean_programs()

    summarize(df)

    write_csv(df, PROGRAMS_CLEAN)
    print(f'\n  Saved: {PROGRAMS_CLEAN}')
    print(f'  Rows: {len(df):,}')
    print(f'  Columns: {list(df.columns)}')

    print(f'\nDone.')


if __name__ == '__main__':
    main()
