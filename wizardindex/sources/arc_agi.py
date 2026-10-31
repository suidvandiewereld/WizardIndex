"""ARC Prize leaderboard: the site serves its model and evaluation tables as static JSON."""

from .. import http
from ..models import Result, canonical, effort

MODELS = "https://arcprize.org/media/data/models.json"
EVALUATIONS = "https://arcprize.org/media/data/evaluations.json"


def fetch(bench: dict):
    models = {m["id"]: m for m in http.json(MODELS)}
    results = []
    for ev in http.json(EVALUATIONS):
        if ev.get("datasetId") != bench["dataset"] or not ev.get("display", True):
            continue
        m = models.get(ev["modelId"])
        if not m or m.get("providerId") == "Human" or m.get("modelType") is None:
            continue  # human panels and hand-built systems aren't models
        name = m["displayName"]
        release = (m.get("modelReleaseDate") or "")[:10] or None
        notes = [m["notes"]] if m.get("notes") else []
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(name),
            model_raw=name,
            score=round(ev["score"] * 100, 3),
            effort=effort(name),
            org=m.get("providerId"),
            release_date=release,
            notes=notes,
        ))
    return results, {"url": "https://arcprize.org/leaderboard", "dataset": bench["dataset"]}
