"""Project-wide paths and constants.

All paths are defined relative to ROOT (the project root directory).
Import from any script to get consistent path resolution.
Never hardcode paths in downstream scripts — always reference this module.
"""

from pathlib import Path

# ---- Core paths ----
ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'
NOTEBOOKS_DIR = ROOT / 'notebooks'
TESTS_DIR = ROOT / 'tests'
ESSAY_DIR = ROOT / 'essay'

# ---- Raw data files (read-only) ----
ATHLETES_FILE = DATA_DIR / 'summerOly_athletes.csv'
MEDAL_COUNTS_FILE = DATA_DIR / 'summerOly_medal_counts.csv'
PROGRAMS_FILE = DATA_DIR / 'summerOly_programs.csv'
HOSTS_FILE = DATA_DIR / 'summerOly_hosts.csv'
DATA_DICT_FILE = DATA_DIR / 'data_dictionary.csv'

# ---- Phase 1 output: cleaned data ----
CLEANED_DIR = OUTPUT_DIR / 'cleaned'
ATHLETES_CLEAN = CLEANED_DIR / 'athletes_clean.csv'
MEDAL_COUNTS_CLEAN = CLEANED_DIR / 'medal_counts_clean.csv'
PROGRAMS_CLEAN = CLEANED_DIR / 'programs_clean.csv'
HOSTS_CLEAN = CLEANED_DIR / 'hosts_clean.csv'
NOC_MAPPING = CLEANED_DIR / 'noc_mapping.csv'
NOC_DECISIONS_MANUAL = CLEANED_DIR / 'noc_decisions_manual.csv'
UNKNOWN_NOC = CLEANED_DIR / 'unknown_noc.csv'
MEDAL_MISMATCH = CLEANED_DIR / 'medal_mismatch.csv'

# ---- Phase 2 output: features ----
FEATURES_DIR = OUTPUT_DIR / 'features'
FEATURE_MATRIX = FEATURES_DIR / 'feature_matrix.csv'
DISCIPLINE_INDEX = FEATURES_DIR / 'discipline_index.csv'

# ---- Phase 3/4 output: models & predictions ----
MODELS_DIR = OUTPUT_DIR / 'models'
PREDICTIONS_DIR = OUTPUT_DIR / 'predictions'

# ---- Constants ----
CANCELLED_YEARS = {1916, 1940, 1944}
VALID_MEDALS = {'Gold', 'Silver', 'Bronze', 'No medal'}
FIRST_OLYMPIC_YEAR = 1896
LAST_OLYMPIC_YEAR = 2024

# All valid Summer Olympic years (1896–2024, every 4 years, excluding cancelled)
OLYMPIC_YEARS = sorted(
    {y for y in range(FIRST_OLYMPIC_YEAR, LAST_OLYMPIC_YEAR + 1, 4)
     if y not in CANCELLED_YEARS}
)

# Medal weights for Discipline Advantage Index (Section 2.2 of PIPELINE.md)
MEDAL_WEIGHTS = {'Gold': 1.0, 'Silver': 0.6, 'Bronze': 0.4}

# Columns used for deduplication in athlete records
ATHLETE_DEDUP_COLS = ['Name', 'NOC', 'Year', 'Event']

# Columns in the cleaned athlete output
ATHLETE_OUTPUT_COLS = [
    'Name', 'Sex', 'Team', 'NOC', 'Year', 'City',
    'Sport', 'Event', 'Medal', 'is_multi_team'
]


def ensure_dirs() -> None:
    """Create all output directories if they don't already exist."""
    dirs = [
        CLEANED_DIR, FEATURES_DIR, MODELS_DIR, PREDICTIONS_DIR,
        NOTEBOOKS_DIR, TESTS_DIR, ESSAY_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    ensure_dirs()
    print(f'Project root : {ROOT}')
    print(f'Data dir     : {DATA_DIR}')
    print(f'Olympic years: {len(OLYMPIC_YEARS)} Games ({OLYMPIC_YEARS[0]}–{OLYMPIC_YEARS[-1]})')
    print('All directories ready.')
