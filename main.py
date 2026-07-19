import os

from flask import Flask

from db import init_db
from diagram import diagram_bp

app = Flask(__name__)
app.register_blueprint(diagram_bp)
init_db()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")


@app.route("/")
def hello():
    return f"""
<h1>🚀 My First Cloud Deployment Project</h1>
<p><strong>Environment:</strong> {ENVIRONMENT}</p>
<p><a href="/diagram">Open project–risk diagram demo →</a></p>

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
"""

if __name__ == "__main__":
    app.run(port=5000)