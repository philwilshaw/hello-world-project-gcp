"""
List and detail pages for projects, risks, and architecture components.

Detail pages support adding/removing persistent links via a typedropdown
combobox UI and JSON API endpoints.
"""

import html
import re

from flask import Blueprint, abort, jsonify, render_template_string, request

from db import (
    ARCHITECTURE_RELATIONSHIPS,
    RISK_RELATIONSHIPS,
    add_link,
    fetch_all_architecture,
    fetch_all_projects,
    fetch_all_risks,
    fetch_architecture_detail,
    fetch_project_detail,
    fetch_risk_detail,
    get_db_status,
    remove_link,
)

catalog_bp = Blueprint("catalog", __name__)

BASE_STYLES = """
:root {
  --bg: #10151c;
  --panel: #182230;
  --text: #eef3f8;
  --muted: #8fa0b5;
  --line: #2b3a4d;
  --accent: #7dd3c0;
  --link: #8eb6ff;
  --danger: #c94c3f;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  background:
    radial-gradient(ellipse at 15% 0%, #1b2a3b 0%, transparent 45%),
    linear-gradient(180deg, #121820 0%, var(--bg) 100%);
  color: var(--text);
  min-height: 100vh;
  padding-bottom: 2.5rem;
}
header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: baseline;
  gap: 1rem;
  flex-wrap: wrap;
}
header h1 { font-size: 1.2rem; font-weight: 650; }
header p { color: var(--muted); font-size: 0.85rem; }
nav {
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  font-size: 0.85rem;
}
nav a, a { color: var(--link); text-decoration: none; }
nav a:hover, a:hover { text-decoration: underline; }
main { padding: 1.25rem 1.5rem; max-width: 1100px; }
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
th, td {
  padding: 0.7rem 0.8rem;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-weight: 600;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: rgba(0,0,0,0.18);
}
tr:last-child td { border-bottom: none; }
.title-link {
  color: var(--accent);
  font-weight: 650;
}
.detail-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
  padding: 1.1rem 1.2rem;
  margin-bottom: 1.25rem;
}
.detail-card h2 {
  font-size: 1.35rem;
  margin-bottom: 0.85rem;
}
.fields {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 0.55rem 1rem;
  font-size: 0.92rem;
}
.fields dt { color: var(--muted); }
.fields dd { color: var(--text); }
.section-title {
  font-size: 1rem;
  margin: 1.4rem 0 0.7rem;
}
.linked-list {
  list-style: none;
  display: grid;
  gap: 0.55rem;
}
.linked-list li {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.7rem 0.85rem;
  background: rgba(255,255,255,0.02);
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
}
.linked-list .meta {
  color: var(--muted);
  font-size: 0.8rem;
  margin-top: 0.25rem;
}
.linked-list .item-main { min-width: 0; }
.empty { color: var(--muted); font-size: 0.9rem; }
.rag {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 650;
}
.rag.Green { background: #2f9e6b; color: #fff; }
.rag.Amber { background: #d4a017; color: #111; }
.rag.Red { background: #c94c3f; color: #fff; }
.link-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.65rem 0 1rem;
  align-items: center;
}
.link-form input[type="text"],
.link-form select {
  background: #121820;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.45rem 0.6rem;
  font: inherit;
  min-width: 180px;
}
.link-form input[type="text"] { min-width: min(280px, 100%); flex: 1; }
.link-form button,
button.remove-link {
  background: var(--accent);
  color: #102018;
  border: none;
  border-radius: 6px;
  padding: 0.45rem 0.75rem;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}
button.remove-link {
  background: transparent;
  color: var(--danger);
  border: 1px solid var(--danger);
  flex: 0 0 auto;
}
.link-form .hint, .form-status {
  width: 100%;
  color: var(--muted);
  font-size: 0.78rem;
}
.form-status.error { color: #ff8f84; }
.form-status.ok { color: var(--accent); }
.db-banner {
  margin: 0 0 1rem;
  padding: 0.65rem 0.8rem;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.03);
  font-size: 0.82rem;
  color: var(--muted);
}
.db-banner strong { color: var(--text); }
.db-banner.locked {
  border-color: #c94c3f55;
  background: #c94c3f18;
}
.db-banner.open {
  border-color: #2f9e6b55;
  background: #2f9e6b18;
}
.link-form.writes-locked input,
.link-form.writes-locked select,
.link-form.writes-locked button,
button.remove-link:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(0.4);
}
"""

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
    return html.escape(str(value), quote=True)


def _nav(active=None):
    links = [
        ("/", "Home"),
        ("/diagram", "Timeline"),
        ("/projects", "Projects"),
        ("/risks", "Risks"),
        ("/architecture", "Architecture"),
        ("/architecture/diagram", "Arch diagram"),
        ("/architecture/capabilities", "By capability"),
        ("/architecture/roadmap", "Arch roadmap"),
    ]
    parts = []
    for href, label in links:
        if label.lower() == (active or "").lower():
            parts.append(f"<span style='color:var(--accent)'>{_esc(label)}</span>")
        else:
            parts.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
    return " ".join(parts)


def _money(value):
    return f"£{value:,.0f}"


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


def _db_banner(status=None):
    status = status or get_db_status()
    if status["writes_enabled"]:
        return (
            "<div class='db-banner open'>"
            f"<strong>Environment:</strong> {_esc(status['environment'])} · "
            "<strong>Database changes:</strong> allowed · "
            "This database is backed up hourly and reset to the last safe copy at midnight."
            "</div>"
        )
    return (
        "<div class='db-banner locked'>"
        f"<strong>Environment:</strong> {_esc(status['environment'])} · "
        "<strong>Database changes:</strong> locked · "
        "Add/remove link controls are disabled. "
        "The database is still reset to the last safe copy at midnight."
        "</div>"
    )


def _remove_button(edge_id, label, writes_enabled=True):
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
              <td>{_esc(p['accountable_contact_name'])}</td>
              <td>{_esc(p['start_date'])}</td>
              <td>{_esc(p['end_date'])}</td>
              <td><span class="rag {_esc(p['rag_status'])}">{_esc(p['rag_status'])}</span></td>
              <td>{_esc(_money(p['capex_gbp']))}</td>
              <td>{_esc(_money(p['opex_gbp']))}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Projects",
        subtitle="All projects from the projects table",
        styles=BASE_STYLES,
        nav=_nav("Projects"),
        db_banner=_db_banner(),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Accountable contact</th><th>Start</th><th>End</th>
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
              <td>{_esc(r['value'])}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Risks",
        subtitle="All corporate risks from the risks table",
        styles=BASE_STYLES,
        nav=_nav("Risks"),
        db_banner=_db_banner(),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Impact</th><th>Proximity</th><th>Value</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="6" class="empty">No risks</td></tr>',
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
              <td>{_esc(a['capability'])}</td>
              <td>{_esc(a['outlook'])}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Architecture",
        subtitle="All architecture components from the architecture_components table",
        styles=BASE_STYLES,
        nav=_nav("Architecture"),
        db_banner=_db_banner(),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Type</th><th>Owner</th><th>Capability</th><th>Outlook</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="7" class="empty">No architecture components</td></tr>',
    )


@catalog_bp.route("/projects/<project_id>")
def project_detail(project_id):
    data = fetch_project_detail(project_id)
    if data is None:
        abort(404)
    p = data["project"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]
    form_lock = "" if writes_enabled else " writes-locked"
    form_disabled = "" if writes_enabled else " disabled"

    linked_risk_ids = {r["id"] for r in data["linked_risks"]}
    linked_arch_ids = {a["id"] for a in data["linked_architecture"]}
    risk_options = [r for r in fetch_all_risks() if r["id"] not in linked_risk_ids]
    arch_options = [
        a for a in fetch_all_architecture() if a["id"] not in linked_arch_ids
    ]

    risk_items = [
        _linked_item(
            f"/risks/{r['id']}",
            f"{r['id']}: {r['title']}",
            f"Relationship: {r['relationship']}",
            r["edge_id"],
            f"{r['id']} {r['relationship']}",
            writes_enabled=writes_enabled,
        )
        for r in data["linked_risks"]
    ]
    arch_items = [
        _linked_item(
            f"/architecture/{a['id']}",
            f"{a['id']}: {a['title']}",
            f"Relationship: {a['relationship']}",
            a["edge_id"],
            f"{a['id']} {a['relationship']}",
            writes_enabled=writes_enabled,
        )
        for a in data["linked_architecture"]
    ]

    fields = f"""
      <dt>ID</dt><dd>{_esc(p['id'])}</dd>
      <dt>Title</dt><dd>{_esc(p['title'])}</dd>
      <dt>Description</dt><dd>{_esc(p['description'])}</dd>
      <dt>Accountable contact</dt><dd>{_esc(p['accountable_contact_name'])}</dd>
      <dt>Start date</dt><dd>{_esc(p['start_date'])}</dd>
      <dt>End date</dt><dd>{_esc(p['end_date'])}</dd>
      <dt>RAG status</dt><dd><span class="rag {_esc(p['rag_status'])}">{_esc(p['rag_status'])}</span></dd>
      <dt>Capex (GBP)</dt><dd>{_esc(_money(p['capex_gbp']))}</dd>
      <dt>Opex (GBP)</dt><dd>{_esc(_money(p['opex_gbp']))}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked risks</h3>
      {"<ul class='linked-list'>" + "".join(risk_items) + "</ul>" if risk_items else "<p class='empty'>No linked risks</p>"}
      <form class="link-form{form_lock}" data-mode="from-project" data-project-id="{_esc(p['id'])}" data-linked-type="risk">
        <input type="text" name="item" list="risk-options" placeholder="Select or type a risk" autocomplete="off"{form_disabled} />
        <select name="relationship"{form_disabled}>{_relationship_options(RISK_RELATIONSHIPS)}</select>
        <button type="submit"{form_disabled}>Add risk link</button>
        <div class="hint">Pick from the dropdown or type an ID / name.</div>
        <div class="form-status"></div>
      </form>
      {_datalist(risk_options, "risk-options")}

      <h3 class="section-title">Linked architecture</h3>
      {"<ul class='linked-list'>" + "".join(arch_items) + "</ul>" if arch_items else "<p class='empty'>No linked architecture</p>"}
      <form class="link-form{form_lock}" data-mode="from-project" data-project-id="{_esc(p['id'])}" data-linked-type="architecture">
        <input type="text" name="item" list="arch-options" placeholder="Select or type an architecture item" autocomplete="off"{form_disabled} />
        <select name="relationship"{form_disabled}>{_relationship_options(ARCHITECTURE_RELATIONSHIPS)}</select>
        <button type="submit"{form_disabled}>Add architecture link</button>
        <div class="hint">Pick from the dropdown or type an ID / name.</div>
        <div class="form-status"></div>
      </form>
      {_datalist(arch_options, "arch-options")}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=p["title"],
        subtitle=f"Project detail · {p['id']}",
        styles=BASE_STYLES,
        nav=_nav("Projects"),
        db_banner=_db_banner(status),
        back_href="/projects",
        back_label="← All projects",
        fields=fields,
        linked=linked,
        link_script=LINK_SCRIPT,
    )


@catalog_bp.route("/risks/<risk_id>")
def risk_detail(risk_id):
    data = fetch_risk_detail(risk_id)
    if data is None:
        abort(404)
    r = data["risk"]
    status = get_db_status()
    writes_enabled = status["writes_enabled"]
    form_lock = "" if writes_enabled else " writes-locked"
    form_disabled = "" if writes_enabled else " disabled"

    linked_project_ids = {p["id"] for p in data["linked_projects"]}
    project_options = [
        p for p in fetch_all_projects() if p["id"] not in linked_project_ids
    ]

    project_items = [
        _linked_item(
            f"/projects/{p['id']}",
            f"{p['id']}: {p['title']}",
            f"Relationship: {p['relationship']} · RAG {p['rag_status']}",
            p["edge_id"],
            f"{p['id']} {p['relationship']}",
            writes_enabled=writes_enabled,
        )
        for p in data["linked_projects"]
    ]

    fields = f"""
      <dt>ID</dt><dd>{_esc(r['id'])}</dd>
      <dt>Title</dt><dd>{_esc(r['title'])}</dd>
      <dt>Description</dt><dd>{_esc(r['description'])}</dd>
      <dt>Impact</dt><dd>{_esc(r['impact'])}</dd>
      <dt>Proximity</dt><dd>{_esc(r['proximity'])}</dd>
      <dt>Value</dt><dd>{_esc(r['value'])}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked projects</h3>
      {"<ul class='linked-list'>" + "".join(project_items) + "</ul>" if project_items else "<p class='empty'>No linked projects</p>"}
      <form class="link-form{form_lock}" data-mode="to-project" data-item-id="{_esc(r['id'])}" data-linked-type="risk">
        <input type="text" name="item" list="project-options" placeholder="Select or type a project" autocomplete="off"{form_disabled} />
        <select name="relationship"{form_disabled}>{_relationship_options(RISK_RELATIONSHIPS)}</select>
        <button type="submit"{form_disabled}>Add project link</button>
        <div class="hint">Pick from the dropdown or type an ID / name.</div>
        <div class="form-status"></div>
      </form>
      {_datalist(project_options, "project-options")}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=r["title"],
        subtitle=f"Risk detail · {r['id']}",
        styles=BASE_STYLES,
        nav=_nav("Risks"),
        db_banner=_db_banner(status),
        back_href="/risks",
        back_label="← All risks",
        fields=fields,
        linked=linked,
        link_script=LINK_SCRIPT,
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
    form_lock = "" if writes_enabled else " writes-locked"
    form_disabled = "" if writes_enabled else " disabled"

    linked_project_ids = {p["id"] for p in data["linked_projects"]}
    project_options = [
        p for p in fetch_all_projects() if p["id"] not in linked_project_ids
    ]

    project_items = [
        _linked_item(
            f"/projects/{p['id']}",
            f"{p['id']}: {p['title']}",
            f"Relationship: {p['relationship']} · RAG {p['rag_status']}",
            p["edge_id"],
            f"{p['id']} {p['relationship']}",
            writes_enabled=writes_enabled,
        )
        for p in data["linked_projects"]
    ]

    fields = f"""
      <dt>ID</dt><dd>{_esc(a['id'])}</dd>
      <dt>Title</dt><dd>{_esc(a['title'])}</dd>
      <dt>Description</dt><dd>{_esc(a['description'])}</dd>
      <dt>Component type</dt><dd>{_esc(a['component_type'])}</dd>
      <dt>Owner</dt><dd>{_esc(a['owner'])}</dd>
      <dt>Capability</dt><dd>{_esc(a['capability'])}</dd>
      <dt>Arch outlook</dt><dd>{_esc(a['outlook'])}</dd>
      <dt>Implemented</dt><dd>{_esc(a.get('implemented_date') or '—')}</dd>
      <dt>Go live</dt><dd>{_esc(a.get('go_live_date') or '—')}</dd>
      <dt>Decommissioned</dt><dd>{_esc(a.get('decommissioned_date') or '—')}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked projects</h3>
      {"<ul class='linked-list'>" + "".join(project_items) + "</ul>" if project_items else "<p class='empty'>No linked projects</p>"}
      <form class="link-form{form_lock}" data-mode="to-project" data-item-id="{_esc(a['id'])}" data-linked-type="architecture">
        <input type="text" name="item" list="project-options" placeholder="Select or type a project" autocomplete="off"{form_disabled} />
        <select name="relationship"{form_disabled}>{_relationship_options(ARCHITECTURE_RELATIONSHIPS)}</select>
        <button type="submit"{form_disabled}>Add project link</button>
        <div class="hint">Pick from the dropdown or type an ID / name.</div>
        <div class="form-status"></div>
      </form>
      {_datalist(project_options, "project-options")}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=a["title"],
        subtitle=f"Architecture detail · {a['id']}",
        styles=BASE_STYLES,
        nav=_nav("Architecture"),
        db_banner=_db_banner(status),
        back_href="/architecture",
        back_label="← All architecture",
        fields=fields,
        linked=linked,
        link_script=LINK_SCRIPT,
    )


LIST_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <style>{{ styles }}</style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p>{{ subtitle }}</p>
    <nav>{{ nav|safe }}</nav>
  </header>
  <main>
    {{ db_banner|safe }}
    <div class="table-wrap">
      <table>
        <thead><tr>{{ table_head|safe }}</tr></thead>
        <tbody>{{ table_body|safe }}</tbody>
      </table>
    </div>
  </main>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <style>{{ styles }}</style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p>{{ subtitle }}</p>
    <nav>{{ nav|safe }}</nav>
  </header>
  <main>
    {{ db_banner|safe }}
    <p style="margin-bottom:1rem"><a href="{{ back_href }}">{{ back_label }}</a></p>
    <section class="detail-card">
      <h2>{{ title }}</h2>
      <dl class="fields">{{ fields|safe }}</dl>
    </section>
    {{ linked|safe }}
  </main>
  {{ link_script|safe }}
</body>
</html>
"""
