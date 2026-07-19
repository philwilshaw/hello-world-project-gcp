"""
Interactive project timeline demo.

Reads projects, risks, architecture components, and edges from SQLite, then
renders projects as RAG bars with linked risks (diamonds) and architecture
impacts (triangles) on the right of each bar.
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
  <title>Project Impact Timeline</title>
  <style>
    :root {
      --bg: #10151c;
      --text: #eef3f8;
      --muted: #8fa0b5;
      --line: #2b3a4d;
      --accent: #7dd3c0;
      --risk: #d7dee8;
      --arch: #8eb6ff;
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

    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem 1.25rem;
      padding: 0.85rem 1.5rem 0.35rem;
      color: var(--muted);
      font-size: 0.82rem;
      border-bottom: 1px solid rgba(43, 58, 77, 0.55);
    }

    .controls label {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      cursor: pointer;
      user-select: none;
    }

    .controls input {
      accent-color: var(--accent);
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

    .swatch.triangle {
      width: 0;
      height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 11px solid var(--arch);
      background: transparent;
      border-radius: 0;
      vertical-align: -2px;
    }

    .swatch.green { background: var(--rag-green); }
    .swatch.amber { background: var(--rag-amber); }
    .swatch.red { background: var(--rag-red); }

    .timeline-wrap {
      padding: 0.5rem 1rem 1.5rem;
      overflow-x: auto;
    }

    #timeline {
      min-width: 960px;
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
      min-height: 120px;
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
      min-height: 120px;
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

    .impact-marker {
      position: absolute;
      width: 24px;
      height: 24px;
      transform: translate(-50%, 0);
      cursor: pointer;
      z-index: 3;
      transition: opacity 180ms ease, filter 180ms ease;
    }

    .impact-marker .shape {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
    }

    .impact-marker .glyph {
      position: relative;
      z-index: 1;
      font-size: 0.68rem;
      font-weight: 750;
      line-height: 1;
      color: #10151c;
      pointer-events: none;
    }

    .impact-marker.risk .shape-visual {
      width: 16px;
      height: 16px;
      background: var(--risk);
      border: 2px solid #10151c;
      transform: rotate(45deg);
    }

    .impact-marker.risk .glyph {
      transform: translateY(0.5px);
    }

    .impact-marker.architecture .shape-visual {
      width: 0;
      height: 0;
      border-left: 11px solid transparent;
      border-right: 11px solid transparent;
      border-bottom: 18px solid var(--arch);
      filter: drop-shadow(0 0 0 #10151c);
    }

    .impact-marker.architecture .glyph {
      position: absolute;
      top: 8px;
      left: 50%;
      transform: translateX(-50%);
      color: #10151c;
    }

    .impact-marker:hover,
    .impact-marker.selected {
      filter: drop-shadow(0 0 4px rgba(125, 211, 192, 0.8));
    }

    .impact-label {
      position: absolute;
      z-index: 2;
      max-width: 150px;
      font-size: 0.68rem;
      line-height: 1.25;
      color: var(--text);
      cursor: pointer;
      transition: opacity 180ms ease;
    }

    .impact-label .iid {
      color: var(--accent);
      font-weight: 650;
    }

    .impact-label.side-right { text-align: left; }
    .impact-label.side-left { text-align: right; }

    .faded {
      opacity: 0.18 !important;
      filter: grayscale(0.35);
    }

    .impact-marker.faded,
    .impact-label.faded,
    .project-bar.faded {
      opacity: 0.22 !important;
    }

    .impact-marker.selected,
    .impact-label.selected,
    .project-bar.selected {
      opacity: 1 !important;
      filter: none;
    }

    .hidden-layer {
      display: none !important;
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
    <h1>Project Impact Timeline</h1>
    <p>Projects address corporate risks and change architecture components</p>
    <a href="/">← Home</a>
  </header>

  <div class="controls">
    <label><input type="checkbox" id="toggle-projects" checked /> Projects</label>
    <label><input type="checkbox" id="toggle-risks" checked /> Risks</label>
    <label><input type="checkbox" id="toggle-architecture" checked /> Architecture impacts</label>
  </div>

  <div class="legend">
    <span><i class="swatch green"></i>Green</span>
    <span><i class="swatch amber"></i>Amber</span>
    <span><i class="swatch red"></i>Red</span>
    <span><i class="swatch diamond"></i>Risk (R)</span>
    <span><i class="swatch triangle"></i>Architecture (A)</span>
  </div>

  <div class="timeline-wrap">
    <div id="timeline"></div>
  </div>

  <p class="hint">Click a risk or architecture marker to highlight every instance and its linked projects. Click again or elsewhere to clear. Use the checkboxes to show or hide layers.</p>

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
      const archById = Object.fromEntries(
        data.architecture_components.map((a) => [a.id, a])
      );
      const edgesByProject = {};
      for (const edge of data.edges) {
        (edgesByProject[edge.project_id] ||= []).push(edge);
      }

      const allStarts = data.projects.map((p) => parseDate(p.start_date));
      const allEnds = data.projects.map((p) => parseDate(p.end_date));
      const rangeStart = Math.min(...allStarts) - 20 * 24 * 3600 * 1000;
      const rangeEnd = Math.max(...allEnds) + 90 * 24 * 3600 * 1000;

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

      let selected = null; // { type, id }

      function applySelection() {
        const rows = [...root.querySelectorAll(".row")];
        const bars = [...root.querySelectorAll(".project-bar")];
        const markers = [...root.querySelectorAll(".impact-marker")];
        const labels = [...root.querySelectorAll(".impact-label")];

        if (!selected) {
          rows.forEach((el) => el.classList.remove("faded"));
          bars.forEach((el) => el.classList.remove("selected", "faded"));
          markers.forEach((el) => el.classList.remove("selected", "faded"));
          labels.forEach((el) => el.classList.remove("selected", "faded"));
          return;
        }

        const linkedProjects = new Set(
          data.edges
            .filter(
              (e) =>
                e.linked_type === selected.type && e.linked_id === selected.id
            )
            .map((e) => e.project_id)
        );

        rows.forEach((row) => {
          row.classList.toggle(
            "faded",
            !linkedProjects.has(row.dataset.projectId)
          );
        });

        bars.forEach((el) => {
          const match = linkedProjects.has(el.dataset.projectId);
          el.classList.toggle("selected", match);
          el.classList.toggle("faded", !match);
        });

        markers.forEach((el) => {
          const match =
            el.dataset.linkedType === selected.type &&
            el.dataset.linkedId === selected.id;
          el.classList.toggle("selected", match);
          el.classList.toggle("faded", !match);
        });

        labels.forEach((el) => {
          const match =
            el.dataset.linkedType === selected.type &&
            el.dataset.linkedId === selected.id;
          el.classList.toggle("selected", match);
          el.classList.toggle("faded", !match);
        });
      }

      function toggleItem(type, id) {
        if (selected && selected.type === type && selected.id === id) {
          selected = null;
        } else {
          selected = { type, id };
        }
        applySelection();
      }

      function applyVisibility() {
        const showProjects = document.getElementById("toggle-projects").checked;
        const showRisks = document.getElementById("toggle-risks").checked;
        const showArch = document.getElementById("toggle-architecture").checked;

        root.querySelectorAll(".project-bar").forEach((el) => {
          el.classList.toggle("hidden-layer", !showProjects);
        });
        root.querySelectorAll('.impact-marker.risk, .impact-label.risk').forEach((el) => {
          el.classList.toggle("hidden-layer", !showRisks);
        });
        root.querySelectorAll(
          ".impact-marker.architecture, .impact-label.architecture"
        ).forEach((el) => {
          el.classList.toggle("hidden-layer", !showArch);
        });
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
        bar.dataset.projectId = project.id;
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
          const isRisk = edge.linked_type === "risk";
          const item = isRisk
            ? risksById[edge.linked_id]
            : archById[edge.linked_id];
          if (!item) return;

          const markerLeft = left + Math.max(width, 8) + 2.4 + index * 0.2;
          const side = markerLeft > 76 ? "left" : "right";
          const labelOffset = side === "right" ? 1.7 : -1.7;
          const top = 22 + index * 24;

          const marker = document.createElement("div");
          marker.className = `impact-marker ${edge.linked_type}`;
          marker.dataset.linkedType = edge.linked_type;
          marker.dataset.linkedId = item.id;
          marker.dataset.edgeId = edge.id;
          marker.style.left = markerLeft + "%";
          marker.style.top = top + "px";
          marker.title = `${item.id}: ${item.title} (${edge.relationship})`;
          marker.innerHTML = isRisk
            ? `<div class="shape"><div class="shape-visual"></div><span class="glyph">R</span></div>`
            : `<div class="shape"><div class="shape-visual"></div><span class="glyph">A</span></div>`;
          marker.addEventListener("click", (evt) => {
            evt.stopPropagation();
            toggleItem(edge.linked_type, item.id);
          });

          const impactLabel = document.createElement("div");
          impactLabel.className = `impact-label ${edge.linked_type} side-${side}`;
          impactLabel.dataset.linkedType = edge.linked_type;
          impactLabel.dataset.linkedId = item.id;
          impactLabel.style.left = markerLeft + labelOffset + "%";
          impactLabel.style.top = top - 2 + "px";
          if (side === "left") {
            impactLabel.style.transform = "translateX(-100%)";
          }
          impactLabel.innerHTML = `<span class="iid">${item.id}</span> ${item.title}<br /><span style="color:var(--muted)">${edge.relationship}</span>`;
          impactLabel.addEventListener("click", (evt) => {
            evt.stopPropagation();
            toggleItem(edge.linked_type, item.id);
          });

          track.appendChild(marker);
          track.appendChild(impactLabel);
        });

        // Grow the track if many impacts stack vertically.
        const neededHeight = 22 + linked.length * 24 + 28;
        track.style.minHeight = Math.max(120, neededHeight) + "px";
        row.style.minHeight = Math.max(120, neededHeight) + "px";

        row.appendChild(label);
        row.appendChild(track);
        root.appendChild(row);
      }

      ["toggle-projects", "toggle-risks", "toggle-architecture"].forEach((id) => {
        document.getElementById(id).addEventListener("change", (evt) => {
          evt.stopPropagation();
          applyVisibility();
        });
      });
      applyVisibility();

      document.body.addEventListener("click", () => {
        if (selected) {
          selected = null;
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
