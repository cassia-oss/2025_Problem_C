"""Static checks on src/utils/config.py constants."""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import (
    OLYMPIC_YEARS, CANCELLED_YEARS,
    FIRST_OLYMPIC_YEAR, LAST_OLYMPIC_YEAR,
    MEDAL_COUNTS_CLEAN, ATHLETES_CLEAN, PROGRAMS_CLEAN, HOSTS_CLEAN,
)


class TestOlympicYears:
    def test_excludes_1906(self):
        assert 1906 not in OLYMPIC_YEARS

    def test_count_30(self):
        assert len(OLYMPIC_YEARS) == 30

    def test_cancelled_years_excluded(self):
        for y in CANCELLED_YEARS:
            assert y not in OLYMPIC_YEARS, f"{y} should not be in OLYMPIC_YEARS"

    def test_all_4_year_cycle_present(self):
        for y in range(1896, 2025, 4):
            if y not in CANCELLED_YEARS:
                assert y in OLYMPIC_YEARS, f"{y} missing from OLYMPIC_YEARS"

    def test_first_last_constants(self):
        assert FIRST_OLYMPIC_YEAR == 1896
        assert LAST_OLYMPIC_YEAR == 2024


class TestCleanedDataYears:
    """Every cleaned table's Year values must be a subset of OLYMPIC_YEARS."""

    @pytest.mark.parametrize("label,path,exclude_col,exclude_val", [
        ("athletes_clean",    ATHLETES_CLEAN,    None, None),
        ("medal_counts_clean", MEDAL_COUNTS_CLEAN, None, None),
        ("programs_clean",    PROGRAMS_CLEAN,    None, None),
        # hosts_clean includes cancelled (1916/1940/1944) and future (2028/2032)
        # — only check years that actually took place
        ("hosts_clean",       HOSTS_CLEAN,       "is_cancelled", 0),
    ])
    def test_years_in_oly_years(self, label, path, exclude_col, exclude_val):
        df = pd.read_csv(path)
        if exclude_col is not None:
            df = df[df[exclude_col] == exclude_val]
            # Also exclude future years from hosts check
            if "is_future" in df.columns:
                df = df[df["is_future"] == 0]
        years = set(df["Year"].unique())
        bad = years - set(OLYMPIC_YEARS)
        assert bad == set(), \
            f"{label}: years {bad} are not in OLYMPIC_YEARS"
