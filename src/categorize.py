"""Rule-based transaction categorization.

Categories are assigned by matching keywords against the transaction description.
The first category whose keyword matches wins, so order matters: put structural
buckets (transfers, loan payments, income) before merchant buckets.

Customize via ``config/categories.yaml`` (copy from ``categories.example.yaml``).
Anything unmatched becomes ``Uncategorized``.

``NON_SPENDING`` marks categories that move money between your own accounts or pay
down balances. Exclude these from spending totals so the same dollar isn't counted
twice across accounts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Fallback when no config/categories.yaml exists.
DEFAULT_RULES: dict[str, list[str]] = {
    "Credit Card Payment": ["payment - thank you", "paiement - merci"],
    "Transfer": [
        "online banking transfer", "online transfer", "e-transfer", "etransfer",
        "interac e-trf", "atm deposit",
    ],
    "Loan & Interest": [
        "loan payment", "loan interest", "overdraft interest", "mortgage",
    ],
    "Income": ["payroll", "salary", "direct deposit", "tax refund", "interest paid"],
    "Investments": ["investment", "sun life", "rrsp", "tfsa"],
    "Insurance": ["insurance", "manulife"],
    "Housing": ["rent", "mortgage payment", "property", "hoa", "condo fee"],
    "Utilities": [
        "telus", "shaw", "rogers", "bell", "electric", "water", "internet", "utility",
    ],
    "Groceries": [
        "grocery", "supermarket", "wal-mart", "walmart", "costco", "safeway",
        "superstore", "instacart",
    ],
    "Alcohol": ["liquor", "wine", "brewery", "beer"],
    "Dining": [
        "restaurant", "cafe", "coffee", "starbucks", "tim hortons", "mcdonald",
        "doordash", "uber eats", "ubereats", "skipthedishes", "grubhub",
        "pub", "bar", "bistro", "sq *", "tst-",
    ],
    "Transport": ["uber", "lyft", "cab", "taxi", "transit", "parking", "toll"],
    "Fuel": ["petro canada", "petro-canada", "esso", "shell", "chevron", "gas station"],
    "Auto": ["automotive", "canadian tire", "jiffy lube", "auto"],
    "Software & Subscriptions": [
        "netflix", "spotify", "amazon web services", "aws", "google", "apple.com",
        "microsoft", "subscription", "prime",
    ],
    "Shopping": ["amazon", "best buy", "target", "store", "shop"],
    "Health": ["pharmacy", "rexall", "shoppers drug", "dental", "clinic", "doctor", "gym"],
    "Recreation": ["golf", "ski", "yoga", "climbing", "sport"],
    "Entertainment": ["theatre", "cinema", "cineplex", "concert", "ticket"],
    "Travel": ["hotel", "airbnb", "airline", "flight", "expedia"],
    "Fees": ["fee", "service charge", "atm withdrawal", "nsf"],
}

NON_SPENDING = {"Transfer", "Credit Card Payment", "Investments"}

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "categories.yaml"


def load_rules(path: str | Path | None = None) -> dict[str, list[str]]:
    """Load keyword rules from YAML, or return built-in defaults."""
    path = Path(path) if path else _CONFIG_PATH
    if not path.exists():
        return DEFAULT_RULES
    try:
        import yaml
    except ImportError as e:
        raise ImportError("PyYAML required to load config/categories.yaml — pip install pyyaml") from e
    data = yaml.safe_load(path.read_text()) or {}
    rules = data.get("rules")
    if not isinstance(rules, dict):
        raise ValueError(f"{path}: expected top-level 'rules' mapping")
    return {str(k): [str(v) for v in vals] for k, vals in rules.items()}


def load_non_spending(path: str | Path | None = None) -> set[str]:
    """Load non-spending category names from YAML, or return defaults."""
    path = Path(path) if path else _CONFIG_PATH
    if not path.exists():
        return set(NON_SPENDING)
    import yaml
    data = yaml.safe_load(path.read_text()) or {}
    items = data.get("non_spending", list(NON_SPENDING))
    return set(str(x) for x in items)


def _match_category(description: str, rules: dict[str, list[str]]) -> str:
    text = description.lower()
    for category, keywords in rules.items():
        for kw in keywords:
            if re.search(re.escape(kw.lower()), text):
                return category
    return "Uncategorized"


def categorize(
    df: pd.DataFrame,
    rules: dict[str, list[str]] | None = None,
    column: str = "description",
) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``category`` column added."""
    rules = rules or load_rules()
    out = df.copy()
    out["category"] = out[column].apply(lambda d: _match_category(str(d), rules))
    return out
