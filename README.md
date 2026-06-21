# Personal Budget & Debt Analysis

Analyze bank CSV/Excel exports locally with Jupyter — no cloud, no account linking.

**Features**

- Load common bank export formats (single `Amount` column, debit/credit pairs, RBC-style `CAD$`/`USD$`)
- Keyword-based spending categories (YAML-configurable)
- Multi-account analysis (one file per account in `data/raw/`)
- Debt payoff math: single-loan amortization and multi-debt avalanche (highest APR first)
- **Integrated debt planning:** income − budget − emergency fund → debt payment, with scenario comparison
- **Income phases:** model a raise or job change mid-plan (`income.phases` in plan.yaml)
- **Recurring bill detection:** find subscriptions and monthly charges from transaction patterns
- **Plan vs actual:** compare plan budget lines to trailing categorized spend

## Quick start

```bash
git clone <your-repo-url>
cd budgeting
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```

Open `notebooks/01_budget_analysis.ipynb` and run all cells — it works immediately on included sample data.

## Use your own data

1. Export transactions from your bank as CSV or Excel.
2. Drop files into `data/raw/` (one file per account, any filename).
3. Re-run the notebook.

Your exports are **git-ignored** — see [SECURITY.md](SECURITY.md) before pushing anywhere public.

### Customize categories

```bash
cp config/categories.example.yaml config/categories.yaml
# edit keywords for your merchants
```

### Plan debt payoff

```bash
cp config/debts.example.yaml config/debts.yaml
# enter balances and APRs
jupyter lab notebooks/02_debt_payoff.ipynb
```

### Full debt plan (budget + scenarios)

```bash
./scripts/init_local.sh
# edit config/plan.yaml — income, budget lines, debts, scenarios
jupyter lab notebooks/03_debt_plan.ipynb
```

The plan notebook compares scenarios (balanced, lean lifestyle, phased sprint, safety-net-first) and charts debt + emergency fund over time.

`01_budget_analysis.ipynb` also includes **recurring bills** and **plan vs actual** when `config/plan.yaml` exists.

## Supported export formats

The loader auto-detects column headers (case-insensitive):

| Canonical | Recognized aliases |
|-----------|-------------------|
| Date | `Date`, `Transaction Date`, `Posted Date`, … |
| Description | `Description`, `Description 1`, `Memo`, `Payee`, … |
| Amount | `Amount`, `CAD$`, `USD$`, … |
| Debit / Credit | `Debit`, `Withdrawal`, `Credit`, `Deposit`, … |

**RBC-style exports:** `Description 1` + `Description 2` are merged; if `CAD$` is blank, `USD$` is used at face value (no FX conversion).

Sample files:

- `data/sample_transactions.csv` — generic 3-column format
- `data/sample_rbc_export.csv` — RBC multi-column format (fake account numbers)

## Project layout

```
config/
  categories.example.yaml   committed template
  debts.example.yaml        committed template
  plan.example.yaml         committed template (budget + scenarios)
  categories.yaml           your rules (git-ignored)
  debts.yaml                your balances (git-ignored)
  plan.yaml                 your full plan (git-ignored)
data/
  raw/                      your bank exports (git-ignored)
  sample_*.csv              demo data (committed)
notebooks/
  01_budget_analysis.ipynb
  02_debt_payoff.ipynb
  03_debt_plan.ipynb        budget-integrated scenarios
reports/                    generated charts (git-ignored)
src/
  loader.py                 CSV/Excel normalization
  categorize.py             keyword categorization
  payoff.py                 amortization & avalanche
  planner.py                budget + scenario simulation
```

**Amount convention:** negative = money out, positive = money in.

**Non-spending categories** (transfers, credit-card payments, investments) are excluded from spending totals so money moving between your own accounts isn't double-counted.

## Development

```bash
source .venv/bin/activate
python src/payoff.py          # self-check amortization math
python src/planner.py         # self-check scenario planner
python -c "from src import load_transactions, categorize; print(categorize(load_transactions('data/sample_rbc_export.csv')).head())"
```

## License

MIT — see [LICENSE](LICENSE).

## Security

Read [SECURITY.md](SECURITY.md) before publishing this repo or sharing notebooks.
