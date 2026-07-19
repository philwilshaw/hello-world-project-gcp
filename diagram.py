"""
Interactive project–risk diagram demo.

Data model (mock "databases"):
  - projects: nodes of type "project"
  - risks:    nodes of type "risk"
  - edges:    relationships between projects and risks

The diagram reads edges first, then resolves only the nodes those edges
reference. That pattern scales to more node types and more visualisations
(timelines, tables, architecture views) without rewriting the data layer.
"""

from flask import Blueprint, jsonify, render_template_string

diagram_bp = Blueprint("diagram", __name__)

# ---------------------------------------------------------------------------
# Mock databases — replace with real DB queries later
# ---------------------------------------------------------------------------

PROJECTS = [
    {"id": "p1", "name": "Website Redesign", "type": "project"},
    {"id": "p2", "name": "Mobile App Launch", "type": "project"},
    {"id": "p3", "name": "Data Migration", "type": "project"},
]

RISKS = [
    {"id": "r1", "name": "Budget Overrun", "type": "risk"},
    {"id": "r2", "name": "Schedule Slip", "type": "risk"},
    {"id": "r3", "name": "Key Person Dependency", "type": "risk"},
    {"id": "r4", "name": "Vendor Delay", "type": "risk"},
]

# Edges link project → risk. Only linked nodes appear on the diagram.
EDGES = [
    {"id": "e1", "source": "p1", "target": "r1", "label": "exposed to"},
    {"id": "e2", "source": "p1", "target": "r2", "label": "exposed to"},
    {"id": "e3", "source": "p2", "target": "r2", "label": "exposed to"},
    {"id": "e4", "source": "p2", "target": "r3", "label": "exposed to"},
    {"id": "e5", "source": "p3", "target": "r1", "label": "exposed to"},
    {"id": "e6", "source": "p3", "target": "r4", "label": "exposed to"},
]

# Registry of node tables by type — add new types here as the app grows.
NODE_TABLES = {
    "project": PROJECTS,
    "risk": RISKS,
}


def get_graph():
    """Build a cytoscape-ready graph from edges + node tables."""
    nodes_by_id = {
        node["id"]: node
        for table in NODE_TABLES.values()
        for node in table
    }

    used_ids = set()
    for edge in EDGES:
        used_ids.add(edge["source"])
        used_ids.add(edge["target"])

    elements = []
    for node_id in used_ids:
        node = nodes_by_id[node_id]
        elements.append(
            {
                "data": {
                    "id": node["id"],
                    "label": node["name"],
                    "type": node["type"],
                }
            }
        )

    for edge in EDGES:
        elements.append(
            {
                "data": {
                    "id": edge["id"],
                    "source": edge["source"],
                    "target": edge["target"],
                    "label": edge.get("label", ""),
                }
            }
        )

    return elements


DIAGRAM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Project–Risk Diagram</title>
  <script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --text: #e8eef6;
      --muted: #8b9bb4;
      --project: #3d8bfd;
      --risk: #e85d4c;
      --edge: #5a6a82;
      --accent: #7dd3c0;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      background: radial-gradient(ellipse at 20% 0%, #1a2a3a 0%, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      padding: 1rem 1.5rem;
      border-bottom: 1px solid #2a3548;
      display: flex;
      align-items: baseline;
      gap: 1rem;
      flex-wrap: wrap;
    }

    header h1 {
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    header p {
      color: var(--muted);
      font-size: 0.85rem;
    }

    header a {
      color: var(--accent);
      text-decoration: none;
      font-size: 0.85rem;
      margin-left: auto;
    }

    .legend {
      display: flex;
      gap: 1.25rem;
      padding: 0.75rem 1.5rem;
      font-size: 0.8rem;
      color: var(--muted);
    }

    .legend span::before {
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 0.4rem;
      vertical-align: middle;
    }

    .legend .project::before { background: var(--project); }
    .legend .risk::before { background: var(--risk); }

    #cy {
      flex: 1;
      min-height: 480px;
      background: transparent;
    }

    .hint {
      padding: 0.6rem 1.5rem 1rem;
      font-size: 0.75rem;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <header>
    <h1>Project–Risk Diagram</h1>
    <p>Nodes and edges loaded from mock project, risk, and edge tables</p>
    <a href="/">← Home</a>
  </header>

  <div class="legend">
    <span class="project">Project</span>
    <span class="risk">Risk</span>
  </div>

  <div id="cy"></div>

  <p class="hint">Drag nodes · scroll to zoom · click a node to highlight its links</p>

  <script>
    fetch("/diagram/data")
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
                color: "#e8eef6",
                "text-valign": "center",
                "text-halign": "center",
                "font-size": 12,
                "font-weight": 500,
                "text-wrap": "wrap",
                "text-max-width": 100,
                width: 88,
                height: 88,
                "border-width": 2,
                "border-color": "#2a3548",
                "overlay-padding": 6,
              },
            },
            {
              selector: 'node[type = "project"]',
              style: {
                "background-color": "#3d8bfd",
                shape: "round-rectangle",
                width: 120,
                height: 52,
              },
            },
            {
              selector: 'node[type = "risk"]',
              style: {
                "background-color": "#e85d4c",
                shape: "ellipse",
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
                color: "#8b9bb4",
                "text-rotation": "autorotate",
                "text-margin-y": -8,
              },
            },
            {
              selector: ".highlighted",
              style: {
                "border-color": "#7dd3c0",
                "border-width": 3,
                "line-color": "#7dd3c0",
                "target-arrow-color": "#7dd3c0",
                "z-index": 999,
              },
            },
            {
              selector: ".faded",
              style: {
                opacity: 0.2,
              },
            },
          ],
          layout: {
            name: "cose",
            animate: true,
            animationDuration: 600,
            nodeRepulsion: 8000,
            idealEdgeLength: 120,
            padding: 40,
          },
          minZoom: 0.4,
          maxZoom: 2.5,
        });

        cy.on("tap", "node", (evt) => {
          const node = evt.target;
          const neighborhood = node.closedNeighborhood();
          cy.elements().addClass("faded").removeClass("highlighted");
          neighborhood.removeClass("faded").addClass("highlighted");
        });

        cy.on("tap", (evt) => {
          if (evt.target === cy) {
            cy.elements().removeClass("faded highlighted");
          }
        });
      });
  </script>
</body>
</html>
"""


@diagram_bp.route("/diagram")
def diagram_page():
    return render_template_string(DIAGRAM_HTML)


@diagram_bp.route("/diagram/data")
def diagram_data():
    return jsonify(get_graph())
