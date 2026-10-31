"""Command line: `fetch` pulls leaderboards into data/results/, `build` writes site/data/index.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import checks, pages, sources, subsidies
from .flair import add_flair
from .scoring import build_index

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "index.yaml"
RESULTS_DIR = ROOT / "data" / "results"
SITE_DATA = ROOT / "site" / "data" / "index.json"
DESCRIPTIONS = ROOT / "data" / "descriptions.yaml"
RELEASES = ROOT / "data" / "release_dates.json"
HISTORY_DATA = ROOT / "site" / "data" / "history.json"
FAMILIES = ROOT / "config" / "families.yaml"
SUBSCRIPTIONS = ROOT / "data" / "subscriptions.yaml"
TASKS = ROOT / "config" / "tasks.yaml"
PREVIOUS = ROOT / "data" / "previous_ranks.json"
TOOLS = ROOT / "data" / "tools.yaml"
SITE = ROOT / "site"


def load_config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def load_descriptions() -> dict:
    """Hand-researched summaries of what users say about each model (data/descriptions.yaml)."""
    if not DESCRIPTIONS.exists():
        return {"models": {}}
    doc = yaml.safe_load(DESCRIPTIONS.read_text(encoding="utf-8")) or {}
    return {"as_of": str(doc.get("as_of") or ""), "models": doc.get("models") or {}}


def benchmarks(config: dict):
    for d in config["dimensions"]:
        for b in d["benchmarks"]:
            yield d, b


def save_previous_ranks() -> None:
    """Keep the ranks as last published, so the next build can show how each model moved."""
    if not SITE_DATA.exists():
        return
    index = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    ranks = {m["model"]: m["rank"] for m in index["models"] if m.get("rank")}
    PREVIOUS.write_text(json.dumps({"generated_at": index.get("generated_at"), "ranks": ranks}, indent=1) + "\n", encoding="utf-8")


def cmd_fetch(args) -> int:
    config = load_config()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not args.only:
        save_previous_ranks()
    failed = []
    for _, b in benchmarks(config):
        if args.only and b["id"] not in args.only:
            continue
        try:
            results, meta = sources.get(b["source"]).fetch(b)
        except Exception:
            # Keep the previous snapshot: one broken leaderboard must not wipe its data.
            failed.append(b["id"])
            print(f"[fail] {b['id']}", file=sys.stderr)
            traceback.print_exc()
            continue
        if not results and b["source"] == "manual":
            print(f"[skip] {b['id']}: {meta.get('status', 'no results')}")
            continue
        doc = {
            "benchmark": b["id"],
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "meta": meta,
            "results": [r.to_dict() for r in results],
        }
        (RESULTS_DIR / f"{b['id']}.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"[ok]   {b['id']}: {len(results)} results")
    if not args.only:
        try:
            dates = sources.get("epoch").release_dates()
            RELEASES.write_text(json.dumps(dict(sorted(dates.items())), indent=1) + "\n", encoding="utf-8")
            print(f"[ok]   release dates: {len(dates)} models")
        except Exception:
            failed.append("release-dates")
            traceback.print_exc()
    return 1 if failed and args.strict else 0


def cmd_build(args) -> int:
    config = load_config()
    snapshots = {}
    for _, b in benchmarks(config):
        path = RESULTS_DIR / f"{b['id']}.json"
        snapshots[b["id"]] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    known = json.loads(RELEASES.read_text(encoding="utf-8")) if RELEASES.exists() else {}
    families = yaml.safe_load(FAMILIES.read_text(encoding="utf-8"))
    results = {k: (v or {}).get("results", []) for k, v in snapshots.items()}
    # Costs are what the work costs the cheapest way to pay for it: a subscription, where one is subsidised.
    rates = subsidies.load(SUBSCRIPTIONS)
    for _, b in benchmarks(config):
        if b.get("kind") == "cost":
            results[b["id"]] = subsidies.apply(results[b["id"]], rates)
    index = build_index(config, results, known_releases=known, families=families)
    index["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    shares, errors = index.pop("shares"), index.pop("estimate_errors")
    index["dimensions"] = [
        {
            "id": d["id"],
            "name": d["name"],
            "weight": d["weight"],
            # Percent of the index this dimension actually carries (None until it has data), and how
            # far its estimates typically miss when checked against measured models.
            "share": shares.get(d["id"]),
            "estimate_error": errors.get(d["id"]),
            "skill": d.get("skill", True),
            "benchmarks": [
                {
                    "id": b["id"],
                    "name": b["name"],
                    "kind": b.get("kind"),
                    "url": b.get("url"),
                    "source": b["source"],
                    "fetched_at": (snapshots[b["id"]] or {}).get("fetched_at"),
                    "meta": (snapshots[b["id"]] or {}).get("meta", {}),
                    "n_results": len((snapshots[b["id"]] or {}).get("results", [])),
                }
                for b in d["benchmarks"]
            ],
        }
        for d in config["dimensions"]
    ]
    index["ranking"] = config.get("ranking", {})
    if PREVIOUS.exists():
        index["previous"] = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    # Benchmarks published by two parties, compared; disagreements are noted on the results themselves.
    index["checks"] = checks.cross_check(config, results)
    checks.annotate(index, index["checks"])
    # Jobs and bars for the "Which model for my job?" picker.
    index["tasks"] = yaml.safe_load(TASKS.read_text(encoding="utf-8")) if TASKS.exists() else {}
    about = load_descriptions()
    for m in index["models"]:
        if m["model"] in about["models"]:
            m["about"] = {**about["models"][m["model"]], "as_of": about.get("as_of")}
    add_flair(index)
    # Each model's product line (config/families.yaml), so the site can tell a newer version from an older one.
    for f in families.get("families", []):
        match, exclude = re.compile(f["match"]), re.compile(f["exclude"]) if f.get("exclude") else None
        for m in index["models"]:
            if "line" not in m and match.search(m["model"]) and not (exclude and exclude.search(m["model"])):
                m["line"] = f["name"]
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    ranked = [m for m in index["models"] if m.get("ranked")]
    print(f"wrote {SITE_DATA.relative_to(ROOT)}: {len(ranked)} ranked / {len(index['models'])} models")
    for m in ranked[: args.top]:
        dims = " ".join(f"{k}={v:.0f}" for k, v in m["dimensions"].items())
        print(f"  {m['rank']:>2}. {m['name']:<28} {m['title']:<32} {m['index']:5.1f}  cov {m['coverage']:>3}%  {dims}")

    history = build_history(index)
    HISTORY_DATA.write_text(json.dumps(history, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {HISTORY_DATA.relative_to(ROOT)}: "
          + ", ".join(f"{f['name']} ({len(f['generations'])})" for f in history["families"]))

    pages.write_tools(yaml.safe_load(TOOLS.read_text(encoding="utf-8")), SITE / "tools.html")
    (SITE / "sitemap.xml").write_text(pages.sitemap(SITE, index["generated_at"]), encoding="utf-8")
    print("wrote site/tools.html and site/sitemap.xml")
    return 0


def build_history(index: dict) -> dict:
    """Group dated models into product lines (config/families.yaml), oldest generation first."""
    import re

    fam_cfg = yaml.safe_load(FAMILIES.read_text(encoding="utf-8"))
    tracked = fam_cfg.get("tracked_benchmarks", [])
    names = {b["id"]: b["name"] for d in index["dimensions"] for b in d["benchmarks"]}
    families = []
    for f in fam_cfg["families"]:
        match, exclude = re.compile(f["match"]), re.compile(f["exclude"]) if f.get("exclude") else None
        gens = [
            {
                "model": m["model"],
                "name": m["name"],
                "org": m["org"],
                "title": m["title"],
                "pixels": m["pixels"],
                "released": m["released"],
                "index": m["index"],
                "coverage": m["coverage"],
                "ranked": m["ranked"],
                "scores": {b: m["benchmarks"][b]["score"] for b in tracked if b in m["benchmarks"]},
            }
            for m in index["models"]
            if m["released"] and match.search(m["model"]) and not (exclude and exclude.search(m["model"]))
        ]
        if len(gens) >= 2:
            families.append({"name": f["name"], "maker": f["maker"],
                             "generations": sorted(gens, key=lambda g: (g["released"], g["name"]))})
    return {
        "generated_at": index["generated_at"],
        "tracked": [{"id": b, "name": names.get(b, b)} for b in tracked],
        "min_measured_to_chart": fam_cfg.get("min_measured_to_chart", 40),
        "families": families,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wizardindex")
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="pull leaderboards into data/results/")
    f.add_argument("--only", nargs="*", help="benchmark ids to fetch")
    f.add_argument("--strict", action="store_true", help="exit non-zero if any source fails")
    f.set_defaults(func=cmd_fetch)
    b = sub.add_parser("build", help="compute the index into site/data/index.json")
    b.add_argument("--top", type=int, default=15, help="rows to print")
    b.set_defaults(func=cmd_build)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
