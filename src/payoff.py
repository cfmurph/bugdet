"""Line-of-credit / loan payoff math.

Simple monthly-compounding amortization. ``payoff`` simulates month by month
(edge-case correct on the final partial payment); ``payment_for_months`` is the
closed-form inverse for "I want it gone in N months".
"""
from __future__ import annotations

import pandas as pd


def payoff(balance: float, apr: float, monthly_payment: float) -> dict | None:
    """Return months, total interest, and total paid for a fixed monthly payment.

    ``apr`` is a percentage (e.g. 5.95). Returns None if the payment is too small
    to ever clear the balance (i.e. it doesn't cover the monthly interest).
    """
    r = apr / 100 / 12
    if monthly_payment <= balance * r:
        return None
    bal, interest, months = balance, 0.0, 0
    while bal > 0:
        charge = bal * r
        interest += charge
        bal += charge - monthly_payment
        months += 1
    return {
        "monthly_payment": round(monthly_payment, 2),
        "months": months,
        "years": round(months / 12, 1),
        "total_interest": round(interest, 2),
        "total_paid": round(balance + interest, 2),
    }


def payment_for_months(balance: float, apr: float, months: int) -> float:
    """Monthly payment needed to clear ``balance`` in exactly ``months`` months."""
    r = apr / 100 / 12
    if r == 0:
        return round(balance / months, 2)
    return round(balance * r / (1 - (1 + r) ** -months), 2)


def compare(balance: float, apr: float, payments: list[float]) -> pd.DataFrame:
    """Payoff table across several candidate monthly payments."""
    rows = [payoff(balance, apr, p) for p in payments]
    return pd.DataFrame([r for r in rows if r]).set_index("monthly_payment")


def avalanche(debts: list[dict], monthly_budget: float) -> dict:
    """Fastest multi-debt payoff for a fixed total monthly budget.

    ``debts``: list of {"name", "balance", "apr"}. Each month interest accrues on
    every debt, then the whole budget is applied highest-APR-first (the avalanche
    method, which minimizes total interest and time). Returns total months/interest
    and the month each debt is cleared. Returns months=None if the budget can't
    cover total monthly interest (debt would never shrink).
    """
    bal = {d["name"]: float(d["balance"]) for d in debts}
    rate = {d["name"]: d["apr"] / 100 / 12 for d in debts}
    order = sorted(bal, key=lambda n: rate[n], reverse=True)

    if monthly_budget <= sum(bal[n] * rate[n] for n in order):
        return {"months": None, "reason": "budget below total monthly interest"}

    interest, months, cleared = 0.0, 0, {}
    while any(b > 0.005 for b in bal.values()) and months < 1200:
        months += 1
        for n in order:
            charge = bal[n] * rate[n]
            interest += charge
            bal[n] += charge
        remaining = monthly_budget
        for n in order:
            if bal[n] <= 0:
                continue
            pay = min(remaining, bal[n])
            bal[n] -= pay
            remaining -= pay
            if bal[n] <= 0.005 and n not in cleared:
                cleared[n] = months
            if remaining <= 0:
                break
    total = sum(d["balance"] for d in debts)
    return {
        "months": months,
        "years": round(months / 12, 1),
        "total_interest": round(interest, 2),
        "total_paid": round(total + interest, 2),
        "cleared_month": cleared,
    }


if __name__ == "__main__":
    # Runnable self-check: a known amortization case.
    res = payoff(1000, 12, 100)  # 1% / month
    assert res["months"] == 11, res
    assert abs(payment_for_months(1000, 12, 11) - 96.45) < 0.5
    assert payoff(10000, 5.95, 40) is None  # below interest-only (~$49.58/mo)
    print("payoff self-check OK:", res)
