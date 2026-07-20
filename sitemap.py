"""
Site map page — main pages plus database-driven detail links.
"""

from flask import Blueprint

from db import fetch_all_architecture, fetch_all_projects, fetch_all_risks
from ui import NAV_ITEMS, esc, render_page

sitemap_bp = Blueprint("sitemap", __name__)


def _main_pages_html() -> str:
    items = []
    for href, label in NAV_ITEMS:
        items.append(
            f'<li><a class="sitemap-main-link" href="{esc(href)}">{esc(label)}</a></li>'
        )
    return "\n".join(items)


def _detail_links(rows, href_prefix: str) -> str:
    if not rows:
        return '<li class="empty">None</li>'
    items = []
    for row in rows:
        items.append(
            f'<li><a class="sitemap-detail-link" href="{esc(href_prefix)}{esc(row["id"])}">'
            f'<span class="sitemap-id">{esc(row["id"])}</span> {esc(row["title"])}</a></li>'
        )
    return "\n".join(items)


@sitemap_bp.route("/sitemap")
def sitemap_page():
    projects = fetch_all_projects()
    risks = fetch_all_risks()
    architecture = fetch_all_architecture()

    body = f"""
<section class="sitemap-section">
  <h2 class="sitemap-heading sitemap-heading-main">Main pages</h2>
  <p class="sitemap-intro">These pages are available from the header menu.</p>
  <ul class="sitemap-list sitemap-list-main">
    {_main_pages_html()}
  </ul>
</section>

<section class="sitemap-section">
  <h2 class="sitemap-heading sitemap-heading-detail">Project detail pages</h2>
  <p class="sitemap-intro">Individual project records from the database.</p>
  <ul class="sitemap-list sitemap-list-detail">
    {_detail_links(projects, "/projects/")}
  </ul>
</section>

<section class="sitemap-section">
  <h2 class="sitemap-heading sitemap-heading-detail">Risk detail pages</h2>
  <p class="sitemap-intro">Individual corporate risk records from the database.</p>
  <ul class="sitemap-list sitemap-list-detail">
    {_detail_links(risks, "/risks/")}
  </ul>
</section>

<section class="sitemap-section">
  <h2 class="sitemap-heading sitemap-heading-detail">Architecture detail pages</h2>
  <p class="sitemap-intro">Individual architecture component records from the database.</p>
  <ul class="sitemap-list sitemap-list-detail">
    {_detail_links(architecture, "/architecture/")}
  </ul>
</section>
"""

    return render_page(
        title="Site map",
        subtitle="All pages on this site",
        body=body,
    )
