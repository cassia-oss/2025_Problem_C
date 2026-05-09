# 2025 MCM Problem C — Olympic Medal Table Improvement Plan

A re-examination of the 2025 Mathematical Contest in Modeling (MCM) Problem C,
with improved data preprocessing, feature engineering, and modeling methodology.

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `data/` | Raw data files (read-only, never modified) |
| `output/cleaned/` | Phase 1: cleaned & standardized datasets |
| `output/features/` | Phase 2: engineered feature matrices |
| `output/models/` | Phase 3: trained model artifacts |
| `output/predictions/` | Phase 4: 2028 predictions & reports |
| `src/preprocess/` | Data cleaning scripts |
| `src/features/` | Feature engineering scripts |
| `src/models/` | Classification, regression, coach-effect models |
| `src/evaluate/` | Metrics, visualization, model comparison |
| `src/utils/` | Shared utilities (config, I/O) |
| `notebooks/` | Exploratory notebooks |
| `tests/` | Unit tests |
| `essay/` | Final paper |

## Quick Start

```bash
# 1. Set up directory structure
python src/utils/config.py

# 2. Run the pipeline phases in order (see PIPELINE.md for details)
python src/preprocess/clean_athletes.py
python src/preprocess/clean_medal_counts.py
python src/preprocess/clean_programs.py
python src/preprocess/clean_hosts.py
python src/preprocess/unify_noc.py
```

## Reference

- [PIPELINE.md](PIPELINE.md) — authoritative step-by-step instruction set
- [2025 MCM Problem C (PDF)](2025_MCM_Problem_C.pdf) — original contest problem
