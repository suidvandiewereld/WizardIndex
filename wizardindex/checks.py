"""Cross-checks: where two parties publish the same benchmark, do their numbers agree?

Nothing is re-run here. A benchmark with `check_against: <id>` in config/index.yaml is compared,
model by model, with another published run of the same test (e.g. Artificial Analysis's own run
of Terminal-Bench against the official leaderboard). Two harnesses usually differ by a steady
offset, so a model is flagged only when its gap strays from the typical (median) gap by more than
`tolerance` points: a sign that one of the two numbers depends on something the other run didn't
share, like a much weaker agent, or is simply wrong.
"""

from __future__ import annotations

from statistics import median

from .scoring import best_per_model

TOLERANCE = 10   # points beyond the typical gap before a model is flagged
MIN_SHARED = 5   # fewer models in common than this and there is no typical gap to speak of


def cross_check(config: dict, results_by_bench: dict[str, list[dict]]) -> list[dict]:
    names = {b["id"]: b["name"] for d in config["dimensions"] for b in d["benchmarks"]}
    checks = []
    for d in config["dimensions"]:
        for b in d["benchmarks"]:
            other = b.get("check_against")
            if not other:
                continue
            mine = best_per_model(results_by_bench.get(b["id"], []))
            theirs = best_per_model(results_by_bench.get(other, []))
            shared = sorted(mine.keys() & theirs.keys())
            check = {"benchmark": b["id"], "against": other, "against_name": names.get(other, other),
                     "shared": len(shared), "tolerance": b.get("tolerance", TOLERANCE)}
            if len(shared) >= MIN_SHARED:
                gaps = {m: mine[m]["score"] - theirs[m]["score"] for m in shared}
                offset = median(gaps.values())
                check["offset"] = round(offset, 1)
                # The typical model's distance from that gap; a median, so the outliers being flagged don't inflate it.
                check["spread"] = round(median(abs(g - offset) for g in gaps.values()), 1)
                check["flagged"] = [
                    {"model": m, "score": mine[m]["score"], "other": theirs[m]["score"], "beyond": round(gaps[m] - offset, 1)}
                    for m in shared if abs(gaps[m] - offset) > check["tolerance"]
                ]
            checks.append(check)
    return checks


def annotate(index: dict, checks: list[dict]) -> None:
    """Note each flagged disagreement on both results it involves, so the receipts show it."""
    names = {b["id"]: b["name"] for d in index["dimensions"] for b in d["benchmarks"]}
    rows = {m["model"]: m for m in index["models"]}
    for c in checks:
        for f in c.get("flagged", []):
            row = rows.get(f["model"])
            if not row:
                continue
            for bench, other, mine, theirs in ((c["benchmark"], c["against"], f["score"], f["other"]),
                                               (c["against"], c["benchmark"], f["other"], f["score"])):
                result = row["benchmarks"].get(bench)
                if result is None:
                    continue
                result["notes"] = [*result.get("notes", []), (
                    f"disagrees with {names.get(other, other)} ({theirs:.1f} there vs {mine:.1f} here), "
                    f"{abs(f['beyond']):.0f} points beyond the usual gap between the two runs; check both before trusting either"
                )]
