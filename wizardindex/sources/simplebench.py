"""SimpleBench: private trick questions on everyday spatial, temporal and social reasoning.

The leaderboard ships as a JavaScript array (static/js/leaderboard-data.js); human rows are skipped.
"""

import re

from .. import http
from ..models import Result, canonical

URL = "https://simple-bench.com/"
DATA = "https://simple-bench.com/static/js/leaderboard-data.js"
ROW = re.compile(r'model:\s*"([^"]+)",\s*score:\s*"([\d.]+)%",\s*organization:\s*"([^"]*)",\s*dateAdded:\s*(?:"([\d-]+)"|null)')


def fetch(bench: dict):
    results = []
    for name, score, org, added in ROW.findall(http.text(DATA)):
        if not org:   # "Human Baseline*", "Highest Human Score*"
            continue
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(name),
            model_raw=name,
            score=float(score),
            org=org,
            notes=[f"added to the leaderboard {added}" if added else "average of 5 runs"],
        ))
    if not results:
        raise ValueError("SimpleBench leaderboard rows not found; data file layout may have changed")
    return results, {"url": URL, "data": DATA}
