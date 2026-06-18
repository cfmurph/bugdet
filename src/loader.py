"""Load and normalize bank CSV exports into a tidy transactions table.

Every bank formats its CSV differently (column names, date formats, whether
debits are negative or split into separate columns). This module maps the common
variants onto a single, predictable schema:

    date        : datetime64
    description : str
    amount      : float   (negative = money out, positive = money in)
    account     : str     (derived from the source filename)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Map of canonical column name -> list of header aliases we've seen in the wild.
COLUMN_ALIASES = {
    "date": ["date", "transaction date", "posted date", "posting date", "trans date"],
    "description": ["description", "description 1", "name", "memo", "payee", "details", "transaction"],
    "amount": ["amount", "amt", "cad$", "cad", "usd$", "usd"],
    "debit": ["debit", "withdrawal", "withdrawals", "money out", "outflow"],
    "credit": ["credit", "deposit", "deposits", "money in", "inflow"],
}

# RBC-style exports split the amount across CAD$/USD$ and the payee across
# Description 1/Description 2. These get merged in load_transactions.
SECONDARY_AMOUNT = ["usd$", "usd", "cad$", "cad"]
SECONDARY_DESC = ["description 2"]


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    lowered = {c.lower().strip(): c for c in columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def load_transactions(path: str | Path, account: str | None = None) -> pd.DataFrame:
    """Load a single bank CSV (or Excel) export into the canonical schema."""
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    cols = list(df.columns)
    date_col = _find_column(cols, COLUMN_ALIASES["date"])
    desc_col = _find_column(cols, COLUMN_ALIASES["description"])
    amount_col = _find_column(cols, COLUMN_ALIASES["amount"])
    debit_col = _find_column(cols, COLUMN_ALIASES["debit"])
    credit_col = _find_column(cols, COLUMN_ALIASES["credit"])

    if date_col is None or desc_col is None:
        raise ValueError(
            f"{path.name}: could not find date/description columns. "
            f"Found columns: {cols}"
        )

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["description"] = df[desc_col].astype(str).str.strip()

    # RBC splits the payee across Description 1/2 — append the second when present.
    desc2_col = _find_column(cols, SECONDARY_DESC)
    if desc2_col is not None:
        desc2 = df[desc2_col].fillna("").astype(str).str.strip()
        out["description"] = (out["description"] + " " + desc2).str.strip()

    if amount_col is not None:
        out["amount"] = pd.to_numeric(df[amount_col], errors="coerce")
        # Some banks split foreign-currency amounts into a second column with the
        # primary amount blank. Backfill at face value (no FX conversion).
        second_col = _find_column(cols, [a for a in SECONDARY_AMOUNT if a != amount_col.lower()])
        if second_col is not None:
            second = pd.to_numeric(df[second_col], errors="coerce")
            out["amount"] = out["amount"].fillna(second)
    elif debit_col is not None or credit_col is not None:
        debit = pd.to_numeric(df.get(debit_col, 0), errors="coerce").fillna(0)
        credit = pd.to_numeric(df.get(credit_col, 0), errors="coerce").fillna(0)
        # Debits are money out (negative), credits are money in (positive).
        out["amount"] = credit - debit.abs()
    else:
        raise ValueError(
            f"{path.name}: no amount column (or debit/credit pair) found in {cols}"
        )

    out["account"] = account or path.stem
    out = out.dropna(subset=["date", "amount"]).reset_index(drop=True)
    return out


def load_all_raw(raw_dir: str | Path = "data/raw") -> pd.DataFrame:
    """Load and concatenate every CSV/Excel file in ``raw_dir``."""
    raw_dir = Path(raw_dir)
    files = sorted(
        p for p in raw_dir.glob("*")
        if p.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )
    if not files:
        raise FileNotFoundError(
            f"No CSV/Excel files in {raw_dir}/. "
            "Drop your bank exports there (or use data/sample_transactions.csv)."
        )
    frames = [load_transactions(f) for f in files]
    return pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
