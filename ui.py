"""
Shared page chrome: header, nav, and HTML shell matching the timeline look.
"""

from __future__ import annotations

import html

from flask import render_template_string

NAV_ITEMS = [
    ("/", "Home"),
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


SHELL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <link rel="stylesheet" href="/static/site.css" />
  {% if extra_css %}
  <style>{{ extra_css|safe }}</style>
  {% endif %}
</head>
<body>
  {{ header|safe }}
  {{ body|safe }}
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
        extra_css=extra_css,
        extra_js=extra_js,
    )
