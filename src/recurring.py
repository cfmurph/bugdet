"""Detect likely recurring charges from transaction history."""
from __future__ import annotations

import re

import pandas as pd

_MERCHANT_RE = re.compile(r"\d{2,}")


def normalize_merchant(description: str) -> str:
    """Collapse noisy descriptions to a stable merchant key."""
    text = str(description).lower().strip()
    text = _MERCHANT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:60] or "unknown"


def detect_recurring(
    df: pd.DataFrame,
    *,
    min_count: int = 3,
    min_interval_days: int = 20,
    max_interval_days: int = 40,
    amount_tolerance: float = 0.20,
) -> pd.DataFrame:
    """Return merchants that look like monthly (or regular) bills.

    Groups outflows by normalized description, checks count and median
    day-gap between charges, and flags amounts that stay within tolerance.
    """
    charges = df[df["amount"] < 0].copy()
    if charges.empty:
        return pd.DataFrame(
            columns=["merchant", "count", "avg_amount", "median_days", "last_date", "sample"]
        )

    charges["merchant"] = charges["description"].map(normalize_merchant)
    charges = charges.sort_values("date")

    rows = []
    for merchant, grp in charges.groupby("merchant"):
        if len(grp) < min_count:
            continue
        amounts = -grp["amount"]
        med = amounts.median()
        if med <= 0:
            continue
        spread = (amounts.max() - amounts.min()) / med
        if spread > amount_tolerance:
            continue

        gaps = grp["date"].sort_values().diff().dt.days.dropna()
        if gaps.empty:
            continue
        median_gap = gaps.median()
        if not (min_interval_days <= median_gap <= max_interval_days):
            continue

        rows.append({
            "merchant": merchant,
            "count": len(grp),
            "avg_amount": round(amounts.mean(), 2),
            "median_days": int(median_gap),
            "last_date": grp["date"].max().date(),
            "sample": grp["description"].iloc[-1][:50],
        })

    if not rows:
        return pd.DataFrame(
            columns=["merchant", "count", "avg_amount", "median_days", "last_date", "sample"]
        )
    return pd.DataFrame(rows).sort_values("avg_amount", ascending=False).reset_index(drop=True)
