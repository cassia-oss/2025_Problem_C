"""Unit tests for parse_event_count in clean_programs.py."""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.preprocess.clean_programs import parse_event_count


@pytest.mark.parametrize("raw, expected", [
    # Demo sports (bullet corrupted to ? during encoding)
    ("?0",    (0, 1, "demo")),         # 0 events, demo
    ("??0",   (0, 1, "demo")),         # 0 events, demo (variant)
    ("?4",    (4, 1, "demo")),         # 4 events, demo — NUMBER MUST BE PRESERVED
    ("??1",   (1, 1, "demo")),         # 1 event, demo — NUMBER MUST BE PRESERVED
    # Cancelled due to weather (S3 footnote)
    ("0[s3]", (0, 0, "cancelled_weather")),
    # Moved to Winter Olympics (S5 footnote)
    ("Included in winter games (see data_dictionary.csv)[s5]",
     (0, 0, "winter_transfer")),
    # Plain numeric: official events
    ("0",     (0, 0, "official")),
    ("1",     (1, 0, "official")),
    ("12",    (12, 0, "official")),
    ("48",    (48, 0, "official")),
    # NaN / None
    (np.nan,  (0, 0, "official")),
    (None,    (0, 0, "official")),
])
def test_parse_event_count(raw, expected):
    result = parse_event_count(raw)
    assert result == expected, \
        f"parse_event_count({repr(raw)}) = {result}, expected {expected}"
