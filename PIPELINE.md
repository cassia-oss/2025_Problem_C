# PIPELINE: 2025 MCM Problem C — Olympic Medal Table Improvement Plan

> **Purpose**: This document defines the step-by-step pipeline for reworking the 2025 MCM Problem C project. It is written to be mutually intelligible to both human collaborators and AI agents (e.g., Codex). Each section defines **what** to do, **why** it matters, and **how** to verify correctness.
>
> **Status**: Phase 0 (Planning) — to be executed incrementally.
> **Start date**: 2026-05-07

---

## 0. Project File Structure (Target)

```
2025_Problem_C/
├── PIPELINE.md                  # <-- this document (instruction set)
├── README.md                    # brief project description
├── data/                        # raw data (READ-ONLY, never modify)
│   ├── summerOly_athletes.csv
│   ├── summerOly_medal_counts.csv
│   ├── summerOly_hosts.csv
│   ├── summerOly_programs.csv
│   └── data_dictionary.csv
├── output/                      # generated artifacts (tables, figures, predictions)
│   ├── cleaned/
│   ├── features/
│   ├── models/
│   └── predictions/
├── src/                         # all source code
│   ├── preprocess/              # Phase 1: data cleaning + standardization
│   │   ├── clean_athletes.py
│   │   ├── clean_medal_counts.py
│   │   ├── clean_programs.py
│   │   ├── clean_hosts.py
│   │   └── unify_noc.py         # NOC name standardization table
│   ├── features/                # Phase 2: feature engineering
│   │   ├── build_features.py    # main feature construction
│   │   └── discipline_index.py  # discipline advantage level index
│   ├── models/                  # Phase 3: modeling
│   │   ├── classifier.py        # binary: will country win medals?
│   │   ├── regressor.py         # regression: how many?
│   │   └── coach_effect.py      # RDiT / great coach analysis
│   ├── evaluate/                # Phase 4: evaluation + visualization
│   │   ├── metrics.py
│   │   └── plots.py
│   └── utils/                   # shared utilities
│       ├── config.py            # paths, constants, global settings
│       └── io_utils.py          # safe file read/write
├── notebooks/                   # exploratory analysis (optional)
│   └── 00_eda.ipynb
├── tests/                       # unit tests for src/ modules
│   ├── test_preprocess.py
│   └── test_features.py
└── essay/                       # final paper (LaTeX or markdown)
    └── main.tex
```

**Key rules:**
- `data/` is immutable — scripts read from it, never write to it.
- All intermediate outputs go to `output/`.
- Every `src/` module is independently runnable and testable.
- Use `src/utils/config.py` for all path definitions; never hardcode paths in scripts.

---

## 1. Phase 1: Data Preprocessing

### 1.0 Critical Findings from Previous Work (Do NOT repeat these mistakes)

| Issue | Old approach | Improved approach |
|-------|-------------|-------------------|
| Post-1992 cutoff | Hand-waved justification ("world order stabilized") | Keep all data; use a `year` feature or a geopolitical-era categorical variable. Full data = more samples for rare countries. |
| Country name inconsistency | Manual ad-hoc fixes in the essay | Build a **NOC unification table** programmatically; validate with `summerOly_medal_counts.csv` NOC values as ground truth |
| "Garbled code" handling | Manual replacement by looking at NOC | Automate: detect non-UTF-8/non-ASCII team names → replace by NOC-mapped canonical name |
| Duplicate removal | Mentioned but not systematic | Define dedup criteria explicitly (same Name + NOC + Year + Event = duplicate) |
| Historical regions (e.g., "United States Virgin Islands") | Manual judgment | Separate NOC code IS a separate entity (IOC rules). Do NOT merge into mainland. Respect IOC NOC designations. |
| Team suffix (e.g., "United States-1") | Ignored/merged | Preserve as a feature flag: `is_multi_team` (BOOL). Multiple teams from one country = more medal chances. |

### 1.1 Athletes Data Cleaning (`src/preprocess/clean_athletes.py`)

**Input**: `data/summerOly_athletes.csv` (252,565 rows, 9 columns)
**Output**: `output/cleaned/athletes_clean.csv`

Steps (execute in order):

```
STEP 1.1.1 — Drop exact duplicates
  Criteria: (Name, NOC, Year, Event) identical → keep first occurrence.
  Rationale: same athlete, same country, same year, same event appearing twice is a recording error.

STEP 1.1.2 — Normalize Team names & flag multi-team entries
  - Detect dash-suffix pattern (e.g. "United States-1", "Germany-2"):
    Extract base_country = Team without suffix
    Set is_multi_team = 1
    Keep Team as-is for traceability
  - Strip whitespace from Team names
  - Flag rows with encoding artifacts (U+FFFD) for review

  DESIGN DECISION (D09): Team names are NOT replaced with canonical_name.
  The NOC 3-letter code (always present, always valid) serves as the
  canonical identifier. All downstream joins MUST use NOC, never Team.
  The NOC mapping table (noc_mapping_v2.csv) bridges NOC ↔ canonical_name
  for display purposes. This avoids alias noise, multi-language names,
  and historical spelling variations inherent in the Team column.

STEP 1.1.3 — Normalize Medal values
  Map: "Gold" → "Gold", "Silver" → "Silver", "Bronze" → "Bronze"
  Map: "No medal" / "No Medal" / "" / NaN → "No medal"
  All values must be one of: {"Gold", "Silver", "Bronze", "No medal"}

STEP 1.1.4 — Validate NOC codes
  Every NOC must appear in the reference list built from summerOly_medal_counts.csv.
  Flag unknown NOCs → write to output/cleaned/unknown_noc.csv for manual review.

STEP 1.1.5 — Validate Year range
  Year must be a valid Summer Olympics year in OLYMPIC_YEARS
  (1896–2024, every 4 years, excluding cancelled years and 1906).
  Non-standard years (e.g., 1906 Intercalated Games) are dropped.

STEP 1.1.6 — Write cleaned output
  Columns: Name, Sex, Team, NOC, Year, City, Sport, Event, Medal, is_multi_team
```

### 1.2 Medal Counts Construction (`src/preprocess/clean_medal_counts.py`)

**Rationale**: The IOC official `summerOly_medal_counts.csv` reflects post-hoc
adjustments (doping disqualifications, political reallocations) that do not
represent on-field competitive trends. We derive medal counts directly from
`athletes_clean.csv` — counting one medal per (NOC, Year, Event, Medal) after
team-event deduplication. This treats the athletes table as the primary source
of truth for "who actually won on the field of play."

The official medal_counts is retained as a comparison reference. Differences
are documented in `output/cleaned/medal_counts_compare.csv`.

**Input**: `output/cleaned/athletes_clean.csv`, `output/cleaned/noc_mapping_v2.csv`
**Output**: `output/cleaned/medal_counts_clean.csv`
**Comparison**: `output/cleaned/medal_counts_compare.csv` (vs `data/summerOly_medal_counts.csv`)

```
STEP 1.2.1 — Build (athlete_NOC, Year) → canonical_name lookup
  From noc_mapping_v2.csv. canonical_name is always populated and serves
  as the project-wide unified country identifier.

STEP 1.2.2 — Team-event deduplication
  Dedup on (NOC, Year, Event, Medal). Team events with N crew members
  count as 1 medal, not N.

STEP 1.2.3 — Count medals per (athlete_NOC, Year, Medal)
  Group by (athlete_NOC, Year, Medal) after removing 'No medal' rows.
  Use .unstack() then reference columns by NAME (Gold/Silver/Bronze),
  never by position — unstack sorts alphabetically.

STEP 1.2.4 — Map athlete_NOC → canonical_name
  Replace 3-letter IOC codes with unified canonical_name from the
  mapping table. This handles historical name changes (e.g. RUS →
  Russian Empire → Soviet Union → ROC depending on Year).

STEP 1.2.5 — Build full participation panel
  Include ALL (NOC, Year) pairs from athletes_clean, even those with
  zero medals. Non-medalists get Gold=Silver=Bronze=Total=0.
  This ensures the table is a complete panel for downstream modeling.

STEP 1.2.6 — Validate
  - NOC must not be null or empty
  - (NOC, Year) must be unique (no duplicate primary keys)
  - Gold + Silver + Bronze == Total for every row
  - All validation failures raise AssertionError (block output)

STEP 1.2.7 — Compare with official medal_counts (audit_medal_compare.py)
  Map official NOC names to canonical_name via noc_mapping_v2,
  join on (canonical_name, Year), and classify each row:
    MATCH — all G/S/B identical
    DIFFER — same (NOC, Year) in both sources, counts differ
    ONLY_IN_ATHLETES — athletes has medals, official has no row
    ONLY_IN_OFFICIAL — official has row, athletes has none
  Output: output/cleaned/medal_counts_compare.csv
```

### 1.3 Programs Data Cleaning (`src/preprocess/clean_programs.py`)

**Input**: `data/summerOly_programs.csv`
**Output**: `output/cleaned/programs_clean.csv` (long format)

```
STEP 1.3.1 — Melt from wide to long format
  Current: columns 1896, 1900, 1904, ... (wide format)
  Target:  Sport | Discipline | Code | Year | EventCount

STEP 1.3.2 — Handle special cell values (per data_dictionary.csv)
  The bullet (•) character was corrupted to '?' during encoding.
  Six special-value types are recognised:

  | Raw value                        | EventCount | is_demo | status_code      |
  |----------------------------------|------------|---------|------------------|
  | ?0, ??0                          | 0          | 1       | demo             |
  | ?4, ??1                          | N (parsed) | 1       | demo             |
  | 0[s3]                            | 0          | 0       | cancelled_weather|
  | Included in winter games...[s5]  | 0          | 0       | winter_transfer  |
  | Plain numeric                    | N          | 0       | official         |

  status_code preserves the WHY behind zero/non-standard values
  for downstream filtering and audit.

STEP 1.3.3 — Drop cancelled years
  Drop rows with Year in {1916, 1940, 1944} (no Games held)

STEP 1.3.4 — Clean special characters in Sport/Discipline names
  Replace encoding artifacts (U+FFFD) and standardize whitespace.
```

### 1.4 Hosts Data Cleaning (`src/preprocess/clean_hosts.py`)

**Input**: `data/summerOly_hosts.csv`
**Output**: `output/cleaned/hosts_clean.csv`

```
STEP 1.4.1 — Extract host_country from Host field
  "Athens, Greece" → City="Athens", Country="Greece", NOC=<mapped code>
  Add NOC column for join compatibility.

STEP 1.4.2 — Flag cancelled years
  Add column is_cancelled (BOOL) for 1916, 1940, 1944.
  For cancelled years, set NOC and canonical_name to 'CANCELLED'
  (sentinel value to prevent NaN in downstream joins).

STEP 1.4.3 — For future years (2028, 2032)
  Add column is_future (BOOL)
```

### 1.5 NOC Unification Table (`src/preprocess/unify_noc.py`)

**This is the single source of truth for country names.**

**Input**: All four datasets
**Output**: `output/cleaned/noc_mapping.csv`

Columns: `NOC | canonical_name | alt_names (pipe-separated) | region | first_year | last_year`

Construction:
```
STEP 1.5.1 — Collect all unique (NOC, Team) pairs from athletes
STEP 1.5.2 — Collect all unique NOC from medal_counts
STEP 1.5.3 — Cross-reference: for each NOC in athletes, find its canonical name
              from medal_counts (medal_counts names are IOC-official)
STEP 1.5.4 — List all alternative Team spellings per NOC
STEP 1.5.5 — Manual review file for ambiguous cases (e.g., historical country splits)
              Write decisions to output/cleaned/noc_decisions_manual.csv
```

**Verification checkpoint**: After this phase, every NOC used anywhere in the project maps to exactly one `canonical_name`. All downstream code uses NOC, not Team name strings.

### 1.6 Cleaned Table Relationships

After Phase 1, five cleaned tables exist. The NOC mapping table (`noc_mapping_v2`) is the central bridge — all cross-table joins go through it.

```
athletes_clean (250,990 rows)              noc_mapping_v2 (4,564 rows)          medal_counts_clean (3,222 rows)
┌──────────────────────────┐            ┌──────────────────────────────┐     ┌──────────────────────────┐
│ Team ────────────────────┼──┐         │ athlete_Team ◄── triple key  │     │ NOC (= canonical_name) ◄─┼── canonical_name
│ NOC ─────────────────────┼──┼───────► │ athlete_NOC  ◄── triple key  │     │ Year                     │
│ Year ────────────────────┼──┼───────► │ Year         ◄── triple key  │     │ Gold Silver Bronze Total │
│ City ─────┐              │  │         │ canonical_name ──────────────┼───► │ Rank                     │
│ Sport ──┐ │              │  │         │ NOC_in_medal_counts          │     └──────────────────────────┘
│ Event   │ │              │  │         │ match_in_medal               │
│ Medal   │ │              │  │         │ entity_type                  │
└─────────┼─┼──────────────┘  │         └──────────────────────────────┘
          │ │                 │
          │ │  ┌──────────────┘
          │ │  │  Triple key: (athlete_NOC, athlete_Team, Year) → canonical_name
          │ │  │  canonical_name is the project-wide unified country identifier.
          │ │  │
          │ │  │  Note: medal_counts_clean.NOC stores canonical_name (full country
          │ │  │  name like "United States"), NOT the 3-letter IOC code.
          │ │  │  athletes_clean.NOC stores the 3-letter IOC code (like "USA").
          │ │  │  The mapping bridges these two naming systems.
          │ │  │
programs_clean (2,201 rows)│ │  │
┌──────────────────────────┐│ │  │
│ Sport ◄──────────────────┼┘ │  │  Join: athletes.Sport = programs.Sport
│ Discipline                │  │  │        AND athletes.Year = programs.Year
│ Code                      │  │  │
│ Year ◄────────────────────┼──┘  │
│ EventCount                │     │
│ is_demo, status_code      │     │
└──────────────────────────┘     │
                                 │
hosts_clean (35 rows)            │
┌──────────────────────────┐     │
│ Year ◄───────────────────┼─────┘  Join: athletes.City = hosts.City
│ City ◄───────────────────┼───────────── AND athletes.Year = hosts.Year
│ Country                   │
│ NOC ◄────────────────────┼──► athletes.NOC (both 3-letter codes)
│ canonical_name ◄──────────┼──► medal_counts.NOC (both full names)
│ is_cancelled, is_future   │
└──────────────────────────┘
```

**Join summary:**

| From | To | Key(s) | Direction |
|------|-----|--------|-----------|
| athletes_clean | noc_mapping_v2 | (athletes.NOC, athletes.Team, athletes.Year) = (mapping.athlete_NOC, mapping.athlete_Team, mapping.Year) | triple key |
| noc_mapping_v2 | medal_counts_clean | mapping.canonical_name = medal_counts.NOC AND mapping.Year = medal_counts.Year | canonical_name + Year |
| athletes_clean | medal_counts_clean | **Two-step**: via noc_mapping_v2. Never join directly. | via bridge |
| athletes_clean | programs_clean | athletes.Sport = programs.Sport AND athletes.Year = programs.Year | Sport + Year |
| athletes_clean | hosts_clean | athletes.City = hosts.City AND athletes.Year = hosts.Year | City + Year |
| medal_counts_clean | hosts_clean | medal_counts.NOC = hosts.canonical_name AND medal_counts.Year = hosts.Year | canonical_name + Year |

**Why triple key for the mapping?** The same 3-letter NOC code can represent different political entities over time (e.g., RUS → Russian Empire → Soviet Union → ROC, depending on Year). The Team name provides additional disambiguation. Together with Year, the triple (NOC, Team, Year) uniquely determines the canonical country identity. Downstream code MUST go through `noc_mapping_v2` to resolve `canonical_name` — never join athletes directly to medal_counts.

### 1.7 Athlete-Discipline Mapping (`src/preprocess/build_discipline_map.py`)

**Rationale**: athletes_clean uses Sport names and Event strings that do not directly
match programs_clean's (Sport, Discipline, Code) hierarchy. Athlete records must be
mapped to the 68 IOC discipline codes for the Discipline Advantage Index (Section 2.2).

**Input**: `output/cleaned/athletes_clean.csv`, `output/cleaned/programs_clean.csv`
**Output**: `output/cleaned/athlete_discipline_map.csv`

Columns: `athlete_Sport | athlete_keyword | programs_Sport | programs_Discipline | Code | match_method`

```
STEP 1.7.1 — Extract unique (Sport, Event) pairs from athletes_clean
  This is the lookup key universe; every row in athletes_clean must map to a Code.

STEP 1.7.2 — Normalize Sport names between the two sources
  | athletes_clean.Sport       | programs_clean.Sport      |
  |----------------------------|---------------------------|
  | Equestrianism              | Equestrian                |
  | Hockey                     | Field hockey              |
  | Synchronized Swimming      | Artistic Swimming (SWA)   |
  | Baseball / Softball (split)| Baseball and Softball (combined) |
  | Canoe Sprint / Canoe Slalom| Canoeing (combined)       |
  | Cycling Road / Track / ... | Cycling (combined)        |

STEP 1.7.3 — Single-discipline sports: direct match
  If a Sport has only one Discipline in programs_clean → assign directly.
  (~33 sports: Judo→JUD, Boxing→BOX, Tennis→TEN, Archery→ARC, etc.)

STEP 1.7.4 — Multi-discipline sports: keyword extraction from Event string
  | Sport       | Keyword in Event           | Discipline       | Code |
  |-------------|---------------------------|------------------|------|
  | Wrestling   | "Freestyle"               | Freestyle        | WRF  |
  | Wrestling   | "Greco-Roman"             | Greco-Roman      | WRG  |
  | Canoeing    | "Slalom"                  | Slalom           | CSL  |
  | Canoeing    | (distance/race keyword)   | Sprint           | CSP  |
  | Cycling     | "Road"                    | Road             | CRD  |
  | Cycling     | "Track"                   | Track            | CTR  |
  | Cycling     | "Mountain"                | Mountain Bike    | MTB  |
  | Cycling     | "BMX Freestyle"           | BMX Freestyle    | BMF  |
  | Cycling     | "BMX" (not Freestyle)     | BMX Racing       | BMX  |
  | Equestrian  | "Dressage"                | Dressage         | EDR  |
  | Equestrian  | "Jumping"                 | Jumping          | EJP  |
  | Equestrian  | "Three-Day" / "Eventing"  | Eventing         | EVE  |
  | Gymnastics  | "Artistic" / plain event  | Artistic         | GAR  |
  | Gymnastics  | "Rhythmic"                | Rhythmic         | GRY  |
  | Gymnastics  | "Trampoline"              | Trampoline       | GTR  |
  | Aquatics    | Sport="Swimming"          | Swimming         | SWM  |
  | Aquatics    | Sport="Diving"            | Diving           | DIV  |
  | Aquatics    | Sport="Water Polo"        | Water Polo       | WPO  |
  | Aquatics    | Sport="Synchronized"      | Artistic Swimming| SWA  |
  | Volleyball  | "Beach"                   | Beach            | VBV  |
  | Volleyball  | no keyword                | Indoor           | VVO  |
  | Basketball  | "3x3"                     | 3x3              | BK3  |
  | Basketball  | no keyword                | Basketball       | BKB  |
  | Rowing      | "Coastal"                 | Coastal          | ROC  |
  | Rowing      | no keyword                | Rowing           | ROW  |
  | Rugby       | Sport="Rugby Sevens"      | Sevens           | RU7  |
  | Rugby       | Sport="Rugby Union"       | Union            | RUG  |
  | Handball    | (Year=1936)               | Field            | HBL  |
  | Handball    | (Year>1936)               | Indoor           | HBL  |
  | Lacrosse    | (historical only)         | Field            | LAX  |
  | Baseball/Softball | Sport name          | Baseball/Softball| BSB/SBL |

STEP 1.7.5 — Year-based inference fallback
  For rows still unmapped: query programs_clean for which disciplines in that
  (programs_Sport, Year) have EventCount > 0. If only one → assign. If multiple
  → flag for manual review.

STEP 1.7.6 — Manual review
  Rows with match_method="manual_review" exported to
  output/cleaned/discipline_map_review.csv for inspection.
```

**Verification**: Every unique (Sport, Event) pair in athletes_clean must have a
non-null Code in the mapping table. The match_method column documents how each
pair was resolved.

---

## 2. Phase 2: Feature Engineering

### 2.1 Core Feature Table (`src/features/build_features.py`)

**Input**: Cleaned data from `output/cleaned/`
**Output**: `output/features/feature_matrix.csv`

**Primary key**: `(canonical_name, Year)` (D14). canonical_name is the project-wide
unified country identifier from `noc_mapping_v2.csv`.

**Row existence rule** (D15): A row exists for an (entity, Year) pair ONLY if the
entity was capable of participating that year. The feature matrix is NOT a full
Cartesian product — dissolved countries have no rows after their final Olympiad.

| entity_type | Row coverage | Example |
|-------------|-------------|---------|
| `country` | first_year → 2024 (all Olympic Years, incl. boycott years) | Afghanistan: 1936–2024 |
| `historical_same` | same as `country` (entity merely renamed) | Chinese Taipei: 1956–2024 |
| `historical_different` | first_year → last_year (dissolved, no rows after) | East Germany: 1968–1988 |
| `special` | first_year → last_year | Refugee Olympic Team: 2016–2024 |

For `country` entities, boycott years (e.g., USA 1980, Afghanistan 1980) still have
rows: the entity existed and could have participated. B1–B4 = 0 (no athletes sent);
B5 computed from most recent actual participation (D19); Target = 0; lag features
skip the boycott year and use the most recent participation (D19).

#### Feature Groups:

**Group A — Lagged Medal Performance** (captures momentum, 3 Olympiad lags)

Source: `medal_counts_clean.csv` (NOC=canonical_name, Year). Lags reference prior
Olympic Years (via OLYMPIC_YEARS list), NOT simple Year-4 arithmetic.

**Non-participation carry-forward rule (D19)**: When the entity did NOT participate
in a given prior Olympiad (boycott, etc.), skip that Olympiad and use the NEXT most
recent one where they DID participate. A boycotting country retains its athletic
capability — USA's expected 1984 performance is better approximated by its 1976
results than by assuming 0 medals.

Example: USA in 1984 → lag1 skips 1980 (boycott) → uses 1976.
If no prior participation exists at all, lag = NaN.

```
A1: gold_lag1, silver_lag1, bronze_lag1, total_lag1   (most recent Olympiad with participation, skipping non-participation years)
A2: gold_lag2, silver_lag2, bronze_lag2, total_lag2   (2nd most recent Olympiad with participation)
A3: gold_lag3, silver_lag3, bronze_lag3, total_lag3   (3rd most recent Olympiad with participation)
A4: medal_won_binary_lag1                              (0/1, did country win any medal at the most recent participation?)
```
NaN only when the entity has no prior participation in its existence window.
0 = "participated (at that prior Olympiad) and won 0 medals."

**Group B — Athlete Delegation**

Source: `athletes_clean.csv` → map athlete_NOC to canonical_name via
`noc_mapping_v2.csv`. For `historical_different` entities: use only athletes
within the entity's existence window.
```
B1: n_athletes_total          (delegation size this year)
B2: n_athletes_male
B3: n_athletes_female
B4: n_unique_events            (how many distinct events the country enters)
B5: athlete_growth_rate        (relative to most recent prior participation:
                                (B1_current - B1_prev) / B1_prev.
                                NaN if B1_prev = 0 or no prior participation, D20)
```

**Group C — Host-Related**

Source: `hosts_clean.csv`, joined on `(hosts.canonical_name = feature.canonical_name, hosts.Year = feature.Year)`.
```
C1: is_host                   (1 if country hosts this year)
C2: is_host_next              (1 if hosting next Olympics — prep effect)
C3: is_host_prev              (1 if hosted previous Olympics — legacy effect)
C4: host_cycle_phase          (categorical: 0=none, 1=pre-host, 2=host, 3=post-host)
C5: years_since_last_host      (integer, -1 if never hosted)
```

**Group D — Event Structure**

Source: `programs_clean.csv`, aggregated per Year. Only rows with status_code='official'
(plain numeric) used for D1–D3.
```
D1: total_events_this_year     (sum of EventCount for official events)
D2: n_sports_this_year         (distinct Sport count)
D3: n_disciplines_this_year    (distinct Code count)
D4: n_new_events               (sum of positive EventCount deltas between this Olympiad
                                and the previous Olympiad, per (Sport, Discipline, Code), D21)
D5: n_discontinued_events      (sum of negative EventCount deltas between this Olympiad
                                and the previous Olympiad, per (Sport, Discipline, Code), D21)
```
D4/D5 use EventCount deltas (方案B): for each (Sport, Discipline, Code), compute
EventCount_current - EventCount_prev. D4 = sum of positive deltas, D5 = sum of
absolute negative deltas. This captures the magnitude of program changes — a
discipline that gained 5 events is weighted 5× more than one that gained 1.
Compare only adjacent Olympic Years (via OLYMPIC_YEARS). First Olympiad in the
dataset (1896) gets D4=D5=NaN.

**Group E — Discipline Advantage Index** (see 2.2)

Source: `discipline_index.csv`, joined on (canonical_name, Year).
```
E1: summary_index              (sum of all T_score for this canonical_name, Year)
E2: n_obvious_advantage        (count of disciplines with T_score > 2)
E3: n_general_advantage        (count of disciplines with 1 <= T_score <= 2)
E4: n_potential_advantage      (count of disciplines with 0 < T_score < 1)
E5: top_discipline_code        (discipline Code with highest T_score)
E6: top_discipline_score       (highest T_score value)
```

**Group F — Geopolitical / Structural** (internal features only — no external GDP/population)

Source: `noc_mapping_v2.csv` + `athletes_clean.csv`.
```
F1: region                     (IOC 5 continental associations: Europe, Asia, Africa,
                                Americas, Oceania — built from athlete_NOC → region
                                dictionary in build_features.py, D16)
F2: years_since_first          (current Year - entity's first Year in athletes_clean)
F3: n_olympiads_participated   (count of Olympiads up to current Year where entity
                                actually sent athletes; boycott years NOT counted)
```
Rationale (D13): Delegation size (Group B, r=0.779) is the strongest country-resource
proxy available. Historical GDP/population data is unreliable before 1960 and for
dissolved countries (USSR, East Germany, etc.). External data may be added later as
an enhancement.

**Group G — Multi-team indicator** (per-Olympiad snapshot, D17)

Source: `athletes_clean.csv` column `is_multi_team`. Computed per (canonical_name, Year).
```
G1: has_multi_teams            (1 if this NOC has any is_multi_team=1 rows at this
                                Olympiad, else 0)
G2: n_multi_disciplines        (count of distinct Sport values where this NOC has
                                is_multi_team=1 at this Olympiad)
```

### 2.2 Discipline Advantage Level Index (`src/features/discipline_index.py`)

**Input**: `athletes_clean` + `athlete_discipline_map` + `noc_mapping_v2` + `programs_clean`
**Output**: `output/features/discipline_index.csv`

**Table structure** (time-aware):
```
canonical_name | Discipline | Code | Year | score_current | score_lag1 | score_lag2 | T_score | n_years_used
```

One row per (canonical_name, Discipline, Year). T_score is computed only from data
available at that Year (no future leakage).

**Step 1 — Map athletes to disciplines**:
  Join athletes_clean → athlete_discipline_map on (Sport, Event keyword)
  → get Code and programs_Sport/Discipline for each athlete row.

**Step 2 — Count medals per (NOC, Discipline, Year, Medal type)**:
  After team-event dedup (NOC, Year, Event, Medal), count Gold/Silver/Bronze
  per (athlete_NOC, Discipline_Code, Year). Map athlete_NOC → canonical_name
  via noc_mapping_v2.

**Step 3 — Compute normalized score per (canonical_name, Discipline, Year)**:
  ```
  score(C, D, Y) = (Gold_C_D_Y / Gold_D_Y) × 1.0
                 + (Silver_C_D_Y / Silver_D_Y) × 0.6
                 + (Bronze_C_D_Y / Bronze_D_Y) × 0.4
  ```
  where Gold_D_Y = total Gold medals awarded in Discipline D at Year Y
  (summed across all countries). If Gold_D_Y = 0 (no events that year),
  score = 0. Weights: w_gold=1.0, w_silver=0.6, w_bronze=0.4.

  **Why normalize?** The number of medal events per discipline varies across
  Olympiads (e.g., Swimming had 10 events in 1904 vs 37 in 2024). Raw medal
  counts would over-weight modern Games. The normalized score means "what
  fraction of this discipline's available medals did this country win?" —
  a gold medal sweep scores 1.0 regardless of whether the discipline offered
  2 or 20 golds.

**Step 4 — Weighted T_score with 3-Olympiad window (λ = 0.7, D02)**:
  ```
  T(C, D, Y) = (w0 × score_current + w1 × score_lag1 + w2 × score_lag2)
             / (w0 + w1 + w2 for terms that exist)

  w0 = 1.0 (current Olympiad)
  w1 = 0.7 (previous Olympiad, Y-4)
  w2 = 0.5 (two Olympiads ago, Y-8)
  ```
  A term only contributes if: (a) the country participated that year, AND
  (b) the discipline had events that year. Missing terms are excluded from
  the denominator. If no terms exist, T_score = NaN.

  At λ=0.7: lag1 weight = 0.70, lag2 weight ≈ 0.49→rounded to 0.5.
  This preserves recency while smoothing year-to-year noise.

### 2.3 Feature Target Alignment

Source: `medal_counts_clean.csv`, joined on `(medal_counts.NOC = canonical_name, medal_counts.Year)`.
`medal_counts_clean.NOC` stores canonical_name (full country name), so the join is direct.

```
Target variables (for each canonical_name, Year), D18:

  y_gold   = Gold   (from medal_counts_clean.Gold)
  y_silver = Silver (from medal_counts_clean.Silver)
  y_bronze = Bronze (from medal_counts_clean.Bronze)
  y_total  = Total  (from medal_counts_clean.Total, = Gold + Silver + Bronze)
  y_any    = 1 if y_total > 0 else 0

All five targets are stored in feature_matrix.csv alongside the features.
Models can predict the broadest set (y_any → y_total) or individual counts
(y_gold, y_silver, y_bronze) as needed.

Train/test split strategy (D12):
  - Rolling temporal split (NEVER random): train on all years before test Olympiad
  - Robustness checks: test = 2008 (train ≤ 2004), test = 2012 (train ≤ 2008)
  - Final evaluation: test = 2016 (train ≤ 2012) — this result goes in the report
  - 2008 and 2012 results confirm model stability, not reported in detail
  - Temporal split respects time-series nature and prevents future leakage.
```

---

## 3. Phase 3: Modeling

### 3.1 Two-Step Framework (Improved)

The original used Random Forest (10 trees) for both stages. Improvement plan:

**Step 1 — Binary Classification** (will NOC win any medal?)

```
Candidate models (compare all, select best via CV):
  - Logistic Regression (baseline, interpretable)
  - Random Forest (≥100 trees, tuned via GridSearchCV)
  - XGBoost (better handling of class imbalance)
  - LightGBM (faster, good with mixed feature types)

Class imbalance handling:
  ~60% of (NOC, Year) pairs have Total == 0
  Use: scale_pos_weight (XGBoost) or class_weight='balanced' (sklearn)
  Evaluate: Precision, Recall, F1, ROC-AUC

Feature importance analysis:
  After fitting, extract top-10 features → informs report writing
```

**Step 2 — Regression** (how many medals, given NOC will win some?)

```
Candidate models:
  - Poisson Regression (count data, natural fit)
  - Negative Binomial Regression (if overdispersion detected)
  - Random Forest Regressor (≥100 trees)
  - XGBoost Regressor
  - Quantile Regression (for prediction intervals directly)

Target transformation:
  - Log(1 + y) for models sensitive to right-skew
  - Raw counts for Poisson/NB

Prediction intervals:
  - Random Forest: use prediction quantiles from individual trees
  - XGBoost: bootstrap resampling
  - Quantile Regression: direct prediction of 10th/90th percentiles
  - Report: 80% and 95% prediction intervals
```

### 3.2 Model Evaluation (`src/evaluate/metrics.py`)

```
For classification:
  - Precision, Recall, F1-score
  - ROC-AUC
  - Confusion matrix (per Olympiad)

For regression:
  - RMSE (root mean squared error)
  - MAE (mean absolute error)
  - R² score
  - MAPE (mean absolute percentage error) — interpretable for report

For prediction intervals:
  - Coverage probability: % of true values falling within predicted interval
  - Interval width: average width of prediction intervals

Baseline comparison:
  - Naive forecast: next Olympiad = current Olympiad (y_{t+1} = y_t)
  - Simple OLS on lag1 only
  - Your model must beat BOTH baselines.
```

### 3.3 Great Coach Effect (`src/models/coach_effect.py`)

**Limitation of original work**: relied on ONE case study (Béla Károlyi) to claim a general effect. This is weak evidence.

**Improvement strategy**:

```
APPROACH A — Systematic search for discontinuity events:
  1. For each (NOC, Discipline) pair with ≥6 Olympiad appearances:
     a. Scan for sudden medal count jumps (2+σ above rolling mean)
     b. Flag candidate "great coach" events
  2. For flagged events, search external sources to confirm coaching change
  3. Apply RDiT to validated events → estimate effect size distribution
  4. Report: median effect, 95% CI, p-value from permutation test

APPROACH B — Synthetic control method:
  1. For a known coach-move event (e.g., Károlyi: Romania→USA):
     a. Build a synthetic control from similar NOCs that did NOT get the coach
     b. Compare actual trajectory vs synthetic control
  2. More robust than RDiT alone; handles confounding trends

APPROACH C — Placebo tests:
  1. Randomly assign "fake" coach arrival years
  2. Run RDiT on these → should find NO effect
  3. If real effect > 95th percentile of placebo distribution, effect is significant
```

**Coach investment recommendation** (3 countries):
```
Use the refined Discipline Advantage Index to identify:
  - Disciplines where the country has NO current advantage (T_jk ≈ 0)
  - BUT many events exist (high medal opportunity)
  - AND the discipline is "coachable" (skill-intensive, not purely genetic/physiological)

Rank candidates by: (event_count) × (1 - normalized_T_score) × (coachability_factor)
```

---

## 4. Phase 4: Prediction & Insights

### 4.1 2028 Prediction

```
1. Construct feature row for each NOC for 2028:
   - Lag features from 2024 and 2020 actuals
   - Athlete counts: use 2024 values (or extrapolate trend)
   - Host features: Los Angeles → USA = host
   - Event counts: use 2028 program (from summerOly_programs.csv column 2028)

2. Step 1 model → probability of winning any medal
3. Step 2 model → predicted counts (for all countries, apply prob threshold)
4. Combine: expected_medals = P(win) × E(medals | win)
5. Report with 80% prediction intervals
```

### 4.2 First-Time Medalists

```
1. Identify NOCs with Total == 0 for all historical years
2. Run Step 1 classifier on these NOCs for 2028
3. Rank by predicted probability
4. Report NOCs with P(win) > threshold (calibrated via CV)
5. Estimate: number of new medalists = sum of P(win) for all zero-history NOCs
   (This is the expected value; also report distribution)
```

### 4.3 Event-Country Relationship

```
For each (NOC, Discipline):
  Correlation between (event_count_in_discipline)_t and (medals_won_by_noc_in_discipline)_t
  Identify: disciplines where correlation > 0.5 → "strategic disciplines"

For host country specifically:
  Compare: host's advantageous disciplines' event counts in hosting year vs non-hosting years
  Quantify: how many "extra" events host nations add to their strong disciplines
```

---

## 5. Execution Order (Sequence)

```
[Day 1-2]  Phase 0: Set up file structure, config.py, io_utils.py
[Day 3-5]  Phase 1: Data preprocessing (all 5 cleaning scripts)
           → CHECKPOINT: All cleaned data passes validation
[Day 6-8]  Phase 2: Feature engineering
           → CHECKPOINT: Feature matrix built, no NaN columns (except structural)
[Day 9-12] Phase 3: Modeling (classification → regression → coach effect)
           → CHECKPOINT: All models beat naive baseline
[Day 13-15] Phase 4: Generate predictions, figures, write report
           → CHECKPOINT: All required problem questions answered
```

---

## 6. Verification & Cross-Check Protocol

After each phase, run these checks before proceeding:

### After Phase 1:
- [ ] `athletes_clean.csv` row count ≈ 249,264 (252,565 − 1,576 dedup − 1,725 from 1906 removal)
- [ ] All NOC values in athletes match `noc_mapping_v2.csv`
- [ ] No "garbled" Team names remain (run detection script)
- [ ] `medal_counts_clean.csv`: (NOC, Year) unique, NOC not null, Gold+Silver+Bronze==Total
- [ ] `medal_counts_clean.csv`: includes zero-medal participation rows (complete panel)

### After Phase 2:
- [ ] `feature_matrix.csv` NaN values are only in documented locations (pre-participation lag features, growth rate for debut Olympiads; structural NAs documented in config)
- [ ] Feature correlation matrix: no pair with |r| > 0.95 (multicollinearity check)
- [ ] Target distribution plotted → right-skew confirmed → log-transform justified
- [ ] No Year=1906 in feature matrix or any join source

### After Phase 3:
- [ ] Classification model: F1 > 0.75 on test set
- [ ] Regression model: beats naive baseline on RMSE by ≥10%
- [ ] Prediction intervals: coverage within ±5% of nominal level
- [ ] Coach effect: placebo test passes (real effect > placebo 95th percentile)

### After Phase 4:
- [ ] 2028 predictions: USA total medals > 80 (face validity)
- [ ] Top-10 predicted countries match expert consensus roughly
- [ ] No country predicted with negative medals

---

## A. Appendix: Key Decisions Log

Record every non-obvious decision here as you work:

| ID | Date | Decision | Rationale | Reversible? |
|----|------|----------|-----------|-------------|
| D01 | 2026-05-10 | Medal counts derived from athletes, not IOC official | Doping DQs & political reallocations = non-sport factors; athletes reflects on-field results. 87.5% match with official (179 diffs, mostly 2008-2024). Official retained as comparison via medal_counts_compare.csv. | Yes — switch to official by changing input source |
| D02 | 2026-05-12 | λ decay factor = 0.7 | For discipline_index.py: Z_weighted = Σ (0.7^n_games_ago) × weighted_medals. Smaller λ weights recent performance more heavily — 16-year-old medals get only 24% weight. Confirmed by Cassie. | Yes — tune as hyperparameter |
| D03 | 2026-05-12 | Classification threshold | - | Yes, calibrate via CV |
| D08 | 2026-05-10 | Programs: added status_code column, fixed demo detection | Bullet (•) corrupted to '?' during encoding. '?4' and '??1' values (5 events over 3 rows) were incorrectly set to EventCount=0. Now correctly parsed as demo with proper event counts. All 6 special-value types handled. | No — status_code is additive, downstream can ignore it |
| D09 | 2026-05-10 | Team names NOT replaced with canonical_name | NOC (3-letter IOC code) is always present and valid. Team column has alias noise, multi-language names, and historical spelling variations. Downstream code MUST join on NOC, never Team. noc_mapping_v2.csv bridges NOC ↔ canonical_name for display. | No — changing would require updating all downstream join logic |
| D10 | 2026-05-12 | 1906 Intercalated Games EXCLUDED from all datasets | 1906 was never an official IOC Olympiad. It breaks the 4-year cycle (causes lag feature misalignment), has no host entry in summerOly_hosts.csv, and the IOC does not count it in official medal tallies. Removed from OLYMPIC_YEARS; all Phase 1 scripts filter it out. Reverses D07. | Yes — re-add by restoring {1906} to OLYMPIC_YEARS and re-running Phase 1 |
| D11 | 2026-05-12 | Lag features before first participation = NaN (not 0) | NaN correctly distinguishes "country did not exist yet" from "country participated and won 0 medals." Models handle NaN explicitly; 0 would mislead training. Applies to all Group A lag features and B5 (athlete_growth_rate). | No — 0 would introduce incorrect signal |
| D12 | 2026-05-12 | Temporal split: train ≤ 2004, test = 2008/2012/2016 (rolling) | Three test Olympiads with rolling training windows. Only 2016 results reported in paper; 2008 and 2012 serve as robustness checks. Simpler than LOOCV, respects time-series nature, and focuses evaluation on the most recent Games. | Yes — expand/contract test set as needed |
| D13 | 2026-05-12 | Group F: internal features only (no external GDP/population data) | Delegation size (Group B, r=0.779) is the strongest country-resource proxy. Historical GDP data unreliable before 1960 and for dissolved countries. Group F retains: region, years_since_first_participation, n_olympiads_participated. External GDP data can be added later as enhancement. | Yes — add external GDP/population as additional columns |
| D14 | 2026-05-13 | Feature matrix primary key = (canonical_name, Year) | canonical_name is the unified country identifier from noc_mapping_v2. All downstream tables use it. Medal counts, discipline index, and hosts all reference canonical_name. Using 3-letter NOC would require constant re-mapping. | No — changing would break all join logic |
| D15 | 2026-05-13 | Entity existence window rules for feature matrix rows | Historical entities (Soviet Union, East Germany, etc.) have NO rows after their dissolution year — predicting medals for nonexistent countries is meaningless. Country entities have rows from first_year through 2024, including boycott years (entity existed, could have participated). Special entities (Refugee Olympic Team) span their appearance window only. | Yes — adjust window boundaries |
| D16 | 2026-05-13 | F1 region via IOC 5 continental association mapping | Hard-coded dictionary in build_features.py maps athlete_NOC (3-letter IOC code) → region (Africa/Asia/Europe/Americas/Oceania). Source: IOC official continental associations (ANOCA, OCA, EOC, Panam Sports, ONOC). Covers all 233 NOCs in athletes_clean. | Yes — update mapping if NOC list changes |
| D17 | 2026-05-13 | Group G: per-Olympiad snapshot (not historical cumulative) | G1 and G2 computed per (canonical_name, Year) from is_multi_team flag in athletes_clean. Captures the within-Olympiad effect of fielding multiple teams, which varies year to year. A historical "ever had multi-team" flag would be nearly collinear with delegation size. | Yes — change to historical cumulative if needed |
| D18 | 2026-05-13 | Target variables include all five medal columns | y_gold, y_silver, y_bronze, y_total, y_any stored in feature_matrix alongside features. Separate gold/silver/bronze targets support per-type analysis (some countries have different efficiency profiles across medal types). All sourced from medal_counts_clean.Gold/Silver/Bronze/Total. | Yes — drop columns as needed |
| D19 | 2026-05-13 | Lag features skip non-participation years (carry-forward) | When computing lag1/lag2/lag3, skip Olympiads where the entity did NOT participate. Instead use the next most recent Olympiad with participation. A boycotting country (USA 1980) still has athletic capability — its expected next-Olympiad performance is closer to its last actual showing than to 0. If no prior participation exists, lag = NaN. Applies to Group A and Group B lag references. | Yes — change back to non-skip (treat boycott as 0) |
| D20 | 2026-05-13 | B5 athlete_growth_rate = NaN when B1_prev = 0 | Division by zero when previous delegation size = 0 (boycott or first participation). NaN distinguishes "cannot compute" from "0 growth." Confirmed by Cassie. | No — 0/0 is undefined |
| D21 | 2026-05-13 | D4/D5 use EventCount deltas (方案B) | For each (Sport, Discipline, Code), compute EventCount_current − EventCount_prev. D4 = sum of positive deltas, D5 = sum of absolute negative deltas. Captures magnitude of program changes — a discipline that added 5 events counts 5× more than one that added 1. More granular than counting new discipline codes (方案A). Confirmed by Cassie. | Yes — switch to counting codes |

---

## B. Appendix: Communication Protocol for Codex Review

When sending output to Codex for review, include:

1. **Which section** of this pipeline the output belongs to (e.g., "Phase 1, Step 1.1.3")
2. **The code** or output being reviewed
3. **Expected behavior** (what should happen)
4. **Actual/observed behavior** (what actually happened)
5. **The verification checklist** items relevant to this step

Example message format:
```
REVIEW REQUEST: Phase 1, Step 1.1.2 (Team name normalization)
INPUT: 100 randomly sampled rows from athletes_clean.csv
EXPECTED: All Team names are ASCII, no garbled characters, is_multi_team correctly flagged
OBSERVED: [paste or describe]
CHECK AGAINST: Pipeline Section 6, After Phase 1, bullet 3 ("No garbled Team names remain")
```
