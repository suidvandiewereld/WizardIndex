"""Subscription subsidies: what a model's work costs when paid for through a plan, not the API.

data/subscriptions.yaml lists, per plan, how many dollars of API usage a month of it buys for
each model. A model's rate is that per subscription dollar, on the plan that buys the most of it.
Its effective cost is the API cost divided by that rate, when that beats paying for the API.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def load(path: Path) -> dict[str, dict]:
    """Model id -> {rate, plan, promo, estimated_from} on the plan that buys the most of it.

    That is the plan a heavy user buys; a cheaper plan's slightly better rate is no use when its
    allowance runs out a quarter of the way through the work.
    """
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    best: dict[str, dict] = {}
    for fam in data.get("families", []):
        for plan in fam.get("plans", []):
            for model, value in plan.get("values", {}).items():
                if model not in best or value > best[model]["value"]:
                    best[model] = {"rate": value / plan["price"], "value": value, "plan": plan["name"], "promo": bool(plan.get("promo"))}
        for model, like in (fam.get("also_serves") or {}).items():
            if model not in best and like in best:
                best[model] = {**best[like], "estimated_from": like}
    return best


def apply(results: list[dict], rates: dict[str, dict]) -> list[dict]:
    """Cost results with each subsidised model's score replaced by its effective cost."""
    out = []
    for r in results:
        sub = rates.get(r["model"])
        if not sub or sub["rate"] <= 1:
            out.append(r)
            continue
        effective = r["score"] / sub["rate"]
        note = (
            f"${r['score']:,.0f} at API prices; on {sub['plan']} a dollar buys ${sub['rate']:.1f} of API usage, "
            f"so ${effective:,.0f} effectively"
        )
        if sub.get("estimated_from"):
            note += f" (rate assumed equal to {sub['estimated_from']}, which was measured on the same plans)"
        if sub["promo"]:
            note += " (measured with promotional limits on; may overstate the usual allowance)"
        out.append({**r, "score": round(effective, 2), "list_price": r["score"], "plan": sub["plan"], "notes": [*r.get("notes", []), note]})
    return out
