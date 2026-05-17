"""
build_features.py — Phase 2, Step 2.1

Build the core feature matrix: one row per (canonical_name, Year) pair,
with features from Groups A–G and target variables.

Input:  output/cleaned/athletes_clean.csv
        output/cleaned/medal_counts_clean.csv
        output/cleaned/programs_clean.csv
        output/cleaned/hosts_clean.csv
        output/cleaned/noc_mapping_v2.csv
        output/features/discipline_index.csv
Output: output/features/feature_matrix.csv

See PIPELINE.md Section 2.1 for full feature specification.
"""

import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    ATHLETES_CLEAN, MEDAL_COUNTS_CLEAN, PROGRAMS_CLEAN, HOSTS_CLEAN,
    NOC_MAPPING, DISCIPLINE_INDEX, FEATURE_MATRIX, FEATURES_DIR,
    OLYMPIC_YEARS,
)
from src.utils.io_utils import read_csv, write_csv

# ---------------------------------------------------------------------------
# IOC NOC 3-letter code → region mapping (D16)
# Source: IOC 5 continental associations (ANOCA, OCA, EOC, Panam Sports, ONOC)
# ---------------------------------------------------------------------------

NOC_REGION = {
    # ── Africa (ANOCA) ──
    'ALG': 'Africa', 'ANG': 'Africa', 'BEN': 'Africa', 'BOT': 'Africa',
    'BUR': 'Africa', 'BDI': 'Africa', 'CMR': 'Africa', 'CPV': 'Africa',
    'CAF': 'Africa', 'CHA': 'Africa', 'COM': 'Africa', 'CGO': 'Africa',
    'COD': 'Africa', 'CIV': 'Africa', 'DJI': 'Africa', 'EGY': 'Africa',
    'ERI': 'Africa', 'SWZ': 'Africa', 'ETH': 'Africa', 'GAB': 'Africa',
    'GAM': 'Africa', 'GHA': 'Africa', 'GUI': 'Africa', 'GBS': 'Africa',
    'GEQ': 'Africa', 'KEN': 'Africa', 'LES': 'Africa', 'LBR': 'Africa',
    'LBA': 'Africa', 'MAD': 'Africa', 'MAW': 'Africa', 'MLI': 'Africa',
    'MAR': 'Africa', 'MRI': 'Africa', 'MTN': 'Africa', 'MOZ': 'Africa',
    'NAM': 'Africa', 'NIG': 'Africa', 'NGR': 'Africa', 'RWA': 'Africa',
    'STP': 'Africa', 'SEN': 'Africa', 'SEY': 'Africa', 'SLE': 'Africa',
    'SOM': 'Africa', 'RSA': 'Africa', 'SSD': 'Africa', 'SUD': 'Africa',
    'UGA': 'Africa', 'TAN': 'Africa', 'TOG': 'Africa', 'TUN': 'Africa',
    'ZAM': 'Africa', 'ZIM': 'Africa',

    # ── Americas (Panam Sports) ──
    'ANT': 'Americas', 'ARG': 'Americas', 'ARU': 'Americas', 'BAH': 'Americas',
    'BAR': 'Americas', 'BIZ': 'Americas', 'BER': 'Americas', 'BOL': 'Americas',
    'BRA': 'Americas', 'CAY': 'Americas', 'CAN': 'Americas', 'CHI': 'Americas',
    'COL': 'Americas', 'CRC': 'Americas', 'CUB': 'Americas', 'DOM': 'Americas',
    'DMA': 'Americas', 'ESA': 'Americas', 'ECU': 'Americas', 'GRN': 'Americas',
    'GUA': 'Americas', 'GUY': 'Americas', 'HAI': 'Americas', 'HON': 'Americas',
    'JAM': 'Americas', 'MEX': 'Americas', 'NCA': 'Americas', 'PAN': 'Americas',
    'PAR': 'Americas', 'PER': 'Americas', 'PUR': 'Americas', 'SKN': 'Americas',
    'LCA': 'Americas', 'VIN': 'Americas', 'SUR': 'Americas', 'TTO': 'Americas',
    'USA': 'Americas', 'URU': 'Americas', 'VEN': 'Americas', 'IVB': 'Americas',
    'ISV': 'Americas',

    # ── Asia (OCA) ──
    'AFG': 'Asia', 'BRN': 'Asia', 'BAN': 'Asia', 'BHU': 'Asia',
    'BRU': 'Asia', 'CAM': 'Asia', 'CHN': 'Asia', 'KOR': 'Asia',
    'HKG': 'Asia', 'IND': 'Asia', 'INA': 'Asia', 'IRI': 'Asia',
    'IRQ': 'Asia', 'JPN': 'Asia', 'JOR': 'Asia', 'KAZ': 'Asia',
    'KGZ': 'Asia', 'KUW': 'Asia', 'LAO': 'Asia', 'LBN': 'Asia',
    'MAS': 'Asia', 'MDV': 'Asia', 'MGL': 'Asia', 'MYA': 'Asia',
    'NEP': 'Asia', 'OMA': 'Asia', 'PAK': 'Asia', 'PLE': 'Asia',
    'PHI': 'Asia', 'QAT': 'Asia', 'PRK': 'Asia', 'KSA': 'Asia',
    'SGP': 'Asia', 'SRI': 'Asia', 'SYR': 'Asia', 'TJK': 'Asia',
    'TPE': 'Asia', 'THA': 'Asia', 'TLS': 'Asia', 'TKM': 'Asia',
    'UAE': 'Asia', 'UZB': 'Asia', 'VIE': 'Asia', 'YEM': 'Asia',

    # ── Europe (EOC) ──
    'ALB': 'Europe', 'AND': 'Europe', 'ARM': 'Europe', 'AUT': 'Europe',
    'AZE': 'Europe', 'BEL': 'Europe', 'BIH': 'Europe', 'BUL': 'Europe',
    'CYP': 'Europe', 'CRO': 'Europe', 'CZE': 'Europe', 'DEN': 'Europe',
    'ESP': 'Europe', 'EST': 'Europe', 'FIN': 'Europe', 'FRA': 'Europe',
    'GEO': 'Europe', 'GER': 'Europe', 'GBR': 'Europe', 'GRE': 'Europe',
    'HUN': 'Europe', 'IRL': 'Europe', 'ISL': 'Europe', 'ISR': 'Europe',
    'ITA': 'Europe', 'KOS': 'Europe', 'LAT': 'Europe', 'LIE': 'Europe',
    'LTU': 'Europe', 'LUX': 'Europe', 'MKD': 'Europe', 'MLT': 'Europe',
    'MDA': 'Europe', 'MON': 'Europe', 'MNE': 'Europe', 'NED': 'Europe',
    'NOR': 'Europe', 'POL': 'Europe', 'POR': 'Europe', 'ROU': 'Europe',
    'SMR': 'Europe', 'SRB': 'Europe', 'SVK': 'Europe', 'SLO': 'Europe',
    'BLR': 'Europe',  # Belarus (neutral participant as AIN in 2024)
    'SWE': 'Europe', 'SUI': 'Europe', 'TUR': 'Europe', 'UKR': 'Europe',

    # ── Oceania (ONOC) ──
    'ASA': 'Oceania', 'AUS': 'Oceania', 'COK': 'Oceania', 'FIJ': 'Oceania',
    'GUM': 'Oceania', 'KIR': 'Oceania', 'MHL': 'Oceania', 'FSM': 'Oceania',
    'NRU': 'Oceania', 'NZL': 'Oceania', 'PLW': 'Oceania', 'PNG': 'Oceania',
    'SOL': 'Oceania', 'SAM': 'Oceania', 'TGA': 'Oceania', 'TUV': 'Oceania',
    'VAN': 'Oceania',

    # ── Historical NOCs ──
    'BOH': 'Europe',       # Bohemia
    'TCH': 'Europe',       # Czechoslovakia
    'GDR': 'Europe',       # East Germany
    'FRG': 'Europe',       # West Germany
    'URS': 'Europe',       # Soviet Union
    'EUN': 'Europe',       # Unified Team (1992)
    'YUG': 'Europe',       # Yugoslavia
    'SCG': 'Europe',       # Serbia and Montenegro
    'IOP': 'Europe',       # Independent Olympic Participants
    'IOA': 'Asia',         # Individual Olympic Athletes
    'AIN': 'Europe',       # Individual Neutral Athletes
    'ANZ': 'Oceania',      # Australasia
    'MAL': 'Asia',         # Malaya
    'BWI': 'Americas',     # British West Indies
    'NBO': 'Asia',         # North Borneo
    'NRH': 'Africa',       # Rhodesia (alt code)
    'RHO': 'Africa',       # Rhodesia
    'SAA': 'Europe',       # Saar
    'VNM': 'Asia',         # South Vietnam
    'YAR': 'Asia',         # North Yemen
    'YMD': 'Asia',         # South Yemen
    'NFL': 'Americas',     # Newfoundland
    'AHO': 'Americas',     # Netherlands Antilles
    'WIF': 'Americas',     # West Indies Federation
    'UAR': 'Africa',       # United Arab Republic
    'RAU': 'Africa',       # United Arab Republic (alt)
    'ROC': 'Europe',       # Russian Olympic Committee
    'EOR': 'Asia',         # Refugee Olympic Team
    'MIX': 'Europe',       # Mixed team
    'UNK': 'Europe',       # Unknown
    'RUC': 'Europe',       # Russian Empire
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prev_olympic_years(year: int, n: int = 3) -> list:
    """Return the n most recent Olympic Years strictly before `year`."""
    prev = [y for y in OLYMPIC_YEARS if y < year]
    return list(reversed(prev[-n:]))


def _build_canonical_lookup(noc_map: pd.DataFrame) -> dict:
    """Build (athlete_NOC, Year) -> canonical_name lookup."""
    lookup = {}
    for _, r in noc_map.iterrows():
        key = (str(r.get('athlete_NOC', '')).strip(), int(r.get('Year', 0)))
        val = str(r.get('canonical_name', '')).strip()
        if val and pd.notna(r.get('canonical_name')):
            lookup[key] = val
    return lookup


def _resolve_canonical(noc: str, year: int, canon_lookup: dict) -> str:
    """Resolve a 3-letter NOC + Year to canonical_name via noc_mapping_v2."""
    key = (str(noc).strip(), int(year))
    return canon_lookup.get(key, str(noc))


# ---------------------------------------------------------------------------
# Step 1: Entity existence windows
# ---------------------------------------------------------------------------

def build_entity_index(ath: pd.DataFrame, noc_map: pd.DataFrame,
                       canon_lookup: dict) -> pd.DataFrame:
    """Build first_year, last_year, entity_type per canonical_name."""
    # Get entity_type per canonical_name from noc_map
    etype = noc_map.groupby('canonical_name')['entity_type'].first().to_dict()

    # Add canonical_name to athletes
    ath = ath.copy()
    ath['_cname'] = ath.apply(
        lambda r: _resolve_canonical(r['NOC'], r['Year'], canon_lookup), axis=1
    )

    yr = ath.groupby('_cname')['Year'].agg(['min', 'max']).reset_index()
    yr.columns = ['canonical_name', 'first_year', 'last_year']
    yr['entity_type'] = yr['canonical_name'].map(etype).fillna('country')

    print(f"\n  Entities: {len(yr)}")
    for et in ['country', 'historical_different', 'historical_same', 'special']:
        n = len(yr[yr['entity_type'] == et])
        print(f"    {et}: {n}")

    return yr


def build_row_index(entities: pd.DataFrame) -> pd.DataFrame:
    """Create valid (canonical_name, Year) rows (D15)."""
    rows = []
    for _, e in entities.iterrows():
        cname = e['canonical_name']
        etype = e['entity_type']
        first = int(e['first_year'])
        last = int(e['last_year'])

        if etype in ('country', 'historical_same'):
            for y in OLYMPIC_YEARS:
                if y >= first:
                    rows.append({'canonical_name': cname, 'Year': y,
                                 'entity_type': etype, 'first_year': first,
                                 'last_year': last})
        else:
            for y in OLYMPIC_YEARS:
                if first <= y <= last:
                    rows.append({'canonical_name': cname, 'Year': y,
                                 'entity_type': etype, 'first_year': first,
                                 'last_year': last})

    result = pd.DataFrame(rows).sort_values(
        ['canonical_name', 'Year']
    ).reset_index(drop=True)
    print(f"\n  Row index: {len(result):,} rows")
    return result


# ---------------------------------------------------------------------------
# Step 2: Group A — Lagged medal performance
# ---------------------------------------------------------------------------

def compute_group_a(index_df: pd.DataFrame,
                    medals: pd.DataFrame) -> pd.DataFrame:
    """Compute lag1/lag2/lag3 with carry-forward for non-participation (D19)."""
    # Lookup: (canonical_name, Year) → (G, S, B, T)
    medal_lookup = {}
    for _, r in medals.iterrows():
        medal_lookup[(str(r['NOC']).strip(), int(r['Year']))] = (
            int(r['Gold']), int(r['Silver']), int(r['Bronze']), int(r['Total'])
        )
    partic_set = set(medal_lookup.keys())

    records = []
    grouped = list(index_df.groupby('canonical_name'))

    for cname, grp in grouped:
        grp = grp.sort_values('Year')
        for _, row in grp.iterrows():
            year = int(row['Year'])
            candidate_years = _prev_olympic_years(year, n=99)
            partic_years = [y for y in candidate_years
                            if (cname, y) in partic_set]

            for lag_i in range(1, 4):
                if len(partic_years) >= lag_i:
                    ly = partic_years[lag_i - 1]
                    g, s, b, t = medal_lookup[(cname, ly)]
                    binary = 1 if t > 0 else 0
                else:
                    g = s = b = t = binary = np.nan

                records.append({
                    'canonical_name': cname, 'Year': year,
                    'lag': lag_i,
                    'gold': g, 'silver': s, 'bronze': b,
                    'total': t, 'binary': binary,
                })

    df_long = pd.DataFrame(records)

    # Pivot each lag into wide columns
    parts = []
    for lag in [1, 2, 3]:
        sub = df_long[df_long['lag'] == lag].drop(columns=['lag'])
        sub = sub.rename(columns={
            'gold': f'gold_lag{lag}',
            'silver': f'silver_lag{lag}',
            'bronze': f'bronze_lag{lag}',
            'total': f'total_lag{lag}',
            'binary': f'medal_won_binary_lag{lag}',
        })
        parts.append(sub.set_index(['canonical_name', 'Year']))

    result = pd.concat(parts, axis=1).reset_index()

    # A4 is binary_lag1 — already present
    print(f"\n  Group A: {len(result)} rows")
    for lag in [1, 2, 3]:
        n_nan = result[f'total_lag{lag}'].isna().sum()
        print(f"    lag{lag} NaN: {n_nan:,} ({n_nan/len(result)*100:.1f}%)")
    return result


# ---------------------------------------------------------------------------
# Step 3: Group B — Athlete delegation
# ---------------------------------------------------------------------------

def compute_group_b(index_df: pd.DataFrame, ath: pd.DataFrame,
                    canon_lookup: dict) -> pd.DataFrame:
    """Compute athlete delegation features (D19 carry-forward for B5)."""
    ath = ath.copy()
    ath['_cname'] = ath.apply(
        lambda r: _resolve_canonical(r['NOC'], r['Year'], canon_lookup), axis=1
    )

    agg = ath.groupby(['_cname', 'Year']).agg(
        n_athletes_total=('Name', 'count'),
        n_athletes_male=('Sex', lambda x: (x == 'M').sum()),
        n_athletes_female=('Sex', lambda x: (x == 'F').sum()),
        n_unique_events=('Event', 'nunique'),
    ).reset_index()
    agg.columns = ['canonical_name', 'Year',
                   'n_athletes_total', 'n_athletes_male',
                   'n_athletes_female', 'n_unique_events']

    result = index_df[['canonical_name', 'Year']].merge(
        agg, on=['canonical_name', 'Year'], how='left'
    )
    for col in ['n_athletes_total', 'n_athletes_male',
                'n_athletes_female', 'n_unique_events']:
        result[col] = result[col].fillna(0).astype(int)

    # B5: growth rate — find most recent prior participation with >0 athletes
    deleg_lookup = {}
    for _, r in agg.iterrows():
        deleg_lookup[(r['canonical_name'], int(r['Year']))] = int(r['n_athletes_total'])

    growth_rates = []
    for _, row in result.iterrows():
        cname = row['canonical_name']
        year = int(row['Year'])
        current = int(row['n_athletes_total'])

        candidate_years = _prev_olympic_years(year, n=99)
        prev_val = None
        for y in candidate_years:
            key = (cname, y)
            if key in deleg_lookup and deleg_lookup[key] > 0:
                prev_val = deleg_lookup[key]
                break

        if prev_val is not None and prev_val > 0 and current > 0:
            rate = round((current - prev_val) / prev_val, 6)
        else:
            rate = np.nan
        growth_rates.append(rate)

    result['athlete_growth_rate'] = growth_rates

    print(f"\n  Group B: {len(result)} rows")
    print(f"    total athletes range: {result['n_athletes_total'].min():,} – "
          f"{result['n_athletes_total'].max():,}")
    print(f"    growth_rate NaN: {result['athlete_growth_rate'].isna().sum():,}")
    return result


# ---------------------------------------------------------------------------
# Step 4: Group C — Host features
# ---------------------------------------------------------------------------

def compute_group_c(index_df: pd.DataFrame, hosts: pd.DataFrame) -> pd.DataFrame:
    """Compute host-related features from hosts_clean."""
    # Build host set + per-cname host years
    host_set = set()
    host_years_by_cname = defaultdict(list)
    for _, r in hosts.iterrows():
        if r.get('is_cancelled') == 1:
            continue
        cname = str(r.get('canonical_name', '')).strip()
        year = int(r['Year'])
        if cname and cname != 'CANCELLED':
            host_set.add((cname, year))
            host_years_by_cname[cname].append(year)

    rows_out = []
    for _, row in index_df.iterrows():
        cname = row['canonical_name']
        year = int(row['Year'])

        is_host = 1 if (cname, year) in host_set else 0

        next_oly = [y for y in OLYMPIC_YEARS if y > year]
        next_oly = next_oly[0] if next_oly else None
        is_host_next = 1 if (next_oly and (cname, next_oly) in host_set) else 0

        prev_oly = [y for y in OLYMPIC_YEARS if y < year]
        prev_oly = prev_oly[-1] if prev_oly else None
        is_host_prev = 1 if (prev_oly and (cname, prev_oly) in host_set) else 0

        if is_host:
            cycle = 2
        elif is_host_next:
            cycle = 1
        elif is_host_prev:
            cycle = 3
        else:
            cycle = 0

        past_hosts = [h for h in host_years_by_cname.get(cname, []) if h < year]
        years_since = year - max(past_hosts) if past_hosts else -1

        rows_out.append({
            'canonical_name': cname, 'Year': year,
            'is_host': is_host,
            'is_host_next': is_host_next,
            'is_host_prev': is_host_prev,
            'host_cycle_phase': cycle,
            'years_since_last_host': years_since,
        })

    result = pd.DataFrame(rows_out)
    print(f"\n  Group C: {len(result)} rows")
    print(f"    host years: {result['is_host'].sum()}")
    return result


# ---------------------------------------------------------------------------
# Step 5: Group D — Event structure (D4/D5: EventCount deltas, D21)
# ---------------------------------------------------------------------------

def compute_group_d(index_df: pd.DataFrame, programs: pd.DataFrame) -> pd.DataFrame:
    """Compute event structure features."""
    off = programs[programs['status_code'] == 'official'].copy()

    # Year-level aggregates
    year_agg = off.groupby('Year').agg(
        total_events=('EventCount', 'sum'),
        n_sports=('Sport', 'nunique'),
        n_disciplines=('Code', 'nunique'),
    ).reset_index()

    # D4/D5: per (Sport, Discipline, Code) EventCount deltas
    event_tbl = off.pivot_table(
        index=['Sport', 'Discipline', 'Code'],
        columns='Year',
        values='EventCount',
        fill_value=0,
    )

    deltas = []
    for year in OLYMPIC_YEARS:
        if year not in event_tbl.columns:
            deltas.append({'Year': year, 'n_new_events': np.nan,
                           'n_discontinued_events': np.nan})
            continue
        prev_year = [y for y in OLYMPIC_YEARS if y < year]
        if not prev_year or prev_year[-1] not in event_tbl.columns:
            deltas.append({'Year': year, 'n_new_events': np.nan,
                           'n_discontinued_events': np.nan})
            continue
        prev_year = prev_year[-1]
        diff = event_tbl[year] - event_tbl[prev_year]
        n_new = int(diff[diff > 0].sum())
        n_disc = int(abs(diff[diff < 0].sum()))
        deltas.append({'Year': year, 'n_new_events': n_new,
                       'n_discontinued_events': n_disc})

    d_features = year_agg.merge(pd.DataFrame(deltas), on='Year', how='left')
    d_features = d_features.rename(columns={
        'total_events': 'total_events_this_year',
        'n_sports': 'n_sports_this_year',
        'n_disciplines': 'n_disciplines_this_year',
    })

    result = index_df[['canonical_name', 'Year']].merge(
        d_features, on='Year', how='left'
    )

    for col in ['total_events_this_year', 'n_sports_this_year',
                'n_disciplines_this_year']:
        result[col] = result[col].astype(int)

    print(f"\n  Group D: {len(result)} rows")
    print(f"    events range: {int(result['total_events_this_year'].min())} – "
          f"{int(result['total_events_this_year'].max())}")
    return result


# ---------------------------------------------------------------------------
# Step 6: Group E — Discipline advantage index
# ---------------------------------------------------------------------------

def compute_group_e(index_df: pd.DataFrame,
                    disc_idx: pd.DataFrame) -> pd.DataFrame:
    """Aggregate discipline_index features per (canonical_name, Year)."""
    di = disc_idx.copy()

    # E1: summary_index
    e1 = di.groupby(['canonical_name', 'Year'])['T_score'].sum().reset_index()
    e1.columns = ['canonical_name', 'Year', 'summary_index']

    # E2–E4: T_score thresholds
    di['tier'] = pd.cut(di['T_score'],
                        bins=[-np.inf, 0, 1, 2, np.inf],
                        labels=['none', 'potential', 'general', 'obvious'],
                        right=False)
    # NaN T_score → tier = 'none'
    di['tier'] = di['tier'].astype(object).fillna('none')

    tier_pivot = di.groupby(
        ['canonical_name', 'Year', 'tier']
    ).size().unstack(fill_value=0).reset_index()

    for tier_label, col_name in [
        ('obvious', 'n_obvious_advantage'),
        ('general', 'n_general_advantage'),
        ('potential', 'n_potential_advantage'),
    ]:
        tier_pivot[col_name] = (
            tier_pivot[tier_label].astype(int)
            if tier_label in tier_pivot.columns else 0
        )

    # E5–E6: top discipline
    top = di.loc[di.groupby(['canonical_name', 'Year'])['T_score'].idxmax()]
    top = top[['canonical_name', 'Year', 'Code', 'T_score']].rename(columns={
        'Code': 'top_discipline_code',
        'T_score': 'top_discipline_score',
    })

    result = index_df[['canonical_name', 'Year']]
    result = result.merge(e1, on=['canonical_name', 'Year'], how='left')
    keep_cols = ['canonical_name', 'Year',
                 'n_obvious_advantage', 'n_general_advantage',
                 'n_potential_advantage']
    result = result.merge(
        tier_pivot[[c for c in keep_cols if c in tier_pivot.columns]],
        on=['canonical_name', 'Year'], how='left'
    )
    result = result.merge(top, on=['canonical_name', 'Year'], how='left')

    for col in ['n_obvious_advantage', 'n_general_advantage',
                'n_potential_advantage']:
        if col in result.columns:
            result[col] = result[col].fillna(0).astype(int)

    print(f"\n  Group E: {len(result)} rows")
    print(f"    summary_index range: [{result['summary_index'].min():.4f}, "
          f"{result['summary_index'].max():.4f}]")
    print(f"    summary_index NaN: {result['summary_index'].isna().sum():,}")
    return result


# ---------------------------------------------------------------------------
# Step 7: Group F — Geopolitical / structural
# ---------------------------------------------------------------------------

def compute_group_f(index_df: pd.DataFrame, ath: pd.DataFrame,
                    noc_map: pd.DataFrame, canon_lookup: dict) -> pd.DataFrame:
    """Compute geopolitical and structural features."""
    # canonical_name → first athlete_NOC seen
    cname_to_noc = {}
    for _, r in noc_map.iterrows():
        cname = str(r.get('canonical_name', '')).strip()
        noc = str(r.get('athlete_NOC', '')).strip()
        if cname and noc and cname not in cname_to_noc:
            cname_to_noc[cname] = noc

    def get_region(cname):
        noc = cname_to_noc.get(cname, '')
        return NOC_REGION.get(noc, 'Unknown')

    # Participation years set per canonical_name
    ath2 = ath.copy()
    ath2['_cname'] = ath2.apply(
        lambda r: _resolve_canonical(r['NOC'], r['Year'], canon_lookup), axis=1
    )
    partic_years = ath2.groupby('_cname')['Year'].apply(set).to_dict()

    rows_out = []
    unmapped = set()
    for _, row in index_df.iterrows():
        cname = row['canonical_name']
        year = int(row['Year'])
        first_y = int(row['first_year'])

        region = get_region(cname)
        if region == 'Unknown':
            unmapped.add(cname)

        years_since_first = year - first_y
        py = partic_years.get(cname, set())
        n_so_far = len([y for y in py if y <= year])

        rows_out.append({
            'canonical_name': cname, 'Year': year,
            'region': region,
            'years_since_first_participation': years_since_first,
            'n_olympiads_participated': n_so_far,
        })

    result = pd.DataFrame(rows_out)

    if unmapped:
        print(f"\n  WARNING: {len(unmapped)} canonical_name(s) unmapped to region:")
        for c in sorted(unmapped):
            print(f"    {c} (NOC={cname_to_noc.get(c, '?')})")

    print(f"\n  Group F: {len(result)} rows")
    for reg, cnt in result['region'].value_counts().items():
        print(f"    {reg}: {cnt:,}")
    return result


# ---------------------------------------------------------------------------
# Step 8: Group G — Multi-team indicator (D17)
# ---------------------------------------------------------------------------

def compute_group_g(index_df: pd.DataFrame, ath: pd.DataFrame,
                    canon_lookup: dict) -> pd.DataFrame:
    """Compute per-Olympiad multi-team features."""
    ath2 = ath.copy()
    ath2['_cname'] = ath2.apply(
        lambda r: _resolve_canonical(r['NOC'], r['Year'], canon_lookup), axis=1
    )
    multi = ath2[ath2['is_multi_team'] == 1]

    agg = multi.groupby(['_cname', 'Year']).agg(
        has_multi_teams=('is_multi_team', lambda x: 1),
        n_multi_disciplines=('Sport', 'nunique'),
    ).reset_index()
    agg.columns = ['canonical_name', 'Year',
                   'has_multi_teams', 'n_multi_disciplines']

    result = index_df[['canonical_name', 'Year']].merge(
        agg, on=['canonical_name', 'Year'], how='left'
    )
    result['has_multi_teams'] = result['has_multi_teams'].fillna(0).astype(int)
    result['n_multi_disciplines'] = result['n_multi_disciplines'].fillna(0).astype(int)

    print(f"\n  Group G: {len(result)} rows")
    print(f"    has_multi_teams=1: {result['has_multi_teams'].sum():,}")
    print(f"    max n_multi_disciplines: {int(result['n_multi_disciplines'].max())}")
    return result


# ---------------------------------------------------------------------------
# Step 9: Target variables (D18)
# ---------------------------------------------------------------------------

def compute_targets(index_df: pd.DataFrame,
                    medals: pd.DataFrame) -> pd.DataFrame:
    """Join medal targets from medal_counts_clean."""
    targets = medals[['NOC', 'Year', 'Gold', 'Silver', 'Bronze', 'Total']].rename(
        columns={'NOC': 'canonical_name'}
    )
    result = index_df[['canonical_name', 'Year']].merge(
        targets, on=['canonical_name', 'Year'], how='left'
    )
    for col in ['Gold', 'Silver', 'Bronze', 'Total']:
        result[col] = result[col].fillna(0).astype(int)
    result = result.rename(columns={
        'Gold': 'y_gold', 'Silver': 'y_silver',
        'Bronze': 'y_bronze', 'Total': 'y_total',
    })
    result['y_any'] = (result['y_total'] > 0).astype(int)

    print(f"\n  Targets: {len(result)} rows")
    print(f"    y_any=1: {result['y_any'].sum():,} "
          f"({result['y_any'].sum()/len(result)*100:.1f}%)")
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame) -> None:
    """Run integrity checks per PIPELINE Section 6."""
    print(f"\n{'='*60}")
    print("Validation")
    print(f"{'='*60}")

    dup = df.duplicated(subset=['canonical_name', 'Year']).sum()
    print(f"  Duplicate keys: {dup}" + ("  ERROR!" if dup else ""))

    if 1906 in df['Year'].values:
        print(f"  ERROR: Year=1906 found!")

    bad_years = set(df['Year'].unique()) - set(OLYMPIC_YEARS)
    if bad_years:
        print(f"  ERROR: Bad years: {sorted(bad_years)}")

    total_ok = (df['y_total'] == df['y_gold'] + df['y_silver'] + df['y_bronze']).all()
    print(f"  y_total == sum(y_gold,silver,bronze): {total_ok}")

    any_ok = ((df['y_any'] == 1) == (df['y_total'] > 0)).all()
    print(f"  y_any consistent: {any_ok}")

    print(f"\n  NaN summary:")
    for col in df.columns:
        n = df[col].isna().sum()
        if n > 0:
            print(f"    {col}: {n:,} ({n/len(df)*100:.1f}%)")

    # Column count
    feature_cols = [c for c in df.columns
                    if not c.startswith('y_') and c not in
                    ('canonical_name', 'Year', 'entity_type',
                     'first_year', 'last_year')]
    target_cols = [c for c in df.columns if c.startswith('y_')]
    print(f"\n  Features: {len(feature_cols)}  Targets: {len(target_cols)}")
    print(f"  Total columns: {len(df.columns)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("build_features.py — Phase 2, Step 2.1")
    print("=" * 60)

    print("\n--- Loading data ---")
    ath = read_csv(ATHLETES_CLEAN)
    print(f"  athletes_clean: {len(ath):,} rows")

    medals = read_csv(MEDAL_COUNTS_CLEAN)
    print(f"  medal_counts_clean: {len(medals):,} rows")

    programs = read_csv(PROGRAMS_CLEAN)
    print(f"  programs_clean: {len(programs):,} rows")

    hosts = read_csv(HOSTS_CLEAN)
    print(f"  hosts_clean: {len(hosts):,} rows")

    noc_map = read_csv(NOC_MAPPING)
    print(f"  noc_mapping_v2: {len(noc_map):,} rows")

    disc_idx = read_csv(DISCIPLINE_INDEX)
    print(f"  discipline_index: {len(disc_idx):,} rows")

    canon_lookup = _build_canonical_lookup(noc_map)

    # Step 1
    print("\n--- Building entity index ---")
    entities = build_entity_index(ath, noc_map, canon_lookup)
    index_df = build_row_index(entities)

    # Step 2–9
    print("\n--- Group A: Lagged medals ---")
    a = compute_group_a(index_df, medals)

    print("\n--- Group B: Athlete delegation ---")
    b = compute_group_b(index_df, ath, canon_lookup)

    print("\n--- Group C: Host features ---")
    c = compute_group_c(index_df, hosts)

    print("\n--- Group D: Event structure ---")
    d = compute_group_d(index_df, programs)

    print("\n--- Group E: Discipline advantage ---")
    e = compute_group_e(index_df, disc_idx)

    print("\n--- Group F: Geopolitical / structural ---")
    f = compute_group_f(index_df, ath, noc_map, canon_lookup)

    print("\n--- Group G: Multi-team ---")
    g = compute_group_g(index_df, ath, canon_lookup)

    print("\n--- Targets ---")
    t = compute_targets(index_df, medals)

    # Assemble
    print("\n--- Assembling ---")
    master = index_df[['canonical_name', 'Year', 'entity_type',
                       'first_year', 'last_year']].copy()
    for df_part in [a, b, c, d, e, f, g, t]:
        merge_cols = [c for c in df_part.columns
                      if c not in ['entity_type', 'first_year', 'last_year']]
        master = master.merge(df_part[merge_cols],
                              on=['canonical_name', 'Year'], how='left')

    print(f"  Assembled: {len(master)} rows × {len(master.columns)} columns")

    validate(master)

    write_csv(master, FEATURE_MATRIX)
    print(f"\n--- Output ---")
    print(f"  Saved: {FEATURE_MATRIX}")
    print(f"  Rows: {len(master):,}")
    print(f"  Countries: {master['canonical_name'].nunique():,}")
    print(f"  Years: {int(master['Year'].min())}–{int(master['Year'].max())}")


if __name__ == "__main__":
    main()
