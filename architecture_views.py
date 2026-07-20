"""
Architecture visualisation pages: relationship diagram and capability grouping.
"""

import json

from flask import Blueprint, jsonify

from db import fetch_architecture_by_capability, fetch_architecture_graph
from ui import esc, render_page

architecture_views_bp = Blueprint("architecture_views", __name__)

OUTLOOK_COLORS = {
    "Retain": "#3cb371",
    "Upgrade": "#f0a202",
    "Decommission": "#e85d4c",
    "to be implemented": "#7eb6ff",
    "continue": "#3cb371",
    "to be decommissioned": "#e85d4c",
    "upgrade": "#f0a202",
    "decommissioned": "#c5c9d0",
}

DIAGRAM_EXTRA_CSS = """
#cy {
  height: min(68vh, 720px);
  min-height: 420px;
}
"""

CAPABILITIES_EXTRA_CSS = """
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
"""


def _esc(value):
    return esc(value)


def _legend_html():
    items = []
    for outlook, color in OUTLOOK_COLORS.items():
        items.append(
            f'<span><i class="swatch" style="background:{color}"></i>{_esc(outlook)}</span>'
        )
    return "".join(items)


@architecture_views_bp.route("/architecture/diagram")
def architecture_diagram_page():
    outlook_colors = json.dumps(OUTLOOK_COLORS)
    body = f"""
  <div class="legend">{_legend_html()}</div>
  <div id="cy"></div>
  <p class="site-hint">Drag nodes · scroll to zoom · click a component to open its detail page</p>
"""
    extra_js = f"""
<script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
<script>
  const OUTLOOK_COLORS = {outlook_colors};

  fetch("/architecture/diagram/data")
    .then((r) => r.json())
    .then((elements) => {{
      const cy = cytoscape({{
        container: document.getElementById("cy"),
        elements,
        style: [
          {{
            selector: "node",
            style: {{
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
            }},
          }},
          {{
            selector: "edge",
            style: {{
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
            }},
          }},
        ],
        layout: {{
          name: "cose",
          animate: true,
          animationDuration: 600,
          nodeRepulsion: 12000,
          idealEdgeLength: 140,
          padding: 40,
        }},
        minZoom: 0.35,
        maxZoom: 2.5,
      }});

      cy.on("tap", "node", (evt) => {{
        const href = evt.target.data("href");
        if (href) window.location.href = href;
      }});
    }});
</script>
"""
    return render_page(
        title="Architecture diagram",
        subtitle="Architecture components and relationships · colour = outlook",
        active="Arch diagram",
        body=body,
        extra_css=DIAGRAM_EXTRA_CSS,
        extra_js=extra_js,
        wide=True,
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

    body = f"""
  <div class="legend">{_legend_html()}</div>
  {"".join(sections) or "<p style='padding:1.5rem;color:var(--muted)'>No architecture components</p>"}
"""
    return render_page(
        title="Architecture by capability",
        subtitle="Components grouped by capability · colour = arch outlook",
        active="By capability",
        body=body,
        extra_css=CAPABILITIES_EXTRA_CSS,
    )
