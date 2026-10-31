"""The published site: what GitHub Pages serves, and the data it reads."""

import json
import re
from pathlib import Path

import pytest
import yaml

from wizardindex import pages

SITE = Path(__file__).resolve().parents[1] / "site"


@pytest.mark.parametrize("page", sorted(p.name for p in SITE.glob("*.html")) + sorted(p.name for p in SITE.glob("*.js")))
def test_paths_are_relative(page):
    """Pages serves the site under /WizardIndex/, so a root-relative path ("/data/...") would 404."""
    text = (SITE / page).read_text(encoding="utf-8")
    absolute = re.findall(r'''(?:src|href)\s*=\s*["']/(?!/)[^"']*|fetch\(\s*["'`]/(?!/)''', text)
    assert not absolute, absolute


@pytest.mark.parametrize("page", sorted(p.name for p in SITE.glob("*.html")))
def test_local_references_exist(page):
    text = (SITE / page).read_text(encoding="utf-8")
    for ref in re.findall(r'''(?:src|href)\s*=\s*["']([^"'#?:]+)["']''', text):
        if ref not in ("./",):
            assert (SITE / ref).exists(), ref


TOOLS = yaml.safe_load((SITE.parent / "data" / "tools.yaml").read_text(encoding="utf-8"))
PAGES = sorted(p.name for p in SITE.glob("*.html"))


def test_tools_data_is_complete():
    ids = [s["id"] for s in TOOLS["sections"]]
    assert len(ids) == len(set(ids))
    for s in TOOLS["sections"]:
        assert s["title"] and s["intro"] and s["items"]
        for t in s["items"]:
            assert t["name"] and t["what"] and t["for"]
            assert t["url"].startswith("https://")
            assert t["referral"] == "" or t["referral"].startswith("https://")


def test_tools_page_is_built_from_the_data():
    """Run `wizardindex build` after editing data/tools.yaml; the page must match it."""
    html = (SITE / "tools.html").read_text(encoding="utf-8")
    assert pages.tools_html(TOOLS) in html and pages.tools_toc(TOOLS) in html


def test_referral_links_are_marked():
    tool = {"name": "X", "url": "https://x.example", "referral": "https://x.example/?ref=wi"}
    html = pages.tool_link(tool)
    assert 'href="https://x.example/?ref=wi"' in html and 'rel="sponsored noopener"' in html and ">referral<" in html
    assert 'rel=' not in pages.tool_link({**tool, "referral": ""})


@pytest.mark.parametrize("page", PAGES)
def test_search_and_share_tags(page):
    html = (SITE / page).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)">', html).group(1)
    assert 50 <= len(title) <= 60 and 150 <= len(desc) <= 160
    assert html.count("<h1") == 1
    assert f'<link rel="canonical" href="{pages.page_url(page)}">' in html
    assert f'<meta property="og:url" content="{pages.page_url(page)}">' in html
    assert '<meta property="og:image" content="' + pages.SITE_URL + 'og.png">' in html
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        json.loads(block)


def test_sitemap_lists_every_page():
    sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    assert sorted(re.findall(r"<loc>(.*?)</loc>", sitemap)) == sorted(pages.page_url(p) for p in PAGES)


def test_index_data_has_what_the_page_reads():
    data = json.loads((SITE / "data" / "index.json").read_text(encoding="utf-8"))
    live = [d for d in data["dimensions"] if d["share"] is not None]
    assert live and sum(d["share"] for d in live) == pytest.approx(100, abs=0.5)
    assert all(d["estimate_error"] is not None for d in live)
    ranked = [m for m in data["models"] if m["ranked"]]
    assert [m["rank"] for m in ranked] == list(range(1, len(ranked) + 1))
    for m in ranked:
        assert m["margin"] >= 0
        assert m["rank_range"][0] <= m["rank"] <= m["rank_range"][1]
    assert isinstance(data["checks"], list)
