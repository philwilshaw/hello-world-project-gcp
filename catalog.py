"""
List and detail pages for projects, risks, and architecture components.
"""

from flask import Blueprint, abort, render_template_string

from db import (
    fetch_all_architecture,
    fetch_all_projects,
    fetch_all_risks,
    fetch_architecture_detail,
    fetch_project_detail,
    fetch_risk_detail,
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
}
.linked-list .meta {
  color: var(--muted);
  font-size: 0.8rem;
  margin-top: 0.25rem;
}
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
"""


def _nav(active=None):
    links = [
        ("/", "Home"),
        ("/diagram", "Timeline"),
        ("/projects", "Projects"),
        ("/risks", "Risks"),
        ("/architecture", "Architecture"),
    ]
    parts = []
    for href, label in links:
        if label.lower() == (active or "").lower():
            parts.append(f"<span style='color:var(--accent)'>{label}</span>")
        else:
            parts.append(f'<a href="{href}">{label}</a>')
    return " ".join(parts)


def _money(value):
    return f"£{value:,.0f}"


@catalog_bp.route("/projects")
def projects_list():
    rows = fetch_all_projects()
    body_rows = []
    for p in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{p['id']}</td>
              <td><a class="title-link" href="/projects/{p['id']}">{p['title']}</a></td>
              <td>{p['description']}</td>
              <td>{p['accountable_contact_name']}</td>
              <td>{p['start_date']}</td>
              <td>{p['end_date']}</td>
              <td><span class="rag {p['rag_status']}">{p['rag_status']}</span></td>
              <td>{_money(p['capex_gbp'])}</td>
              <td>{_money(p['opex_gbp'])}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Projects",
        subtitle="All projects from the projects table",
        active="Projects",
        styles=BASE_STYLES,
        nav=_nav("Projects"),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Accountable contact</th><th>Start</th><th>End</th>
          <th>RAG</th><th>Capex</th><th>Opex</th>
        """,
        table_body="".join(body_rows) or '<tr><td colspan="9" class="empty">No projects</td></tr>',
    )


@catalog_bp.route("/risks")
def risks_list():
    rows = fetch_all_risks()
    body_rows = []
    for r in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{r['id']}</td>
              <td><a class="title-link" href="/risks/{r['id']}">{r['title']}</a></td>
              <td>{r['description']}</td>
              <td>{r['impact']}</td>
              <td>{r['proximity']}</td>
              <td>{r['value']}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Risks",
        subtitle="All corporate risks from the risks table",
        active="Risks",
        styles=BASE_STYLES,
        nav=_nav("Risks"),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Impact</th><th>Proximity</th><th>Value</th>
        """,
        table_body="".join(body_rows) or '<tr><td colspan="6" class="empty">No risks</td></tr>',
    )


@catalog_bp.route("/architecture")
def architecture_list():
    rows = fetch_all_architecture()
    body_rows = []
    for a in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{a['id']}</td>
              <td><a class="title-link" href="/architecture/{a['id']}">{a['title']}</a></td>
              <td>{a['description']}</td>
              <td>{a['component_type']}</td>
              <td>{a['owner']}</td>
            </tr>
            """
        )
    return render_template_string(
        LIST_TEMPLATE,
        title="Architecture",
        subtitle="All architecture components from the architecture_components table",
        active="Architecture",
        styles=BASE_STYLES,
        nav=_nav("Architecture"),
        table_head="""
          <th>ID</th><th>Title</th><th>Description</th>
          <th>Type</th><th>Owner</th>
        """,
        table_body="".join(body_rows)
        or '<tr><td colspan="5" class="empty">No architecture components</td></tr>',
    )


@catalog_bp.route("/projects/<project_id>")
def project_detail(project_id):
    data = fetch_project_detail(project_id)
    if data is None:
        abort(404)
    p = data["project"]

    risk_items = []
    for r in data["linked_risks"]:
        risk_items.append(
            f"""
            <li>
              <a class="title-link" href="/risks/{r['id']}">{r['id']}: {r['title']}</a>
              <div class="meta">Relationship: {r['relationship']}</div>
            </li>
            """
        )

    arch_items = []
    for a in data["linked_architecture"]:
        arch_items.append(
            f"""
            <li>
              <a class="title-link" href="/architecture/{a['id']}">{a['id']}: {a['title']}</a>
              <div class="meta">Relationship: {a['relationship']}</div>
            </li>
            """
        )

    fields = f"""
      <dt>ID</dt><dd>{p['id']}</dd>
      <dt>Title</dt><dd>{p['title']}</dd>
      <dt>Description</dt><dd>{p['description']}</dd>
      <dt>Accountable contact</dt><dd>{p['accountable_contact_name']}</dd>
      <dt>Start date</dt><dd>{p['start_date']}</dd>
      <dt>End date</dt><dd>{p['end_date']}</dd>
      <dt>RAG status</dt><dd><span class="rag {p['rag_status']}">{p['rag_status']}</span></dd>
      <dt>Capex (GBP)</dt><dd>{_money(p['capex_gbp'])}</dd>
      <dt>Opex (GBP)</dt><dd>{_money(p['opex_gbp'])}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked risks</h3>
      {"<ul class='linked-list'>" + "".join(risk_items) + "</ul>" if risk_items else "<p class='empty'>No linked risks</p>"}
      <h3 class="section-title">Linked architecture</h3>
      {"<ul class='linked-list'>" + "".join(arch_items) + "</ul>" if arch_items else "<p class='empty'>No linked architecture</p>"}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=p["title"],
        subtitle=f"Project detail · {p['id']}",
        active="Projects",
        styles=BASE_STYLES,
        nav=_nav("Projects"),
        back_href="/projects",
        back_label="← All projects",
        fields=fields,
        linked=linked,
    )


@catalog_bp.route("/risks/<risk_id>")
def risk_detail(risk_id):
    data = fetch_risk_detail(risk_id)
    if data is None:
        abort(404)
    r = data["risk"]

    project_items = []
    for p in data["linked_projects"]:
        project_items.append(
            f"""
            <li>
              <a class="title-link" href="/projects/{p['id']}">{p['id']}: {p['title']}</a>
              <div class="meta">Relationship: {p['relationship']} · RAG {p['rag_status']}</div>
            </li>
            """
        )

    fields = f"""
      <dt>ID</dt><dd>{r['id']}</dd>
      <dt>Title</dt><dd>{r['title']}</dd>
      <dt>Description</dt><dd>{r['description']}</dd>
      <dt>Impact</dt><dd>{r['impact']}</dd>
      <dt>Proximity</dt><dd>{r['proximity']}</dd>
      <dt>Value</dt><dd>{r['value']}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked projects</h3>
      {"<ul class='linked-list'>" + "".join(project_items) + "</ul>" if project_items else "<p class='empty'>No linked projects</p>"}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=r["title"],
        subtitle=f"Risk detail · {r['id']}",
        active="Risks",
        styles=BASE_STYLES,
        nav=_nav("Risks"),
        back_href="/risks",
        back_label="← All risks",
        fields=fields,
        linked=linked,
    )


@catalog_bp.route("/architecture/<architecture_id>")
def architecture_detail(architecture_id):
    data = fetch_architecture_detail(architecture_id)
    if data is None:
        abort(404)
    a = data["architecture"]

    project_items = []
    for p in data["linked_projects"]:
        project_items.append(
            f"""
            <li>
              <a class="title-link" href="/projects/{p['id']}">{p['id']}: {p['title']}</a>
              <div class="meta">Relationship: {p['relationship']} · RAG {p['rag_status']}</div>
            </li>
            """
        )

    fields = f"""
      <dt>ID</dt><dd>{a['id']}</dd>
      <dt>Title</dt><dd>{a['title']}</dd>
      <dt>Description</dt><dd>{a['description']}</dd>
      <dt>Component type</dt><dd>{a['component_type']}</dd>
      <dt>Owner</dt><dd>{a['owner']}</dd>
    """

    linked = f"""
      <h3 class="section-title">Linked projects</h3>
      {"<ul class='linked-list'>" + "".join(project_items) + "</ul>" if project_items else "<p class='empty'>No linked projects</p>"}
    """

    return render_template_string(
        DETAIL_TEMPLATE,
        title=a["title"],
        subtitle=f"Architecture detail · {a['id']}",
        active="Architecture",
        styles=BASE_STYLES,
        nav=_nav("Architecture"),
        back_href="/architecture",
        back_label="← All architecture",
        fields=fields,
        linked=linked,
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
    <p style="margin-bottom:1rem"><a href="{{ back_href }}">{{ back_label }}</a></p>
    <section class="detail-card">
      <h2>{{ title }}</h2>
      <dl class="fields">{{ fields|safe }}</dl>
    </section>
    {{ linked|safe }}
  </main>
</body>
</html>
"""
