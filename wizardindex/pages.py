"""Parts of the site written at build time, so they are in the HTML itself rather than drawn by script.

The Tools page list comes from data/tools.yaml and is written between the `<!-- tools -->` and
`<!-- toc -->` markers in site/tools.html. sitemap.xml lists every page of the site.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

SITE_URL = "https://suidvandiewereld.github.io/WizardIndex/"
# Pages whose content changes with every weekly build; the rest change only when edited by hand.
DATA_PAGES = {"index.html", "history.html", "sources.html"}


def page_url(name: str) -> str:
    return SITE_URL if name == "index.html" else SITE_URL + name


def tool_link(tool: dict) -> str:
    if tool.get("referral"):
        return (f'<a href="{escape(tool["referral"])}" rel="sponsored noopener">{escape(tool["name"])}</a> '
                f'<span class="ref-mark" title="Referral link: we may earn a commission">referral</span>')
    return f'<a href="{escape(tool["url"])}">{escape(tool["name"])}</a>'


def tools_html(data: dict) -> str:
    blocks = []
    for s in data["sections"]:
        rows = "".join(
            f'\n              <tr><td class="skill">{tool_link(t)}</td><td>{escape(t["what"])}</td><td>{escape(t["for"])}</td></tr>'
            for t in s["items"]
        )
        blocks.append(f'''        <div class="qa" id="{escape(s["id"])}">
          <h2>{escape(s["title"])} <a class="permalink" href="#{escape(s["id"])}">link</a></h2>
          <div class="qa-body">
            <p>{escape(s["intro"])}</p>
            <table class="receipts tools">
              <tr><th>Tool</th><th>What it does</th><th>Good for</th></tr>{rows}
            </table>
          </div>
        </div>''')
    return "\n".join(blocks)


def tools_toc(data: dict) -> str:
    return "\n".join(f'            <li><a href="#{escape(s["id"])}">{escape(s["title"])}</a></li>' for s in data["sections"])


def fill(html: str, marker: str, content: str) -> str:
    """Replace whatever sits between `<!-- marker -->` and `<!-- /marker -->` (each on its own line)."""
    start, end = f"<!-- {marker} -->\n", f"<!-- /{marker} -->"
    i = html.index(start) + len(start)
    j = html.rindex("\n", 0, html.index(end)) + 1
    return html[:i] + content + "\n" + html[j:]


def write_tools(data: dict, page: Path) -> None:
    html = page.read_text(encoding="utf-8")
    html = fill(fill(html, "tools", tools_html(data)), "toc", tools_toc(data))
    page.write_text(html, encoding="utf-8")


def sitemap(site_dir: Path, generated: str) -> str:
    entries = []
    for page in sorted((p.name for p in site_dir.glob("*.html")), key=lambda n: (n != "index.html", n)):
        lastmod = f"<lastmod>{generated[:10]}</lastmod>" if page in DATA_PAGES else ""
        entries.append(f"  <url><loc>{page_url(page)}</loc>{lastmod}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(entries) + "\n</urlset>\n")
