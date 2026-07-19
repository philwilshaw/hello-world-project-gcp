"""
Architecture roadmap timeline: lifespan bars by year with project go-live stars.
"""

from flask import Blueprint, jsonify, render_template_string

from db import fetch_architecture_roadmap

architecture_roadmap_bp = Blueprint("architecture_roadmap", __name__)


ROADMAP_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Architecture Roadmap Timeline</title>
  <style>
    :root {
      --bg: #10151c;
      --text: #eef3f8;
      --muted: #8fa0b5;
      --line: #2b3a4d;
      --accent: #7dd3c0;
      --band-a: rgba(255, 255, 255, 0.025);
      --band-b: rgba(125, 211, 192, 0.045);
      --outlook-to-be-implemented: #7eb6ff;
      --outlook-continue: #3cb371;
      --outlook-to-be-decommissioned: #e85d4c;
      --outlook-upgrade: #f0a202;
      --outlook-decommissioned: #c5c9d0;
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

    header h1 { font-size: 1.15rem; font-weight: 650; }
    header p { color: var(--muted); font-size: 0.85rem; }

    header .nav-links {
      margin-left: auto;
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    header .nav-links a {
      color: var(--accent);
      text-decoration: none;
      font-size: 0.85rem;
    }

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

    .star-legend {
      color: #f5d76e;
      margin-right: 0.25rem;
    }

    .timeline-wrap {
      padding: 0.5rem 1rem 1.5rem;
      overflow-x: auto;
    }

    #timeline { min-width: 980px; position: relative; }

    .chart {
      position: relative;
      margin-left: 220px;
    }

    .bands {
      position: absolute;
      inset: 36px 0 0 0;
      pointer-events: none;
      z-index: 0;
    }

    .year-band {
      position: absolute;
      top: 0;
      bottom: 0;
      border-left: 1px solid rgba(43, 58, 77, 0.65);
    }

    .year-band:nth-child(odd) { background: var(--band-a); }
    .year-band:nth-child(even) { background: var(--band-b); }

    .axis {
      position: relative;
      height: 36px;
      border-bottom: 1px solid var(--line);
      z-index: 1;
    }

    .tick {
      position: absolute;
      bottom: 0;
      transform: translateX(-50%);
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 650;
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

    .rows { position: relative; z-index: 1; }

    .row {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 0.75rem;
      margin-bottom: 1rem;
      margin-left: -220px;
      min-height: 110px;
    }

    .row-label {
      padding: 0.85rem 0.75rem 0.65rem 0;
      color: var(--muted);
      font-size: 0.75rem;
      line-height: 1.35;
    }

    .row-label strong {
      display: block;
      color: var(--text);
      font-size: 1rem;
      margin-bottom: 0.25rem;
    }

    .capability-box {
      position: relative;
      min-height: 110px;
      border: 1px solid rgba(125, 211, 192, 0.28);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.03);
      box-shadow: inset 0 0 0 1px rgba(16, 21, 28, 0.25);
      padding: 0.65rem 0.5rem 0.75rem;
    }

    .arch-lane {
      position: relative;
      min-height: 72px;
      margin-bottom: 0.55rem;
    }

    .arch-lane:last-child { margin-bottom: 0; }

    .arch-bar {
      position: absolute;
      top: 10px;
      height: 52px;
      border-radius: 8px;
      padding: 0.45rem 0.65rem;
      overflow: hidden;
      color: #10151c;
      box-shadow: inset 0 0 0 1px rgba(16, 21, 28, 0.25);
      z-index: 2;
    }

    .arch-bar a {
      color: inherit;
      text-decoration: none;
    }

    .arch-bar .title {
      font-size: 0.9rem;
      font-weight: 700;
      line-height: 1.15;
      margin-bottom: 0.2rem;
    }

    .arch-bar .meta {
      font-size: 0.66rem;
      line-height: 1.3;
      opacity: 0.9;
    }

    .golive {
      position: absolute;
      top: 2px;
      transform: translateX(-50%);
      z-index: 4;
      width: 120px;
      text-align: center;
      cursor: default;
    }

    .golive .star {
      display: block;
      font-size: 1.35rem;
      line-height: 1;
      color: #f5d76e;
      text-shadow: 0 0 6px rgba(245, 215, 110, 0.45);
      filter: drop-shadow(0 1px 1px rgba(0,0,0,0.45));
    }

    .golive .label {
      margin-top: 0.15rem;
      font-size: 0.64rem;
      line-height: 1.25;
      color: var(--text);
      background: rgba(16, 21, 28, 0.72);
      border: 1px solid rgba(245, 215, 110, 0.35);
      border-radius: 6px;
      padding: 0.25rem 0.35rem;
    }

    .golive .label .rel {
      color: var(--muted);
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
    <h1>Architecture Roadmap Timeline</h1>
    <p>Grouped by capability · lifespan bars by year · stars mark project go-lives</p>
    <div class="nav-links">
      <a href="/diagram">Timeline</a>
      <a href="/architecture">Architecture</a>
      <a href="/architecture/diagram">Arch diagram</a>
      <a href="/architecture/capabilities">By capability</a>
      <a href="/">Home</a>
    </div>
  </header>

  <div class="legend">
    <span><i class="swatch" style="background:#7eb6ff"></i>to be implemented</span>
    <span><i class="swatch" style="background:#3cb371"></i>continue</span>
    <span><i class="swatch" style="background:#e85d4c"></i>to be decommissioned</span>
    <span><i class="swatch" style="background:#f0a202"></i>upgrade</span>
    <span><i class="swatch" style="background:#c5c9d0"></i>decommissioned</span>
    <span><span class="star-legend">★</span> project go-live impact</span>
  </div>

  <div class="timeline-wrap">
    <div id="timeline"></div>
  </div>

  <p class="hint">
    Bars use architecture lifecycle dates. Where implemented / go-live / decommissioned
    dates are missing, they are inferred from project edges (implemented / decommissioned)
    when available. Stars sit on project end dates for every project linked to that component.
  </p>

  <script>
    const OUTLOOK_COLORS = {
      "to be implemented": "#7eb6ff",
      "continue": "#3cb371",
      "to be decommissioned": "#e85d4c",
      "upgrade": "#f0a202",
      "decommissioned": "#c5c9d0",
    };

    function parseDate(value) {
      if (!value) return null;
      const [y, m, d] = value.split("-").map(Number);
      return Date.UTC(y, m - 1, d);
    }

    function startOfYear(ms) {
      const d = new Date(ms);
      return Date.UTC(d.getUTCFullYear(), 0, 1);
    }

    function endOfYear(ms) {
      const d = new Date(ms);
      return Date.UTC(d.getUTCFullYear(), 11, 31, 23, 59, 59, 999);
    }

    function yearBands(rangeStart, rangeEnd) {
      const bands = [];
      let year = new Date(rangeStart).getUTCFullYear();
      const last = new Date(rangeEnd).getUTCFullYear();
      while (year <= last) {
        const start = Date.UTC(year, 0, 1);
        const end = Date.UTC(year, 11, 31, 23, 59, 59, 999);
        bands.push({ start, end, label: String(year) });
        year += 1;
      }
      return bands;
    }

    function pct(value, start, end) {
      return ((value - start) / (end - start)) * 100;
    }

    fetch("/architecture/roadmap/data")
      .then((r) => r.json())
      .then((payload) => renderRoadmap(payload.components || []));

    function renderRoadmap(components) {
      const root = document.getElementById("timeline");
      const dated = components.filter((c) => c.bar_start);
      if (!dated.length) {
        root.textContent = "No architecture lifecycle dates available.";
        return;
      }

      const starts = dated.map((c) => parseDate(c.bar_start));
      const ends = dated.map((c) => parseDate(c.bar_end) || parseDate(c.bar_start));
      const goliveDates = dated.flatMap((c) =>
        (c.project_golives || []).map((g) => parseDate(g.date)).filter(Boolean)
      );

      const allDates = [...starts, ...ends, ...goliveDates];
      const rangeStart = startOfYear(Math.min(...allDates));
      const maxYear = new Date(Math.max(...allDates)).getUTCFullYear();
      // Leave one extra year so still-active bars have room to run.
      const rangeEnd = endOfYear(Date.UTC(maxYear + 1, 0, 1));
      const bands = yearBands(rangeStart, rangeEnd);

      const chart = document.createElement("div");
      chart.className = "chart";

      const bandsLayer = document.createElement("div");
      bandsLayer.className = "bands";
      bands.forEach((band) => {
        const el = document.createElement("div");
        el.className = "year-band";
        el.style.left = pct(band.start, rangeStart, rangeEnd) + "%";
        el.style.width =
          pct(band.end, rangeStart, rangeEnd) - pct(band.start, rangeStart, rangeEnd) + "%";
        bandsLayer.appendChild(el);
      });
      chart.appendChild(bandsLayer);

      const axis = document.createElement("div");
      axis.className = "axis";
      bands.forEach((band) => {
        const el = document.createElement("div");
        el.className = "tick";
        const mid = band.start + (band.end - band.start) / 2;
        el.style.left = pct(mid, rangeStart, rangeEnd) + "%";
        el.textContent = band.label;
        axis.appendChild(el);
      });
      chart.appendChild(axis);

      const rows = document.createElement("div");
      rows.className = "rows";
      chart.appendChild(rows);
      root.appendChild(chart);

      const byCapability = {};
      for (const component of dated) {
        (byCapability[component.capability] ||= []).push(component);
      }

      for (const [capability, items] of Object.entries(byCapability)) {
        const row = document.createElement("div");
        row.className = "row";

        const label = document.createElement("div");
        label.className = "row-label";
        label.innerHTML = `
          <strong>${capability}</strong>
          ${items.length} architecture element${items.length === 1 ? "" : "s"}
        `;

        const box = document.createElement("div");
        box.className = "capability-box";

        items.forEach((component) => {
          const lane = document.createElement("div");
          lane.className = "arch-lane";

          const start = parseDate(component.bar_start);
          const end = parseDate(component.bar_end) || rangeEnd;
          const left = pct(start, rangeStart, rangeEnd);
          const width = Math.max(pct(end, rangeStart, rangeEnd) - left, 2.5);
          const color = OUTLOOK_COLORS[component.outlook] || "#8fa0b5";

          const bar = document.createElement("div");
          bar.className = "arch-bar";
          bar.style.left = left + "%";
          bar.style.width = width + "%";
          bar.style.background = `linear-gradient(180deg, ${color}, ${color}dd)`;
          const endLabel = component.decommissioned_date || "active";
          bar.innerHTML = `
            <div class="title"><a href="/architecture/${component.id}">${component.title}</a></div>
            <div class="meta">
              ${component.id} · ${component.outlook}<br />
              ${component.implemented_date || "?"} → ${component.go_live_date || "?"} · end ${endLabel}
            </div>
          `;
          lane.appendChild(bar);

          const golives = component.project_golives || [];
          golives.forEach((g, index) => {
            const when = parseDate(g.date);
            if (!when) return;
            const marker = document.createElement("div");
            marker.className = "golive";
            marker.style.left = pct(when, rangeStart, rangeEnd) + "%";
            marker.style.top = 0 + (index % 2) * 28 + "px";
            marker.title = `${g.project_title} · ${g.relationship} · ${g.date}`;
            marker.innerHTML = `
              <span class="star">★</span>
              <div class="label">
                <strong>${g.project_title}</strong><br />
                <span class="rel">${g.relationship}</span>
              </div>
            `;
            lane.appendChild(marker);
          });

          const laneHeight = 72 + Math.max(0, golives.length - 1) * 16;
          lane.style.minHeight = laneHeight + "px";
          box.appendChild(lane);
        });

        row.appendChild(label);
        row.appendChild(box);
        rows.appendChild(row);
      }
    }
  </script>
</body>
</html>
"""


@architecture_roadmap_bp.route("/architecture/roadmap")
def architecture_roadmap_page():
    return render_template_string(ROADMAP_HTML)


@architecture_roadmap_bp.route("/architecture/roadmap/data")
def architecture_roadmap_data():
    return jsonify(fetch_architecture_roadmap())
