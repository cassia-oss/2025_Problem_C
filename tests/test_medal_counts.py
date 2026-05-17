"""Integrity checks on output/cleaned/medal_counts_clean.csv."""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import (
    MEDAL_COUNTS_CLEAN, ATHLETES_CLEAN, NOC_MAPPING, OLYMPIC_YEARS,
)


@pytest.fixture(scope="module")
def mc():
    return pd.read_csv(MEDAL_COUNTS_CLEAN)


@pytest.fixture(scope="module")
def ath():
    return pd.read_csv(ATHLETES_CLEAN)


@pytest.fixture(scope="module")
def mapping():
    return pd.read_csv(NOC_MAPPING)


class TestMedalCountsIntegrity:
    def test_no_null_noc(self, mc):
        assert mc["NOC"].notna().all()

    def test_no_empty_noc(self, mc):
        assert (mc["NOC"].astype(str).str.strip() != "").all()

    def test_no_duplicate_key(self, mc):
        dup = mc.duplicated(subset=["NOC", "Year"]).sum()
        assert dup == 0, f"Found {dup} duplicate (NOC, Year) rows"

    def test_gold_silver_bronze_equal_total(self, mc):
        calc_total = mc["Gold"] + mc["Silver"] + mc["Bronze"]
        bad = (calc_total != mc["Total"]).sum()
        assert bad == 0, f"Found {bad} rows where G+S+B != Total"


class TestMedalCountsPanel:
    def test_row_count_matches_athletes(self, mc, ath, mapping):
        """Count of unique (NOC, Year) in medal_counts should match
        count of unique (athlete_NOC, Year) in athletes after dedup.
        Medals use canonical_name; athletes use 3-letter NOC — but
        each athlete (NOC, Year) maps to exactly one canonical_name,
        so the row counts should match.
        """
        ath_pairs = ath[["NOC", "Year"]].drop_duplicates()
        assert len(mc) == len(ath_pairs), \
            f"medal_counts has {len(mc)} rows, athletes has {len(ath_pairs)} unique (NOC, Year)"

    def test_all_years_valid(self, mc):
        bad = set(mc["Year"].unique()) - set(OLYMPIC_YEARS)
        assert bad == set(), f"Years {bad} not in OLYMPIC_YEARS"

    def test_zero_medal_rows_exist(self, mc):
        n_zero = (mc["Total"] == 0).sum()
        assert n_zero > 0, "Expected rows with Total=0 (zero-medal participants)"

    def test_medal_count_positive_or_zero(self, mc):
        assert (mc["Gold"] >= 0).all()
        assert (mc["Silver"] >= 0).all()
        assert (mc["Bronze"] >= 0).all()
        assert (mc["Total"] >= 0).all()
