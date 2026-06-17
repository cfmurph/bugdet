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
    "description": ["description", "name", "memo", "payee", "details", "transaction"],
    "amount": ["amount", "amt"],
    "debit": ["debit", "withdrawal", "withdrawals", "money out", "outflow"],
    "credit": ["credit", "deposit", "deposits", "money in", "inflow"],
}


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

    if amount_col is not None:
        out["amount"] = pd.to_numeric(df[amount_col], errors="coerce")
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
