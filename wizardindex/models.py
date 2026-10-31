"""Result records and model-name canonicalization.

Every leaderboard spells model names differently ("Opus 5 [high]", "claude-opus-5",
"anthropic/claude-opus-5", "Claude Opus 5 (Max)"). `canonical()` collapses them to one id
("opus-5") and `effort()` pulls out the reasoning-effort label. Anything the rules get wrong
is fixed in data/aliases.yaml rather than by adding special cases here.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max", "promax", "none", "thinking", "default", "unknown"}
VENDORS = {
    "anthropic", "openai", "google", "xai", "x", "ai", "zhipu", "zai", "z", "deepseek-ai",
    "moonshot", "moonshotai", "meta", "mistral", "mistralai", "xiaomi", "alibaba", "claude",
}
SETTINGS = {"adaptive", "reasoning", "effort"}
TIERS = {"opus", "sonnet", "haiku"}
EFFORT_RE = re.compile(r"[\[(]\s*([a-z]+)\s*[\])]|(?:^|[\s_-])(" + "|".join(EFFORTS) + r")\s*$", re.I)

ALIASES_PATH = Path(__file__).resolve().parent.parent / "data" / "aliases.yaml"


@dataclass
class Result:
    benchmark: str
    model: str            # canonical id
    model_raw: str        # name exactly as the leaderboard shows it
    score: float          # 0-100, higher is better
    ci: float | None = None          # 95% half-width or ±SEM, in score points, when published
    effort: str | None = None
    org: str | None = None
    release_date: str | None = None  # YYYY-MM-DD
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def effort(name: str) -> str | None:
    m = EFFORT_RE.search(name.strip())
    if not m:
        return None
    label = (m.group(1) or m.group(2)).lower()
    return label if label in EFFORTS else None


def canonical(name: str) -> str:
    s = name.lower().split("/")[-1]
    s = re.sub(r"[\[(].*?[\])]", " ", s)          # bracketed effort / variant labels
    s = re.sub(r"\s+-\s+.*$", "", s)                 # "Model - Provider Adapter"
    s = re.sub(r"\d{4}-\d{2}-\d{2}", " ", s)         # dated snapshots
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = s.replace("non-reasoning", "none")           # a reasoning setting, not a separate model
    s = re.sub(r"\bv(\d+)p(\d+)\b", r"v\1-\2", s)    # "v3p2" -> "v3-2"
    aliases = _aliases()
    if s in aliases:
        return aliases[s]
    parts = s.split("-")
    while len(parts) > 1 and parts[0] in VENDORS:
        parts.pop(0)
    # Settings, not models: efforts, thinking budgets ("32k"), full-date API snapshots ("20250805").
    while len(parts) > 1 and (parts[-1] in EFFORTS | SETTINGS or re.fullmatch(r"\d+k|20\d{6}", parts[-1])):
        parts.pop()
    # "Claude 4.1 Opus" -> "opus-4-1"
    if len(parts) > 1 and parts[-1] in TIERS and all(p.isdigit() for p in parts[:-1]):
        parts = [parts[-1], *parts[:-1]]
    # MMDD suffixes ("v4.1-flash-1017") are kept: labs use them for distinct, re-released models.
    s = "-".join(parts)
    return aliases.get(s, s)


_alias_cache: dict[str, str] | None = None


def _aliases() -> dict[str, str]:
    global _alias_cache
    if _alias_cache is None:
        data = yaml.safe_load(ALIASES_PATH.read_text(encoding="utf-8")) if ALIASES_PATH.exists() else None
        _alias_cache = (data or {}).get("aliases", {}) or {}
    return _alias_cache


def display_names() -> dict[str, str]:
    data = yaml.safe_load(ALIASES_PATH.read_text(encoding="utf-8")) if ALIASES_PATH.exists() else None
    return (data or {}).get("display", {}) or {}
