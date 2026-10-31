"""Epoch AI benchmarking hub: one CC-BY zip of CSVs, either Epoch's own runs or results it
collects from each benchmark's official leaderboard (the `Source` column says which).

Benchmark config keys:
    file:    CSV name inside the zip
    column:  score column
    scale:   multiply scores by this (100 for 0-1 fractions; default 100)
    stderr:  optional standard-error column, reported as a 95% half-width
"""

import csv
import io
import zipfile
from functools import lru_cache

from .. import http
from ..models import Result, canonical, effort

ZIP_URL = "https://epoch.ai/data/benchmark_data.zip"
CREDIT = "Epoch AI, 'Capabilities & benchmarking', https://epoch.ai/benchmarks (CC BY 4.0)"


@lru_cache(maxsize=1)
def _archive() -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(http.get(ZIP_URL).content))


def _rows(name: str) -> list[dict]:
    with _archive().open(name) as fh:
        return list(csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8")))


def release_dates() -> dict[str, str]:
    """Earliest known release date per canonical model id, from Epoch's model list.

    Covers models that so far only appear on leaderboards without dates (e.g. Design Arena).
    """
    dates: dict[str, str] = {}
    for row in _rows("model_metadata.csv"):
        version, day = row.get("model_version") or "", row.get("date") or ""
        if version and day:
            m = canonical(version.replace("_", " "))
            dates[m] = min(dates.get(m, day), day)
    return dates


def _float(value: str | None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch(bench: dict):
    scale = bench.get("scale", 100)
    results = []
    for row in _rows(bench["file"]):
        score = _float(row.get(bench["column"]))
        version = row.get("Model version") or ""
        if score is None or not version:
            continue
        se = _float(row.get(bench["stderr"])) if bench.get("stderr") else None
        upstream = row.get("Source") or "Epoch AI evaluation"
        notes = [f"via Epoch AI; source: {upstream}"]
        if row.get("Harness") or row.get("Agent"):
            notes.append(f"harness: {row.get('Harness') or row.get('Agent')}")
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(version.replace("_", " ")),
            model_raw=row.get("Name") or version,
            score=round(score * scale, 3),
            ci=round(1.96 * se * scale, 2) if se else None,
            effort=effort(version.replace("_", " ")) or (row.get("Reasoning effort") or None),
            org=row.get("Organization") or None,
            release_date=row.get("Release date") or None,
            notes=notes,
        ))
    return results, {"url": bench.get("url"), "via": "https://epoch.ai/benchmarks", "credit": CREDIT}
