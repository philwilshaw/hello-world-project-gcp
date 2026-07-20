"""
Shared page chrome: header, nav, footer, and HTML shell matching the timeline look.
"""

from __future__ import annotations

import html
from datetime import datetime

from flask import render_template_string

NAV_ITEMS = [
    ("/", "Home"),
    ("/zones", "Zones"),
    ("/diagram", "Timeline"),
    ("/projects", "Projects"),
    ("/risks", "Risks"),
    ("/architecture", "Architecture"),
    ("/architecture/diagram", "Arch diagram"),
    ("/architecture/capabilities", "By capability"),
    ("/architecture/roadmap", "Arch roadmap"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_nav(active: str | None = None) -> str:
    parts = []
    for href, label in NAV_ITEMS:
        if label.lower() == (active or "").lower():
            parts.append(f'<span class="active">{esc(label)}</span>')
        else:
            parts.append(f'<a href="{esc(href)}">{esc(label)}</a>')
    return "\n".join(parts)


def render_header(title: str, subtitle: str = "", active: str | None = None) -> str:
    subtitle_html = (
        f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ""
    )
    return f"""
<header class="site-header">
  <div class="site-header-top">
    <h1>{esc(title)}</h1>
    <nav class="site-nav">
      {render_nav(active)}
    </nav>
  </div>
  {subtitle_html}
</header>
"""


def render_footer() -> str:
    year = datetime.now().year
    return f"""
<footer class="site-footer">
  <p class="footer-links"><a href="/sitemap">Site map</a></p>
  <p class="footer-note">build with cursor AI on my phone on a train and in the gym in a few hours with zero prior experience</p>
  <p class="footer-copy">&copy; {year}</p>
</footer>
"""


SHELL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{{ title }}</title>
  <link rel="stylesheet" href="/static/site.css" />
  {% if extra_css %}
  <style>{{ extra_css|safe }}</style>
  {% endif %}
</head>
<body>
  {{ header|safe }}
  {{ body|safe }}
  {{ footer|safe }}
  {% if extra_js %}
  {{ extra_js|safe }}
  {% endif %}
</body>
</html>
"""


def render_page(
    *,
    title: str,
    body: str,
    subtitle: str = "",
    active: str | None = None,
    extra_css: str = "",
    extra_js: str = "",
    wide: bool = False,
):
    """Render a full HTML page with the shared header and stylesheet."""
    header = render_header(title, subtitle=subtitle, active=active)
    footer = render_footer()
    # If callers already wrap content, use as-is; otherwise wrap in site-main.
    wrapped = body
    if "<main" not in body and not wide:
        wrapped = f'<main class="site-main">{body}</main>'
    elif wide and "<main" not in body:
        wrapped = f'<main class="site-main wide">{body}</main>'

    return render_template_string(
        SHELL,
        title=title,
        header=header,
        body=wrapped,
        footer=footer,
        extra_css=extra_css,
        extra_js=extra_js,
    )


def register_layout(app) -> None:
    """Ensure HTML responses include the shared footer."""

    @app.after_request
    def ensure_site_footer(response):
        if response.status_code != 200:
            return response
        content_type = response.content_type or ""
        if not content_type.startswith("text/html"):
            return response
        if response.direct_passthrough:
            return response
        html = response.get_data(as_text=True)
        if "</body>" in html and "site-footer" not in html:
            response.set_data(
                html.replace("</body>", f"{render_footer()}\n</body>", 1)
            )
        return response
