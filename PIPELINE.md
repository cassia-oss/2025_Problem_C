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

STEP 1.1.2 — Normalize Team names via NOC
  For each row, if Team contains garbled/non-standard characters:
    Replace Team with canonical_name from the NOC unification table (see 1.5).
  If Team contains a dash-suffix pattern (e.g., "United States-1", "Germany-2"):
    Extract base_country = Team without suffix
    Set is_multi_team = 1
    Keep Team as-is for traceability
  Else:
    Set is_multi_team = 0

STEP 1.1.3 — Normalize Medal values
  Map: "Gold" → "Gold", "Silver" → "Silver", "Bronze" → "Bronze"
  Map: "No medal" / "No Medal" / "" / NaN → "No medal"
  All values must be one of: {"Gold", "Silver", "Bronze", "No medal"}

STEP 1.1.4 — Validate NOC codes
  Every NOC must appear in the reference list built from summerOly_medal_counts.csv.
  Flag unknown NOCs → write to output/cleaned/unknown_noc.csv for manual review.

STEP 1.1.5 — Validate Year range
  Year must be in [1896, 2024] and be a valid Summer Olympics year
  (from summerOly_hosts.csv, excluding cancelled years: 1916, 1940, 1944).

STEP 1.1.6 — Write cleaned output
  Columns: Name, Sex, Team, NOC, Year, City, Sport, Event, Medal, is_multi_team
```

### 1.2 Medal Counts Cleaning (`src/preprocess/clean_medal_counts.py`)

**Input**: `data/summerOly_medal_counts.csv`
**Output**: `output/cleaned/medal_counts_clean.csv`

```
STEP 1.2.1 — Drop rows where all medal counts are 0 AND Rank is missing
  (These are likely placeholder rows for countries that attended but won nothing;
   keep only if Rank is present.)

STEP 1.2.2 — Validate: Gold + Silver + Bronze == Total for every row
  Flag violations → output/cleaned/medal_mismatch.csv
  If Total is missing, impute: Total = Gold + Silver + Bronze

STEP 1.2.3 — Validate Rank monotonicity within each Year
  For each Year group, Rank should be sequential (1, 2, 3, ...).
  Ties: same Total → same Rank (IOC convention). Flag rank gaps.

STEP 1.2.4 — Normalize NOC to match unification table (see 1.5)
```

### 1.3 Programs Data Cleaning (`src/preprocess/clean_programs.py`)

**Input**: `data/summerOly_programs.csv`
**Output**: `output/cleaned/programs_clean.csv` (long format)

```
STEP 1.3.1 — Melt from wide to long format
  Current: columns 1896, 1900, 1904, ... (wide format)
  Target:  Sport | Discipline | Code | Year | EventCount

STEP 1.3.2 — Handle bullet (•) values
  • = demonstration/unfficial sport
  Set EventCount = 0, add column is_demo = 1
  All numeric values: is_demo = 0

STEP 1.3.3 — Handle cancelled years
  Drop rows with Year in {1916, 1940, 1944} (no Games held)

STEP 1.3.4 — Special characters in Sport/Discipline names
  Replace `\xef\xbf\xbd` (Unicode replacement char) with proper characters
  or standardize to ASCII equivalents
```

### 1.4 Hosts Data Cleaning (`src/preprocess/clean_hosts.py`)

**Input**: `data/summerOly_hosts.csv`
**Output**: `output/cleaned/hosts_clean.csv`

```
STEP 1.4.1 — Extract host_country from Host field
  "Athens, Greece" → City="Athens", Country="Greece", NOC=<mapped code>
  Add NOC column for join compatibility.

STEP 1.4.2 — Flag cancelled years
  Add column is_cancelled (BOOL) for 1916, 1940, 1944

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

---

## 2. Phase 2: Feature Engineering

### 2.1 Core Feature Table (`src/features/build_features.py`)

**Input**: Cleaned data from `output/cleaned/`
**Output**: `output/features/feature_matrix.csv`

One row per (NOC, Year) pair. All countries × all Olympic years (post-cleaning).

#### Feature Groups:

**Group A — Lagged Medal Performance** (captures momentum)
```
A1: gold_lag1, silver_lag1, bronze_lag1, total_lag1   (previous Olympics)
A2: gold_lag2, silver_lag2, bronze_lag2, total_lag2   (two Olympics ago)
A3: gold_avg_3, total_avg_3                            (3-Olympiad moving average)
A4: medal_won_binary_lag1                              (0/1, did country win any medal last time?)
```

**Group B — Athlete Delegation**
```
B1: n_athletes_total          (delegation size this year)
B2: n_athletes_male
B3: n_athletes_female
B4: n_athletes_unique_events  (how many distinct events the country enters)
B5: athlete_growth_rate       (relative to previous Olympiad)
```

**Group C — Host-Related**
```
C1: is_host                   (1 if country hosts this year)
C2: is_host_next              (1 if hosting next Olympics — prep effect)
C3: is_host_prev              (1 if hosted previous Olympics — legacy effect)
C4: host_cycle_phase          (categorical: 0=none, 1=pre-host, 2=host, 3=post-host)
C5: years_since_last_host      (integer, -1 if never hosted)
```

**Group D — Event Structure**
```
D1: total_events_this_year     (total medal events at this Olympiad)
D2: n_sports_this_year
D3: n_disciplines_this_year
D4: n_new_events               (events that didn't exist last Olympiad)
D5: n_discontinued_events      (events dropped since last Olympiad)
```

**Group E — Discipline Advantage Index** (see 2.2)
```
E1: summary_index              (sum of all discipline T_jk scores for this country)
E2: n_obvious_advantage        (count of disciplines with T_jk > 2)
E3: n_general_advantage        (count of disciplines with 1 <= T_jk <= 2)
E4: n_potential_advantage      (count of disciplines with T_jk < 1 but > 0)
E5: top_discipline_code        (discipline code with highest T_jk)
E6: top_discipline_score
```

**Group F — Geopolitical / Structural**
```
F1: region                     (from NOC mapping: Europe, Asia, Africa, Americas, Oceania)
F2: is_developed               (UN M49 classification mapped to BOOL — use as supplemental data)
F3: gdp_category               (optional, requires external data — document if used)
F4: years_since_first_participation
F5: n_olympiads_participated
```

**Group G — Multi-team indicator**
```
G1: has_multi_teams            (does this NOC ever have multi-team entries?)
G2: n_multi_team_disciplines   (how many disciplines have multi-team entries)
```

### 2.2 Discipline Advantage Level Index (`src/features/discipline_index.py`)

**Refinement of the original formula** (old formula used fixed weights 1.0/0.6/0.4):

```
For each (NOC, Discipline) pair:

  Z_noc_disc = Σ (w_gold * Gold + w_silver * Silver + w_bronze * Bronze)
               over all Games the NOC participated in

  T_noc_disc = Z_noc_disc / n_games_participated

Weights: w_gold=1.0, w_silver=0.6, w_bronze=0.4  (same as original, validated by literature)

Enhanced version — add decay factor:
  Z_weighted = Σ λ^(n_games_ago) * (Gold + 0.6*Silver + 0.4*Bronze)
  where λ ∈ [0.8, 0.95] controls recency weighting
  This captures the fact that a country's advantage 30 years ago matters less than recent performance.
```

**Output**: `output/features/discipline_index.csv` (NOC | Discipline | T_score | Z_raw | n_games)

### 2.3 Feature Target Alignment

```
Target variables (for each NOC, Year):
  y_gold   = Gold medals won
  y_total  = Total medals won
  y_any    = 1 if Total > 0 else 0

Train/test split strategy:
  - Temporal split (NEVER random): train on years ≤ 2016, validate on 2020, test on 2024
  - Or: leave-one-Olympiad-out cross-validation (LOOCV by Olympiad)
  - This respects the time-series nature of the data and prevents leakage.
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
- [ ] `athletes_clean.csv` row count ≈ 252,565 (minus duplicates only)
- [ ] All NOC values in athletes match `noc_mapping.csv`
- [ ] No "garbled" Team names remain (run detection script)
- [ ] `medal_counts_clean.csv`: Gold+Silver+Bronze == Total for ALL rows

### After Phase 2:
- [ ] `feature_matrix.csv` has no NaN values (except structural NAs documented in config)
- [ ] Feature correlation matrix: no pair with |r| > 0.95 (multicollinearity check)
- [ ] Target distribution plotted → right-skew confirmed → log-transform justified

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
| D01 | - | Post-1992 only vs all data | - | Yes, change in config |
| D02 | - | λ decay factor value | - | Yes, tune as hyperparameter |
| D03 | - | Classification threshold | - | Yes, calibrate via CV |

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
