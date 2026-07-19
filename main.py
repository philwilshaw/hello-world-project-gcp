import os

from flask import Flask

from admin import admin_bp
from architecture_roadmap import architecture_roadmap_bp
from architecture_views import architecture_views_bp
from catalog import catalog_bp
from db import get_db_status, init_db
from diagram import diagram_bp

app = Flask(__name__)
app.register_blueprint(diagram_bp)
app.register_blueprint(architecture_roadmap_bp)
app.register_blueprint(architecture_views_bp)
app.register_blueprint(catalog_bp)
app.register_blueprint(admin_bp)
init_db()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")


@app.route("/")
def hello():
    status = get_db_status()
    writes_label = (
        "Changes allowed"
        if status["writes_enabled"]
        else "Changes locked (read-only links)"
    )
    writes_color = "#2f9e6b" if status["writes_enabled"] else "#c94c3f"
    safe_label = "available" if status["has_last_safe"] else "not set yet"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hello World Project</title>
  <style>
    body {{
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 1.25rem;
      line-height: 1.45;
      color: #1b2430;
      background: #f5f7fa;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #d5dbe3;
      border-radius: 10px;
      padding: 0.9rem 1rem;
      margin: 0.85rem 0 1.25rem;
    }}
    .status {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
      align-items: center;
      font-size: 0.95rem;
    }}
    .pill {{
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      color: #fff;
      font-weight: 650;
      font-size: 0.85rem;
      background: {writes_color};
    }}
    .note {{
      color: #5b6775;
      font-size: 0.9rem;
      margin-top: 0.55rem;
    }}
    button {{
      background: #1f6feb;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0.55rem 0.85rem;
      font-weight: 650;
      cursor: pointer;
    }}
    button:disabled {{
      background: #a8b3c2;
      cursor: not-allowed;
    }}
    #restore-status {{ margin-top: 0.5rem; font-size: 0.88rem; color: #5b6775; }}
    a {{ color: #1558c0; }}
  </style>
</head>
<body>
<h1>🚀 My First Cloud Deployment Project</h1>
<p><strong>Environment:</strong> {ENVIRONMENT}</p>

<div class="panel">
  <div class="status">
    <span>Database writes: <span class="pill">{writes_label}</span></span>
    <span>Last safe copy: <strong>{safe_label}</strong></span>
    <span>Bucket: <strong>{status["database_bucket"] or "local file only"}</strong></span>
  </div>
  <p class="note">
    This environment has its own database. It is backed up hourly and reset to the
    last safe copy every night at midnight (Europe/London). Demo edits are temporary
    unless a new last-safe snapshot is created from Cursor.
  </p>
  <p style="margin:0.85rem 0 0.35rem">
    <button id="restore-btn" type="button" {"disabled" if not status["has_last_safe"] else ""}>
      Restore database to last safe copy
    </button>
  </p>
  <div id="restore-status"></div>
</div>

<p>
  <a href="/diagram">Timeline demo</a> ·
  <a href="/projects">Projects</a> ·
  <a href="/risks">Risks</a> ·
  <a href="/architecture">Architecture</a> ·
  <a href="/architecture/diagram">Arch diagram</a> ·
  <a href="/architecture/capabilities">By capability</a> ·
  <a href="/architecture/roadmap">Arch roadmap</a>
</p>
<p class="note">
  Pages above read from the <strong>{ENVIRONMENT}</strong> database.
  Link add/remove controls are disabled when changes are locked.
</p>

<h2>✅ What I accomplished</h2>

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

<hr>

<h2>🧠 What I built (big picture)</h2>
<p>
A working cloud system combining:
</p>
<ul>
<li>Python (Flask backend)</li>
<li>Git & GitHub (version control)</li>
<li>Google Cloud Platform</li>
<li>Serverless deployment (Cloud Run)</li>
<li>Automated builds triggered by code changes</li>
<li>Separate development and production environments</li>
</ul>

<hr>

<h2>🧱 Challenges I solved</h2>

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
</ul>

<hr>

<h2>🧠 What I learned</h2>

<ul>
<li>How backend web apps work</li>
<li>How HTTP requests and responses behave</li>
<li>Basics of DNS and domain mapping</li>
<li>How cloud deployments work</li>
<li>How containers are built and run</li>
<li>How permissions and billing affect cloud systems</li>
<li>How branch-based workflows support safe testing before production releases</li>
<li>How environment variables distinguish development from production deployments</li>
</ul>

<hr>

<h2>🎯 Where I am now</h2>

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
</ul>

<p><strong>This project represents my first complete end-to-end cloud deployment, with separate development and production environments.</strong></p>

<script>
  const restoreBtn = document.getElementById("restore-btn");
  const restoreStatus = document.getElementById("restore-status");
  if (restoreBtn) {{
    restoreBtn.addEventListener("click", async () => {{
      const ok = window.confirm(
        "Restore the {ENVIRONMENT} database to the last safe copy?\\n\\nCurrent link edits in this environment will be discarded."
      );
      if (!ok) return;
      restoreBtn.disabled = true;
      restoreStatus.textContent = "Restoring...";
      try {{
        const response = await fetch("/api/db/restore-last-safe", {{ method: "POST" }});
        const data = await response.json();
        if (!response.ok) {{
          restoreStatus.textContent = data.error || "Restore failed";
          restoreBtn.disabled = false;
          return;
        }}
        restoreStatus.textContent = data.message || "Restored.";
        window.setTimeout(() => window.location.reload(), 800);
      }} catch (err) {{
        restoreStatus.textContent = "Restore failed";
        restoreBtn.disabled = false;
      }}
    }});
  }}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(port=5000)
