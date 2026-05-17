"""Unit tests for discipline mapping helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.discipline_resolver import (
    make_athlete_keyword,
    resolve_discipline_with_method,
)


def test_make_athlete_keyword_normalizes_whitespace_and_case():
    assert make_athlete_keyword("  Baseball   Team  ") == "baseball team"


def test_baseball_softball_is_split_by_event_keyword():
    single = {}

    disc, code, method = resolve_discipline_with_method(
        "Baseball/Softball", "Softball Team", single
    )
    assert (disc, code, method) == ("Softball", "SBL", "keyword")

    disc, code, method = resolve_discipline_with_method(
        "Baseball/Softball", "Baseball Team", single
    )
    assert (disc, code, method) == ("Baseball", "BSB", "keyword")


def test_cycling_track_events_no_longer_fall_back_to_road():
    single = {}
    disc, code, method = resolve_discipline_with_method(
        "Cycling", "Cycling Men's Keirin", single
    )
    assert (disc, code, method) == ("Track", "CTR", "keyword")

    disc, code, method = resolve_discipline_with_method(
        "Cycling", "Cycling Women's Individual Time Trial", single
    )
    assert (disc, code, method) == ("Road", "CRD", "keyword")
