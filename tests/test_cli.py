import json

from wizardindex import cli


def test_previous_ranks_keep_the_published_ranking(tmp_path, monkeypatch):
    site, previous = tmp_path / "index.json", tmp_path / "previous_ranks.json"
    site.write_text(json.dumps({"generated_at": "2026-10-29T10:42:40+00:00", "models": [
        {"model": "opus-5-5", "rank": 1}, {"model": "gpt-6-astra", "rank": 2}, {"model": "old-1", "ranked": False},
    ]}), encoding="utf-8")
    monkeypatch.setattr(cli, "SITE_DATA", site)
    monkeypatch.setattr(cli, "PREVIOUS", previous)
    cli.save_previous_ranks()
    assert json.loads(previous.read_text(encoding="utf-8")) == {
        "generated_at": "2026-10-29T10:42:40+00:00", "ranks": {"opus-5-5": 1, "gpt-6-astra": 2},
    }


def test_previous_ranks_need_a_published_ranking(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SITE_DATA", tmp_path / "missing.json")
    monkeypatch.setattr(cli, "PREVIOUS", tmp_path / "previous_ranks.json")
    cli.save_previous_ranks()
    assert not (tmp_path / "previous_ranks.json").exists()
