# Security

This project is designed for **local, personal financial analysis**. Treat your transaction data as sensitive.

## What stays local

These paths are **git-ignored** and must never be committed:

| Path | Contains |
|------|----------|
| `data/raw/*` | Bank CSV/Excel exports (account numbers, merchants, amounts) |
| `data/processed/*` | Cleaned output you generate |
| `config/categories.yaml` | Your merchant keyword rules |
| `config/debts.yaml` | Your debt balances and APRs |
| `config/plan.yaml` | Income, budget, EF target, scenarios |
| `config/budget.yaml` | Personal budget targets (if added) |
| `reports/*` | Charts that may reflect your spending |
| `.env` | Secrets or API keys (if added later) |

Only **sample data** under `data/sample_*.csv` and `config/*.example.yaml` belong in git.

## Before pushing to GitHub

1. Run `git status` and confirm no files under `data/raw/`, `config/*.yaml` (non-example), or `reports/` appear.
2. Clear notebook outputs if you re-ran analysis on real data:  
   `jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`
3. Search the repo for account numbers or names:  
   `git grep -i 'your-bank-account-pattern'` (adjust as needed).
4. If this repo was ever committed with real data, **rotating account numbers won't help** — assume the history is compromised and use `git filter-repo` or a fresh repo.

## Notebook outputs

Executed notebooks embed HTML/text outputs. Even with git-ignored CSVs, **merchant names and totals can leak via notebook cells**. Ship notebooks with outputs cleared, or add `notebooks/*.ipynb` outputs to a pre-commit hook.

## This is not financial advice

Payoff projections and categorization are approximations. Tax, FX, and bank-specific quirks are not modeled. Verify numbers against your statements.

## Reporting issues

Do not open public GitHub issues containing real transaction data or account numbers.
