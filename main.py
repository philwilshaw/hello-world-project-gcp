import os

from flask import Flask

from admin import admin_bp
from architecture_roadmap import architecture_roadmap_bp
from architecture_views import architecture_views_bp
from catalog import catalog_bp
from cost_dashboard import cost_dashboard_bp
from db import get_db_status, init_db
from diagram import diagram_bp
from run_contract_roadmap import run_contract_roadmap_bp
from sitemap import sitemap_bp
from zones import zones_bp
from ui import esc, register_layout, render_page

app = Flask(__name__)
app.register_blueprint(diagram_bp)
app.register_blueprint(architecture_roadmap_bp)
app.register_blueprint(architecture_views_bp)
app.register_blueprint(catalog_bp)
app.register_blueprint(cost_dashboard_bp)
app.register_blueprint(run_contract_roadmap_bp)
app.register_blueprint(sitemap_bp)
app.register_blueprint(zones_bp)
app.register_blueprint(admin_bp)
register_layout(app)
init_db()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")

HOME_CARDS = [
    {
        "href": "/zones",
        "title": "Zones",
        "blurb": "Explore the L1 / L2 / L3 operating hierarchy and zone owners.",
        "image": "/static/home/zones.svg",
        "theme": "zones",
    },
    {
        "href": "/projects",
        "title": "Project List",
        "blurb": "Browse every project with cost, dates, and RAG status.",
        "image": "/static/home/project-list.svg",
        "theme": "projects",
    },
    {
        "href": "/diagram",
        "title": "Project Roadmap",
        "blurb": "See project timelines grouped by zone and sub-zone.",
        "image": "/static/home/project-roadmap.svg",
        "theme": "projects",
    },
    {
        "href": "/architecture",
        "title": "Architecture List",
        "blurb": "Review architecture components and their outlook.",
        "image": "/static/home/architecture-list.svg",
        "theme": "architecture",
    },
    {
        "href": "/architecture/diagram",
        "title": "Architecture Diagram",
        "blurb": "Trace relationships between architecture elements.",
        "image": "/static/home/architecture-diagram.svg",
        "theme": "architecture",
    },
    {
        "href": "/architecture/capabilities",
        "title": "Architecture Model",
        "blurb": "Navigate Zone → SubZone → Capability structure.",
        "image": "/static/home/architecture-model.svg",
        "theme": "architecture",
    },
    {
        "href": "/architecture/roadmap",
        "title": "Architecture Roadmap",
        "blurb": "Follow component lifespans and project go-live impacts.",
        "image": "/static/home/architecture-roadmap.svg",
        "theme": "architecture",
    },
    {
        "href": "/risks",
        "title": "Risk List",
        "blurb": "Inspect corporate risks, scores, and responses.",
        "image": "/static/home/risk-list.svg",
        "theme": "risks",
    },
    {
        "href": "/cost-dashboard",
        "title": "Cost Dashboard",
        "blurb": "Compare Capex and Opex spend by zone and year.",
        "image": "/static/home/cost-dashboard.svg",
        "theme": "finance",
    },
    {
        "href": "/budgets",
        "title": "Budget List",
        "blurb": "Open budget lines that fund projects and contracts.",
        "image": "/static/home/budget-list.svg",
        "theme": "finance",
    },
    {
        "href": "/run-contracts",
        "title": "Run Contract List",
        "blurb": "Browse vendor run contracts and renewal dates.",
        "image": "/static/home/run-contract-list.svg",
        "theme": "finance",
    },
    {
        "href": "/run-contracts/roadmap",
        "title": "Run Contract Roadmap",
        "blurb": "Visualise contract terms, PO renewals, and next actions.",
        "image": "/static/home/run-contract-roadmap.svg",
        "theme": "finance",
    },
    {
        "href": "/about",
        "title": "About this site",
        "blurb": "How this demo was built, what was learned, and what is next.",
        "image": "/static/home/about.svg",
        "theme": "about",
    },
]

HOME_CSS = """
.home-intro {
  max-width: 46rem;
  margin: 0 0 1.75rem;
  color: var(--muted);
  font-size: 1.05rem;
  line-height: 1.55;
}
.home-intro strong {
  color: var(--text);
  font-weight: 650;
}
.home-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.15rem;
}
@media (max-width: 1100px) {
  .home-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .home-card-grid { grid-template-columns: 1fr; }
}
.home-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  background: rgba(255, 255, 255, 0.02);
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}
.home-card:hover {
  transform: translateY(-2px);
  text-decoration: none;
  background: rgba(255, 255, 255, 0.04);
}
.home-card-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: #10151c;
}
.home-card-body {
  padding: 0.95rem 1rem 1.1rem;
  border-top: 1px solid var(--line);
}
.home-card-kicker {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 0.3rem;
}
.home-card-title {
  font-size: 1.08rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
  color: var(--text);
}
.home-card-blurb {
  font-size: 0.88rem;
  line-height: 1.4;
  color: var(--muted);
}
.home-card.theme-zones {
  border-color: rgba(125, 211, 192, 0.35);
}
.home-card.theme-zones .home-card-kicker { color: #7dd3c0; }
.home-card.theme-zones:hover { border-color: rgba(125, 211, 192, 0.65); }
.home-card.theme-projects {
  border-color: rgba(91, 141, 239, 0.35);
}
.home-card.theme-projects .home-card-kicker { color: #5b8def; }
.home-card.theme-projects:hover { border-color: rgba(91, 141, 239, 0.65); }
.home-card.theme-architecture {
  border-color: rgba(240, 162, 2, 0.35);
}
.home-card.theme-architecture .home-card-kicker { color: #f0a202; }
.home-card.theme-architecture:hover { border-color: rgba(240, 162, 2, 0.65); }
.home-card.theme-risks {
  border-color: rgba(232, 93, 76, 0.35);
}
.home-card.theme-risks .home-card-kicker { color: #e85d4c; }
.home-card.theme-risks:hover { border-color: rgba(232, 93, 76, 0.65); }
.home-card.theme-finance {
  border-color: rgba(60, 179, 113, 0.35);
}
.home-card.theme-finance .home-card-kicker { color: #3cb371; }
.home-card.theme-finance:hover { border-color: rgba(60, 179, 113, 0.65); }
.home-card.theme-about {
  border-color: rgba(143, 160, 181, 0.35);
}
.home-card.theme-about .home-card-kicker { color: #8fa0b5; }
.home-card.theme-about:hover { border-color: rgba(143, 160, 181, 0.65); }
"""

THEME_LABELS = {
    "zones": "Zones",
    "projects": "Projects",
    "architecture": "Architecture",
    "risks": "Risks",
    "finance": "Finance",
    "about": "About",
}


def _home_cards_html() -> str:
    cards = []
    for card in HOME_CARDS:
        theme = card["theme"]
        cards.append(
            f"""
            <a class="home-card theme-{esc(theme)}" href="{esc(card['href'])}">
              <img class="home-card-image" src="{esc(card['image'])}" alt="" />
              <div class="home-card-body">
                <div class="home-card-kicker">{esc(THEME_LABELS.get(theme, theme))}</div>
                <div class="home-card-title">{esc(card['title'])}</div>
                <p class="home-card-blurb">{esc(card['blurb'])}</p>
              </div>
            </a>
            """
        )
    return "\n".join(cards)


@app.route("/")
def hello():
    body = f"""
<p class="home-intro">
  <strong>PhilTech portfolio demo</strong> — a cloud-hosted sample of how technology
  delivery, architecture, risk, and run finance can sit together. Browse zones,
  projects, architecture, risks, budgets, and run contracts through linked catalogs,
  roadmaps, and a cost dashboard. All data is dummy sample content hosted on personal GCP.
</p>
<div class="home-card-grid">
  {_home_cards_html()}
</div>
"""
    return render_page(
        title="PhilTech portfolio demo",
        subtitle="Zones, projects, architecture, risk, and finance — linked in one place",
        active="Home",
        body=body,
        extra_css=HOME_CSS,
        wide=True,
    )


@app.route("/about")
def about_page():
    status = get_db_status()
    writes_enabled = status["writes_enabled"]
    writes_label = (
        "Changes allowed" if writes_enabled else "Changes locked (read-only links)"
    )
    pill_class = "open" if writes_enabled else "locked"
    safe_label = "available" if status["has_last_safe"] else "not set yet"
    bucket = status["database_bucket"] or "local file only"
    env = esc(ENVIRONMENT)
    body = f"""
<div class="prose">
<div class="panel">
  <div class="status-row">
    <span>Database writes: <span class="pill {pill_class}">{esc(writes_label)}</span></span>
    <span>Last safe copy: <strong>{esc(safe_label)}</strong></span>
    <span>Bucket: <strong>{esc(bucket)}</strong></span>
    <span>Environment: <strong>{env}</strong></span>
  </div>
  <p class="note">
    Link add/remove controls are disabled when changes are locked.
  </p>
  <p class="note">
    This environment has its own database. Hourly backup and midnight reset jobs are
    built into the app, but the Cloud Scheduler setup is still outstanding. Demo edits
    should be treated as temporary unless a new last-safe snapshot is created from
    Cursor.
  </p>
  <p style="margin:0.85rem 0 0.35rem">
    <button id="restore-btn" class="restore-btn" type="button" disabled
      title="Restore is temporarily disabled">
      Restore database to last safe copy
    </button>
  </p>
</div>

<h2>What I accomplished</h2>

<h3>1. Built my first Python web app</h3>
<ul>
<li>Created a Python file and built a Flask application</li>
<li>Ran it locally and accessed it in my browser</li>
</ul>

<h3>2. Learned the development workflow</h3>
<ul>
<li>Created and edited files in Cursor</li>
<li>Used the terminal to run commands</li>
<li>Installed dependencies using pip</li>
</ul>

<h3>3. Set up Git</h3>
<ul>
<li>Installed Git and configured my account</li>
<li>Initialised a repository</li>
<li>Committed my code</li>
</ul>

<h3>4. Used GitHub</h3>
<ul>
<li>Created a repository</li>
<li>Linked my local code</li>
<li>Pushed my code online</li>
</ul>

<h3>5. Set up Google Cloud</h3>
<ul>
<li>Installed the gcloud CLI</li>
<li>Authenticated and configured a project</li>
</ul>

<h3>6. Deployed a live app</h3>
<ul>
<li>Deployed using Cloud Run</li>
<li>Built and ran a container automatically</li>
<li>Made the app publicly accessible</li>
</ul>

<h3>7. Set up separate dev and production environments</h3>
<ul>
<li>Created a development branch alongside the main production branch</li>
<li>Configured automated builds that run when code is pushed to GitHub</li>
<li>Used separate deployment configs so dev and production deploy independently</li>
<li>Deployed each environment to its own Cloud Run service</li>
<li>Passed an environment label into the app so each deployment identifies itself</li>
<li>Granted the build service the permissions needed to deploy to Cloud Run</li>
</ul>

<h3>8. Built an interactive project, risk, and architecture demo</h3>
<ul>
<li>Added a SQLite database with tables for projects, corporate risks, architecture components, and relationship edges</li>
<li>Seeded realistic sample data, including project costs, RAG status, risk impact fields, and architecture outlook/capability</li>
<li>Created a project impact timeline with quarterly banding, RAG-coloured bars, risk diamonds, and architecture triangles</li>
<li>Added table pages and detail pages for projects, risks, and architecture, with click-through navigation between linked items</li>
<li>Made links editable from detail pages using a typeable dropdown, with remove buttons and confirmation dialogs</li>
<li>Built architecture views: relationship diagram, capability grouping, and a year-based architecture roadmap timeline</li>
<li>Grouped the architecture roadmap by capability and marked project go-lives with stars showing impact type</li>
</ul>

<h3>9. Added environment-aware database controls</h3>
<ul>
<li>Split dev and prod onto separate database buckets so environments no longer share one data file</li>
<li>Added restore-to-last-safe from the homepage for the current environment only</li>
<li>Added Cursor-only admin commands to mark a last-safe snapshot and to enable or disable database writes</li>
<li>Show write-lock status in the app and grey out / disable mutating controls when changes are locked</li>
<li>Prepared backup and midnight-reset endpoints, plus a saved setup prompt for finishing Cloud Scheduler later</li>
</ul>

<h3>10. Added a zones hierarchy</h3>
<ul>
<li>Modelled L1 zones, L2 sub-zones, and L3 capabilities in the database</li>
<li>Built a Zones page with zone owners, descriptions, and entity counts</li>
<li>Added toggles to show or hide L2 and L3 detail on the Zones page</li>
<li>Linked projects, risks, architecture, budgets, and run contracts back to zones and sub-zones</li>
</ul>

<h3>11. Expanded the data model from an Excel schema workbook</h3>
<ul>
<li>Updated the schema to match a multi-tab Excel workbook covering projects, risks, architecture, budgets, run contracts, and edges</li>
<li>Added new <code>budgets</code> and <code>run_contracts</code> tables, and expanded project / risk / architecture columns</li>
<li>Generated 50 sample records each for projects, risks, architecture, budgets, and run contracts</li>
<li>Wired edges so projects link to risks, architecture, budgets, and run contracts, following the workbook rules</li>
</ul>

<h3>12. Built budget and run contract catalogs</h3>
<ul>
<li>Added Budget List and Budget Detail pages with all budget columns</li>
<li>Added Run Contract List and Run Contract Detail pages with all contract columns</li>
<li>Extended every detail page to show linked projects, risks, architecture, budgets, and run contracts</li>
<li>Included cross-links via shared projects, plus owning-budget and funded-by-budget relationships</li>
</ul>

<h3>13. Upgraded the Project Roadmap and Architecture Model</h3>
<ul>
<li>Renamed Timeline to Project Roadmap and grouped projects by zone and sub-zone in faint boxes</li>
<li>Aligned milestones to project end dates, stacked them vertically with one-line labels, and collapsed empty space when filters hide them</li>
<li>Slimmed project bars to title plus ID / dates</li>
<li>Grouped the Architecture Model by Zone → SubZone → Capability in a denser 3-column layout</li>
<li>Added checkboxes to show or hide architecture descriptions and owners, with cards shrinking when content is hidden</li>
</ul>

<h3>14. Built a Cost Dashboard</h3>
<ul>
<li>Added a Cost Dashboard page summarising budget Capex, Opex, and Total by zone for 2026–2029</li>
<li>Shaded total columns and separated year groups with whitespace</li>
<li>Added a stacked Capex / Opex bar chart grouped by zone then year, with £0.0m labels</li>
<li>Listed the top 10 most expensive projects for 2026 and 2027, each linking to the project detail page</li>
</ul>

<h3>15. Polished the shared site chrome</h3>
<ul>
<li>Added a PhilTech logo in the header and increased H1 / H2 sizes across the site</li>
<li>Made page subtitles render as H2 and renamed nav / page titles for clearer labels</li>
<li>Centered all pages in a 1400px max-width container without changing inner content alignment</li>
<li>Kept environment and database status messaging on the About page</li>
<li>Expanded the site map to include budgets, run contracts, and the newer pages</li>
</ul>

<hr>

<h2>What I built (big picture)</h2>
<p>
A working cloud system combining:
</p>
<ul>
<li>Python (Flask backend)</li>
<li>Git &amp; GitHub (version control)</li>
<li>Google Cloud Platform</li>
<li>Serverless deployment (Cloud Run)</li>
<li>Automated builds triggered by code changes</li>
<li>Separate development and production environments</li>
<li>A SQLite-backed data model for zones, projects, risks, architecture, budgets, and run contracts</li>
<li>Interactive roadmaps, catalogs, architecture views, and a cost dashboard</li>
<li>Environment-specific data storage with restore and write-lock controls</li>
</ul>

<hr>

<h2>Challenges I solved</h2>

<ul>
<li>Understanding Cursor UI and file creation</li>
<li>Installing Python and fixing pip issues</li>
<li>Debugging a local server not starting</li>
<li>Fixing Git installation and PATH errors</li>
<li>Connecting GitHub and pushing code</li>
<li>Installing and configuring gcloud</li>
<li>Resolving billing setup issues</li>
<li>Fixing permissions (IAM roles)</li>
<li>Debugging Cloud Run build failures</li>
<li>Understanding DNS and domain configuration</li>
<li>Configuring build triggers and connecting a repository to the cloud platform</li>
<li>Resolving service account and permission issues for automated deployments</li>
<li>Designing a simple data model and keeping sample relationships consistent across pages</li>
<li>Working out how ephemeral Cloud Run storage differs from durable database storage</li>
<li>Separating demo editability from Cursor-only admin controls</li>
<li>Turning an Excel workbook into a regenerated schema and large linked sample dataset</li>
<li>Keeping roadmaps and dashboards readable as the volume of demo data grew</li>
</ul>

<hr>

<h2>What I learned</h2>

<ul>
<li>How backend web apps work</li>
<li>How HTTP requests and responses behave</li>
<li>Basics of DNS and domain mapping</li>
<li>How cloud deployments work</li>
<li>How containers are built and run</li>
<li>How permissions and billing affect cloud systems</li>
<li>How branch-based workflows support safe testing before production releases</li>
<li>How environment variables distinguish development from production deployments</li>
<li>How SQLite can power a small interactive demo before moving to a fuller database setup</li>
<li>How timelines, architecture views, and cost views can be driven from the same underlying tables and edges</li>
<li>How admin actions can be kept out of the public UI while still being controllable from Cursor</li>
<li>How zone / sub-zone hierarchy and cross-linked catalogs make a portfolio demo feel coherent</li>
</ul>

<hr>

<h2>Where I am now</h2>

<p>
I started with no experience and now I can:
</p>

<ul>
<li>Build a web application</li>
<li>Deploy it to the cloud</li>
<li>Debug real technical issues</li>
<li>Use Git and GitHub confidently</li>
<li>Test changes in a development environment before releasing to production</li>
<li>Let automated builds deploy my app when I push code</li>
<li>Grow a hello-world app into a multi-page interactive demo with real sample data</li>
<li>Iterate quickly with Cursor while keeping environment-specific cloud deployments working</li>
<li>Extend a schema from spreadsheet instructions and keep list, detail, roadmap, and dashboard pages in sync</li>
</ul>

<p><strong>This project represents my first complete end-to-end cloud deployment, with separate development and production environments, plus an interactive portfolio demo covering zones, projects, risks, architecture, budgets, run contracts, and cost.</strong></p>

<hr>

<h2>Still to do</h2>
<ul>
<li><strong>Vanity URL</strong> — map a clean custom domain to the Cloud Run service</li>
<li><strong>Database backup scheduled jobs</strong> — finish Cloud Scheduler setup for hourly backups and midnight reset-to-last-safe (prompt saved in <code>scripts/tomorrow-scheduler-setup-prompt.txt</code>)</li>
<li><strong>Admin token and bucket permissions</strong> — set <code>ADMIN_TOKEN</code> on Cloud Run and confirm each environment can read/write its own GCS database bucket</li>
<li><strong>Mark and manage last-safe snapshots from Cursor</strong> — use the admin commands day to day once the token/jobs setup is complete</li>
</ul>
</div>
"""

    return render_page(
        title="About this site",
        subtitle="Build story, database status, and what comes next",
        active="About this site",
        body=body,
    )


if __name__ == "__main__":
    app.run(port=5000)
