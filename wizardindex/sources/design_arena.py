"""Design Arena: blind side-by-side human votes on what models build (websites, UI, charts...).

Ratings are Bradley-Terry (Elo-style), so the benchmark should be configured `kind: rating`.
Config keys:
    category:     Design Arena category id (website, uicomponent, dataviz, 3d, gamedev, ...)
    min_battles:  ignore models with fewer votes than this; small samples swing wildly (default 200)
"""

import requests

from ..http import HEADERS, TIMEOUT
from ..models import Result, canonical, effort

API = "https://www.designarena.ai/api/leaderboard"


def fetch(bench: dict):
    resp = requests.post(
        API,
        json={"arenaType": "models", "category": bench["category"]},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise ValueError(f"Design Arena: {body.get('message')}")

    min_battles = bench.get("min_battles", 200)
    results = []
    for m in body["data"]:
        if m["battles"] < min_battles:
            continue
        se = m.get("btStdErr")
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(m["modelId"]),
            model_raw=m["modelId"],
            score=float(m["elo"]),
            ci=round(1.96 * se, 1) if se else None,
            effort=effort(m["modelId"]),
            notes=[f"{m['battles']} blind votes, {m['winRate']}% win rate"],
        ))
    meta = {
        "url": f"https://www.designarena.ai/leaderboard/{bench['category']}",
        "category": bench["category"],
        "updated": body.get("metadata", {}).get("lastUpdateTime"),
        "total_votes": body.get("metadata", {}).get("totalVotes"),
    }
    return results, meta
