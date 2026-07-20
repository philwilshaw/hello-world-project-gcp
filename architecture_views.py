"""
Architecture visualisation pages: relationship diagram and capability grouping.
"""

import json

from flask import Blueprint, jsonify

from db import fetch_architecture_graph, fetch_architecture_model
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
.model-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.35rem;
  margin: 0 0 1rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  font-size: 0.85rem;
  color: var(--muted);
}
.model-controls label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  user-select: none;
}
.model-controls input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  accent-color: var(--accent);
  cursor: pointer;
}
.model-legend {
  padding: 0 0 0.85rem;
}
.zone-block { margin-bottom: 1.35rem; }
.zone-heading {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 1.25rem 0 0.55rem;
  padding-bottom: 0.3rem;
  border-bottom: 2px solid var(--accent);
}

.zone-block:first-child .zone-heading {
  margin-top: 0.75rem;
}
.subzone-block { margin: 0 0 0.95rem; }
.subzone-heading {
  font-size: 1.05rem;
  font-weight: 650;
  margin: 0 0 0.45rem;
  color: var(--text);
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem 0.75rem;
  align-items: start;
}
.capability {
  margin: 0;
  min-width: 0;
}
.capability-heading {
  font-size: 0.78rem;
  font-weight: 650;
  margin: 0 0 0.4rem;
  padding-bottom: 0.2rem;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  line-height: 1.25;
}
.card-stack {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.card {
  display: block;
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--line);
  color: var(--text);
  transition: transform 140ms ease, border-color 140ms ease, padding 140ms ease;
}
.card:hover {
  transform: translateY(-1px);
  text-decoration: none;
}
.card-title {
  font-weight: 700;
  font-size: 0.88rem;
  line-height: 1.2;
  margin-bottom: 0.15rem;
}
.card-id {
  color: var(--muted);
  font-size: 0.68rem;
  margin-bottom: 0.25rem;
}
.card-outlook {
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: lowercase;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: var(--outlook);
  color: #10151c;
  margin-bottom: 0;
}
.card-desc {
  font-size: 0.74rem;
  line-height: 1.3;
  color: #d7dee8;
  margin-top: 0.35rem;
}
.card-owner {
  color: var(--muted);
  font-size: 0.68rem;
  margin-top: 0.3rem;
}
.model-root.hide-desc .card-desc {
  display: none;
}
.model-root.hide-owner .card-owner {
  display: none;
}
@media (max-width: 980px) {
  .capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .capability-grid {
    grid-template-columns: 1fr;
  }
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


def _component_card(component):
    color = OUTLOOK_COLORS.get(component["outlook"], "#8fa0b5")
    return f"""
    <a class="card" href="/architecture/{_esc(component['id'])}"
       style="background:{color}33;border-color:{color};border-left:4px solid {color}">
      <div class="card-title">{_esc(component['title'])}</div>
      <div class="card-id">{_esc(component['id'])} · {_esc(component['component_type'])}</div>
      <div class="card-outlook" style="background:{color}">{_esc(component['outlook'])}</div>
      <div class="card-desc">{_esc(component['description'])}</div>
      <div class="card-owner">Owner: {_esc(component['owner'])}</div>
    </a>
    """


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
        title="Architecture Diagram",
        subtitle="Architecture components and relationships · colour = outlook",
        active="Architecture Diagram",
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
    model = fetch_architecture_model()
    zone_sections = []
    for zone in model:
        subzone_sections = []
        for sub_zone in zone["sub_zones"]:
            capability_sections = []
            for capability in sub_zone["capabilities"]:
                cards = [_component_card(c) for c in capability["components"]]
                capability_sections.append(
                    f"""
                    <section class="capability">
                      <h4 class="capability-heading">{_esc(capability['name'])}</h4>
                      <div class="card-stack">{"".join(cards)}</div>
                    </section>
                    """
                )
            subzone_sections.append(
                f"""
                <section class="subzone-block">
                  <h3 class="subzone-heading">SubZone: {_esc(sub_zone['sub_zone_name'])}</h3>
                  <div class="capability-grid">{"".join(capability_sections)}</div>
                </section>
                """
            )
        zone_sections.append(
            f"""
            <section class="zone-block">
              <h2 class="zone-heading">Zone: {_esc(zone['zone_name'])}</h2>
              {"".join(subzone_sections)}
            </section>
            """
        )

    body = f"""
  <div id="architecture-model" class="model-root">
    <div class="model-controls">
      <label><input type="checkbox" id="toggle-desc" checked /> Show description</label>
      <label><input type="checkbox" id="toggle-owner" checked /> Show owner</label>
    </div>
    <div class="legend model-legend">{_legend_html()}</div>
    {"".join(zone_sections) or "<p style='color:var(--muted)'>No architecture components</p>"}
  </div>
"""
    extra_js = """
<script>
  (function () {
    const root = document.getElementById("architecture-model");
    if (!root) return;
    const desc = document.getElementById("toggle-desc");
    const owner = document.getElementById("toggle-owner");

    function apply() {
      root.classList.toggle("hide-desc", !desc.checked);
      root.classList.toggle("hide-owner", !owner.checked);
    }

    desc.addEventListener("change", apply);
    owner.addEventListener("change", apply);
    apply();
  })();
</script>
"""
    return render_page(
        title="Architecture Model",
        subtitle="Components grouped by zone, sub-zone, and capability · colour = arch outlook",
        active="Architecture Model",
        body=body,
        extra_css=CAPABILITIES_EXTRA_CSS,
        extra_js=extra_js,
    )
