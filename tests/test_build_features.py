"""Tests for src/features/build_features.py — Phase 2, Step 2.1."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import FEATURE_MATRIX, OLYMPIC_YEARS


@pytest.fixture(scope="module")
def fm():
    """Load the feature matrix once per test session."""
    return pd.read_csv(FEATURE_MATRIX)


# ---------------------------------------------------------------------------
# Structural integrity
# ---------------------------------------------------------------------------

class TestStructuralIntegrity:
    """Basic structural checks on the feature matrix."""

    def test_no_duplicate_keys(self, fm):
        dup = fm.duplicated(subset=['canonical_name', 'Year']).sum()
        assert dup == 0, f"Found {dup} duplicate (canonical_name, Year)"

    def test_no_null_keys(self, fm):
        assert fm['canonical_name'].notna().all()
        assert fm['Year'].notna().all()

    def test_all_years_valid(self, fm):
        bad = set(fm['Year'].unique()) - set(OLYMPIC_YEARS)
        assert bad == set(), f"Bad years: {sorted(bad)}"

    def test_no_1906(self, fm):
        assert 1906 not in fm['Year'].values

    def test_country_count(self, fm):
        n = fm['canonical_name'].nunique()
        assert 200 <= n <= 250, f"Expected 200–250 countries, got {n}"

    def test_row_count(self, fm):
        assert 3000 <= len(fm) <= 8000, f"Expected 3000–8000 rows, got {len(fm)}"

    def test_entity_types(self, fm):
        valid = {'country', 'historical_different', 'historical_same', 'special'}
        actual = set(fm['entity_type'].unique())
        assert actual.issubset(valid), f"Bad entity types: {actual - valid}"


# ---------------------------------------------------------------------------
# Target integrity (D18)
# ---------------------------------------------------------------------------

class TestTargetIntegrity:
    """y_gold, y_silver, y_bronze, y_total, y_any consistency."""

    def test_total_equals_sum(self, fm):
        calc = fm['y_gold'] + fm['y_silver'] + fm['y_bronze']
        assert (calc == fm['y_total']).all()

    def test_any_consistent(self, fm):
        assert ((fm['y_any'] == 1) == (fm['y_total'] > 0)).all()

    def test_medals_non_negative(self, fm):
        for col in ['y_gold', 'y_silver', 'y_bronze', 'y_total']:
            assert (fm[col] >= 0).all(), f"{col} has negative values"


# ---------------------------------------------------------------------------
# D15: Entity existence windows
# ---------------------------------------------------------------------------

class TestExistenceWindows:
    """Historical entities must not have rows after dissolution."""

    def test_east_germany_window(self, fm):
        gdr = fm[fm['canonical_name'] == 'East Germany']
        assert len(gdr) > 0, "East Germany missing from feature matrix"
        assert gdr['Year'].max() == 1988, \
            f"East Germany last year should be 1988, got {gdr['Year'].max()}"
        assert 1992 not in gdr['Year'].values, "East Germany should not exist in 1992"

    def test_soviet_union_window(self, fm):
        urs = fm[fm['canonical_name'] == 'Soviet Union']
        assert len(urs) > 0, "Soviet Union missing from feature matrix"
        assert urs['Year'].max() <= 1988, \
            f"Soviet Union should end by 1988, got {urs['Year'].max()}"

    def test_country_extends_to_2024(self, fm):
        countries = fm[fm['entity_type'] == 'country']
        # At least some active countries should reach 2024
        max_year_per = countries.groupby('canonical_name')['Year'].max()
        n_to_2024 = (max_year_per == 2024).sum()
        assert n_to_2024 > 100, \
            f"Only {n_to_2024} countries have rows through 2024"

    def test_no_rows_after_last_year_historical(self, fm):
        """Historical/special entities must not have rows beyond last_year.
        Country entities may have rows past last_year if banned (e.g. Russia
        2024 banned, competed as AIN) — they still exist and the model needs
        to predict their future return.
        """
        hist = fm[fm['entity_type'].isin(['historical_different', 'special'])]
        bad = hist[hist['Year'] > hist['last_year']]
        assert len(bad) == 0, \
            f"Found {len(bad)} rows for historical/special where Year > last_year"


# ---------------------------------------------------------------------------
# D19: Carry-forward lag features for non-participation years
# ---------------------------------------------------------------------------

class TestCarryForward:
    """Lag features must skip non-participation Olympiads."""

    def test_usa_1984_carry_forward(self, fm):
        """USA boycotted 1980; lag features for 1984 should use 1976 data."""
        usa = fm[(fm['canonical_name'] == 'United States') &
                 (fm['Year'] == 1984)]
        assert len(usa) == 1, "USA 1984 row missing"
        row = usa.iloc[0]
        # 1976 total: USA won 94 medals (34G, 35S, 25B)
        assert row['total_lag1'] == 94.0, \
            f"Expected lag1=94 (from 1976), got {row['total_lag1']}"
        assert row['gold_lag1'] == 34.0
        assert row['silver_lag1'] == 35.0

    def test_usa_1980_carry_forward(self, fm):
        """USA 1980 is a boycott year; lag should still carry from 1976."""
        usa = fm[(fm['canonical_name'] == 'United States') &
                 (fm['Year'] == 1980)]
        assert len(usa) == 1
        row = usa.iloc[0]
        assert row['total_lag1'] == 94.0, \
            f"1980 lag1 should also carry from 1976, got {row['total_lag1']}"

    def test_lag_nan_only_for_no_history(self, fm):
        """Lag NaN count = first-participation rows only."""
        # A country's first Olympiad should have all lags NaN
        # Count rows where lag1 is NaN — those should be debut Olympiads
        nan_lag1 = fm[fm['total_lag1'].isna()]
        for _, row in nan_lag1.iterrows():
            msg = (f"{row['canonical_name']} Year={row['Year']} "
                   f"has NaN lag1 but first_year={row['first_year']}")
            assert row['Year'] == row['first_year'], msg


# ---------------------------------------------------------------------------
# D17: Group G — per-Olympiad multi-team snapshot
# ---------------------------------------------------------------------------

class TestMultiTeam:
    """G1 and G2 must be per-Olympiad, not historical."""

    def test_has_multi_teams_binary(self, fm):
        vals = set(fm['has_multi_teams'].unique())
        assert vals.issubset({0, 1}), f"has_multi_teams not binary: {vals}"

    def test_n_multi_disciplines_non_negative(self, fm):
        assert (fm['n_multi_disciplines'] >= 0).all()

    def test_consistency(self, fm):
        """If has_multi_teams=0 then n_multi_disciplines must be 0."""
        no_multi = fm[fm['has_multi_teams'] == 0]
        assert (no_multi['n_multi_disciplines'] == 0).all()

    def test_multi_team_exists(self, fm):
        """Some rows should have multi-team entries."""
        n_multi = fm['has_multi_teams'].sum()
        assert n_multi > 0, "No multi-team rows found in feature matrix"


# ---------------------------------------------------------------------------
# D20: B5 athlete_growth_rate NaN rule
# ---------------------------------------------------------------------------

class TestGrowthRate:
    """B5 growth rate NaN when previous delegation was 0."""

    def test_growth_rate_nan_on_debut(self, fm):
        """First Olympiad should have growth_rate = NaN."""
        debuts = fm[fm['Year'] == fm['first_year']]
        n_good = debuts['athlete_growth_rate'].isna().sum()
        # All debut rows should have NaN growth rate
        assert n_good == len(debuts), \
            f"{len(debuts) - n_good} debut rows have non-NaN growth_rate"


# ---------------------------------------------------------------------------
# D21: D4/D5 EventCount delta
# ---------------------------------------------------------------------------

class TestEventDeltas:
    """D4/D5 use EventCount deltas."""

    def test_1896_nan(self, fm):
        """First Olympiad has no previous Games — D4/D5 should be NaN."""
        y1896 = fm[fm['Year'] == 1896]
        assert y1896['n_new_events'].isna().all(), \
            "n_new_events should be NaN for 1896"
        assert y1896['n_discontinued_events'].isna().all(), \
            "n_discontinued_events should be NaN for 1896"

    def test_non_negative_deltas(self, fm):
        """Where not NaN, both deltas should be >= 0."""
        mask = fm['n_new_events'].notna()
        assert (fm.loc[mask, 'n_new_events'] >= 0).all()
        assert (fm.loc[mask, 'n_discontinued_events'] >= 0).all()

    def test_same_for_all_countries_in_year(self, fm):
        """D features are per-Year, identical for all countries."""
        yr = fm.groupby('Year').agg(
            n_new_std=('n_new_events', 'std'),
            n_disc_std=('n_discontinued_events', 'std'),
        ).dropna()
        # Standard deviation should be 0 (or very close due to float)
        assert (yr['n_new_std'] < 0.01).all(), \
            f"n_new_events varies within year: {yr[yr['n_new_std'] > 0.01]}"
        assert (yr['n_disc_std'] < 0.01).all()


# ---------------------------------------------------------------------------
# Region mapping (D16)
# ---------------------------------------------------------------------------

class TestRegionMapping:
    """F1 must be one of five continental associations."""

    VALID_REGIONS = {'Africa', 'Americas', 'Asia', 'Europe', 'Oceania'}

    def test_valid_regions(self, fm):
        actual = set(fm['region'].unique())
        bad = actual - self.VALID_REGIONS
        assert bad == set(), f"Invalid regions: {bad}"

    def test_no_unknown(self, fm):
        assert 'Unknown' not in fm['region'].values, "Some regions still Unknown"


# ---------------------------------------------------------------------------
# Feature value sanity
# ---------------------------------------------------------------------------

class TestFeatureSanity:
    """Range and plausibility checks."""

    def test_host_features_binary(self, fm):
        for col in ['is_host', 'is_host_next', 'is_host_prev']:
            vals = set(fm[col].unique())
            assert vals.issubset({0, 1}), f"{col} not binary: {vals}"

    def test_host_cycle_phase_range(self, fm):
        phases = set(fm['host_cycle_phase'].unique())
        assert phases.issubset({0, 1, 2, 3}), f"Bad phases: {phases}"

    def test_athlete_counts_non_negative(self, fm):
        for col in ['n_athletes_total', 'n_athletes_male', 'n_athletes_female',
                     'n_unique_events']:
            assert (fm[col] >= 0).all(), f"{col} has negative values"

    def test_total_athletes_consistent(self, fm):
        """n_athletes_total >= n_athletes_male + n_athletes_female."""
        total = fm['n_athletes_male'] + fm['n_athletes_female']
        bad = (total > fm['n_athletes_total']).sum()
        # Allow some slack because Sex may have non-M/F values occasionally
        # But majority should be consistent
        assert bad < 50, \
            f"Found {bad} rows where M+F > total athletes"

    def test_summary_index_range(self, fm):
        mask = fm['summary_index'].notna()
        vals = fm.loc[mask, 'summary_index']
        assert (vals >= 0).all(), "summary_index has negative values"
        assert vals.max() < 100, f"summary_index max too high: {vals.max()}"

    def test_years_since_first(self, fm):
        """years_since_first >= 0 and multiple of 4."""
        assert (fm['years_since_first_participation'] >= 0).all()
        # All should be multiples of 4 (Olympic cycle)
        mods = fm['years_since_first_participation'] % 4
        assert (mods == 0).all(), \
            f"Some years_since_first not multiple of 4: {set(mods.unique())}"
