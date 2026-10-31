import json

import pytest

from wizardindex.sources import _nextjs, artificial_analysis as aa, manual


def record(slug, label=None, level=None, reasoning=True, **fields):
    effort = {"slug": label, "label": label, "level": level} if label else None
    return {"id": slug, "slug": slug, "name": slug, "intelligenceIndex": 50, "effort": effort, "isReasoning": reasoning,
            "releaseDate": "2026-10-01", "creator": {"name": "Lab"}, **fields}


@pytest.fixture
def records(monkeypatch):
    recs = {
        # AA's default slug has no effort suffix: here it is the max setting.
        "model-x": record("model-x", "max", 60, hle=0.60, intelligenceIndexCost={"total": 900.0}),
        "model-x-xhigh": record("model-x-xhigh", "xhigh", 50, hle=0.55, intelligenceIndexCost={"total": 400.0}),
        "model-x-low": record("model-x-low", "low", 20, hle=0.40, intelligenceIndexCost={"total": 50.0}),
        "model-y": record("model-y", hle=0.30, intelligenceIndexCost=120.0),
        "model-y-non-reasoning": record("model-y-non-reasoning", reasoning=False, hle=0.20, intelligenceIndexCost=10.0),
    }
    monkeypatch.setattr(aa, "_records", lambda: recs)
    return recs


def test_scan_finds_model_records_in_a_payload():
    payload = 'noise{"id":"a","slug":"model-a","intelligenceIndex":40,"hle":0.5}more{"id":"b","other":1}'
    assert list(aa._scan(payload)) == ["model-a"]


def test_flight_payload_joins_next_chunks():
    html = '<script>self.__next_f.push([1,"{\\"a\\":"])</script><script>self.__next_f.push([1,"1}"])</script>'
    assert json.loads(_nextjs.flight_payload(html)) == {"a": 1}


def test_skill_results_carry_aas_own_effort_label(records):
    results, _ = aa.fetch({"id": "aa-hle", "field": "hle"})
    by_raw = {r.model_raw: r for r in results}
    assert by_raw["model-x"].effort == "max"          # slug alone would say nothing
    assert by_raw["model-x-xhigh"].effort == "xhigh"
    assert {r.model for r in results} == {"model-x", "model-y"}


def test_price_is_taken_at_the_top_setting(records):
    results, _ = aa.fetch({"id": "aa-cost", "cost": "intelligenceIndexCost"})
    price = {r.model: r for r in results}
    assert price["model-x"].score == 900.0 and price["model-x"].effort == "max"
    # Non-reasoning variants only count when nothing else was tested.
    assert price["model-y"].score == 120.0


def test_price_setting_falls_back_to_non_reasoning_when_alone():
    only = [record("m-nr", reasoning=False)]
    assert aa._price_setting(only) is only[0]


def test_manual_results_are_read_from_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "MANUAL_DIR", tmp_path)
    (tmp_path / "ifbench.yaml").write_text(
        "source: https://example.org/table\nretrieved: 2026-10-31\n"
        "results:\n  - model: Claude Opus 5.5 [max]\n    score: 61.5\n    ci: 2.1\n",
        encoding="utf-8",
    )
    results, meta = manual.fetch({"id": "ifbench", "url": "https://example.org"})
    assert meta["url"] == "https://example.org/table"
    [r] = results
    assert (r.model, r.score, r.ci, r.effort) == ("opus-5-5", 61.5, 2.1, "max")


def test_manual_benchmark_without_a_file_reports_no_data(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "MANUAL_DIR", tmp_path)
    results, meta = manual.fetch({"id": "oodeval", "url": "https://example.org"})
    assert results == [] and meta["status"] == "no data transcribed yet"
