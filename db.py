"""
SQLite database for projects, risks, and edges.

Tables are created and seeded on first use so the demo works locally
and on Cloud Run without a separate database service.
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "app.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and load mock data if the database is empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                accountable_contact_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                rag_status TEXT NOT NULL,
                capex_gbp REAL NOT NULL,
                opex_gbp REAL NOT NULL,
                CHECK (start_date < end_date)
            );

            CREATE TABLE IF NOT EXISTS risks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                impact TEXT NOT NULL,
                proximity TEXT NOT NULL,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                risk_id TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT 'exposed to',
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (risk_id) REFERENCES risks(id)
            );
            """
        )

        project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if project_count == 0:
            _seed(conn)


def _seed(conn):
    conn.executemany(
        """
        INSERT INTO projects (
            id, title, description, accountable_contact_name,
            start_date, end_date, rag_status, capex_gbp, opex_gbp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "p1",
                "Website Redesign",
                "Rebuild the public website with a clearer information architecture and faster load times.",
                "Aisha Khan",
                "2026-03-01",
                "2026-11-30",
                "Amber",
                180000.00,
                42000.00,
            ),
            (
                "p2",
                "Mobile App Launch",
                "Ship the first customer mobile app for iOS and Android with account login and basic self-service.",
                "James O'Neill",
                "2026-06-15",
                "2027-04-30",
                "Green",
                320000.00,
                75000.00,
            ),
            (
                "p3",
                "Data Migration",
                "Move legacy finance records into the new cloud data platform with validated cutover.",
                "Priya Sharma",
                "2026-09-01",
                "2027-02-28",
                "Red",
                95000.00,
                28000.00,
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO risks (id, title, description, impact, proximity, value)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "r1",
                "Budget Overrun",
                "Delivery costs rise above the approved business case.",
                "High — may force scope cuts or extra funding approval.",
                "Near-term — cost pressure already visible in supplier quotes.",
                "Estimated exposure around £75,000.",
            ),
            (
                "r2",
                "Schedule Slip",
                "Key milestones move later than the agreed plan.",
                "Medium — delays dependent releases and stakeholder confidence.",
                "Medium-term — likely if design reviews overrun.",
                "About six to eight weeks of programme delay.",
            ),
            (
                "r3",
                "Key Person Dependency",
                "Critical knowledge sits with a single specialist.",
                "High — absence would stall mobile build work.",
                "Ongoing while the specialist remains the only owner.",
                "Hard to price; contingency cover roughly £20,000.",
            ),
            (
                "r4",
                "Vendor Delay",
                "External vendor misses contracted delivery dates.",
                "Medium — blocks migration rehearsal windows.",
                "Closer to cutover in early 2027.",
                "Potential rework and standby costs near £35,000.",
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO edges (id, project_id, risk_id, label)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("e1", "p1", "r1", "exposed to"),
            ("e2", "p1", "r2", "exposed to"),
            ("e3", "p2", "r2", "exposed to"),
            ("e4", "p2", "r3", "exposed to"),
            ("e5", "p3", "r1", "exposed to"),
            ("e6", "p3", "r4", "exposed to"),
        ],
    )


def fetch_graph_elements():
    """Return Cytoscape elements from edges plus the linked project/risk rows."""
    init_db()

    with get_connection() as conn:
        edges = conn.execute(
            "SELECT id, project_id, risk_id, label FROM edges"
        ).fetchall()

        project_ids = {edge["project_id"] for edge in edges}
        risk_ids = {edge["risk_id"] for edge in edges}

        projects = []
        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            projects = conn.execute(
                f"SELECT * FROM projects WHERE id IN ({placeholders})",
                tuple(project_ids),
            ).fetchall()

        risks = []
        if risk_ids:
            placeholders = ",".join("?" for _ in risk_ids)
            risks = conn.execute(
                f"SELECT * FROM risks WHERE id IN ({placeholders})",
                tuple(risk_ids),
            ).fetchall()

    elements = []

    for project in projects:
        elements.append(
            {
                "data": {
                    "id": project["id"],
                    "label": project["title"],
                    "type": "project",
                    "description": project["description"],
                    "accountable_contact_name": project["accountable_contact_name"],
                    "start_date": project["start_date"],
                    "end_date": project["end_date"],
                    "rag_status": project["rag_status"],
                    "capex_gbp": project["capex_gbp"],
                    "opex_gbp": project["opex_gbp"],
                }
            }
        )

    for risk in risks:
        elements.append(
            {
                "data": {
                    "id": risk["id"],
                    "label": risk["title"],
                    "type": "risk",
                    "description": risk["description"],
                    "impact": risk["impact"],
                    "proximity": risk["proximity"],
                    "value": risk["value"],
                }
            }
        )

    for edge in edges:
        elements.append(
            {
                "data": {
                    "id": edge["id"],
                    "source": edge["project_id"],
                    "target": edge["risk_id"],
                    "label": edge["label"],
                }
            }
        )

    return elements
