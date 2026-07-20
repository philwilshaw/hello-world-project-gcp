"""
List and detail pages for projects, risks, architecture, budgets, and run contracts.

Detail pages support adding/removing persistent links via a typedropdown
combobox UI and JSON API endpoints.
"""

import re

from flask import Blueprint, abort, jsonify, request

from db import (
    ARCHITECTURE_RELATIONSHIPS,
    BUDGET_RELATIONSHIPS,
    RISK_RELATIONSHIPS,
    RUN_CONTRACT_RELATIONSHIPS,
    add_link,
    fetch_all_architecture,
    fetch_all_budgets,
    fetch_all_projects,
    fetch_all_risks,
    fetch_all_run_contracts,
    fetch_architecture_detail,
    fetch_budget_detail,
    fetch_project_detail,
    fetch_risk_detail,
    fetch_run_contract_detail,
    get_db_status,
    remove_link,
)
from ui import esc, render_page

catalog_bp = Blueprint("catalog", __name__)

LINK_SCRIPT = r"""
<script>
  function parseSelectedId(raw) {
    const value = (raw || "").trim();
    if (!value) return "";
    const match = value.match(/^([A-Za-z0-9_-]+)\s*[—\-:]/);
    if (match) return match[1];
    if (/^[A-Za-z0-9_-]+$/.test(value)) return value;
    return "";
  }

  async function addLinkFromForm(form) {
    const status = form.querySelector(".form-status");
    status.textContent = "";
    status.className = "form-status";

    const selectedId = parseSelectedId(form.querySelector("[name=item]").value);
    const relationship = form.querySelector("[name=relationship]").value;

    let payload;
    if (form.dataset.mode === "to-project") {
      payload = {
        project_id: selectedId,
        linked_type: form.dataset.linkedType,
        linked_id: form.dataset.itemId,
        relationship,
      };
    } else {
      payload = {
        project_id: form.dataset.projectId,
        linked_type: form.dataset.linkedType,
        linked_id: selectedId,
        relationship,
      };
    }

    if (!payload.project_id || !payload.linked_id) {
      status.textContent = "Choose an item from the list (or type its ID).";
      status.classList.add("error");
      return;
    }

    if (form.classList.contains("writes-locked")) {
      status.textContent = "Database changes are currently locked.";
      status.classList.add("error");
      return;
    }

    const response = await fetch("/api/links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      status.textContent = data.error || "Could not add link";
      status.classList.add("error");
      return;
    }
    window.location.reload();
  }

  async function removeLink(edgeId, label, button) {
    if (button && button.disabled) return;
    const ok = window.confirm(
      "Remove this link" + (label ? ` (${label})` : "") + "?\n\nThis cannot be undone from this screen."
    );
    if (!ok) return;

    const response = await fetch("/api/links/" + encodeURIComponent(edgeId), {
      method: "DELETE",
    });
    const data = await response.json();
    if (!response.ok) {
      window.alert(data.error || "Could not remove link");
      return;
    }
    window.location.reload();
  }

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.classList.contains("link-form")) return;
    event.preventDefault();
    addLinkFromForm(form);
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button.remove-link");
    if (!button) return;
    event.preventDefault();
    removeLink(button.dataset.edgeId, button.dataset.label || "", button);
  });
</script>
"""


def _esc(value):
    return esc(value)


def _money(value):
    try:
        return f"£{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _option_label(item):
    return f"{item['id']} — {item['title']}"


def _datalist(options, list_id):
    opts = "".join(
        f'<option value="{_esc(_option_label(item))}"></option>' for item in options
    )
    return f'<datalist id="{_esc(list_id)}">{opts}</datalist>'


def _relationship_options(values):
    return "".join(
        f'<option value="{_esc(value)}">{_esc(value)}</option>' for value in values
    )


def _remove_button(edge_id, label, writes_enabled=True):
    if not edge_id:
        return ""
    disabled = "" if writes_enabled else " disabled"
    return (
        f'<button type="button" class="remove-link" '
        f'data-edge-id="{_esc(edge_id)}" data-label="{_esc(label)}"{disabled}>Remove</button>'
    )


def _linked_item(href, text, meta, edge_id, label, writes_enabled=True):
    return f"""
      <li>
        <div class="item-main">
          <a class="title-link" href="{_esc(href)}">{_esc(text)}</a>
          <div class="meta">{_esc(meta)}</div>
        </div>
        {_remove_button(edge_id, label, writes_enabled=writes_enabled)}
      </li>
    """


def _item_meta(item, *, relationship_key="relationship"):
    parts = [f"Relationship: {item.get(relationship_key, '—')}"]
    if item.get("via_project_id"):
        parts.append(f"via {item['via_project_id']}")
    return " · ".join(parts)


def _link_form(
    *,
    title,
    empty_label,
    items_html,
    form_attrs,
    placeholder,
    list_id,
    options,
    relationships,
    button_label,
    form_lock,
    form_disabled,
):
    list_html = (
        f"<ul class='linked-list'>{''.join(items_html)}</ul>"
        if items_html
        else f"<p class='empty'>{_esc(empty_label)}</p>"
    )
    return f"""
      <h3 class="section-title">{_esc(title)}</h3>
      {list_html}
      <form class="link-form{form_lock}" {form_attrs}>
        <input type="text" name="item" list="{_esc(list_id)}" placeholder="{_esc(placeholder)}" autocomplete="off"{form_disabled} />
        <select name="relationship"{form_disabled}>{_relationship_options(relationships)}</select>
        <button type="submit"{form_disabled}>{_esc(button_label)}</button>
        <div class="hint">Pick from the dropdown or type an ID / name.</div>
        <div class="form-status"></div>
      </form>
      {_datalist(options, list_id)}
    """


def _list_page(*, title, subtitle, active, table_head, table_body, wide=False):
    body = f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{table_head}</tr></thead>
        <tbody>{table_body}</tbody>
      </table>
    </div>
    """
    return render_page(
        title=title,
        subtitle=subtitle,
        active=active,
        body=body,
        wide=wide,
    )


def _detail_page(
    *,
    title,
    subtitle,
    active,
    back_href,
    back_label,
    fields,
    linked,
):
    body = f"""
    <p style="margin-bottom:1rem"><a href="{_esc(back_href)}">{_esc(back_label)}</a></p>
    <section class="detail-card">
      <h2>{_esc(title)}</h2>
      <dl class="fields">{fields}</dl>
    </section>
    {linked}
    """
    return render_page(
        title=title,
        subtitle=subtitle,
        active=active,
        body=body,
        extra_js=LINK_SCRIPT,
    )


def _render_all_linked_sections(
    *,
    data,
    writes_enabled,
    project_id=None,
    item_id=None,
    linked_type_for_project_form=None,
):
    """
    Render projects / risks / architecture / budgets / run contracts sections.

    When project_id is set, forms add links from that project.
    When item_id + linked_type_for_project_form are set, forms add a project link
    to this item (to-project mode). Cross-linked siblings are list-only.
    """
    form_lock = "" if writes_enabled else " writes-locked"
    form_disabled = "" if writes_enabled else " disabled"

    linked_projects = data.get("linked_projects") or []
    linked_risks = data.get("linked_risks") or []
    linked_architecture = data.get("linked_architecture") or []
    linked_budgets = data.get("linked_budgets") or []
    linked_run_contracts = data.get("linked_run_contracts") or []

    project_items = [
        _linked_item(
            f"/projects/{p['id']}",
            f"{p['id']}: {p['title']}",
            _item_meta(p) + (f" · RAG {p.get('rag_status', '')}" if p.get("rag_status") else ""),
            p.get("edge_id"),
            f"{p['id']} {p.get('relationship', '')}",
            writes_enabled=writes_enabled,
        )
        for p in linked_projects
    ]
    risk_items = [
        _linked_item(
            f"/risks/{r['id']}",
            f"{r['id']}: {r['title']}",
            _item_meta(r),
            r.get("edge_id"),
            f"{r['id']} {r.get('relationship', '')}",
            writes_enabled=writes_enabled,
        )
        for r in linked_risks
    ]
    arch_items = [
        _linked_item(
            f"/architecture/{a['id']}",
            f"{a['id']}: {a['title']}",
            _item_meta(a),
            a.get("edge_id"),
            f"{a['id']} {a.get('relationship', '')}",
            writes_enabled=writes_enabled,
        )
        for a in linked_architecture
    ]
    budget_items = [
        _linked_item(
            f"/budgets/{b['id']}",
            f"{b['id']}: {b['title']}",
            _item_meta(b),
            b.get("edge_id"),
            f"{b['id']} {b.get('relationship', '')}",
            writes_enabled=writes_enabled,
        )
        for b in linked_budgets
    ]
    run_items = [
        _linked_item(
            f"/run-contracts/{rc['id']}",
            f"{rc['id']}: {rc['title']}",
            _item_meta(rc),
            rc.get("edge_id"),
            f"{rc['id']} {rc.get('relationship', '')}",
            writes_enabled=writes_enabled,
        )
        for rc in linked_run_contracts
    ]

    sections = []

    if project_id:
        linked_risk_ids = {r["id"] for r in linked_risks}
        linked_arch_ids = {a["id"] for a in linked_architecture}
        linked_budget_ids = {b["id"] for b in linked_budgets}
        linked_run_ids = {rc["id"] for rc in linked_run_contracts}

        sections.append(
            _link_form(
                title="Linked risks",
                empty_label="No linked risks",
                items_html=risk_items,
                form_attrs=f'data-mode="from-project" data-project-id="{_esc(project_id)}" data-linked-type="risk"',
                placeholder="Select or type a risk",
                list_id="risk-options",
                options=[r for r in fetch_all_risks() if r["id"] not in linked_risk_ids],
                relationships=RISK_RELATIONSHIPS,
                button_label="Add risk link",
                form_lock=form_lock,
                form_disabled=form_disabled,
            )
        )
        sections.append(
            _link_form(
                title="Linked architecture",
                empty_label="No linked architecture",
                items_html=arch_items,
                form_attrs=f'data-mode="from-project" data-project-id="{_esc(project_id)}" data-linked-type="architecture"',
                placeholder="Select or type an architecture item",
                list_id="arch-options",
                options=[
                    a
                    for a in fetch_all_architecture()
                    if a["id"] not in linked_arch_ids
                ],
                relationships=ARCHITECTURE_RELATIONSHIPS,
                button_label="Add architecture link",
                form_lock=form_lock,
                form_disabled=form_disabled,
            )
        )
        sections.append(
            _link_form(
                title="Linked budgets",
                empty_label="No linked budgets",
                items_html=budget_items,
                form_attrs=f'data-mode="from-project" data-project-id="{_esc(project_id)}" data-linked-type="budget"',
                placeholder="Select or type a budget",
                list_id="budget-options",
                options=[
                    b for b in fetch_all_budgets() if b["id"] not in linked_budget_ids
                ],
                relationships=BUDGET_RELATIONSHIPS,
                button_label="Add budget link",
                form_lock=form_lock,
                form_disabled=form_disabled,
            )
        )
        sections.append(
            _link_form(
                title="Linked run contracts",
                empty_label="No linked run contracts",
                items_html=run_items,
                form_attrs=f'data-mode="from-project" data-project-id="{_esc(project_id)}" data-linked-type="run_contract"',
                placeholder="Select or type a run contract",
                list_id="run-options",
                options=[
                    rc
                    for rc in fetch_all_run_contracts()
                    if rc["id"] not in linked_run_ids
                ],
                relationships=RUN_CONTRACT_RELATIONSHIPS,
                button_label="Add run contract link",
                form_lock=form_lock,
                form_disabled=form_disabled,
            )
        )
    else:
        rels = {
            "risk": RISK_RELATIONSHIPS,
            "architecture": ARCHITECTURE_RELATIONSHIPS,
            "budget": BUDGET_RELATIONSHIPS,
            "run_contract": RUN_CONTRACT_RELATIONSHIPS,
        }.get(linked_type_for_project_form, RISK_RELATIONSHIPS)

        linked_project_ids = {p["id"] for p in linked_projects}
        sections.append(
            _link_form(
                title="Linked projects",
                empty_label="No linked projects",
                items_html=project_items,
                form_attrs=(
                    f'data-mode="to-project" data-item-id="{_esc(item_id)}" '
                    f'data-linked-type="{_esc(linked_type_for_project_form)}"'
                ),
                placeholder="Select or type a project",
                list_id="project-options",
                options=[
                    p for p in fetch_all_projects() if p["id"] not in linked_project_ids
                ],
                relationships=rels,
                button_label="Add project link",
                form_lock=form_lock,
                form_disabled=form_disabled,
            )
        )

        def _readonly_section(title, empty_label, items):
            list_html = (
                f"<ul class='linked-list'>{''.join(items)}</ul>"
                if items
                else f"<p class='empty'>{_esc(empty_label)}</p>"
            )
            return f"""
              <h3 class="section-title">{_esc(title)}</h3>
              {list_html}
              <p class="hint">Shown via shared project links.</p>
            """

        if linked_type_for_project_form != "risk":
            sections.append(
                _readonly_section("Linked risks", "No linked risks", risk_items)
            )
        if linked_type_for_project_form != "architecture":
            sections.append(
                _readonly_section(
                    "Linked architecture", "No linked architecture", arch_items
                )
            )
        if linked_type_for_project_form != "budget":
            sections.append(
                _readonly_section("Linked budgets", "No linked budgets", budget_items)
            )
        if linked_type_for_project_form != "run_contract":
            sections.append(
                _readonly_section(
                    "Linked run contracts", "No linked run contracts", run_items
                )
            )

    return "\n".join(sections)


@catalog_bp.route("/api/links", methods=["POST"])
def api_add_link():
    payload = request.get_json(silent=True) or {}
    project_id = str(payload.get("project_id", "")).strip()
    linked_type = str(payload.get("linked_type", "")).strip()
    linked_id = str(payload.get("linked_id", "")).strip()
    relationship = str(payload.get("relationship", "")).strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", project_id or ""):
        return jsonify({"error": "invalid project_id"}), 400
    if not re.fullmatch(r"[A-Za-z0-9_-]+", linked_id or ""):
        return jsonify({"error": "invalid linked_id"}), 400

    ok, message, edge = add_link(project_id, linked_type, linked_id, relationship)
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify({"ok": True, "edge": edge}), 201


@catalog_bp.route("/api/links/<edge_id>", methods=["DELETE"])
def api_remove_link(edge_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", edge_id or ""):
        return jsonify({"error": "invalid edge id"}), 400
    ok, message = remove_link(edge_id)
    if not ok:
        return jsonify({"error": message}), 404
    return jsonify({"ok": True, "message": message})


@catalog_bp.route("/projects")
def projects_list():
    rows = fetch_all_projects()
    body_rows = []
    for p in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{_esc(p['id'])}</td>
              <td><a class="title-link" href="/projects/{_esc(p['id'])}">{_esc(p['title'])}</a></td>
              <td>{_esc(p['description'])}</td>
              <td>{_esc(p.get('budget_status', '—'))}</td>
              <td>{_esc(p['start_date'])}</td>
              <td>{_esc(p['end_date'])}</td>
              <td><span class="rag {_esc(p['rag_status'])}">{_esc(p['rag_status'])}</span></td>
              <td>{_esc(_money(p['capex_gbp']))}</td>
              <td>{_esc(_money(p['opex_gbp']))}</td>
            </tr>
            """
        )
    return _list_page(
        title="Project List",
        subtitle="All projects from the projects table",
        active="Project List",
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Budget status</th><th>Start</th><th>End</th>
          <th>RAG</th><th>Capex</th><th>Opex</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="9" class="empty">No projects</td></tr>',
    )


@catalog_bp.route("/risks")
def risks_list():
    rows = fetch_all_risks()
    body_rows = []
    for r in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{_esc(r['id'])}</td>
              <td><a class="title-link" href="/risks/{_esc(r['id'])}">{_esc(r['title'])}</a></td>
              <td>{_esc(r['description'])}</td>
              <td>{_esc(r['impact'])}</td>
              <td>{_esc(r['proximity'])}</td>
              <td>{_esc(r.get('risk_score', ''))}</td>
              <td>{_esc(r.get('status', ''))}</td>
            </tr>
            """
        )
    return _list_page(
        title="Risk List",
        subtitle="All corporate risks from the risks table",
        active="Risk List",
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Impact band</th><th>Proximity</th><th>Score</th><th>Status</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="7" class="empty">No risks</td></tr>',
    )


@catalog_bp.route("/architecture")
def architecture_list():
    rows = fetch_all_architecture()
    body_rows = []
    for a in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{_esc(a['id'])}</td>
              <td><a class="title-link" href="/architecture/{_esc(a['id'])}">{_esc(a['title'])}</a></td>
              <td>{_esc(a['description'])}</td>
              <td>{_esc(a['component_type'])}</td>
              <td>{_esc(a['owner'])}</td>
              <td>{_esc(a.get('capability', ''))}</td>
              <td>{_esc(a['outlook'])}</td>
              <td>{_esc(a.get('deployment_state', ''))}</td>
            </tr>
            """
        )
    return _list_page(
        title="Architecture List",
        subtitle="All architecture components from the architecture_components table",
        active="Architecture List",
        table_head="""
          <th>ID</th><th>Name</th><th>Description</th>
          <th>Host type</th><th>Architect</th><th>Capability</th><th>Outlook</th><th>State</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="8" class="empty">No architecture components</td></tr>',
    )


@catalog_bp.route("/budgets")
def budgets_list():
    rows = fetch_all_budgets()
    body_rows = []
    for b in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{_esc(b['line_id'])}</td>
              <td>{_esc(b['budget_id'])}</td>
              <td><a class="title-link" href="/budgets/{_esc(b['line_id'])}">{_esc(b['title'])}</a></td>
              <td>{_esc(b['description'])}</td>
              <td>{_esc(b['status'])}</td>
              <td>{_esc(b['category'])}</td>
              <td>{_esc(b['spend_type'])}</td>
              <td>{_esc(b.get('zone_name', ''))}</td>
              <td>{_esc(b.get('sub_zone_name', ''))}</td>
              <td>{_esc(_money(b['capex_2026']))}</td>
              <td>{_esc(_money(b['opex_2026']))}</td>
              <td>{_esc(_money(b['capex_2027']))}</td>
              <td>{_esc(_money(b['opex_2027']))}</td>
              <td>{_esc(_money(b['capex_2028']))}</td>
              <td>{_esc(_money(b['opex_2028']))}</td>
              <td>{_esc(_money(b['capex_2029']))}</td>
              <td>{_esc(_money(b['opex_2029']))}</td>
              <td>{_esc(b['contact'])}</td>
            </tr>
            """
        )
    return _list_page(
        title="Budget List",
        subtitle="All budget line items from the budgets table",
        active="Budget List",
        wide=True,
        table_head="""
          <th>Line ID</th><th>Budget ID</th><th>Title</th><th>Description</th>
          <th>Status</th><th>Category</th><th>Spend Type</th>
          <th>Zone</th><th>SubZone</th>
          <th>2026 Capex</th><th>2026 Opex</th>
          <th>2027 Capex</th><th>2027 Opex</th>
          <th>2028 Capex</th><th>2028 Opex</th>
          <th>2029 Capex</th><th>2029 Opex</th>
          <th>Contact</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="18" class="empty">No budgets</td></tr>',
    )


@catalog_bp.route("/run-contracts")
def run_contracts_list():
    rows = fetch_all_run_contracts()
    body_rows = []
    for rc in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{_esc(rc['fin_id'])}</td>
              <td>{_esc(rc['service_type'])}</td>
              <td>{_esc(rc['linked_budget_id'])}</td>
              <td>{_esc(rc['vendor_name'])}</td>
              <td>{_esc(rc['manufacturer'])}</td>
              <td><a class="title-link" href="/run-contracts/{_esc(rc['fin_id'])}">{_esc(rc['contract_name'])}</a></td>
              <td>{_esc(rc['description'])}</td>
              <td>{_esc(rc['detailed_description'])}</td>
              <td>{_esc(rc['contract_start_date'])}</td>
              <td>{_esc(rc['contract_end_date'])}</td>
              <td>{_esc(rc['po_renewal_date'])}</td>
              <td>{_esc(rc['contract_status'])}</td>
              <td>{_esc(rc['vendor_manager'])}</td>
              <td>{_esc(rc['operational_owner'])}</td>
              <td>{_esc(rc.get('zone_name', ''))}</td>
              <td>{_esc(rc.get('sub_zone_name', ''))}</td>
            </tr>
            """
        )
    return _list_page(
        title="Run Contract List",
        subtitle="All run contracts from the run_contracts table",
        active="Run Contract List",
        wide=True,
        table_head="""
          <th>Fin ID</th><th>Service Type</th><th>Linked Budget ID</th>
          <th>VendorName</th><th>Manufacturer</th><th>ContractName</th>
          <th>Description</th><th>DetailedDescription</th>
          <th>ContractStartDate</th><th>ContractEndDate</th><th>PORenewalDate</th>
          <th>ContractStatus</th><th>VendorManager</th><th>OperationalOwner</th>
          <th>Zone</th><th>Subzone</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="16" class="empty">No run contracts</td></tr>',
    )


@catalog_bp.route("/projects/<project_id>")
def project_detail(project_id):
    data = fetch_project_detail(project_id)
    if data is None:
        abort(404)
    p = data["project"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]

    fields = f"""
      <dt>ID</dt><dd>{_esc(p['id'])}</dd>
      <dt>Title</dt><dd>{_esc(p['title'])}</dd>
      <dt>Description</dt><dd>{_esc(p['description'])}</dd>
      <dt>Budget ID</dt><dd>{_esc(p['budget_id'])}</dd>
      <dt>Budget status</dt><dd>{_esc(p.get('budget_status', '—'))}</dd>
      <dt>Sub-zone</dt><dd>{_esc(p.get('sub_zone_name', '—'))}</dd>
      <dt>Zone</dt><dd>{_esc(p.get('zone_name', '—'))}</dd>
      <dt>2027 priority</dt><dd>{_esc(p.get('priority_2027') or '—')}</dd>
      <dt>Timeline start</dt><dd>{_esc(p['start_date'])}</dd>
      <dt>Timeline end</dt><dd>{_esc(p['end_date'])}</dd>
      <dt>RAG status</dt><dd><span class="rag {_esc(p['rag_status'])}">{_esc(p['rag_status'])}</span></dd>
      <dt>Capex (GBP)</dt><dd>{_esc(_money(p['capex_gbp']))}</dd>
      <dt>Opex (GBP)</dt><dd>{_esc(_money(p['opex_gbp']))}</dd>
      <dt>Outcomes</dt><dd><pre class="field-block">{_esc(p.get('outcomes', ''))}</pre></dd>
      <dt>Delivery approach</dt><dd><pre class="field-block">{_esc(p.get('delivery_approach', ''))}</pre></dd>
    """

    return _detail_page(
        title=f"Project: {p['title']}",
        subtitle=f"Project detail · {p['id']}",
        active="Project List",
        back_href="/projects",
        back_label="← Project List",
        fields=fields,
        linked=_render_all_linked_sections(
            data=data, writes_enabled=writes_enabled, project_id=p["id"]
        ),
    )


@catalog_bp.route("/risks/<risk_id>")
def risk_detail(risk_id):
    data = fetch_risk_detail(risk_id)
    if data is None:
        abort(404)
    r = data["risk"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]

    fields = f"""
      <dt>ID</dt><dd>{_esc(r['id'])}</dd>
      <dt>Title</dt><dd>{_esc(r['title'])}</dd>
      <dt>Description</dt><dd>{_esc(r['description'])}</dd>
      <dt>Sub-zone</dt><dd>{_esc(r.get('sub_zone_name', '—'))}</dd>
      <dt>Zone</dt><dd>{_esc(r.get('zone_name', '—'))}</dd>
      <dt>Impact band</dt><dd>{_esc(r['impact'])}</dd>
      <dt>Proximity band</dt><dd>{_esc(r['proximity'])}</dd>
      <dt>Risk score</dt><dd>{_esc(r.get('risk_score', ''))}</dd>
      <dt>Status</dt><dd>{_esc(r.get('status', ''))}</dd>
      <dt>Risk response</dt><dd>{_esc(r.get('risk_response', ''))}</dd>
      <dt>Category</dt><dd>{_esc(r.get('category', ''))}</dd>
      <dt>Risk owner</dt><dd>{_esc(r.get('risk_owner', ''))}</dd>
      <dt>Likelihood</dt><dd>{_esc(r.get('current_likelihood', ''))}</dd>
      <dt>Date created</dt><dd>{_esc(r.get('date_created', ''))}</dd>
      <dt>Date closed</dt><dd>{_esc(r.get('date_closed') or '—')}</dd>
    """

    return _detail_page(
        title=f"Risk: {r['title']}",
        subtitle=f"Risk detail · {r['id']}",
        active="Risk List",
        back_href="/risks",
        back_label="← Risk List",
        fields=fields,
        linked=_render_all_linked_sections(
            data=data,
            writes_enabled=writes_enabled,
            item_id=r["id"],
            linked_type_for_project_form="risk",
        ),
    )


@catalog_bp.route("/architecture/<architecture_id>")
def architecture_detail(architecture_id):
    if architecture_id in {"diagram", "capabilities", "roadmap"}:
        abort(404)
    data = fetch_architecture_detail(architecture_id)
    if data is None:
        abort(404)
    a = data["architecture"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]

    fields = f"""
      <dt>ID</dt><dd>{_esc(a['id'])}</dd>
      <dt>Name</dt><dd>{_esc(a['title'])}</dd>
      <dt>Description</dt><dd>{_esc(a['description'])}</dd>
      <dt>Comments</dt><dd>{_esc(a.get('comments') or '—')}</dd>
      <dt>Host type</dt><dd>{_esc(a['component_type'])}</dd>
      <dt>Architect</dt><dd>{_esc(a['owner'])}</dd>
      <dt>Sub-zone</dt><dd>{_esc(a.get('sub_zone_name', '—'))}</dd>
      <dt>Zone</dt><dd>{_esc(a.get('zone_name', '—'))}</dd>
      <dt>Capability</dt><dd>{_esc(a.get('capability', ''))}</dd>
      <dt>Architecture outlook</dt><dd>{_esc(a['outlook'])}</dd>
      <dt>Deployment state</dt><dd>{_esc(a.get('deployment_state', ''))}</dd>
      <dt>Deployment date</dt><dd>{_esc(a.get('deployment_date') or '—')}</dd>
      <dt>Decommission date</dt><dd>{_esc(a.get('decommission_date') or '—')}</dd>
      <dt>In scope of ESA</dt><dd>{_esc(a.get('in_scope_of_esa', ''))}</dd>
      <dt>Class of service</dt><dd>{_esc(a.get('class_of_service', ''))}</dd>
      <dt>Replaced by</dt><dd>{_esc(a.get('replaced_by_arch_id') or '—')}</dd>
      <dt>Support L1 / L2 / L3</dt>
      <dd>{_esc(a.get('support_partner_l1', ''))} / {_esc(a.get('support_partner_l2', ''))} / {_esc(a.get('support_partner_l3', ''))}</dd>
      <dt>Vendor</dt><dd>{_esc(a.get('vendor', ''))}</dd>
    """

    return _detail_page(
        title=f"Architecture Component: {a['title']}",
        subtitle=f"Architecture detail · {a['id']}",
        active="Architecture List",
        back_href="/architecture",
        back_label="← Architecture List",
        fields=fields,
        linked=_render_all_linked_sections(
            data=data,
            writes_enabled=writes_enabled,
            item_id=a["id"],
            linked_type_for_project_form="architecture",
        ),
    )


@catalog_bp.route("/budgets/<budget_id>")
def budget_detail(budget_id):
    data = fetch_budget_detail(budget_id)
    if data is None:
        abort(404)
    b = data["budget"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]

    fields = f"""
      <dt>Line ID</dt><dd>{_esc(b['line_id'])}</dd>
      <dt>Budget ID</dt><dd>{_esc(b['budget_id'])}</dd>
      <dt>Title</dt><dd>{_esc(b['title'])}</dd>
      <dt>Description</dt><dd>{_esc(b['description'])}</dd>
      <dt>Status</dt><dd>{_esc(b['status'])}</dd>
      <dt>Category</dt><dd>{_esc(b['category'])}</dd>
      <dt>Spend Type</dt><dd>{_esc(b['spend_type'])}</dd>
      <dt>Zone</dt><dd>{_esc(b.get('zone_name', '—'))}</dd>
      <dt>SubZone</dt><dd>{_esc(b.get('sub_zone_name', '—'))}</dd>
      <dt>2026 Capex / Opex</dt><dd>{_esc(_money(b['capex_2026']))} / {_esc(_money(b['opex_2026']))}</dd>
      <dt>2027 Capex / Opex</dt><dd>{_esc(_money(b['capex_2027']))} / {_esc(_money(b['opex_2027']))}</dd>
      <dt>2028 Capex / Opex</dt><dd>{_esc(_money(b['capex_2028']))} / {_esc(_money(b['opex_2028']))}</dd>
      <dt>2029 Capex / Opex</dt><dd>{_esc(_money(b['capex_2029']))} / {_esc(_money(b['opex_2029']))}</dd>
      <dt>Contact</dt><dd>{_esc(b['contact'])}</dd>
    """

    return _detail_page(
        title=f"Budget: {b['title']}",
        subtitle=f"Budget detail · {b['line_id']}",
        active="Budget List",
        back_href="/budgets",
        back_label="← Budget List",
        fields=fields,
        linked=_render_all_linked_sections(
            data=data,
            writes_enabled=writes_enabled,
            item_id=b["line_id"],
            linked_type_for_project_form="budget",
        ),
    )


@catalog_bp.route("/run-contracts/<fin_id>")
def run_contract_detail(fin_id):
    data = fetch_run_contract_detail(fin_id)
    if data is None:
        abort(404)
    rc = data["run_contract"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]

    fields = f"""
      <dt>Fin ID</dt><dd>{_esc(rc['fin_id'])}</dd>
      <dt>Service Type</dt><dd>{_esc(rc['service_type'])}</dd>
      <dt>Linked Budget ID</dt><dd>{_esc(rc['linked_budget_id'])}</dd>
      <dt>Vendor</dt><dd>{_esc(rc['vendor_name'])}</dd>
      <dt>Manufacturer</dt><dd>{_esc(rc['manufacturer'])}</dd>
      <dt>Contract name</dt><dd>{_esc(rc['contract_name'])}</dd>
      <dt>Description</dt><dd>{_esc(rc['description'])}</dd>
      <dt>Detailed description</dt><dd>{_esc(rc['detailed_description'])}</dd>
      <dt>Start / End</dt><dd>{_esc(rc['contract_start_date'])} → {_esc(rc['contract_end_date'])}</dd>
      <dt>PO renewal date</dt><dd>{_esc(rc['po_renewal_date'])}</dd>
      <dt>Status</dt><dd>{_esc(rc['contract_status'])}</dd>
      <dt>Vendor manager</dt><dd>{_esc(rc['vendor_manager'])}</dd>
      <dt>Operational owner</dt><dd>{_esc(rc['operational_owner'])}</dd>
      <dt>Zone</dt><dd>{_esc(rc.get('zone_name', '—'))}</dd>
      <dt>Subzone</dt><dd>{_esc(rc.get('sub_zone_name', '—'))}</dd>
    """

    return _detail_page(
        title=f"Run Contract: {rc['title']}",
        subtitle=f"Run contract detail · {rc['fin_id']}",
        active="Run Contract List",
        back_href="/run-contracts",
        back_label="← Run Contract List",
        fields=fields,
        linked=_render_all_linked_sections(
            data=data,
            writes_enabled=writes_enabled,
            item_id=rc["fin_id"],
            linked_type_for_project_form="run_contract",
        ),
    )
