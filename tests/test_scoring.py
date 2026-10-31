import random
from datetime import date

import pytest

from wizardindex import scoring
from wizardindex.scoring import build_index


def result(model, score, **kw):
    return {"model": model, "model_raw": model, "score": score, **kw}


def config(**ranking):
    return {
        "ranking": {"min_dimensions": 2, "required_any": ["swe"], "min_measured": 50, **ranking},
        "dimensions": [
            {"id": "swe", "weight": 50, "benchmarks": [{"id": "s1"}]},
            {"id": "reasoning", "weight": 30, "benchmarks": [{"id": "r1"}]},
            {"id": "taste", "weight": 20, "benchmarks": [{"id": "t1"}]},
            {"id": "cleanliness", "weight": 10, "benchmarks": [{"id": "c1"}]},   # never has data
        ],
    }


def field(n=12, skip_taste=("m5",)):
    """n models whose skills rise together, m0 weakest; `skip_taste` models were never tested on taste."""
    models = [f"m{i}" for i in range(n)]
    return {
        "s1": [result(m, 10 + 5 * i) for i, m in enumerate(models)],
        "r1": [result(m, 20 + 4 * i) for i, m in enumerate(models)],
        "t1": [result(m, 1000 + 30 * i) for i, m in enumerate(models) if m not in skip_taste],
    }


def rows(index):
    return {r["model"]: r for r in index["models"]}


def test_scale_anchors_weakest_median_and_leader():
    scaled = scoring._scale({"a": 0, "b": 5, "c": 10, "d": 20}, pool={"a", "b", "c", "d"})
    assert scaled["a"] == 0 and scaled["d"] == 100
    assert scaled["b"] == pytest.approx(50 * 5 / 7.5)        # median of the pool is 7.5
    assert scaled["c"] == pytest.approx(50 + 50 * 2.5 / 12.5)


def test_cost_scale_cheapest_wins_on_a_square_root_scale():
    scaled = scoring._cost_scale({"cheap": 1, "mid": 25, "dear": 100}, lo=1, hi=10)
    assert scaled == pytest.approx({"cheap": 100, "mid": 100 * 5 / 9, "dear": 0})


def test_percentile_matches_the_linear_definition():
    rng = random.Random(7)
    vals = sorted(rng.choice(range(20)) for _ in range(200))
    for v in range(-1, 22):
        slow = (sum(x < v for x in vals) + sum(x == v for x in vals) / 2) / len(vals)
        assert scoring._percentile(vals, v) == pytest.approx(slow)


def test_ranking_order_and_scale():
    out = rows(build_index(config(), field(), today=date(2026, 10, 31)))
    assert out["m11"]["rank"] == 1 and out["m11"]["index"] == pytest.approx(100)
    assert out["m0"]["index"] == pytest.approx(0)
    ranks = [out[f"m{i}"]["rank"] for i in range(11, -1, -1)]
    assert ranks == sorted(ranks)


def test_shares_only_count_dimensions_with_data():
    index = build_index(config(), field(), today=date(2026, 10, 31))
    assert set(index["shares"]) == {"swe", "reasoning", "taste"}
    assert sum(index["shares"].values()) == pytest.approx(100, abs=0.2)
    assert index["shares"]["swe"] == pytest.approx(50)


def test_untested_dimension_is_estimated_with_a_margin():
    index = build_index(config(), field(), today=date(2026, 10, 31))
    out = rows(index)
    gap = out["m5"]
    assert "taste" not in gap["dimensions"] and "taste" in gap["estimated"]
    assert gap["coverage"] == 80
    # The margin is the dimension's backtested error, weighted by its share of the index.
    assert gap["margin"] == pytest.approx(index["estimate_errors"]["taste"] * 20 / 100, abs=0.1)
    assert out["m6"]["margin"] == 0


def test_rank_range_spans_the_rank_and_widens_with_estimates():
    out = rows(build_index(config(), field(), today=date(2026, 10, 31)))
    for r in out.values():
        lo, hi = r["rank_range"]
        assert lo <= r["rank"] <= hi
    assert out["m11"]["rank_range"] == [1, 1]


def test_estimate_errors_reward_skills_that_predict_each_other():
    agree = build_index(config(), field(), today=date(2026, 10, 31))["estimate_errors"]["taste"]
    scrambled = field()
    rng = random.Random(3)
    scores = [r["score"] for r in scrambled["t1"]]
    rng.shuffle(scores)
    scrambled["t1"] = [{**r, "score": s} for r, s in zip(scrambled["t1"], scores)]
    disagree = build_index(config(), scrambled, today=date(2026, 10, 31))["estimate_errors"]["taste"]
    assert agree < disagree


def test_outdated_models_are_listed_but_not_ranked():
    data = field()
    data["s1"] = [{**r, "release_date": "2025-01-01"} if r["model"] == "m11" else r for r in data["s1"]]
    out = rows(build_index(config(max_age_days=120), data, today=date(2026, 10, 31)))
    assert out["m11"]["outdated"] and not out["m11"]["ranked"] and "rank" not in out["m11"]
    assert out["m10"]["rank"] == 1


def test_fallback_only_counts_for_models_missing_from_the_primary():
    cfg = config()
    cfg["dimensions"][0]["benchmarks"].append({"id": "s2", "fallback_for": "s1"})
    data = field()
    data["s1"] = [r for r in data["s1"] if r["model"] != "m3"]
    data["s2"] = [result(m, 50) for m in ("m3", "m4")]
    out = rows(build_index(cfg, data, today=date(2026, 10, 31)))
    assert "s2" in out["m3"]["benchmarks"] and "s1" not in out["m3"]["benchmarks"]
    assert "s2" not in out["m4"]["benchmarks"]


def test_cheaper_is_better_on_cost_benchmarks():
    cfg = config()
    cfg["dimensions"].append({"id": "price", "weight": 10, "skill": False, "benchmarks": [{"id": "p1", "kind": "cost"}]})
    data = field()
    data["p1"] = [result("m0", 4), result("m11", 400), result("m6", 100)]
    out = rows(build_index(cfg, data, today=date(2026, 10, 31)))
    assert out["m0"]["dimensions"]["price"] == 100 and out["m11"]["dimensions"]["price"] == 0
    assert 0 < out["m6"]["dimensions"]["price"] < 100
