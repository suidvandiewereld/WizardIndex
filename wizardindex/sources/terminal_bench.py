"""Terminal-Bench: official submissions are JSON files in the harbor-framework/terminal-bench repo."""

from .. import http
from ..models import Result, canonical

REPO = "harbor-framework/terminal-bench"
LISTING = f"https://api.github.com/repos/{REPO}/contents/leaderboard/submissions"
DEFINITION = f"https://raw.githubusercontent.com/{REPO}/main/leaderboard/leaderboard.yaml"


def fetch(bench: dict):
    import yaml

    definition = yaml.safe_load(http.text(DEFINITION))
    files = [f for f in http.json(LISTING) if f["name"].endswith(".json")]

    results = []
    for f in files:
        sub = http.json(f["download_url"])
        md, metrics, src = sub["metadata"], sub["metrics"], sub.get("source_filter", {})
        raw = src.get("model_name") or md["model_display"]["label"]
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(raw),
            model_raw=raw,
            score=metrics["accuracy"],
            ci=metrics.get("accuracy_ci95_half_width"),
            effort=md.get("reasoning_effort") or src.get("reasoning_effort"),
            org=md.get("model_org", {}).get("label"),
            release_date=md.get("release_date"),
            notes=[f"agent: {md['agent_display']['label']}", f"trials: {metrics.get('n_trials')}"],
        ))
    meta = {
        "url": "https://www.tbench.ai",
        "version": definition.get("title"),
        "submissions": f"https://github.com/{REPO}/tree/main/leaderboard/submissions",
    }
    return results, meta
