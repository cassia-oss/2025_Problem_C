"""
discipline_resolver.py — shared discipline resolution logic

Used by build_discipline_map.py (Phase 1) and discipline_index.py (Phase 2)
to map an athlete's (Sport, Event) pair to an IOC discipline (Discipline, Code).

Centralising this logic ensures the two modules stay in sync.
"""

import re

import pandas as pd

# ── Sport name normalisation: athletes_clean.Sport → programs_clean.Sport ──
SPORT_NAME_NORMALIZE = {
    "Equestrianism": "Equestrian",
    "Hockey": "Field hockey",
    "Synchronized Swimming": "Aquatics",
    "Artistic Swimming": "Aquatics",
    "Water Polo": "Aquatics",
    "Swimming": "Aquatics",
    "Diving": "Aquatics",
    "Marathon Swimming": "Aquatics",
    "Beach Volleyball": "Volleyball",
    "Canoe Slalom": "Canoeing",
    "Canoe Sprint": "Canoeing",
    "Cycling Road": "Cycling",
    "Cycling Track": "Cycling",
    "Cycling Mountain Bike": "Cycling",
    "Cycling BMX Freestyle": "Cycling",
    "Cycling BMX Racing": "Cycling",
    "Artistic Gymnastics": "Gymnastics",
    "Rhythmic Gymnastics": "Gymnastics",
    "Trampoline Gymnastics": "Gymnastics",
    "Trampolining": "Gymnastics",
    "Rugby Sevens": "Rugby",
    "Baseball": "Baseball and Softball",
    "Softball": "Baseball and Softball",
    "Baseball/Softball": "Baseball and Softball",
    "3x3 Basketball": "Basketball",
    # Excluded (no discipline mapping)
    "Art Competitions": None,
    "Aeronautics": None,
    "Alpinism": None,
    "Motorboating": None,
    "Figure Skating": None,
    "Ice Hockey": None,
    # Name mismatches
    "Tug-Of-War": "Tug of War",
    "Racquets": "Rackets",
    "Jeu De Paume": "Jeu de Paume",
}

# ── Direct maps for sub-sports already split out in athletes_clean ──
AQUATICS_DIRECT_MAP = {
    "Swimming": ("Swimming", "SWM"),
    "Diving": ("Diving", "DIV"),
    "Water Polo": ("Water Polo", "WPO"),
    "Synchronized Swimming": ("Artistic Swimming", "SWA"),
    "Artistic Swimming": ("Artistic Swimming", "SWA"),
    "Marathon Swimming": ("Marathon Swimming", "OWS"),
}

CYCLING_DIRECT_MAP = {
    "Cycling Road": ("Road", "CRD"),
    "Cycling Track": ("Track", "CTR"),
    "Cycling Mountain Bike": ("Mountain Bike", "MTB"),
    "Cycling BMX Freestyle": ("BMX Freestyle", "BMF"),
    "Cycling BMX Racing": ("BMX Racing", "BMX"),
}

GYMNASTICS_DIRECT_MAP = {
    "Artistic Gymnastics": ("Artistic", "GAR"),
    "Rhythmic Gymnastics": ("Rhythmic", "GRY"),
    "Trampoline Gymnastics": ("Trampoline", "GTR"),
    "Trampolining": ("Trampoline", "GTR"),
}

CANOE_DIRECT_MAP = {
    "Canoe Slalom": ("Slalom", "CSL"),
    "Canoe Sprint": ("Sprint", "CSP"),
}

RUGBY_DIRECT_MAP = {
    "Rugby Sevens": ("Sevens", "RU7"),
}

VOLLEYBALL_DIRECT_MAP = {
    "Beach Volleyball": ("Beach", "VBV"),
}

BASKETBALL_DIRECT_MAP = {
    "3x3 Basketball": ("3x3", "BK3"),
}

BASEBALL_SOFTBALL_DIRECT_MAP = {
    "Baseball": ("Baseball", "BSB"),
    "Softball": ("Softball", "SBL"),
}

# All direct maps keyed by Sport name
_DIRECT_MAPS = [
    AQUATICS_DIRECT_MAP,
    CYCLING_DIRECT_MAP,
    GYMNASTICS_DIRECT_MAP,
    CANOE_DIRECT_MAP,
    RUGBY_DIRECT_MAP,
    VOLLEYBALL_DIRECT_MAP,
    BASKETBALL_DIRECT_MAP,
    BASEBALL_SOFTBALL_DIRECT_MAP,
]


# ── Keyword rules for multi-discipline sports ──
# Ordered by priority — first match wins.
DISCIPLINE_KEYWORD_RULES = {
    "Aquatics": [
        ("Water Polo", "Water Polo", "WPO"),
        ("Synchronized", "Artistic Swimming", "SWA"),
        ("Marathon", "Marathon Swimming", "OWS"),
        ("Diving", "Diving", "DIV"),
    ],
    "Wrestling": [
        ("Greco-Roman", "Greco-Roman", "WRG"),
        ("Freestyle", "Freestyle", "WRF"),
    ],
    "Canoeing": [
        ("Slalom", "Slalom", "CSL"),
    ],
    "Cycling": [
        ("Road Race", "Road", "CRD"),
        ("Individual Time Trial", "Road", "CRD"),
        ("Team Time Trial", "Road", "CRD"),
        ("Mountainbike", "Mountain Bike", "MTB"),
        ("Mountain Bike", "Mountain Bike", "MTB"),
        ("Cross-Country", "Mountain Bike", "MTB"),
        ("BMX Freestyle", "BMX Freestyle", "BMF"),
        ("BMX Racing", "BMX Racing", "BMX"),
        ("BMX", "BMX Racing", "BMX"),
        ("Keirin", "Track", "CTR"),
        ("Madison", "Track", "CTR"),
        ("Omnium", "Track", "CTR"),
        ("Points Race", "Track", "CTR"),
        ("Pursuit", "Track", "CTR"),
        ("Team Sprint", "Track", "CTR"),
        ("Sprint", "Track", "CTR"),
        ("Time Trial", "Track", "CTR"),
        ("Tandem", "Track", "CTR"),
        ("1 mile", "Track", "CTR"),
        ("1/2 mile", "Track", "CTR"),
        ("1/3 mile", "Track", "CTR"),
        ("1/4 mile", "Track", "CTR"),
        ("10,000 metres", "Track", "CTR"),
        ("12-Hours Race", "Track", "CTR"),
        ("2 mile", "Track", "CTR"),
        ("20 kilometres", "Track", "CTR"),
        ("25 kilometres", "Track", "CTR"),
        ("25 mile", "Track", "CTR"),
        ("5 mile", "Track", "CTR"),
        ("5,000 metres", "Track", "CTR"),
        ("50 kilometres", "Track", "CTR"),
        ("Road", "Road", "CRD"),
    ],
    "Equestrian": [
        ("Dressage", "Dressage", "EDR"),
        ("Jumping", "Jumping", "EJP"),
        ("Three-Day", "Eventing", "EVE"),
        ("Eventing", "Eventing", "EVE"),
        ("Driving", "Driving", "EDV"),
        ("Vaulting", "Vaulting", "EVL"),
    ],
    "Gymnastics": [
        ("Rhythmic", "Rhythmic", "GRY"),
        ("Trampoline", "Trampoline", "GTR"),
    ],
    "Volleyball": [
        ("Beach", "Beach", "VBV"),
    ],
    "Basketball": [
        ("3x3", "3x3", "BK3"),
    ],
    "Rowing": [
        ("Coastal", "Coastal", "ROC"),
    ],
    "Rugby": [
        ("Sevens", "Sevens", "RU7"),
    ],
    "Lacrosse": [
        ("Sixes", "Sixes", "LAX"),
    ],
    "Baseball and Softball": [
        ("Softball", "Softball", "SBL"),
        ("Baseball", "Baseball", "BSB"),
    ],
}

# ── Default discipline when no keyword matches ──
MULTI_DISC_DEFAULTS = {
    "Aquatics": ("Swimming", "SWM"),
    "Wrestling": ("Freestyle", "WRF"),
    "Canoeing": ("Sprint", "CSP"),
    "Cycling": ("Track", "CTR"),
    "Equestrian": ("Jumping", "EJP"),
    "Gymnastics": ("Artistic", "GAR"),
    "Volleyball": ("Indoor", "VVO"),
    "Basketball": ("Basketball", "BKB"),
    "Rowing": ("Rowing", "ROW"),
    "Rugby": ("Union", "RUG"),
    "Handball": ("Indoor", "HBL"),
    "Lacrosse": ("Field", "LAX"),
}

EXCLUDED_SPORTS = {
    "Art Competitions", "Aeronautics", "Alpinism", "Motorboating",
    "Figure Skating", "Ice Hockey",
}


# ── Public API ──

def make_athlete_keyword(event: str) -> str:
    """Normalize Event text into a stable mapping key."""
    text = "" if pd.isna(event) else str(event)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def get_single_disc_sports(programs_df: pd.DataFrame) -> dict:
    """Return {Sport: (Discipline, Code)} for sports with exactly one discipline."""
    disc_per_sport = (
        programs_df[['Sport', 'Discipline', 'Code']]
        .drop_duplicates()
        .groupby('Sport')[['Discipline', 'Code']]
        .apply(lambda g: list(zip(g['Discipline'], g['Code'])),
               include_groups=False)
        .to_dict()
    )
    return {s: items[0] for s, items in disc_per_sport.items()
            if len(items) == 1}


def resolve_discipline(athlete_sport: str, event: str,
                       single_disc_sports: dict) -> tuple:
    """Backward-compatible wrapper around resolve_discipline_with_method."""
    discipline, code, _ = resolve_discipline_with_method(
        athlete_sport, event, single_disc_sports
    )
    return (discipline, code)


def resolve_discipline_with_method(athlete_sport: str, event: str,
                                   single_disc_sports: dict) -> tuple:
    """Map an athlete (Sport, Event) pair to (Discipline, Code).

    Returns ('', '') if the sport is excluded or cannot be resolved.
    """
    sport = str(athlete_sport).strip()
    evt = str(event).strip()

    # 1. Normalise sport name
    norm_sport = SPORT_NAME_NORMALIZE.get(sport, sport)
    if norm_sport is None:
        return ('', '', 'excluded')

    # 2. Handle combined values (e.g. "Cycling Road, Cycling Track")
    lookup_sport = sport
    if ', ' in sport:
        lookup_sport = sport.split(', ')[0].strip()

    # Re-normalise after splitting
    norm_lookup = SPORT_NAME_NORMALIZE.get(lookup_sport, lookup_sport)
    if norm_lookup is None:
        return ('', '', 'excluded')

    # 3. Check sub-sport direct maps
    for direct_map in _DIRECT_MAPS:
        if lookup_sport in direct_map:
            discipline, code = direct_map[lookup_sport]
            return (discipline, code, 'sub_sport')

    # 4. Single-discipline sports (one-to-one mapping)
    if norm_lookup in single_disc_sports:
        discipline, code = single_disc_sports[norm_lookup]
        return (discipline, code, 'single_disc')

    # 5. Keyword rules against Event string
    rules = DISCIPLINE_KEYWORD_RULES.get(norm_lookup, [])
    for keyword, discipline, code in rules:
        if keyword.lower() in evt.lower():
            return (discipline, code, 'keyword')

    # 6. Default for multi-discipline sports
    if norm_lookup in MULTI_DISC_DEFAULTS:
        discipline, code = MULTI_DISC_DEFAULTS[norm_lookup]
        return (discipline, code, 'default')

    return ('', '', 'unmapped')


# ── Spot-check (run directly) ──
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.config import PROGRAMS_CLEAN
    from src.utils.io_utils import read_csv

    prog = read_csv(PROGRAMS_CLEAN)
    single = get_single_disc_sports(prog)
    print(f"Single-discipline sports: {len(single)}")

    cases = [
        # Multi-discipline: keyword match
        ("Wrestling", "Men's Freestyle 57kg", "Freestyle", "WRF"),
        ("Wrestling", "Men's Greco-Roman 130kg", "Greco-Roman", "WRG"),
        ("Cycling", "Road race, Individual", "Road", "CRD"),
        ("Cycling", "Mountain Bike, Cross-Country", "Mountain Bike", "MTB"),
        ("Cycling", "BMX Racing, Individual", "BMX Racing", "BMX"),
        ("Canoeing", "Slalom C-1", "Slalom", "CSL"),
        ("Canoeing", "Sprint K-1 1000m", "Sprint", "CSP"),
        # Multi-discipline: via sub-sport direct map
        ("Cycling Road", "Road race, Individual", "Road", "CRD"),
        ("Cycling Track", "Sprint, Individual", "Track", "CTR"),
        ("Cycling Mountain Bike", "Cross-Country", "Mountain Bike", "MTB"),
        ("Canoe Slalom", "Slalom C-1", "Slalom", "CSL"),
        ("Canoe Sprint", "Sprint K-1 1000m", "Sprint", "CSP"),
        # Multi-discipline: Equestrianism → Equestrian normalisation
        ("Equestrianism", "Dressage, Individual", "Dressage", "EDR"),
        ("Equestrianism", "Jumping, Individual", "Jumping", "EJP"),
        ("Equestrianism", "Three-Day Event, Individual", "Eventing", "EVE"),
        ("Equestrianism", "Vaulting, Individual", "Vaulting", "EVL"),
        # Single-discipline: direct match
        ("Judo", "Men's Heavyweight", "Judo", "JUD"),
        ("Athletics", "Men's 100m", "Athletics", "ATH"),
        ("Boxing", "Men's Lightweight", "Boxing", "BOX"),
    ]

    all_ok = True
    for sport, event, exp_disc, exp_code in cases:
        disc, code = resolve_discipline(sport, event, single)
        ok = (disc == exp_disc and code == exp_code)
        if not ok:
            print(f"  FAIL: ({sport!r}, {event!r}) → ({disc!r}, {code!r})  "
                  f"expected ({exp_disc!r}, {exp_code!r})")
            all_ok = False
        else:
            print(f"  OK:   ({sport!r}, {event!r}) → ({disc}, {code})")

    print(f"\n{'All passed!' if all_ok else 'SOME FAILED!'}")
