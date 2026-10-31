"""DeepSWE (Datacurve): the leaderboard table is server-rendered, so we read it from the HTML."""

import html as htmllib
import re

from .. import http
from ..models import Result, canonical

URL = "https://deepswe.datacurve.ai/"
ROW = re.compile(r"([a-z][a-z0-9.\-]+) \[ ([a-z]+) \] (\d+(?:\.\d+)?) % ± (\d+(?:\.\d+)?) %")
UPDATED = re.compile(r"(\d+) tasks · updated ([A-Z][a-z]+ \d{1,2}, \d{4})")


def _visible_text(page: str) -> str:
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", page)))


def fetch(bench: dict):
    text = _visible_text(http.text(URL))
    results, seen = [], set()
    for name, eff, score, ci in ROW.findall(text):
        if name in seen:
            continue  # the table repeats each row in a mobile layout
        seen.add(name)
        results.append(Result(
            benchmark=bench["id"],
            model=canonical(name),
            model_raw=f"{name} [{eff}]",
            score=float(score),
            ci=float(ci),
            effort=eff,
            notes=["agent: mini-swe-agent", "best effort level shown on leaderboard"],
        ))
    if not results:
        raise ValueError("DeepSWE leaderboard rows not found; page layout may have changed")
    meta = {"url": URL}
    if m := UPDATED.search(text):
        meta.update(tasks=int(m.group(1)), updated=m.group(2))
    return results, meta
