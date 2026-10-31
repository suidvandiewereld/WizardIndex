"""Results transcribed by hand from papers or leaderboards that offer no machine-readable data.

File format (data/manual/<benchmark id>.yaml):

    source: https://link-to-the-table-you-copied-from
    retrieved: 2026-10-28
    results:
      - model: Claude Opus 5 [max]
        score: 61.5          # 0-100
        ci: 2.1              # optional
"""

from pathlib import Path

import yaml

from ..models import Result, canonical, effort

MANUAL_DIR = Path(__file__).resolve().parents[2] / "data" / "manual"


def fetch(bench: dict):
    path = MANUAL_DIR / f"{bench['id']}.yaml"
    if not path.exists():
        return [], {"url": bench.get("url"), "status": "no data transcribed yet"}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    results = [
        Result(
            benchmark=bench["id"],
            model=canonical(r["model"]),
            model_raw=r["model"],
            score=float(r["score"]),
            ci=r.get("ci"),
            effort=r.get("effort") or effort(r["model"]),
            release_date=r.get("release_date"),
            notes=["transcribed manually"],
        )
        for r in doc.get("results") or []
    ]
    return results, {"url": doc.get("source") or bench.get("url"), "retrieved": doc.get("retrieved")}
