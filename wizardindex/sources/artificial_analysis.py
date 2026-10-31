"""Artificial Analysis: the evaluations they run themselves, one benchmark at a time.

Their Intelligence Index is deliberately never used. Every model page embeds the full table of
per-benchmark results for all models (Next.js payload), so one page gives everything.

Benchmark config keys:
    field:  key in AA's model record (e.g. terminalBench40, frontierCode, hle, omniscience)
    scale:  multiply by this (100 for 0-1 fractions; default 100)
    cost:   instead of a score, the dollar cost AA paid to run its evaluations (e.g.
            intelligenceIndexCost, briefcaseTotalCost), one setting per model: see `_price_setting`
"""

import json
from collections import defaultdict
from functools import lru_cache

from .. import http
from ..models import Result, canonical, effort
from ._nextjs import flight_payload

# Any model page carries every model's data; try a few in case one is retired.
PAGES = [
    "https://artificialanalysis.ai/models/claude-opus-5-5",
    "https://artificialanalysis.ai/models/gpt-6-1-sol",
    "https://artificialanalysis.ai/models/gemini-4-argon",
]
CREDIT = "Artificial Analysis, https://artificialanalysis.ai (their own evaluation runs)"


@lru_cache(maxsize=1)
def _records() -> dict[str, dict]:
    for url in PAGES:
        payload = flight_payload(http.text(url))
        found = _scan(payload)
        if len(found) > 200:
            return found
    raise ValueError("Artificial Analysis: model table not found on any page; layout may have changed")


def _scan(payload: str) -> dict[str, dict]:
    decoder, found, i = json.JSONDecoder(), {}, 0
    while (i := payload.find('{"id":"', i)) >= 0:
        try:
            obj, _ = decoder.raw_decode(payload, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict) and "slug" in obj and "intelligenceIndex" in obj:
            found[obj["slug"]] = obj
        i += 1
    return found


def fetch(bench: dict):
    if bench.get("cost"):
        return _fetch_cost(bench)
    scale = bench.get("scale", 100)
    results = []
    for slug, rec in _records().items():
        value = rec.get(bench["field"])
        if value is None:
            continue
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(slug),
            model_raw=rec.get("name") or slug,
            score=round(value * scale, 3),
            # The default slug carries no effort suffix ("claude-opus-5-5" is max), so AA's own label comes first.
            effort=_setting(rec) or effort(slug.replace("-", " ")),
            org=(rec.get("creator") or {}).get("name") if isinstance(rec.get("creator"), dict) else None,
            release_date=rec.get("releaseDate"),
            notes=["run by Artificial Analysis on their own harness"],
        ))
    return results, {"url": "https://artificialanalysis.ai", "field": bench["field"], "credit": CREDIT}


def _setting(rec: dict) -> str | None:
    """AA's label for the reasoning setting a record was run at ("max", "xhigh", ...), if any."""
    return (rec.get("effort") or {}).get("label")


def _price_setting(records: list[dict]) -> dict:
    """The record a model is priced at: its highest reasoning setting AA tested.

    Skill scores keep each model's best result, which nearly always comes from its top setting, so
    the price is what that setting costs: a score and its price describe the same configuration.
    Non-reasoning variants count only when nothing else was tested.
    """
    level = lambda r: (r.get("effort") or {}).get("level")
    reasoning = [r for r in records if r.get("isReasoning") is not False] or records
    return max(reasoning, key=lambda r: level(r) or 0)


def _fetch_cost(bench: dict):
    by_model: dict[str, list[dict]] = defaultdict(list)
    for slug, rec in _records().items():
        by_model[canonical(slug)].append(rec)
    results = []
    for model, records in by_model.items():
        rec = _price_setting(records)
        value = rec.get(bench["cost"])
        value = value.get("total") if isinstance(value, dict) else value
        if not value or value <= 0:   # untested at this setting (or a bogus $0 run)
            continue
        setting = _setting(rec)
        tested = sorted({_setting(r) or ("non-reasoning" if r.get("isReasoning") is False else "default") for r in records})
        results.append(Result(
            benchmark=bench["id"],
            model=model,
            model_raw=rec.get("name") or rec["slug"],
            score=round(value, 2),
            effort=setting,
            org=(rec.get("creator") or {}).get("name") if isinstance(rec.get("creator"), dict) else None,
            release_date=rec.get("releaseDate"),
            notes=[f"priced at {setting or 'its only reasoning setting'}; AA tested: {', '.join(tested)}"],
        ))
    return results, {"url": "https://artificialanalysis.ai", "cost": bench["cost"], "credit": CREDIT}
