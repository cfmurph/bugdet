# Budgeting & Analysis

A small Python project for analyzing personal spending from bank CSV/Excel exports.

## Setup

```bash
cd budgeting
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Then open `notebooks/01_budget_analysis.ipynb` and run all cells.

## Using your own data

Drop your bank's CSV or Excel exports into `data/raw/`. They're **git-ignored**, so your
financial data never gets committed. The loader auto-detects common column layouts
(`Date`/`Description`/`Amount`, or separate debit/credit columns). With `data/raw/` empty,
the notebook falls back to `data/sample_transactions.csv` so it runs out of the box.

## Categories

Spending is tagged by keyword rules in `src/categorize.py`. Edit `DEFAULT_RULES` to match
your own merchants; anything unmatched shows up as `Uncategorized` in the notebook so you
know what to add.

## Layout

```
data/raw/          your bank exports (private, git-ignored)
data/processed/    optional cleaned output (git-ignored)
data/sample_transactions.csv   demo data
notebooks/         analysis notebook
src/               loader + categorization helpers
reports/           exported charts (git-ignored)
```

Convention: in the `amount` column, **negative = money out**, **positive = money in**.
