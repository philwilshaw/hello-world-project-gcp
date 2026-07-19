"""
SQLite database for projects, risks, and edges.

Tables are created and seeded on first use so the demo works locally
and on Cloud Run without a separate database service.
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "app.db"))
SCHEMA_VERSION = 2


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and load mock data; refresh when the schema version changes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        current_version = int(row["value"]) if row else 0

        if current_version != SCHEMA_VERSION:
            conn.executescript(
                """
                DROP TABLE IF EXISTS edges;
                DROP TABLE IF EXISTS risks;
                DROP TABLE IF EXISTS projects;
                """
            )

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
                relationship TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (risk_id) REFERENCES risks(id)
            );
            """
        )

        if current_version != SCHEMA_VERSION:
            _seed(conn)
            conn.execute(
                """
                INSERT INTO meta (key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )


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
                "Rebuild the public website to modernise brand presence and reduce reliance on outdated pages.",
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
                "Deliver a customer mobile app so routine requests can be handled without call-centre contact.",
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
                "Move finance records onto the cloud platform to remove fragile legacy reporting dependencies.",
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
                "Outdated Digital Presence",
                "Corporate website no longer reflects current products or accessibility standards.",
                "High — damages trust and conversion across public channels.",
                "Immediate — customer feedback already cites confusing content.",
                "Estimated brand and conversion impact around £120,000 a year.",
            ),
            (
                "r2",
                "Weak Customer Self-Service",
                "Customers cannot complete common tasks online and default to phone support.",
                "Medium — keeps operating cost and queue times elevated.",
                "Near-term — volumes rise further during seasonal peaks.",
                "Avoidable support cost estimated at £90,000 a year.",
            ),
            (
                "r3",
                "Critical Skills Concentration",
                "Essential digital delivery knowledge sits with too few specialists.",
                "High — absence would slow several corporate change programmes.",
                "Ongoing until knowledge is shared and documented.",
                "Contingency cover and delay exposure roughly £45,000.",
            ),
            (
                "r4",
                "Fragile Legacy Finance Data",
                "Core finance reporting depends on unsupported on-premise systems.",
                "High — audit and decision-making risk if systems fail.",
                "Closer to year-end reporting cycles in early 2027.",
                "Potential remediation and audit cost near £150,000.",
            ),
        ],
    )

    # Projects are delivered to address corporate risks.
    # A risk can link to more than one project.
    conn.executemany(
        """
        INSERT INTO edges (id, project_id, risk_id, relationship)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("e1", "p1", "r1", "resolves"),
            ("e2", "p1", "r2", "reduces"),
            ("e3", "p2", "r2", "resolves"),
            ("e4", "p2", "r3", "reduces"),
            ("e5", "p3", "r4", "resolves"),
            ("e6", "p3", "r1", "reduces"),
        ],
    )


def fetch_timeline_data():
    """Return projects, risks, and relationships for the timeline view."""
    init_db()

    with get_connection() as conn:
        edges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, project_id, risk_id, relationship
                FROM edges
                ORDER BY id
                """
            )
        ]

        project_ids = {edge["project_id"] for edge in edges}
        risk_ids = {edge["risk_id"] for edge in edges}

        projects = []
        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            projects = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT *
                    FROM projects
                    WHERE id IN ({placeholders})
                    ORDER BY start_date, id
                    """,
                    tuple(project_ids),
                )
            ]

        risks = []
        if risk_ids:
            placeholders = ",".join("?" for _ in risk_ids)
            risks = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT *
                    FROM risks
                    WHERE id IN ({placeholders})
                    ORDER BY id
                    """,
                    tuple(risk_ids),
                )
            ]

    return {
        "projects": projects,
        "risks": risks,
        "edges": edges,
    }
