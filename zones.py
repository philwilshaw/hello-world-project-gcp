"""
Zones visualisation: L1 zones, L2 sub-zones, and L3 capabilities.
"""

from db import fetch_zones_tree
from ui import esc, render_page

from flask import Blueprint

zones_bp = Blueprint("zones", __name__)

EXTRA_CSS = """
.zones-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.5rem;
  margin-bottom: 0.85rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  font-size: 0.85rem;
}

.zones-controls label {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  cursor: pointer;
  user-select: none;
}

.zones-controls input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  accent-color: var(--accent);
  cursor: pointer;
}

.zones-grid.hide-l2 .sub-zone-block {
  display: none;
}

.zones-grid.hide-l3 .capability-list,
.zones-grid.hide-l3 .sub-zone-meta {
  display: none;
}

.zones-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  margin-bottom: 1.25rem;
  color: var(--muted);
  font-size: 0.82rem;
}

.zones-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.legend-pill {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-pill.l1 { background: var(--accent); }
.legend-pill.l2 { background: var(--link); }
.legend-pill.l3 { background: var(--muted); }

.zones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.1rem;
}

.zone-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.zone-card-header {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 0.85rem;
  padding: 1rem;
  border-bottom: 1px solid var(--line);
  background: rgba(125, 211, 192, 0.06);
}

.zone-owner-photo {
  width: 88px;
  height: 88px;
  border-radius: 10px;
  object-fit: cover;
  border: 2px solid rgba(125, 211, 192, 0.35);
}

.zone-card-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
}

.zone-card-owner {
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 650;
  margin-bottom: 0.35rem;
}

.zone-card-desc {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.35;
}

.zone-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.75rem;
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--line);
  font-size: 0.75rem;
  color: var(--muted);
}

.zone-stats strong {
  color: var(--text);
}

.zone-body {
  padding: 0.85rem 1rem 1rem;
  display: grid;
  gap: 0.75rem;
}

.sub-zone-block {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(142, 182, 255, 0.04);
  padding: 0.65rem 0.75rem;
}

.sub-zone-title {
  font-size: 0.88rem;
  font-weight: 650;
  color: var(--link);
  margin-bottom: 0.35rem;
}

.sub-zone-meta {
  font-size: 0.72rem;
  color: var(--muted);
  margin-bottom: 0.45rem;
}

.capability-list {
  list-style: none;
  display: grid;
  gap: 0.28rem;
}

.capability-list li {
  font-size: 0.76rem;
  color: #c5d0dc;
  padding-left: 0.65rem;
  position: relative;
}

.capability-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.45em;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--muted);
}

.entity-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.45rem;
}

.entity-tag {
  font-size: 0.68rem;
  padding: 0.12rem 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--muted);
}

.entity-tag.has-items {
  border-color: rgba(125, 211, 192, 0.45);
  color: var(--accent);
}
"""

EXTRA_JS = """
<script>
  (function () {
    const grid = document.querySelector(".zones-grid");
    const toggleL2 = document.getElementById("zones-show-l2");
    const toggleL3 = document.getElementById("zones-show-l3");
    if (!grid || !toggleL2 || !toggleL3) return;

    function syncVisibility() {
      grid.classList.toggle("hide-l2", !toggleL2.checked);
      grid.classList.toggle("hide-l3", !toggleL3.checked);
    }

    toggleL2.addEventListener("change", syncVisibility);
    toggleL3.addEventListener("change", syncVisibility);
    syncVisibility();
  })();
</script>
"""


def _entity_tags(sub_zone: dict) -> str:
    tags = []
    for label, key in (
        ("Projects", "project_count"),
        ("Risks", "risk_count"),
        ("Architecture", "architecture_count"),
    ):
        count = sub_zone.get(key, 0)
        css = "entity-tag has-items" if count else "entity-tag"
        tags.append(f'<span class="{css}">{label}: {count}</span>')
    return "".join(tags)


def _zone_card(zone: dict) -> str:
    sub_blocks = []
    for sub_zone in zone["sub_zones"]:
        caps = "".join(
            f"<li>{esc(capability['name'])}</li>"
            for capability in sub_zone["capabilities"]
        )
        sub_blocks.append(
            f"""
            <div class="sub-zone-block">
              <div class="sub-zone-title">L2 · {esc(sub_zone['name'])}</div>
              <div class="sub-zone-meta">
                {len(sub_zone['capabilities'])} L3 capabilities
              </div>
              <ul class="capability-list">{caps}</ul>
              <div class="entity-tags">{_entity_tags(sub_zone)}</div>
            </div>
            """
        )

    return f"""
    <article class="zone-card">
      <div class="zone-card-header">
        <img class="zone-owner-photo" src="{esc(zone['owner_image'])}" alt="{esc(zone['owner_name'])}" loading="lazy" />
        <div>
          <div class="zone-card-title">L1 · {esc(zone['name'])}</div>
          <div class="zone-card-owner">Zone owner: {esc(zone['owner_name'])}</div>
          <p class="zone-card-desc">{esc(zone['description'])}</p>
        </div>
      </div>
      <div class="zone-stats">
        <span><strong>{zone['sub_zone_count']}</strong> sub-zones</span>
        <span><strong>{zone['capability_count']}</strong> capabilities</span>
        <span><strong>{zone['project_count']}</strong> projects</span>
        <span><strong>{zone['risk_count']}</strong> risks</span>
        <span><strong>{zone['architecture_count']}</strong> architecture</span>
      </div>
      <div class="zone-body">
        {"".join(sub_blocks)}
      </div>
    </article>
    """


@zones_bp.route("/zones")
def zones_page():
    data = fetch_zones_tree()
    cards = "".join(_zone_card(zone) for zone in data["zones"])
    body = f"""
<div class="zones-controls">
  <span>Show:</span>
  <label for="zones-show-l2">
    <input type="checkbox" id="zones-show-l2" checked />
    L2 sub-zones
  </label>
  <label for="zones-show-l3">
    <input type="checkbox" id="zones-show-l3" checked />
    L3 capabilities
  </label>
</div>
<div class="zones-legend">
  <span><i class="legend-pill l1"></i>L1 Zone</span>
  <span><i class="legend-pill l2"></i>L2 Sub-zone</span>
  <span><i class="legend-pill l3"></i>L3 Capability</span>
</div>
<div class="zones-grid">
  {cards}
</div>
"""
    return render_page(
        title="Zones",
        subtitle="L1 zones, L2 sub-zones, and L3 SaaS capabilities",
        active="Zones",
        body=body,
        extra_css=EXTRA_CSS,
        extra_js=EXTRA_JS,
    )
