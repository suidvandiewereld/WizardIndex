import pytest

from wizardindex import checks, subsidies


def test_subsidy_uses_the_plan_that_buys_the_most(tmp_path):
    path = tmp_path / "subs.yaml"
    path.write_text(
        "families:\n"
        "  - name: Lab\n"
        "    also_serves: {small-1: big-1}\n"
        "    plans:\n"
        "      - {name: Plus, price: 20, values: {big-1: 400}}\n"
        "      - {name: Max, price: 200, values: {big-1: 3000}}\n",
        encoding="utf-8",
    )
    rates = subsidies.load(path)
    assert rates["big-1"]["plan"] == "Max" and rates["big-1"]["rate"] == pytest.approx(15)
    assert rates["small-1"]["estimated_from"] == "big-1"


def test_subsidy_divides_cost_only_when_it_beats_the_api():
    rates = {"big-1": {"rate": 10.0, "plan": "Max", "promo": False}, "meh-1": {"rate": 0.8, "plan": "Basic", "promo": False}}
    out = {r["model"]: r for r in subsidies.apply(
        [{"model": "big-1", "score": 500.0}, {"model": "meh-1", "score": 80.0}, {"model": "api-1", "score": 30.0}], rates)}
    assert out["big-1"]["score"] == 50.0 and out["big-1"]["list_price"] == 500.0
    assert out["meh-1"]["score"] == 80.0 and out["api-1"]["score"] == 30.0


CONFIG = {"dimensions": [{"id": "agentic", "benchmarks": [
    {"id": "official", "name": "Official board"},
    {"id": "rerun", "name": "Third-party run", "check_against": "official"},
]}]}


def runs(gaps, base=40.0):
    official = [{"model": m, "model_raw": m, "score": base} for m in gaps]
    rerun = [{"model": m, "model_raw": m, "score": base + g} for m, g in gaps.items()]
    return {"official": official, "rerun": rerun}


def test_cross_check_flags_only_gaps_beyond_the_usual_offset():
    gaps = {"a": -2, "b": -1, "c": -2, "d": -3, "e": -2, "f": 14}
    [c] = checks.cross_check(CONFIG, runs(gaps))
    assert c["shared"] == 6 and c["offset"] == -2
    assert [f["model"] for f in c["flagged"]] == ["f"]
    assert c["flagged"][0]["beyond"] == 16


def test_cross_check_needs_enough_models_in_common():
    [c] = checks.cross_check(CONFIG, runs({"a": 30, "b": 0}))
    assert c["shared"] == 2 and "offset" not in c


def test_annotate_notes_the_disagreement_on_the_result():
    data = runs({"a": -2, "b": -1, "c": -2, "d": -3, "e": -2, "f": 14})
    index = {
        "dimensions": CONFIG["dimensions"],
        "models": [{"model": "f", "benchmarks": {"official": {"score": 40.0, "notes": ["agent: X"]}}}],
    }
    checks.annotate(index, checks.cross_check(CONFIG, data))
    notes = index["models"][0]["benchmarks"]["official"]["notes"]
    assert notes[0] == "agent: X" and notes[1].startswith("disagrees with Third-party run (54.0 there vs 40.0 here)")
