"""Unit tests for src/features/discipline_index.py."""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.features.discipline_index import attach_discipline_map, compute_medal_counts
from src.utils.discipline_resolver import make_athlete_keyword


def test_attach_discipline_map_joins_on_sport_and_keyword():
    athletes = pd.DataFrame([
        {'Sport': 'Baseball/Softball', 'Event': 'Softball Team', 'NOC': 'USA', 'Year': 2020, 'Medal': 'Silver'},
        {'Sport': 'Baseball/Softball', 'Event': 'Baseball Team', 'NOC': 'JPN', 'Year': 2020, 'Medal': 'Gold'},
    ])
    disc_map = pd.DataFrame([
        {
            'athlete_Sport': 'Baseball/Softball',
            'athlete_keyword': make_athlete_keyword('Softball Team'),
            'programs_Discipline': 'Softball',
            'Code': 'SBL',
            'match_method': 'keyword',
        },
        {
            'athlete_Sport': 'Baseball/Softball',
            'athlete_keyword': make_athlete_keyword('Baseball Team'),
            'programs_Discipline': 'Baseball',
            'Code': 'BSB',
            'match_method': 'keyword',
        },
    ])

    merged = attach_discipline_map(athletes, disc_map)
    got = merged[['Event', 'Discipline', 'Code']].sort_values('Event')
    expect = pd.DataFrame([
        {'Event': 'Baseball Team', 'Discipline': 'Baseball', 'Code': 'BSB'},
        {'Event': 'Softball Team', 'Discipline': 'Softball', 'Code': 'SBL'},
    ])
    pd.testing.assert_frame_equal(got.reset_index(drop=True), expect)


def test_compute_medal_counts_keeps_zero_medal_participants():
    athletes = pd.DataFrame([
        {'NOC': 'ISR', 'Year': 2020, 'Event': 'Baseball Team', 'Medal': 'No medal', 'Code': 'BSB', 'Discipline': 'Baseball'},
        {'NOC': 'ISR', 'Year': 2020, 'Event': 'Baseball Team', 'Medal': 'No medal', 'Code': 'BSB', 'Discipline': 'Baseball'},
        {'NOC': 'USA', 'Year': 2020, 'Event': 'Baseball Team', 'Medal': 'Silver', 'Code': 'BSB', 'Discipline': 'Baseball'},
        {'NOC': 'USA', 'Year': 2020, 'Event': 'Baseball Team', 'Medal': 'Silver', 'Code': 'BSB', 'Discipline': 'Baseball'},
    ])
    canon_lookup = {('ISR', 2020): 'Israel', ('USA', 2020): 'United States'}

    result = compute_medal_counts(athletes, canon_lookup)
    result = result.sort_values('canonical_name').reset_index(drop=True)

    israel = result[result['canonical_name'] == 'Israel'].iloc[0]
    usa = result[result['canonical_name'] == 'United States'].iloc[0]

    assert israel['Code'] == 'BSB'
    assert israel['Total'] == 0
    assert israel['Gold'] == 0
    assert israel['Silver'] == 0
    assert israel['Bronze'] == 0

    assert usa['Silver'] == 1
    assert usa['Total'] == 1
