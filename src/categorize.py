"""Rule-based transaction categorization.

Categories are assigned by matching keywords against the transaction
description. Edit ``DEFAULT_RULES`` to fit your own spending — the first
category whose keywords match wins. Anything unmatched becomes "Uncategorized".
"""
from __future__ import annotations

import re

import pandas as pd

# category -> list of lowercase keywords/substrings to match in the description.
DEFAULT_RULES: dict[str, list[str]] = {
    "Income": ["payroll", "salary", "direct deposit", "deposit from", "interest paid"],
    "Housing": ["rent", "mortgage", "hoa", "property"],
    "Utilities": ["electric", "water", "gas company", "internet", "comcast", "verizon", "at&t", "utility"],
    "Groceries": ["grocery", "supermarket", "whole foods", "trader joe", "safeway", "kroger", "aldi", "costco"],
    "Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "chipotle", "doordash", "uber eats", "grubhub"],
    "Transport": ["uber", "lyft", "shell", "chevron", "exxon", "gas station", "transit", "parking", "toll"],
    "Shopping": ["amazon", "target", "walmart", "best buy", "store", "shop"],
    "Subscriptions": ["netflix", "spotify", "hulu", "disney", "apple.com", "google", "subscription", "prime"],
    "Health": ["pharmacy", "cvs", "walgreens", "doctor", "dental", "clinic", "gym", "fitness"],
    "Travel": ["airline", "hotel", "airbnb", "delta", "united", "expedia", "flight"],
    "Fees": ["fee", "interest charge", "service charge", "atm"],
}


def _match_category(description: str, rules: dict[str, list[str]]) -> str:
    text = description.lower()
    for category, keywords in rules.items():
        for kw in keywords:
            if re.search(re.escape(kw), text):
                return category
    return "Uncategorized"


def categorize(
    df: pd.DataFrame,
    rules: dict[str, list[str]] | None = None,
    column: str = "description",
) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``category`` column added."""
    rules = rules or DEFAULT_RULES
    out = df.copy()
    out["category"] = out[column].apply(lambda d: _match_category(str(d), rules))
    return out
