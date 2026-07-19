"""
Architecture visualisation pages: relationship diagram and capability grouping.
"""

import html
import json

from flask import Blueprint, jsonify, render_template_string

from db import fetch_architecture_by_capability, fetch_architecture_graph

architecture_views_bp = Blueprint("architecture_views", __name__)

OUTLOOK_COLORS = {
    "to be implemented": "#7eb6ff",
    "continue": "#3cb371",
    "to be decommissioned": "#e85d4c",
    "upgrade": "#f0a202",
    "decommissioned": "#c5c9d0",
}

BASE_STYLES = """
:root {
  --bg: #10151c;
  --text: #eef3f8;
  --muted: #8fa0b5;
  --line: #2b3a4d;
  --accent: #7dd3c0;
  --link: #8eb6ff;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  background:
    radial-gradient(ellipse at 15% 0%, #1b2a3b 0%, transparent 45%),
    linear-gradient(180deg, #121820 0%, var(--bg) 100%);
  color: var(--text);
  min-height: 100vh;
}
header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: baseline;
  gap: 1rem;
  flex-wrap: wrap;
}
header h1 { font-size: 1.2rem; font-weight: 650; }
header p { color: var(--muted); font-size: 0.85rem; }
nav {
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.85rem;
}
nav a, a { color: var(--link); text-decoration: none; }
nav a:hover, a:hover { text-decoration: underline; }
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem 1.1rem;
  padding: 0.85rem 1.5rem;
  color: var(--muted);
  font-size: 0.8rem;
}
.swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  margin-right: 0.35rem;
  vertical-align: -1px;
}
"""


def _esc(value):
    return html.escape(str(value), quote=True)


def _nav(active=None):
    links = [
        ("/", "Home"),
        ("/diagram", "Timeline"),
        ("/projects", "Projects"),
        ("/risks", "Risks"),
        ("/architecture", "Architecture"),
        ("/architecture/diagram", "Arch diagram"),
        ("/architecture/capabilities", "By capability"),
    ]
    parts = []
    for href, label in links:
        if label.lower() == (active or "").lower():
            parts.append(f"<span style='color:var(--accent)'>{_esc(label)}</span>")
        else:
            parts.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
    return " ".join(parts)


def _legend_html():
    items = []
    for outlook, color in OUTLOOK_COLORS.items():
        items.append(
            f'<span><i class="swatch" style="background:{color}"></i>{_esc(outlook)}</span>'
        )
    return "".join(items)


@architecture_views_bp.route("/architecture/diagram")
def architecture_diagram_page():
    return render_template_string(
        DIAGRAM_TEMPLATE,
        styles=BASE_STYLES,
        nav=_nav("Arch diagram"),
        legend=_legend_html(),
        outlook_colors=json.dumps(OUTLOOK_COLORS),
    )


@architecture_views_bp.route("/architecture/diagram/data")
def architecture_diagram_data():
    data = fetch_architecture_graph()
    elements = []
    for component in data["components"]:
        elements.append(
            {
                "data": {
                    "id": component["id"],
                    "label": component["title"],
                    "outlook": component["outlook"],
                    "capability": component["capability"],
                    "href": f"/architecture/{component['id']}",
                }
            }
        )
    for edge in data["edges"]:
        elements.append(
            {
                "data": {
                    "id": edge["id"],
                    "source": edge["source_id"],
                    "target": edge["target_id"],
                    "label": edge["relationship"],
                }
            }
        )
    return jsonify(elements)


@architecture_views_bp.route("/architecture/capabilities")
def architecture_capabilities_page():
    grouped = fetch_architecture_by_capability()
    sections = []
    for capability, components in grouped.items():
        cards = []
        for component in components:
            color = OUTLOOK_COLORS.get(component["outlook"], "#8fa0b5")
            cards.append(
                f"""
                <a class="card" href="/architecture/{_esc(component['id'])}"
                   style="background:{color}33;border-color:{color};border-left:4px solid {color}">
                  <div class="card-title">{_esc(component['title'])}</div>
                  <div class="card-id">{_esc(component['id'])} · {_esc(component['component_type'])}</div>
                  <div class="card-outlook" style="background:{color}">{_esc(component['outlook'])}</div>
                  <div class="card-desc">{_esc(component['description'])}</div>
                  <div class="card-owner">Owner: {_esc(component['owner'])}</div>
                </a>
                """
            )
        sections.append(
            f"""
            <section class="capability">
              <h2>{_esc(capability)}</h2>
              <div class="grid">{"".join(cards)}</div>
            </section>
            """
        )

    return render_template_string(
        CAPABILITIES_TEMPLATE,
        styles=BASE_STYLES,
        nav=_nav("By capability"),
        legend=_legend_html(),
        sections="".join(sections)
        or "<p style='padding:1.5rem;color:var(--muted)'>No architecture components</p>",
    )


DIAGRAM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Architecture diagram</title>
  <script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
  <style>
    {{ styles }}
    #cy {
      height: calc(100vh - 140px);
      min-height: 520px;
    }
    .hint {
      padding: 0 1.5rem 1rem;
      color: var(--muted);
      font-size: 0.75rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>Architecture diagram</h1>
    <p>Architecture components and relationships · colour = outlook</p>
    <nav>{{ nav|safe }}</nav>
  </header>
  <div class="legend">{{ legend|safe }}</div>
  <div id="cy"></div>
  <p class="hint">Drag nodes · scroll to zoom · click a component to open its detail page</p>
  <script>
    const OUTLOOK_COLORS = {{ outlook_colors|safe }};

    fetch("/architecture/diagram/data")
      .then((r) => r.json())
      .then((elements) => {
        const cy = cytoscape({
          container: document.getElementById("cy"),
          elements,
          style: [
            {
              selector: "node",
              style: {
                label: "data(label)",
                color: "#10151c",
                "text-valign": "center",
                "text-halign": "center",
                "font-size": 11,
                "font-weight": 650,
                "text-wrap": "wrap",
                "text-max-width": 110,
                width: 130,
                height: 52,
                shape: "round-rectangle",
                "background-color": (ele) =>
                  OUTLOOK_COLORS[ele.data("outlook")] || "#8fa0b5",
                "border-width": 2,
                "border-color": "#10151c",
              },
            },
            {
              selector: "edge",
              style: {
                width: 2,
                "line-color": "#5a6a82",
                "target-arrow-color": "#5a6a82",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                label: "data(label)",
                "font-size": 9,
                color: "#8fa0b5",
                "text-rotation": "autorotate",
                "text-margin-y": -8,
              },
            },
          ],
          layout: {
            name: "cose",
            animate: true,
            animationDuration: 600,
            nodeRepulsion: 12000,
            idealEdgeLength: 140,
            padding: 40,
          },
          minZoom: 0.35,
          maxZoom: 2.5,
        });

        cy.on("tap", "node", (evt) => {
          const href = evt.target.data("href");
          if (href) window.location.href = href;
        });
      });
  </script>
</body>
</html>
"""

CAPABILITIES_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Architecture by capability</title>
  <style>
    {{ styles }}
    main { padding: 0.5rem 1.5rem 2rem; }
    .capability { margin-bottom: 1.75rem; }
    .capability h2 {
      font-size: 1.05rem;
      margin-bottom: 0.75rem;
      padding-bottom: 0.35rem;
      border-bottom: 1px solid var(--line);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 0.85rem;
    }
    .card {
      display: block;
      border-radius: 10px;
      padding: 0.85rem 0.9rem;
      border: 1px solid var(--line);
      color: var(--text);
      transition: transform 140ms ease, border-color 140ms ease;
    }
    .card:hover {
      transform: translateY(-2px);
      text-decoration: none;
    }
    .card-title {
      font-weight: 700;
      font-size: 0.98rem;
      margin-bottom: 0.25rem;
    }
    .card-id, .card-owner {
      color: var(--muted);
      font-size: 0.72rem;
      margin-bottom: 0.35rem;
    }
    .card-outlook {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: lowercase;
      padding: 0.15rem 0.45rem;
      border-radius: 999px;
      background: var(--outlook);
      color: #10151c;
      margin-bottom: 0.45rem;
    }
    .card-desc {
      font-size: 0.8rem;
      line-height: 1.35;
      color: #d7dee8;
    }
  </style>
</head>
<body>
  <header>
    <h1>Architecture by capability</h1>
    <p>Components grouped by capability · colour = arch outlook</p>
    <nav>{{ nav|safe }}</nav>
  </header>
  <div class="legend">{{ legend|safe }}</div>
  <main>{{ sections|safe }}</main>
</body>
</html>
"""
