"""Compare planned budget lines to actual categorized spending."""
from __future__ import annotations

from copy import deepcopy

import pandas as pd

DEFAULT_MAPPING: dict[str, list[str]] = {
    "essentials": [
        "Groceries", "Utilities", "Insurance", "Housing", "Fuel", "Transport",
        "Auto", "Health", "Software & Subscriptions", "Fees",
    ],
    "lifestyle": [
        "Dining", "Alcohol", "Entertainment", "Shopping", "Recreation", "Travel",
    ],
}


def budget_mapping(plan: dict) -> dict[str, list[str]]:
    """Category lists per plan bucket (essentials / lifestyle)."""
    custom = plan.get("budget_mapping")
    if not custom:
        return deepcopy(DEFAULT_MAPPING)
    return {str(k): [str(c) for c in v] for k, v in custom.items()}


def _category_bucket(category: str, mapping: dict[str, list[str]]) -> str | None:
    for bucket, categories in mapping.items():
        if category in categories:
            return bucket
    return None


def monthly_bucket_spend(
    df: pd.DataFrame,
    plan: dict,
    *,
    months: int = 3,
    exclude_categories: set[str] | None = None,
) -> pd.DataFrame:
    """Average monthly spend per plan bucket over the last ``months`` periods."""
    exclude = exclude_categories or set()
    mapping = budget_mapping(plan)
    spending = df[(df["amount"] < 0) & (~df["category"].isin(exclude))].copy()
    spending["out"] = -spending["amount"]
    spending["month"] = spending["date"].dt.to_period("M")

    recent = sorted(spending["month"].unique())[-months:]
    if not len(recent):
        return pd.DataFrame(columns=["bucket", "avg_monthly"])

    spending = spending[spending["month"].isin(recent)]
    spending["bucket"] = spending["category"].map(
        lambda c: _category_bucket(c, mapping) or "unmapped"
    )

    by_bucket = spending.groupby("bucket")["out"].sum() / len(recent)
    return by_bucket.reset_index(name="avg_monthly").rename(columns={"bucket": "line"})


def compare_plan_to_actual(
    df: pd.DataFrame,
    plan: dict,
    *,
    months: int = 3,
    exclude_categories: set[str] | None = None,
) -> pd.DataFrame:
    """Planned budget lines vs trailing average actuals."""
    actual = monthly_bucket_spend(
        df, plan, months=months, exclude_categories=exclude_categories
    )
    budget = plan.get("budget", {})
    lines = [
        {"line": "essentials", "planned": float(budget.get("essentials", 0))},
        {"line": "lifestyle", "planned": float(budget.get("lifestyle", 0))},
    ]
    planned = pd.DataFrame(lines)
    table = planned.merge(actual, on="line", how="outer").fillna(0)
    table["avg_monthly"] = table["avg_monthly"].round(2)
    table["delta"] = (table["avg_monthly"] - table["planned"]).round(2)
    table["pct_of_plan"] = table.apply(
        lambda r: round(100 * r["avg_monthly"] / r["planned"], 1) if r["planned"] else None,
        axis=1,
    )
    return table.sort_values("line").reset_index(drop=True)
