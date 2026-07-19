"""
Interactive project–risk diagram demo.

Reads projects, risks, and edges from the SQLite database, then renders
only the nodes referenced by edges using Cytoscape.js.
"""

from flask import Blueprint, jsonify, render_template_string

from db import fetch_graph_elements

diagram_bp = Blueprint("diagram", __name__)


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
    <p>Nodes and edges loaded from the SQLite projects, risks, and edges tables</p>
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
    return jsonify(fetch_graph_elements())
