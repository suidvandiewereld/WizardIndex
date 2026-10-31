"""Cosmetic extras for the site: a wizard title and a unique pixel icon for every model.

Models listed in data/flair.yaml get a hand-written title; everyone else gets a generated one.

Generated titles come from the numbers. The rank word follows the index score, and the domain is the
skill where the model stands highest among current models (by percentile, so a 40 on a hard
skill can beat an 85 on an easy one). Ranked models get distinct titles: on a clash, the
tier's other words are tried, then the next strongest skill.

Icons are abstract 8x8 pixel patterns seeded from the model id: a quarter, half or rotated
half of the grid is drawn at random and the rest follows by symmetry. Each pixel is empty (0),
the maker's color (1), a dark shade of it (2) or gold (3). Icons are assigned oldest model
first and re-rolled on a clash, so every model's icon is unique and a newcomer never changes
an existing one.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

import yaml

FLAIR = Path(__file__).resolve().parent.parent / "data" / "flair.yaml"

RANKS = [
    (90, ["Archmage", "Grand Wizard"]),
    (80, ["Sorcerer", "Enchanter"]),
    (70, ["Wizard", "Warlock"]),
    (60, ["Magus", "Thaumaturge"]),
    (50, ["Conjurer", "Illusionist", "Diviner"]),
    (40, ["Apprentice", "Acolyte", "Novice"]),
]
LOWEST = ["Hedge Wizard", "Charlatan", "Street Magician"]
DOMAINS = {
    "swe": "of the Codebase",
    "taste": "of Fair Design",
    "agentic": "of the Terminal",
    "reasoning": "of Riddles",
    "adaptability": "of the Unknown",
    "reliability": "of Plain Truth",
    "spatial": "of Solid Forms",
    "creativity": "of Invention",
    "architecture": "of Foundations",
    "cleanliness": "of Tidy Code",
    "instructions": "of the Letter",
}

SIZE = 8


def add_flair(index: dict) -> None:
    models = index["models"]
    custom = _custom()
    current = [m for m in models if not m["outdated"]]
    field = {}
    for m in current:
        for k, v in m["dimensions"].items():
            field.setdefault(k, []).append(v)

    taken = set(custom.values())
    for m in models:  # already in rank order
        if m["model"] in custom:
            m["title"] = custom[m["model"]]
        else:
            m["title"] = _title(m, field, taken if m["ranked"] else None)

    seen: set[str] = set()
    for m in sorted(models, key=lambda m: (m["released"] or "9999", m["model"])):
        m["pixels"] = _pixels(m["model"], seen)


def _custom() -> dict[str, str]:
    """Hand-written titles by model id."""
    if not FLAIR.exists():
        return {}
    return (yaml.safe_load(FLAIR.read_text(encoding="utf-8")) or {}).get("titles") or {}


def _title(m: dict, field: dict, taken: set[str] | None) -> str:
    if m["outdated"]:
        words = ["Wizard Emeritus"]
    elif not m["ranked"]:
        words = ["Initiate"]
    else:
        words = next((w for floor, w in RANKS if m["index"] >= floor), LOWEST)
    standing = sorted(
        ((sum(x < v for x in field.get(k, [])) / max(len(field.get(k, [])), 1), k) for k, v in m["dimensions"].items()),
        reverse=True,
    )
    options = [f"{w} {DOMAINS.get(k, '')}".strip() for _, k in standing for w in words] or words[:1]
    if taken is None:
        return options[0]
    title = next((t for t in options if t not in taken), options[0])
    taken.add(title)
    return title


def _pixels(model: str, seen: set[str]) -> str:
    """The icon as 64 digits, row by row (see the module docstring)."""
    half = SIZE // 2
    for attempt in range(1000):
        rng = random.Random(hashlib.sha256(f"{model}:{attempt}".encode()).digest())
        symmetry = rng.choice(["mirror", "quad", "turn"])
        density, gold = rng.uniform(0.4, 0.6), rng.uniform(0.08, 0.2)
        grid = [[0] * SIZE for _ in range(SIZE)]
        for y in range(SIZE):
            for x in range(SIZE):
                if symmetry == "mirror" and x >= half or symmetry == "quad" and (x >= half or y >= half)                         or symmetry == "turn" and y >= half:
                    continue
                r = rng.random()
                grid[y][x] = 0 if r > density else 3 if r < density * gold else 1 if r < density * 0.7 else 2
        for y in range(SIZE):
            for x in range(SIZE):
                if symmetry == "mirror" and x >= half:
                    grid[y][x] = grid[y][SIZE - 1 - x]
                elif symmetry == "quad" and (x >= half or y >= half):
                    grid[y][x] = grid[min(y, SIZE - 1 - y)][min(x, SIZE - 1 - x)]
                elif symmetry == "turn" and y >= half:
                    grid[y][x] = grid[SIZE - 1 - y][SIZE - 1 - x]
        code = "".join(str(v) for row in grid for v in row)
        if code.count("0") > SIZE * SIZE * 0.7 or code in seen:
            continue
        seen.add(code)
        return code
    raise ValueError(f"no free icon for {model}")
