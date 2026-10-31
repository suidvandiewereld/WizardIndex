"""Leaderboard ingestors.

Each module exposes `fetch(bench: dict) -> (list[Result], dict)`: the results, plus metadata
describing exactly what was pulled (version, task window, URLs) so a run can be audited.
"""

from importlib import import_module


def get(source: str):
    return import_module(f"wizardindex.sources.{source}")
