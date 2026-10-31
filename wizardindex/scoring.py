"""Turn per-benchmark results into dimension scores and one weighted index.

1. Per benchmark, keep each model's best configuration (highest score across effort levels).
2. Rescale every benchmark the same way: the leader scores 100, the median of the models that
   can be ranked scores 50, the weakest model on the board 0, linear in between. This puts
   benchmarks with very different raw scales (ARC-AGI-3 at ~1%, Elo ratings around 1,300) on
   one footing, and keeps saturated boards, where everyone scores 90%+, from making every
   frontier model look alike. `kind: cost` benchmarks (dollars, cheaper is better) are instead
   placed between the dearest and cheapest on a square-root scale.
3. A dimension score is the mean of its benchmarks' normalized scores the model has.
4. The index is the weighted mean over every dimension that has data. Where a model has no
   result for a dimension, it is estimated. If a relative (same product line or variant group in
   config/families.yaml) was measured there, the closest one by release date is the starting
   point: the relative's percentile on that dimension, shifted by how far apart the two are on
   the dimensions both were measured on. Otherwise it comes from how the model stands on the
   dimensions it does have: across current models measured on both, a line is fitted from the
   average percentile on those dimensions to the percentile on the missing one, so the estimate
   leans toward the median exactly as much as skill areas fail to predict each other. With too
   few such models, its average percentile is read off the missing dimension's distribution and
   pulled halfway toward that dimension's median. Dimensions marked `skill: false` (price) are
   estimated the same way but never used to estimate anything else. `coverage` is the share of weight actually
   measured; models below `ranking.min_measured` are listed but not ranked. Dimensions with
   no data at all are left out of the weights. Models below
   `ranking.min_dimensions`, with no `ranking.required_any` coding dimension, or released more
   than `ranking.max_age_days` ago are listed but not ranked.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date

from .models import display_names


def best_per_model(results: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for r in results:
        if r["model"] not in best or r["score"] > best[r["model"]]["score"]:
            best[r["model"]] = r
    return best


def build_index(
    config: dict,
    results_by_bench: dict[str, list[dict]],
    today: date | None = None,
    known_releases: dict[str, str] | None = None,
    families: dict | None = None,
) -> dict:
    dims = config["dimensions"]
    total_weight = sum(d["weight"] for d in dims)
    ranking = config.get("ranking", {})
    min_dims = ranking.get("min_dimensions", 2)
    required_any = set(ranking.get("required_any", []))
    max_age = ranking.get("max_age_days")
    today = today or date.today()

    # Release dates first: each benchmark is scaled against the models that can be ranked.
    releases: dict[str, list[str]] = defaultdict(list)
    for m, day in (known_releases or {}).items():
        releases[m].append(day)
    for results in results_by_bench.values():
        for r in results:
            if r.get("release_date"):
                releases[r["model"]].append(r["release_date"])
    released_on = {m: min(days) for m, days in releases.items()}
    is_old = lambda m: bool(max_age and m in released_on and (today - date.fromisoformat(released_on[m])).days > max_age)

    bench_best: dict[str, dict[str, dict]] = {
        b["id"]: best_per_model(results_by_bench.get(b["id"], [])) for d in dims for b in d["benchmarks"]
    }
    # The models that can be ranked, judged on what they were tested on (not how they scored).
    tested = defaultdict(set)
    for d in dims:
        for b in d["benchmarks"]:
            for m in bench_best[b["id"]]:
                tested[m].add(d["id"])
    live_ids = {k for m, ks in tested.items() if not is_old(m) for k in ks}
    live_w = sum(d["weight"] for d in dims if d["id"] in live_ids) or 1
    pool = {
        m for m, ks in tested.items()
        if not is_old(m) and len(ks) >= min_dims and (not required_any or required_any & ks)
        and 100 * sum(d["weight"] for d in dims if d["id"] in ks) / live_w >= ranking.get("min_measured", 50)
    }
    normalized: dict[str, dict[str, float]] = {}
    cost_range: dict[str, tuple[float, float]] = {}
    for d in dims:
        for b in d["benchmarks"]:
            best = bench_best[b["id"]]
            if b.get("kind") == "cost":
                # Cheaper is better: place each model between the dearest (0) and the cheapest (100)
                # on a square-root scale. A log scale would spend most of the range on gaps between
                # very cheap models ($86 vs $521) that matter far less than $500 vs $5,000.
                roots = [math.sqrt(r["score"]) for r in best.values() if r["score"] > 0]
                cost_range[b["id"]] = (min(roots, default=0), max(roots, default=0))
                normalized[b["id"]] = _cost_scale({m: r["score"] for m, r in best.items()}, *cost_range[b["id"]])
                continue
            normalized[b["id"]] = _scale({m: r["score"] for m, r in best.items()}, pool)
    # A fallback benchmark (e.g. a third party's re-run of a leaderboard) is scaled against its own
    # full field, then kept only for models the primary benchmark hasn't covered. A fallback cost
    # is first converted to the primary's dollars, so every model's price sits on one scale.
    for d in dims:
        for b in d["benchmarks"]:
            primary = b.get("fallback_for")
            if primary:
                covered = bench_best.get(primary, {}).keys()
                if b.get("kind") == "cost" and primary in cost_range:
                    as_primary = _cost_converter(bench_best[b["id"]], bench_best[primary])
                    if as_primary:
                        normalized[b["id"]] = _cost_scale(
                            {m: as_primary(r["score"]) for m, r in bench_best[b["id"]].items()}, *cost_range[primary]
                        )
                bench_best[b["id"]] = {m: r for m, r in bench_best[b["id"]].items() if m not in covered}
                normalized[b["id"]] = {m: v for m, v in normalized[b["id"]].items() if m not in covered}

    models = sorted({m for best in bench_best.values() for m in best})
    names = _display_names(results_by_bench)
    per_model = {}
    for m in models:
        dim_scores = {}
        for d in dims:
            vals = [normalized[b["id"]][m] for b in d["benchmarks"] if m in normalized[b["id"]]]
            if vals:
                dim_scores[d["id"]] = sum(vals) / len(vals)
        released = released_on.get(m)
        outdated = is_old(m)
        per_model[m] = (dim_scores, released, outdated)

    # Distribution of each dimension over current models: the yardstick for estimating gaps.
    field = {}
    for d in dims:
        vals = sorted(ds[d["id"]] for ds, _, old in per_model.values() if d["id"] in ds and not old)
        if vals:
            field[d["id"]] = vals
    medians = {k: _quantile(v, 0.5) for k, v in field.items()}
    live = [d for d in dims if d["id"] in field]
    live_weight = sum(d["weight"] for d in live)
    min_measured = ranking.get("min_measured", 50)
    relatives = _relatives(models, families)
    # Only skills predict other skills; price says nothing about how well a model codes.
    skills = {d["id"] for d in live if d.get("skill", True)}

    rows = []
    for m, (dim_scores, released, outdated) in per_model.items():
        standing = [_percentile(field[k], v) for k, v in dim_scores.items() if k in skills]
        pct = sum(standing) / len(standing) if standing else 0.5
        estimated, estimated_from = {}, {}
        for d in live:
            if d["id"] in dim_scores:
                continue
            kin = _from_relative(m, d["id"], per_model, field, relatives, skills)
            if kin:
                estimated[d["id"]], estimated_from[d["id"]] = kin
                continue
            fit = _from_skills(m, d["id"], per_model, field, skills)
            estimated[d["id"]] = fit if fit is not None else (_quantile(field[d["id"]], pct) + medians[d["id"]]) / 2
        filled = {**estimated, **dim_scores}
        score = sum(filled[d["id"]] * d["weight"] for d in live) / live_weight
        weight = sum(d["weight"] for d in live if d["id"] in dim_scores)
        coverage = round(100 * weight / live_weight)
        raw = {
            bid: {k: best[m][k] for k in ("score", "ci", "effort", "model_raw", "notes", "list_price", "plan") if k in best[m]}
            for bid, best in bench_best.items() if m in best
        }
        orgs = [r["org"] for r in raw_records(bench_best, m) if r.get("org")]
        rows.append({
            "model": m,
            "name": names.get(m, m),
            "org": Counter(o.lower() for o in orgs).most_common(1)[0][0] if orgs else None,
            "released": released,
            "outdated": outdated,
            "index": round(score, 1),
            "coverage": coverage,
            "ranked": (
                not outdated
                and coverage >= min_measured
                and len(dim_scores) >= min_dims
                and (not required_any or bool(required_any & dim_scores.keys()))
            ),
            "dimensions": {k: round(v, 1) for k, v in dim_scores.items()},
            "estimated": {k: round(v, 1) for k, v in estimated.items()},
            "estimated_from": {k: names.get(r, r) for k, r in estimated_from.items()},
            "benchmarks": raw,
        })

    rows.sort(key=lambda r: (not r["ranked"], -r["index"]))
    rank = 0
    for r in rows:
        if r["ranked"]:
            rank += 1
            r["rank"] = rank
    return {"models": rows, "medians": {k: round(v, 1) for k, v in medians.items()}}


def _cost_scale(costs: dict[str, float], lo: float, hi: float) -> dict[str, float]:
    """Dollars to 0-100: the dearest (square root `hi`) 0, the cheapest (`lo`) 100, clipped."""
    if hi <= lo:
        return {}
    return {m: min(100.0, max(0.0, 100 * (hi - math.sqrt(c)) / (hi - lo))) for m, c in costs.items() if c > 0}


def _cost_converter(fallback: dict[str, dict], primary: dict[str, dict]):
    """A fit from one cost benchmark's dollars to another's, over models priced on both.

    Costs of running different evaluation suites scale together across models (a model that burns
    tokens on one burns them on the other), so log(primary) is fitted as a line in log(fallback).
    Returns the conversion, or None with fewer than 8 models in common.
    """
    pairs = [
        (math.log(fallback[m]["score"]), math.log(primary[m]["score"]))
        for m in fallback.keys() & primary.keys()
        if fallback[m]["score"] > 0 and primary[m]["score"] > 0
    ]
    if len(pairs) < 8:
        return None
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    var = sum((x - mx) ** 2 for x, _ in pairs)
    slope = sum((x - mx) * (y - my) for x, y in pairs) / var if var else 1.0
    return lambda c: math.exp(my + slope * (math.log(c) - mx)) if c > 0 else 0.0


def _scale(scores: dict[str, float], pool: set[str]) -> dict[str, float]:
    """Weakest model on the board 0, the median rankable model 50, the leader 100, linear between.

    Anchoring the middle on the models that compete for the ranking, not on every model a board
    lists (often dozens of small ones), is what separates the frontier from the middle of the pack.
    It works the same for percentages and Elo-style ratings, since it never relies on a true zero.
    """
    if not scores:
        return {}
    lo, top = min(scores.values()), max(scores.values())
    field = sorted(v for m, v in scores.items() if m in pool)
    mid = _quantile(field, 0.5) if len(field) >= 3 else _quantile(sorted(scores.values()), 0.5)

    def place(v: float) -> float:
        if v >= mid:
            return 50 + 50 * (v - mid) / (top - mid) if top > mid else 100.0
        return 50 * (v - lo) / (mid - lo) if mid > lo else 0.0

    return {m: place(v) for m, v in scores.items()}


def _relatives(models: list[str], families: dict | None) -> dict[str, set[str]]:
    """Each model's relatives: the rest of its product line or variant group (config/families.yaml)."""
    import re

    groups = []
    for f in (families or {}).get("families", []):
        match, exclude = re.compile(f["match"]), re.compile(f["exclude"]) if f.get("exclude") else None
        groups.append({m for m in models if match.search(m) and not (exclude and exclude.search(m))})
    groups += [set(g) for g in (families or {}).get("variants", [])]
    kin: dict[str, set[str]] = defaultdict(set)
    for g in groups:
        for m in g:
            kin[m] |= g - {m}
    return kin


def _from_relative(model, dim, per_model, field, relatives, skills):
    """Estimate `dim` from the relative closest in release date that was measured on it.

    For a skill, the relative's percentile on `dim` is shifted by the average percentile gap
    between the two on the skills both were measured on (at least two), then read off the field.
    For a dimension that isn't a skill (price), the relative's percentile is taken as is: being
    better at things doesn't make a model cheaper. Returns (score, relative) or None.
    """
    mine, released, _ = per_model[model]
    best = None
    for r in relatives.get(model, ()):
        if r not in per_model:
            continue
        theirs, their_release, _ = per_model[r]
        shared = [k for k in mine if k in theirs and k in skills]
        if dim not in theirs or len(shared) < 2:
            continue
        gap = (
            abs((date.fromisoformat(released) - date.fromisoformat(their_release)).days)
            if released and their_release else 10_000
        )
        key = (gap, -len(shared), r)
        if best is None or key < best[0]:
            best = (key, r, theirs, shared)
    if not best:
        return None
    _, r, theirs, shared = best
    shift = sum(_percentile(field[k], mine[k]) - _percentile(field[k], theirs[k]) for k in shared) / len(shared)
    if dim not in skills:
        shift = 0.0
    pct = min(1.0, max(0.0, _percentile(field[dim], theirs[dim]) + shift))
    return _quantile(field[dim], pct), r


def _from_skills(model, dim, per_model, field, skills, min_peers=8):
    """Estimate `dim` from the model's skills, as far as they actually predict it.

    Among current models measured on `dim` and on every skill this model has, fit a line from
    their average percentile on those skills to their percentile on `dim`, then read this
    model's average through it. How strongly skills go together sets how far the estimate leans
    toward the median. Returns a score, or None with fewer than `min_peers` such models.
    """
    mine = [k for k in per_model[model][0] if k in skills and k != dim]
    if not mine:
        return None
    avg = lambda ds: sum(_percentile(field[k], ds[k]) for k in mine) / len(mine)
    peers = [
        (avg(ds), _percentile(field[dim], ds[dim]))
        for p, (ds, _, old) in per_model.items()
        if p != model and not old and dim in ds and all(k in ds for k in mine)
    ]
    if len(peers) < min_peers:
        return None
    mx = sum(x for x, _ in peers) / len(peers)
    my = sum(y for _, y in peers) / len(peers)
    var = sum((x - mx) ** 2 for x, _ in peers)
    slope = sum((x - mx) * (y - my) for x, y in peers) / var if var else 0.0
    pct = min(1.0, max(0.0, my + slope * (avg(per_model[model][0]) - mx)))
    return _quantile(field[dim], pct)


def _percentile(sorted_vals: list[float], v: float) -> float:
    """Share of the field below v, counting ties as half."""
    below = sum(x < v for x in sorted_vals)
    ties = sum(x == v for x in sorted_vals)
    return (below + ties / 2) / len(sorted_vals)


def _quantile(sorted_vals: list[float], q: float) -> float:
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def raw_records(bench_best: dict[str, dict[str, dict]], model: str):
    return [best[model] for best in bench_best.values() if model in best]


def _display_names(results_by_bench: dict[str, list[dict]]) -> dict[str, str]:
    """Most common leaderboard spelling of each model, minus effort labels; aliases.yaml wins."""
    import re

    seen: dict[str, Counter] = defaultdict(Counter)
    for results in results_by_bench.values():
        for r in results:
            name = re.sub(r"\s*[\[(].*?[\])]", "", r["model_raw"]).split("/")[-1]
            name = re.sub(r"\s+-\s+.*$", "", name)
            name = re.sub(r"[-\s](minimal|low|medium|high|xhigh|max)$", "", name, flags=re.I)
            seen[r["model"]][name.strip()] += 1
    def pretty(item):
        name, count = item
        return (name != name.lower(), " " in name, count)

    names = {m: max(c.items(), key=pretty)[0] for m, c in seen.items()}
    names.update(display_names())
    return names
