"""
Interactive project–risk timeline demo.

Reads projects, risks, and edges from SQLite, then renders:
  - projects as RAG-coloured bars on a timeline
  - linked corporate risks as diamonds at the right side of each project
"""

from flask import Blueprint, jsonify, render_template_string

from db import fetch_timeline_data

diagram_bp = Blueprint("diagram", __name__)


DIAGRAM_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Project–Risk Timeline</title>
  <style>
    :root {
      --bg: #10151c;
      --panel: #182230;
      --text: #eef3f8;
      --muted: #8fa0b5;
      --line: #2b3a4d;
      --accent: #7dd3c0;
      --risk: #d7dee8;
      --rag-green: #2f9e6b;
      --rag-amber: #d4a017;
      --rag-red: #c94c3f;
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

    header h1 {
      font-size: 1.15rem;
      font-weight: 650;
    }

    header p {
      color: var(--muted);
      font-size: 0.85rem;
    }

    header a {
      margin-left: auto;
      color: var(--accent);
      text-decoration: none;
      font-size: 0.85rem;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      padding: 0.75rem 1.5rem;
      color: var(--muted);
      font-size: 0.8rem;
    }

    .swatch {
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 0.35rem;
      vertical-align: -1px;
      border-radius: 2px;
    }

    .swatch.diamond {
      width: 10px;
      height: 10px;
      border-radius: 0;
      transform: rotate(45deg);
      background: var(--risk);
    }

    .swatch.green { background: var(--rag-green); }
    .swatch.amber { background: var(--rag-amber); }
    .swatch.red { background: var(--rag-red); }

    .timeline-wrap {
      padding: 0.5rem 1rem 1.5rem;
      overflow-x: auto;
    }

    #timeline {
      min-width: 920px;
      position: relative;
    }

    .axis {
      position: relative;
      height: 36px;
      margin: 0 0 0.5rem 220px;
      border-bottom: 1px solid var(--line);
    }

    .tick {
      position: absolute;
      bottom: 0;
      transform: translateX(-50%);
      color: var(--muted);
      font-size: 0.72rem;
      text-align: center;
    }

    .tick::before {
      content: "";
      display: block;
      width: 1px;
      height: 8px;
      margin: 0 auto 4px;
      background: var(--line);
    }

    .row {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 0.75rem;
      align-items: stretch;
      min-height: 108px;
      margin-bottom: 0.85rem;
      transition: opacity 180ms ease;
    }

    .row-label {
      padding: 0.65rem 0.75rem 0.65rem 0;
      color: var(--muted);
      font-size: 0.75rem;
      line-height: 1.35;
    }

    .row-label strong {
      display: block;
      color: var(--text);
      font-size: 0.92rem;
      margin-bottom: 0.2rem;
    }

    .track {
      position: relative;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 8px;
      min-height: 108px;
    }

    .project-bar {
      position: absolute;
      top: 14px;
      height: 78px;
      border-radius: 8px;
      padding: 0.55rem 0.7rem;
      overflow: hidden;
      color: #fff;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
      transition: opacity 180ms ease, filter 180ms ease;
    }

    .project-bar .title {
      font-size: 0.98rem;
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: 0.28rem;
    }

    .project-bar .meta {
      font-size: 0.68rem;
      line-height: 1.35;
      opacity: 0.92;
    }

    .project-bar.rag-green { background: linear-gradient(180deg, #36b078, var(--rag-green)); }
    .project-bar.rag-amber { background: linear-gradient(180deg, #e0b02a, var(--rag-amber)); }
    .project-bar.rag-red { background: linear-gradient(180deg, #dc5d4f, var(--rag-red)); }

    .risk-marker {
      position: absolute;
      top: 34px;
      width: 18px;
      height: 18px;
      transform: translate(-50%, 0) rotate(45deg);
      background: var(--risk);
      border: 2px solid #10151c;
      cursor: pointer;
      z-index: 3;
      transition: opacity 180ms ease, transform 180ms ease, box-shadow 180ms ease;
    }

    .risk-marker:hover,
    .risk-marker.selected {
      box-shadow: 0 0 0 3px rgba(125, 211, 192, 0.55);
    }

    .risk-label {
      position: absolute;
      top: 30px;
      z-index: 2;
      max-width: 150px;
      font-size: 0.68rem;
      line-height: 1.25;
      color: var(--text);
      cursor: pointer;
      transition: opacity 180ms ease;
    }

    .risk-label .rid {
      color: var(--accent);
      font-weight: 650;
    }

    .risk-label.side-right { text-align: left; }
    .risk-label.side-left { text-align: right; }

    .faded {
      opacity: 0.18 !important;
      filter: grayscale(0.35);
    }

    .risk-marker.faded,
    .risk-label.faded {
      opacity: 0.22 !important;
    }

    .risk-marker.selected,
    .risk-label.selected {
      opacity: 1 !important;
      filter: none;
    }

    .hint {
      padding: 0 1.5rem 1.25rem;
      color: var(--muted);
      font-size: 0.75rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>Project–Risk Timeline</h1>
    <p>Projects address corporate risks · bars coloured by RAG · diamonds show linked risks</p>
    <a href="/">← Home</a>
  </header>

  <div class="legend">
    <span><i class="swatch green"></i>Green</span>
    <span><i class="swatch amber"></i>Amber</span>
    <span><i class="swatch red"></i>Red</span>
    <span><i class="swatch diamond"></i>Corporate risk</span>
  </div>

  <div class="timeline-wrap">
    <div id="timeline"></div>
  </div>

  <p class="hint">Click a risk diamond or label to highlight every instance of that risk and its linked projects. Click again or elsewhere to clear.</p>

  <script>
    const RAG_CLASS = {
      Green: "rag-green",
      Amber: "rag-amber",
      Red: "rag-red",
    };

    function parseDate(value) {
      const [y, m, d] = value.split("-").map(Number);
      return Date.UTC(y, m - 1, d);
    }

    function formatMoney(value) {
      return new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
        maximumFractionDigits: 0,
      }).format(value);
    }

    function monthTicks(rangeStart, rangeEnd) {
      const ticks = [];
      const start = new Date(rangeStart);
      const cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
      while (cursor.getTime() <= rangeEnd) {
        ticks.push(cursor.getTime());
        cursor.setUTCMonth(cursor.getUTCMonth() + 1);
      }
      return ticks;
    }

    function pct(value, start, end) {
      return ((value - start) / (end - start)) * 100;
    }

    fetch("/diagram/data")
      .then((r) => r.json())
      .then((data) => renderTimeline(data));

    function renderTimeline(data) {
      const root = document.getElementById("timeline");
      const risksById = Object.fromEntries(data.risks.map((r) => [r.id, r]));
      const edgesByProject = {};
      for (const edge of data.edges) {
        (edgesByProject[edge.project_id] ||= []).push(edge);
      }

      const allStarts = data.projects.map((p) => parseDate(p.start_date));
      const allEnds = data.projects.map((p) => parseDate(p.end_date));
      const rangeStart = Math.min(...allStarts) - 20 * 24 * 3600 * 1000;
      const rangeEnd = Math.max(...allEnds) + 70 * 24 * 3600 * 1000;

      const axis = document.createElement("div");
      axis.className = "axis";
      for (const tick of monthTicks(rangeStart, rangeEnd)) {
        const el = document.createElement("div");
        el.className = "tick";
        el.style.left = pct(tick, rangeStart, rangeEnd) + "%";
        const date = new Date(tick);
        el.textContent = date.toLocaleString("en-GB", {
          month: "short",
          year: "2-digit",
          timeZone: "UTC",
        });
        axis.appendChild(el);
      }
      root.appendChild(axis);

      let selectedRiskId = null;

      function applySelection() {
        const rows = [...root.querySelectorAll(".row")];
        const markers = [...root.querySelectorAll(".risk-marker")];
        const labels = [...root.querySelectorAll(".risk-label")];

        if (!selectedRiskId) {
          rows.forEach((el) => el.classList.remove("faded"));
          markers.forEach((el) => el.classList.remove("selected", "faded"));
          labels.forEach((el) => el.classList.remove("selected", "faded"));
          return;
        }

        const linkedProjects = new Set(
          data.edges
            .filter((e) => e.risk_id === selectedRiskId)
            .map((e) => e.project_id)
        );

        rows.forEach((row) => {
          row.classList.toggle("faded", !linkedProjects.has(row.dataset.projectId));
        });

        markers.forEach((el) => {
          const match = el.dataset.riskId === selectedRiskId;
          el.classList.toggle("selected", match);
          el.classList.toggle("faded", !match);
        });

        labels.forEach((el) => {
          const match = el.dataset.riskId === selectedRiskId;
          el.classList.toggle("selected", match);
          el.classList.toggle("faded", !match);
        });
      }

      function toggleRisk(riskId) {
        selectedRiskId = selectedRiskId === riskId ? null : riskId;
        applySelection();
      }

      for (const project of data.projects) {
        const row = document.createElement("div");
        row.className = "row";
        row.dataset.projectId = project.id;

        const label = document.createElement("div");
        label.className = "row-label";
        label.innerHTML = `<strong>${project.id}</strong>${project.rag_status} · Capex ${formatMoney(project.capex_gbp)}`;

        const track = document.createElement("div");
        track.className = "track";

        const start = parseDate(project.start_date);
        const end = parseDate(project.end_date);
        const left = pct(start, rangeStart, rangeEnd);
        const width = pct(end, rangeStart, rangeEnd) - left;

        const bar = document.createElement("div");
        bar.className = `project-bar ${RAG_CLASS[project.rag_status] || "rag-amber"}`;
        bar.style.left = left + "%";
        bar.style.width = Math.max(width, 8) + "%";
        bar.innerHTML = `
          <div class="title">${project.title}</div>
          <div class="meta">
            ${project.accountable_contact_name}<br />
            ${project.start_date} → ${project.end_date}<br />
            Capex ${formatMoney(project.capex_gbp)} · Opex ${formatMoney(project.opex_gbp)}<br />
            ${project.description}
          </div>
        `;
        track.appendChild(bar);

        const linked = edgesByProject[project.id] || [];
        linked.forEach((edge, index) => {
          const risk = risksById[edge.risk_id];
          if (!risk) return;

          // Place diamonds just past the right edge of the project bar.
          const markerLeft = left + Math.max(width, 8) + 2.2 + index * 0.15;
          const side = markerLeft > 78 ? "left" : "right";
          const labelOffset = side === "right" ? 1.6 : -1.6;

          const marker = document.createElement("div");
          marker.className = "risk-marker";
          marker.dataset.riskId = risk.id;
          marker.dataset.edgeId = edge.id;
          marker.style.left = markerLeft + "%";
          marker.style.top = 28 + index * 22 + "px";
          marker.title = `${risk.id}: ${risk.title} (${edge.relationship})`;
          marker.addEventListener("click", (evt) => {
            evt.stopPropagation();
            toggleRisk(risk.id);
          });

          const riskLabel = document.createElement("div");
          riskLabel.className = `risk-label side-${side}`;
          riskLabel.dataset.riskId = risk.id;
          riskLabel.style.left = markerLeft + labelOffset + "%";
          riskLabel.style.top = 26 + index * 22 + "px";
          if (side === "left") {
            riskLabel.style.transform = "translateX(-100%)";
          }
          riskLabel.innerHTML = `<span class="rid">${risk.id}</span> ${risk.title}<br /><span style="color:var(--muted)">${edge.relationship}</span>`;
          riskLabel.addEventListener("click", (evt) => {
            evt.stopPropagation();
            toggleRisk(risk.id);
          });

          track.appendChild(marker);
          track.appendChild(riskLabel);
        });

        row.appendChild(label);
        row.appendChild(track);
        root.appendChild(row);
      }

      document.body.addEventListener("click", () => {
        if (selectedRiskId) {
          selectedRiskId = null;
          applySelection();
        }
      });
    }
  </script>
</body>
</html>
"""


@diagram_bp.route("/diagram")
def diagram_page():
    return render_template_string(DIAGRAM_HTML)


@diagram_bp.route("/diagram/data")
def diagram_data():
    return jsonify(fetch_timeline_data())
