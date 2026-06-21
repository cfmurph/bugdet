"""Integrated budget + debt planning.

Ties take-home income, living expenses, emergency-fund savings, and multi-debt
avalanche payoff into one simulation. Supports phased budgets (e.g. a temporary
lifestyle cut) and one-time lump payments (bonuses).
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import yaml

_PLAN_PATH = Path(__file__).resolve().parent.parent / "config" / "plan.yaml"


def load_plan(path: str | Path | None = None) -> dict:
    """Load a plan config YAML (copy from ``config/plan.example.yaml``)."""
    path = Path(path) if path else _PLAN_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — copy config/plan.example.yaml to config/plan.yaml"
        )
    return yaml.safe_load(path.read_text()) or {}


def surplus(take_home: float, essentials: float, lifestyle: float, emergency: float) -> float:
    """Cash left for debt after fixed budget lines."""
    return round(take_home - essentials - lifestyle - emergency, 2)


def take_home_at(plan: dict, month: int) -> float:
    """Take-home pay for plan month index (0 = first month).

    Uses ``income.phases`` when present, otherwise ``income.monthly_take_home``.
    The last phase without ``months`` applies for all remaining months.
    """
    income = plan.get("income", {})
    phases = income.get("phases")
    if not phases:
        return float(income["monthly_take_home"])

    idx = 0
    for i, phase in enumerate(phases):
        th = float(phase["monthly_take_home"])
        if "months" not in phase:
            return th
        n = int(phase["months"])
        if month < idx + n:
            return th
        idx += n
    return float(phases[-1]["monthly_take_home"])


def _budget_phase_for_month(plan: dict, scenario: dict, month: int) -> dict:
    """Lifestyle/EF overrides for a given plan month."""
    phases = scenario.get("phases")
    if not phases:
        return scenario
    idx = 0
    for phase in phases:
        n = int(phase["months"])
        if month < idx + n:
            return phase
        idx += n
    return plan["budget"]


def _debt_budget_for_phase(
    plan: dict,
    phase: dict,
    take_home: float | None = None,
) -> float:
    income = take_home if take_home is not None else float(plan["income"]["monthly_take_home"])
    essentials = float(plan["budget"]["essentials"])
    lifestyle = float(phase.get("lifestyle", plan["budget"]["lifestyle"]))
    ef = float(phase.get("emergency_fund", plan["budget"]["emergency_fund"]))
    return surplus(income, essentials, lifestyle, ef)


def build_monthly_budgets(plan: dict, scenario: dict, max_months: int = 360) -> list[float]:
    """Debt payment budget for each month (respects income + lifestyle phases)."""
    return [
        _debt_budget_for_phase(
            plan,
            _budget_phase_for_month(plan, scenario, m),
            take_home_at(plan, m),
        )
        for m in range(max_months)
    ]


def simulate_avalanche(
    debts: list[dict],
    monthly_budget: float | list[float],
    *,
    months_max: int = 360,
    lump_payments: dict[int, float] | None = None,
    tail_budget: float | None = None,
) -> pd.DataFrame:
    """Month-by-month avalanche simulation.

    ``monthly_budget`` is a fixed float or a list indexed by month (0 = first month).
    After the list ends, ``tail_budget`` applies (defaults to the list's last value).
    ``lump_payments`` maps month index → extra one-time payment (e.g. bonus).
    """
    bal = {d["name"]: float(d["balance"]) for d in debts}
    rate = {d["name"]: d["apr"] / 100 / 12 for d in debts}
    order = sorted(bal, key=lambda n: rate[n], reverse=True)
    lumps = lump_payments or {}

    rows = []
    month = 0
    cleared: dict[str, int] = {}

    while any(b > 0.005 for b in bal.values()) and month < months_max:
        if isinstance(monthly_budget, list):
            if month < len(monthly_budget):
                budget = monthly_budget[month]
            elif tail_budget is not None:
                budget = tail_budget
            else:
                budget = monthly_budget[-1]
        else:
            budget = monthly_budget
        budget += lumps.get(month, 0)

        interest = 0.0
        for n in order:
            charge = bal[n] * rate[n]
            interest += charge
            bal[n] += charge

        remaining = budget
        paid = {n: 0.0 for n in order}
        for n in order:
            if bal[n] <= 0:
                continue
            p = min(remaining, bal[n])
            bal[n] -= p
            paid[n] += p
            remaining -= p
            if bal[n] <= 0.005 and n not in cleared:
                cleared[n] = month + 1
            if remaining <= 0:
                break

        rows.append({
            "month": month + 1,
            "debt_budget": round(budget - lumps.get(month, 0), 2),
            "lump": round(lumps.get(month, 0), 2),
            "interest": round(interest, 2),
            "total_debt": round(sum(max(b, 0) for b in bal.values()), 2),
            **{f"bal_{n}": round(max(bal[n], 0), 2) for n in order},
            **{f"paid_{n}": round(paid[n], 2) for n in order},
        })
        month += 1

    return pd.DataFrame(rows)


def _summary_from_history(history: pd.DataFrame) -> dict:
    cleared = {}
    for col in history.columns:
        if not col.startswith("bal_"):
            continue
        name = col[4:]
        hits = history.loc[history[col] <= 0.005, "month"]
        if len(hits):
            cleared[name] = int(hits.iloc[0])
    return {
        "months": len(history),
        "years": round(len(history) / 12, 1),
        "total_interest": round(history["interest"].sum(), 2),
        "cleared_month": cleared,
    }


def _min_interest(debts: list[dict]) -> float:
    return sum(float(d["balance"]) * float(d["apr"]) / 100 / 12 for d in debts)


def run_scenario(plan: dict, scenario: dict) -> dict:
    """Run one named scenario from a plan config."""
    debts = deepcopy(plan["debts"])
    ef = plan.get("emergency_fund", {})
    ef_current = float(ef.get("current", 0))
    ef_target = float(ef.get("target", 0))
    ef_monthly = float(scenario.get("emergency_fund", plan["budget"]["emergency_fund"]))

    lumps: dict[int, float] = {}
    bonus = float(plan["income"].get("bonus_net") or 0)
    if bonus > 0:
        bonus_month = int(plan["income"].get("bonus_month", 1)) - 1
        split = scenario.get("bonus_to", plan.get("bonus_to", "debt"))
        if split == "debt":
            lumps[bonus_month] = lumps.get(bonus_month, 0) + bonus
        elif split == "emergency_fund":
            ef_current += bonus
        elif split == "split":
            half = bonus / 2
            lumps[bonus_month] = lumps.get(bonus_month, 0) + half
            ef_current += half

    budgets = build_monthly_budgets(plan, scenario)
    start_budget = budgets[0]
    if start_budget <= _min_interest(debts) and not lumps:
        return {
            "name": scenario["name"],
            "history": pd.DataFrame(),
            "summary": {"months": None, "reason": f"debt budget ${start_budget:.0f}/mo below interest floor"},
            "debt_free_month": None,
            "ef_at_end": ef_current,
            "monthly_debt_start": start_budget,
        }
    history = simulate_avalanche(debts, budgets, lump_payments=lumps)

    # Emergency fund grows each month until target.
    ef_rows = []
    ef_bal = ef_current
    for _ in history.itertuples():
        if ef_bal < ef_target:
            ef_bal = min(ef_bal + ef_monthly, ef_target)
        ef_rows.append(round(ef_bal, 2))
    history["emergency_fund"] = ef_rows

    summary = _summary_from_history(history)

    return {
        "name": scenario["name"],
        "history": history,
        "summary": summary,
        "debt_free_month": len(history),
        "ef_at_end": ef_bal,
        "monthly_debt_start": float(history.iloc[0]["debt_budget"]) if len(history) else 0,
    }


def compare_scenarios(plan: dict) -> pd.DataFrame:
    """Run every scenario in the plan and return a comparison table."""
    rows = []
    for scenario in plan["scenarios"]:
        r = run_scenario(plan, scenario)
        s = r["summary"]
        rows.append({
            "scenario": r["name"],
            "debt/mo (start)": r["monthly_debt_start"],
            "debt-free (mo)": r["debt_free_month"] if r["debt_free_month"] else "—",
            "interest": r["summary"].get("total_interest", "—"),
            "EF at end": r["ef_at_end"],
            "cleared": ", ".join(
                f"{k} mo {v}" for k, v in sorted(s.get("cleared_month", {}).items(), key=lambda x: x[1])
            ) if s.get("cleared_month") else s.get("reason", ""),
        })
    return pd.DataFrame(rows).set_index("scenario")


if __name__ == "__main__":
    example = Path(__file__).resolve().parent.parent / "config" / "plan.example.yaml"
    plan = yaml.safe_load(example.read_text())
    table = compare_scenarios(plan)
    assert len(table) >= 2, table
    assert table.loc["Balanced", "debt-free (mo)"] > 0
    print("planner self-check OK:\n", table.to_string())
