"""
clean_hosts.py — Phase 1, Step 1.4

Input:  data/summerOly_hosts.csv
Output: output/cleaned/hosts_clean.csv

Steps 1.4.1 through 1.4.3 per PIPELINE.md.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import HOSTS_FILE, HOSTS_CLEAN, CANCELLED_YEARS
from src.utils.io_utils import read_csv, write_csv


# Manual mapping: (City, Country) -> (athlete_NOC, canonical_name)
# Built by looking up each host entity in noc_mapping_v2.csv and IOC records.
HOST_MAP = {
    ('Athens', 'Greece'):                     ('GRE', 'Greece'),
    ('Paris', 'France'):                      ('FRA', 'France'),
    ('St. Louis', 'United States'):           ('USA', 'United States'),
    ('London', 'United Kingdom'):             ('GBR', 'Great Britain'),
    ('Stockholm', 'Sweden'):                  ('SWE', 'Sweden'),
    ('Antwerp', 'Belgium'):                   ('BEL', 'Belgium'),
    ('Amsterdam', 'Netherlands'):             ('NED', 'Netherlands'),
    ('Los Angeles', 'United States'):         ('USA', 'United States'),
    ('Berlin', 'Germany'):                    ('GER', 'Germany'),
    ('Helsinki', 'Finland'):                  ('FIN', 'Finland'),
    ('Melbourne', 'Australia'):               ('AUS', 'Australia'),
    ('Rome', 'Italy'):                        ('ITA', 'Italy'),
    ('Tokyo', 'Japan'):                       ('JPN', 'Japan'),
    ('Mexico City', 'Mexico'):                ('MEX', 'Mexico'),
    ('Munich', 'West Germany'):               ('FRG', 'West Germany'),
    ('Montreal', 'Canada'):                   ('CAN', 'Canada'),
    ('Moscow', 'Soviet Union'):               ('URS', 'Soviet Union'),
    ('Seoul', 'South Korea'):                 ('KOR', 'South Korea'),
    ('Barcelona', 'Spain'):                   ('ESP', 'Spain'),
    ('Atlanta', 'United States'):             ('USA', 'United States'),
    ('Sydney', 'Australia'):                  ('AUS', 'Australia'),
    ('Beijing', 'China'):                     ('CHN', 'China'),
    ('Rio de Janeiro', 'Brazil'):             ('BRA', 'Brazil'),
    ('Brisbane', 'Australia'):                ('AUS', 'Australia'),
}


def clean_hosts() -> pd.DataFrame:
    """Read and clean the hosts CSV."""
    df = read_csv(HOSTS_FILE)

    # Parse Host column: "City, Country" or "City, Country (note)"
    def parse_host(host_str):
        if pd.isna(host_str):
            return None, None
        host_str = str(host_str).strip()
        # Remove parenthetical notes like "(postponed...)"
        if '(' in host_str:
            host_str = host_str[:host_str.index('(')].strip()
        # Remove leading/trailing spaces and quotes
        host_str = host_str.strip('" ')
        if ',' in host_str:
            parts = host_str.split(',', 1)
            city = parts[0].strip()
            country = parts[1].strip()
            return city, country
        return host_str, None

    parsed = df['Host'].apply(parse_host)
    df['City'] = parsed.apply(lambda x: x[0])
    df['Country'] = parsed.apply(lambda x: x[1])

    # Flag special years
    df['is_cancelled'] = df['Year'].isin(CANCELLED_YEARS).astype(int)
    df['is_future'] = (df['Year'] > 2024).astype(int)

    # Map to NOC and canonical_name (only for non-cancelled, non-future)
    df['NOC'] = ''
    df['canonical_name'] = ''

    for idx, row in df.iterrows():
        if row['is_cancelled']:
            df.at[idx, 'NOC'] = 'CANCELLED'
            df.at[idx, 'canonical_name'] = 'CANCELLED'
            continue

        if row['is_future']:
            if row['Year'] == 2028:
                df.at[idx, 'NOC'] = 'USA'
                df.at[idx, 'canonical_name'] = 'United States'
            elif row['Year'] == 2032:
                df.at[idx, 'NOC'] = 'AUS'
                df.at[idx, 'canonical_name'] = 'Australia'
            continue

        key = (row['City'], row['Country'])
        if key in HOST_MAP:
            df.at[idx, 'NOC'] = HOST_MAP[key][0]
            df.at[idx, 'canonical_name'] = HOST_MAP[key][1]
        else:
            print(f'  WARNING: No NOC mapping for {key}')

    # Reorder columns
    out_cols = ['Year', 'City', 'Country', 'NOC', 'canonical_name',
                'is_cancelled', 'is_future']
    df_out = df[out_cols].copy()

    return df_out


def main():
    print('=' * 60)
    print('clean_hosts.py — Phase 1, Step 1.4')
    print('=' * 60)

    print(f'\nLoading: {HOSTS_FILE}')
    df = read_csv(HOSTS_FILE)
    print(f'  {len(df)} rows')

    print(f'\n--- Cleaning hosts ---')
    cleaned = clean_hosts()

    n_cancelled = cleaned['is_cancelled'].sum()
    n_future = cleaned['is_future'].sum()
    n_hosted = len(cleaned) - n_cancelled - n_future

    print(f'  Hosted: {n_hosted}')
    print(f'  Cancelled: {n_cancelled} ({CANCELLED_YEARS})')
    print(f'  Future: {n_future} (2028, 2032)')
    print(f'  NOC codes assigned: {(cleaned["NOC"] != "").sum()}')

    # Check for unmapped entries
    unmapped = cleaned[(cleaned['is_cancelled'] == 0) &
                       (cleaned['is_future'] == 0) &
                       (cleaned['NOC'] == '')]
    if len(unmapped) > 0:
        print(f'\n  WARNING: {len(unmapped)} rows without NOC mapping:')
        for _, r in unmapped.iterrows():
            print(f'    {int(r["Year"])}: {r["City"]}, {r["Country"]}')

    write_csv(cleaned, HOSTS_CLEAN)
    print(f'\n  Saved: {HOSTS_CLEAN}')
    print(f'  Columns: {list(cleaned.columns)}')

    print(f'\nDone.')


if __name__ == '__main__':
    main()
