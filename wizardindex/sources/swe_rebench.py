"""SWE-rebench (Nebius): fresh GitHub tasks collected in rolling time windows.

The page embeds every model's resolved rate for every task window. All models must be compared
on the same window, so we use the newest window and, among windows ending then, the one that
covers the most models. Models released after the window opened are flagged: they could have
seen those tasks' upstream fixes during training.
"""

from collections import Counter
from datetime import date, datetime, timezone

from .. import http
from ..models import Result, canonical, effort
from ._nextjs import extract_json, flight_payload

URL = "https://swe-rebench.com"


def _day(ms: str | int) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()


def _pick_window(items: list[dict]) -> str:
    counts = Counter(
        key
        for it in items
        if it["meta"].get("instance_type") == "model"
        for key, stats in it["rangeStats"]["all"].items()
        if stats.get("resolvedRate")
    )
    latest_end = max(int(k.split(":")[1]) for k in counts)
    ending = [k for k in counts if int(k.split(":")[1]) == latest_end]
    # Most models first; on a tie prefer the longer window (more tasks, less noise).
    return max(ending, key=lambda k: (counts[k], -int(k.split(":")[0])))


def fetch(bench: dict):
    items = extract_json(flight_payload(http.text(URL)), "items")
    window = _pick_window(items)
    start, end = (_day(x) for x in window.split(":"))

    results = []
    for it in items:
        if it["meta"].get("instance_type") != "model":
            continue  # products like Cursor / Claude Code are agents, not models
        stats = it["rangeStats"]["all"].get(window)
        if not stats or not stats.get("resolvedRate"):
            continue
        release = (it.get("release") or {}).get("date")
        notes = []
        if release and date.fromisoformat(release) > date.fromisoformat(start):
            notes.append(f"released {release}, after task window opened {start}: contamination possible")
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(it["modelName"]),
            model_raw=it["modelName"],
            score=round(stats["resolvedRate"], 2),
            ci=round(1.96 * stats["sem"], 2) if stats.get("sem") else None,
            effort=effort(it["modelName"]),
            org=it["meta"].get("developer"),
            release_date=release,
            notes=notes,
        ))
    meta = {"url": URL, "task_window": {"from": start, "to": end}}
    return results, meta
