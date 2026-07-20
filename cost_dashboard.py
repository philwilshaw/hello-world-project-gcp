"""
Cost dashboard: zone spend by year (table + stacked bars) and top projects.
"""

from flask import Blueprint

from db import fetch_cost_dashboard
from ui import esc, render_page

cost_dashboard_bp = Blueprint("cost_dashboard", __name__)


def _money(value):
    return f"£{float(value):,.0f}"


def _millions(value):
    return f"£{float(value) / 1_000_000:.1f}m"


EXTRA_CSS = r"""
.cost-section { margin-bottom: 2rem; }
.cost-section h2 {
  font-size: 1.35rem;
  margin: 0 0 0.75rem;
}
.cost-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem 1.2rem;
  margin: 0 0 0.85rem;
  color: var(--muted);
  font-size: 0.82rem;
}
.cost-legend .swatch.capex { background: #5b8def; }
.cost-legend .swatch.opex { background: #7dd3c0; }
.cost-legend .swatch.total { background: rgba(245, 215, 110, 0.45); border: 1px solid rgba(245, 215, 110, 0.55); }

.cost-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.cost-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.82rem;
}

.cost-table th,
.cost-table td {
  padding: 0.55rem 0.65rem;
  text-align: right;
  white-space: nowrap;
  border-bottom: 1px solid var(--line);
}

.cost-table th:first-child,
.cost-table td:first-child {
  text-align: left;
  position: sticky;
  left: 0;
  background: #141b24;
  z-index: 1;
}

.cost-table thead .year-head th {
  text-align: center;
  font-size: 0.78rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--text);
  background: rgba(0, 0, 0, 0.22);
  border-bottom: 1px solid var(--line);
}

.cost-table thead .metric-head th {
  color: var(--muted);
  font-weight: 600;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: rgba(0, 0, 0, 0.14);
}

.cost-table .year-gap {
  width: 14px;
  min-width: 14px;
  padding: 0 !important;
  border-bottom: none !important;
  background: transparent !important;
}

.cost-table .total-col {
  background: rgba(245, 215, 110, 0.08);
}

.cost-table thead .total-col {
  background: rgba(245, 215, 110, 0.14);
}

.cost-table tbody tr:hover td {
  background: rgba(125, 211, 192, 0.06);
}

.cost-table tbody tr:hover td:first-child {
  background: #182230;
}

.cost-table .grand-row td {
  font-weight: 700;
  background: rgba(125, 211, 192, 0.08);
  border-bottom: none;
}

.cost-table .grand-row td:first-child {
  background: rgba(125, 211, 192, 0.1);
}

.cost-table .grand-row .total-col {
  background: rgba(245, 215, 110, 0.16);
}

.chart-wrap {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.85rem 0.75rem 0.7rem;
  overflow: visible;
}

.zone-chart {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 0.55rem;
  width: 100%;
}

.zone-group {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.year-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.18rem;
  min-height: 150px;
}

.year-bar-group {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.year-bar-stack {
  width: 100%;
  max-width: 34px;
  display: flex;
  flex-direction: column-reverse;
  border-radius: 5px 5px 2px 2px;
  overflow: hidden;
  min-height: 2px;
  box-shadow: inset 0 0 0 1px rgba(16, 21, 28, 0.25);
}

.seg-capex { background: linear-gradient(180deg, #7aa6f5, #5b8def); }
.seg-opex { background: linear-gradient(180deg, #9be0d2, #7dd3c0); }

.year-bar-value {
  font-size: 0.58rem;
  font-weight: 650;
  color: var(--text);
  margin-bottom: 0.18rem;
  white-space: nowrap;
  line-height: 1;
}

.year-bar-caption {
  margin-top: 0.28rem;
  font-size: 0.62rem;
  color: var(--muted);
  line-height: 1.1;
  white-space: nowrap;
}

.zone-caption {
  margin-top: 0.4rem;
  padding-top: 0.35rem;
  border-top: 1px solid rgba(43, 58, 77, 0.75);
  text-align: center;
  font-size: 0.7rem;
  font-weight: 650;
  color: var(--text);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.top-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.85rem 1rem 1rem;
}

.top-card h3 {
  font-size: 1.05rem;
  margin: 0 0 0.7rem;
}

.top-list {
  list-style: none;
  display: grid;
  gap: 0.45rem;
}

.top-list li {
  display: grid;
  grid-template-columns: 1.6rem 1fr auto;
  gap: 0.55rem;
  align-items: baseline;
  padding: 0.45rem 0.55rem;
  border: 1px solid rgba(43, 58, 77, 0.7);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.12);
}

.top-list .rank {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 650;
}

.top-list .title-link {
  font-size: 0.88rem;
  font-weight: 650;
  min-width: 0;
}

.top-list .amount {
  color: var(--muted);
  font-size: 0.78rem;
  white-space: nowrap;
}

.top-list .empty {
  color: var(--muted);
  font-size: 0.85rem;
  padding: 0.35rem 0;
}

@media (max-width: 860px) {
  .top-lists { grid-template-columns: 1fr; }
}
"""


def _table_html(data):
    years = data["years"]
    year_heads = ['<th scope="col"></th>']
    metric_heads = ['<th scope="col">Zone</th>']
    for i, year in enumerate(years):
        if i:
            year_heads.append('<th class="year-gap" aria-hidden="true"></th>')
            metric_heads.append('<th class="year-gap" aria-hidden="true"></th>')
        year_heads.append(f'<th colspan="3">{esc(year)}</th>')
        metric_heads.extend(
            [
                "<th>Capex</th>",
                "<th>Opex</th>",
                '<th class="total-col">Total</th>',
            ]
        )

    body_rows = []
    for zone in data["zones"]:
        cells = [f"<td>{esc(zone['zone_name'])}</td>"]
        for i, year in enumerate(years):
            if i:
                cells.append('<td class="year-gap" aria-hidden="true"></td>')
            y = zone["years"][year]
            cells.extend(
                [
                    f"<td>{esc(_money(y['capex']))}</td>",
                    f"<td>{esc(_money(y['opex']))}</td>",
                    f'<td class="total-col">{esc(_money(y["total"]))}</td>',
                ]
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    grand = data["grand_total"]
    grand_cells = ["<td>All zones</td>"]
    for i, year in enumerate(years):
        if i:
            grand_cells.append('<td class="year-gap" aria-hidden="true"></td>')
        y = grand["years"][year]
        grand_cells.extend(
            [
                f"<td>{esc(_money(y['capex']))}</td>",
                f"<td>{esc(_money(y['opex']))}</td>",
                f'<td class="total-col">{esc(_money(y["total"]))}</td>',
            ]
        )
    body_rows.append(f'<tr class="grand-row">{"".join(grand_cells)}</tr>')

    return f"""
    <div class="cost-table-wrap">
      <table class="cost-table">
        <thead>
          <tr class="year-head">{"".join(year_heads)}</tr>
          <tr class="metric-head">{"".join(metric_heads)}</tr>
        </thead>
        <tbody>
          {"".join(body_rows)}
        </tbody>
      </table>
    </div>
    """


def _chart_html(data):
    max_total = 0.0
    for zone in data["zones"]:
        for year in data["years"]:
            max_total = max(max_total, zone["years"][year]["total"])
    max_total = max(max_total, 1.0)
    chart_px = 140

    groups = []
    for zone in data["zones"]:
        bars = []
        for year in data["years"]:
            y = zone["years"][year]
            total = y["total"]
            year_label = str(year)
            if total <= 0:
                bars.append(
                    f"""
                    <div class="year-bar-group" title="{esc(zone['zone_name'])} · {esc(year_label)} · £0.0m">
                      <div class="year-bar-value">£0.0m</div>
                      <div class="year-bar-stack" style="height:2px"></div>
                      <div class="year-bar-caption">{esc(year_label)}</div>
                    </div>
                    """
                )
                continue
            height = max(int(round((total / max_total) * chart_px)), 8)
            capex_h = int(round((y["capex"] / total) * height)) if total else 0
            opex_h = max(height - capex_h, 0)
            bars.append(
                f"""
                <div class="year-bar-group" title="{esc(zone['zone_name'])} · {esc(year_label)} · Capex {esc(_money(y['capex']))} · Opex {esc(_money(y['opex']))}">
                  <div class="year-bar-value">{esc(_millions(total))}</div>
                  <div class="year-bar-stack" style="height:{height}px">
                    <div class="seg-capex" style="height:{capex_h}px"></div>
                    <div class="seg-opex" style="height:{opex_h}px"></div>
                  </div>
                  <div class="year-bar-caption">{esc(year_label)}</div>
                </div>
                """
            )
        groups.append(
            f"""
            <div class="zone-group">
              <div class="year-bars">{"".join(bars)}</div>
              <div class="zone-caption" title="{esc(zone['zone_name'])}">{esc(zone['zone_name'])}</div>
            </div>
            """
        )

    return f'<div class="chart-wrap"><div class="zone-chart">{"".join(groups)}</div></div>'


def _top_list_html(*, heading, items, empty_label, href_prefix, value_key, value_format):
    if not items:
        return f"""
        <div class="top-card">
          <h3>{esc(heading)}</h3>
          <p class="empty">{esc(empty_label)}</p>
        </div>
        """
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            f"""
            <li>
              <span class="rank">{index}</span>
              <a class="title-link" href="{esc(href_prefix)}{esc(item['id'])}">{esc(item['title'])}</a>
              <span class="amount">{esc(value_format(item[value_key]))}</span>
            </li>
            """
        )
    return f"""
    <div class="top-card">
      <h3>{esc(heading)}</h3>
      <ol class="top-list">{"".join(rows)}</ol>
    </div>
    """


@cost_dashboard_bp.route("/cost-dashboard")
def cost_dashboard_page():
    data = fetch_cost_dashboard()
    body = f"""
    <section class="cost-section">
      <h2>Cost by zone and year</h2>
      <div class="cost-legend">
        <span><i class="swatch capex"></i>Capex</span>
        <span><i class="swatch opex"></i>Opex</span>
        <span><i class="swatch total"></i>Total (shaded)</span>
      </div>
      {_table_html(data)}
    </section>

    <section class="cost-section">
      <h2>Spend by zone · stacked Capex / Opex</h2>
      <div class="cost-legend">
        <span><i class="swatch capex"></i>Capex</span>
        <span><i class="swatch opex"></i>Opex</span>
      </div>
      {_chart_html(data)}
    </section>

    <section class="cost-section">
      <h2>Top lists</h2>
      <div class="top-lists">
        {_top_list_html(
            heading="Top 10 projects · 2026",
            items=data["top_projects"][2026],
            empty_label="No project spend in 2026",
            href_prefix="/projects/",
            value_key="total",
            value_format=_money,
        )}
        {_top_list_html(
            heading="Top 10 projects · 2027",
            items=data["top_projects"][2027],
            empty_label="No project spend in 2027",
            href_prefix="/projects/",
            value_key="total",
            value_format=_money,
        )}
        {_top_list_html(
            heading="Top 10 run contracts by value",
            items=data["top_run_contracts"],
            empty_label="No run contract spend",
            href_prefix="/run-contracts/",
            value_key="total",
            value_format=_money,
        )}
        {_top_list_html(
            heading="Top 10 risks by risk score",
            items=data["top_risks"],
            empty_label="No risks",
            href_prefix="/risks/",
            value_key="risk_score",
            value_format=lambda score: f"Score {score}/10",
        )}
      </div>
    </section>
    """
    return render_page(
        title="Cost Dashboard",
        subtitle="Budget spend by zone and year · stacked Capex / Opex · top projects, contracts, and risks",
        active="Cost Dashboard",
        body=body,
        extra_css=EXTRA_CSS,
        wide=True,
    )
