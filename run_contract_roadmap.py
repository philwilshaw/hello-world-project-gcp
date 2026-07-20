"""
Run contract roadmap timeline: contract bars by zone/sub-zone with PO renewals
and next-renewal outlook (extension, terminate, or TBC).
"""

from flask import Blueprint, jsonify

from db import fetch_run_contract_roadmap
from ui import render_page

run_contract_roadmap_bp = Blueprint("run_contract_roadmap", __name__)


EXTRA_CSS = r"""
.timeline-wrap {
  padding: 0.5rem 0 1.5rem;
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

.zone-group {
  margin-bottom: 1.35rem;
}

.zone-group-title {
  margin: 1rem 0 0.55rem;
  margin-left: -220px;
  padding-left: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
}

.zone-block:first-child .zone-group-title {
  margin-top: 0.75rem;
}

.row {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 0.75rem;
  align-items: stretch;
  margin-bottom: 0.85rem;
  margin-left: -220px;
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

.group-box {
  position: relative;
  border: 1px solid rgba(125, 211, 192, 0.28);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  box-shadow: inset 0 0 0 1px rgba(16, 21, 28, 0.25);
  padding: 0.65rem 0.5rem 0.75rem;
}

.contract-lane {
  position: relative;
  min-height: 96px;
  margin-bottom: 0.55rem;
}

.contract-lane:last-child { margin-bottom: 0; }

.contract-track {
  position: relative;
  min-height: 96px;
}

.contract-bar,
.contract-extension {
  position: absolute;
  top: 8px;
  height: 50px;
  border-radius: 8px;
  padding: 0.4rem 0.6rem;
  overflow: hidden;
  color: #10151c;
  box-shadow: inset 0 0 0 1px rgba(16, 21, 28, 0.25);
  z-index: 2;
}

.contract-extension {
  z-index: 1;
  border-style: dashed;
  border-width: 1px;
  border-color: rgba(16, 21, 28, 0.35);
}

.contract-bar a {
  color: inherit;
  text-decoration: none;
}

.contract-bar .title {
  font-size: 0.86rem;
  font-weight: 700;
  line-height: 1.15;
  margin-bottom: 0.15rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.contract-bar .meta {
  font-size: 0.64rem;
  line-height: 1.25;
  opacity: 0.92;
}

.po-rail {
  position: absolute;
  left: 0;
  right: 0;
  top: 44px;
  height: 22px;
  z-index: 3;
}

.po-marker {
  position: absolute;
  bottom: 0;
  transform: translateX(-50%);
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 1px solid rgba(125, 211, 192, 0.55);
  background: rgba(16, 21, 28, 0.88);
  color: var(--accent);
  font-size: 0.58rem;
  font-weight: 800;
  line-height: 20px;
  text-align: center;
  letter-spacing: -0.02em;
}

.end-marker {
  position: absolute;
  top: 14px;
  transform: translateX(-50%);
  z-index: 4;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 800;
  line-height: 1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
}

.end-marker.terminate {
  background: #e85d4c;
  color: #fff;
  border: 1px solid #c94a3a;
}

.end-marker.tbc {
  background: rgba(143, 160, 181, 0.35);
  color: var(--text);
  border: 1px solid rgba(143, 160, 181, 0.55);
}
"""

ROADMAP_BODY = """
  <div class="legend">
    <span><i class="swatch" style="background:#5b8def"></i>Current contract</span>
    <span><i class="swatch" style="background:#8fa0b5"></i>Archive</span>
    <span><i class="swatch" style="background:rgba(91,141,239,0.35);border:1px dashed rgba(16,21,28,0.35)"></i>Renewal extension</span>
    <span><span class="po-marker" style="position:static;display:inline-block;transform:none;vertical-align:middle;margin-right:0.2rem">PO</span> annual PO renewal</span>
    <span><span class="end-marker terminate" style="position:static;display:inline-flex;transform:none;vertical-align:middle;width:22px;height:22px;font-size:0.8rem;margin-right:0.2rem">✕</span> terminate</span>
    <span><span class="end-marker tbc" style="position:static;display:inline-flex;transform:none;vertical-align:middle;width:22px;height:22px;font-size:0.8rem;margin-right:0.2rem">?</span> TBC</span>
  </div>

  <div class="timeline-wrap">
    <div id="timeline"></div>
  </div>

  <p class="site-hint">
    Contracts are grouped by zone and sub-zone. Bars show contract start and end dates.
    PO markers sit on each annual renewal date (start of term, not the final end date).
    At contract end, a semi-transparent extension shows planned renewals; terminate and TBC
    contracts show ✕ and ? instead.
  </p>
"""

ROADMAP_JS = r"""
<script>
  const STATUS_COLORS = {
    Current: "#5b8def",
    Archive: "#8fa0b5",
  };

  function parseDate(value) {
    if (!value) return null;
    const [y, m, d] = value.split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  }

  function addYearsMs(ms, years) {
    const d = new Date(ms);
    return Date.UTC(d.getUTCFullYear() + years, d.getUTCMonth(), d.getUTCDate());
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

  fetch("/run-contracts/roadmap/data")
    .then((r) => r.json())
    .then((payload) => renderRoadmap(payload.contracts || []));

  function renderRoadmap(contracts) {
    const root = document.getElementById("timeline");
    const dated = contracts.filter((c) => c.contract_start_date && c.contract_end_date);
    if (!dated.length) {
      root.textContent = "No run contract dates available.";
      return;
    }

    const allDates = [];
    for (const contract of dated) {
      const start = parseDate(contract.contract_start_date);
      const end = parseDate(contract.contract_end_date);
      allDates.push(start, end);
      if (contract.extension_years) {
        allDates.push(addYearsMs(end, contract.extension_years));
      }
      (contract.po_dates || []).forEach((d) => {
        const when = parseDate(d);
        if (when) allDates.push(when);
      });
    }

    const rangeStart = startOfYear(Math.min(...allDates));
    const maxYear = new Date(Math.max(...allDates)).getUTCFullYear();
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

    const byZone = {};
    for (const contract of dated) {
      const zoneName = contract.zone_name || "Unassigned zone";
      const subName = contract.sub_zone_name || "Unassigned sub-zone";
      ((byZone[zoneName] ||= {})[subName] ||= []).push(contract);
    }

    for (const [zoneName, subZones] of Object.entries(byZone)) {
      const zoneGroup = document.createElement("div");
      zoneGroup.className = "zone-group zone-block";

      const zoneTitle = document.createElement("h2");
      zoneTitle.className = "zone-group-title";
      zoneTitle.textContent = `Zone: ${zoneName}`;
      zoneGroup.appendChild(zoneTitle);

      for (const [subName, items] of Object.entries(subZones)) {
        const row = document.createElement("div");
        row.className = "row";

        const label = document.createElement("div");
        label.className = "row-label";
        label.innerHTML = `
          <strong>SubZone: ${subName}</strong>
          ${items.length} contract${items.length === 1 ? "" : "s"}
        `;

        const box = document.createElement("div");
        box.className = "group-box";

        items.forEach((contract) => {
          const lane = document.createElement("div");
          lane.className = "contract-lane";

          const track = document.createElement("div");
          track.className = "contract-track";

          const start = parseDate(contract.contract_start_date);
          const end = parseDate(contract.contract_end_date);
          const left = pct(start, rangeStart, rangeEnd);
          const width = Math.max(pct(end, rangeStart, rangeEnd) - left, 2.5);
          const color = STATUS_COLORS[contract.contract_status] || "#7eb6ff";
          const action = contract.next_renewal_action || "TBC";
          const extensionYears = contract.extension_years || 0;

          const bar = document.createElement("div");
          bar.className = "contract-bar";
          bar.style.left = left + "%";
          bar.style.width = width + "%";
          bar.style.background = `linear-gradient(180deg, ${color}, ${color}dd)`;
          bar.innerHTML = `
            <div class="title"><a href="/run-contracts/${contract.id}">${contract.title}</a></div>
            <div class="meta">
              ${contract.id} · ${contract.contract_start_date} → ${contract.contract_end_date}<br />
              ${contract.service_type} · ${action}
            </div>
          `;
          track.appendChild(bar);

          if (extensionYears > 0) {
            const extStart = end;
            const extEnd = addYearsMs(end, extensionYears);
            const extLeft = pct(extStart, rangeStart, rangeEnd);
            const extWidth = Math.max(
              pct(extEnd, rangeStart, rangeEnd) - extLeft,
              2.5
            );
            const extension = document.createElement("div");
            extension.className = "contract-extension";
            extension.style.left = extLeft + "%";
            extension.style.width = extWidth + "%";
            extension.style.background = `linear-gradient(180deg, ${color}66, ${color}44)`;
            extension.title = `${action} · ${extensionYears} year extension`;
            track.appendChild(extension);
          } else if (action === "Terminate") {
            const marker = document.createElement("div");
            marker.className = "end-marker terminate";
            marker.style.left = pct(end, rangeStart, rangeEnd) + "%";
            marker.title = "Planned termination";
            marker.textContent = "✕";
            track.appendChild(marker);
          } else if (action === "TBC") {
            const marker = document.createElement("div");
            marker.className = "end-marker tbc";
            marker.style.left = pct(end, rangeStart, rangeEnd) + "%";
            marker.title = "Renewal decision TBC";
            marker.textContent = "?";
            track.appendChild(marker);
          }

          const poRail = document.createElement("div");
          poRail.className = "po-rail";
          (contract.po_dates || []).forEach((poDate) => {
            const when = parseDate(poDate);
            if (!when) return;
            const po = document.createElement("div");
            po.className = "po-marker";
            po.style.left = pct(when, rangeStart, rangeEnd) + "%";
            po.title = `PO renewal · ${poDate}`;
            po.textContent = "PO";
            poRail.appendChild(po);
          });
          track.appendChild(poRail);

          lane.appendChild(track);
          box.appendChild(lane);
        });

        row.appendChild(label);
        row.appendChild(box);
        zoneGroup.appendChild(row);
      }

      rows.appendChild(zoneGroup);
    }
  }
</script>
"""


@run_contract_roadmap_bp.route("/run-contracts/roadmap")
def run_contract_roadmap_page():
    return render_page(
        title="Run Contract Roadmap",
        subtitle="Grouped by zone and sub-zone · contract bars · PO renewals · next renewal action",
        active="Run Contract Roadmap",
        body=ROADMAP_BODY,
        extra_css=EXTRA_CSS,
        extra_js=ROADMAP_JS,
        wide=True,
    )


@run_contract_roadmap_bp.route("/run-contracts/roadmap/data")
def run_contract_roadmap_data():
    return jsonify(fetch_run_contract_roadmap())
