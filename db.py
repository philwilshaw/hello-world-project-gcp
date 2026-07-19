"""
SQLite database for projects, risks, architecture components, and links.

Tables are created and seeded on first use so the demo works locally
and on Cloud Run without a separate database service.
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "app.db"))
SCHEMA_VERSION = 3


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
                DROP TABLE IF EXISTS architecture_components;
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

            CREATE TABLE IF NOT EXISTS architecture_components (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                component_type TEXT NOT NULL,
                owner TEXT NOT NULL
            );

            -- Links projects to risks or architecture components.
            -- linked_type is 'risk' or 'architecture'.
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                linked_type TEXT NOT NULL,
                linked_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
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

    conn.executemany(
        """
        INSERT INTO architecture_components (
            id, title, description, component_type, owner
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                "a1",
                "Public Website",
                "Customer-facing web presence and content delivery stack.",
                "Application",
                "Digital Channels",
            ),
            (
                "a2",
                "Mobile Banking App",
                "iOS and Android app for authenticated customer journeys.",
                "Application",
                "Digital Channels",
            ),
            (
                "a3",
                "Customer API Gateway",
                "API layer used by web and mobile channels.",
                "Integration",
                "Platform Engineering",
            ),
            (
                "a4",
                "Legacy Finance Ledger",
                "On-premise finance system due to be retired after migration.",
                "System",
                "Finance Technology",
            ),
            (
                "a5",
                "Cloud Finance Warehouse",
                "Target cloud data platform for finance reporting.",
                "Data Platform",
                "Data Engineering",
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO edges (id, project_id, linked_type, linked_id, relationship)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            # Risk links
            ("e1", "p1", "risk", "r1", "resolves"),
            ("e2", "p1", "risk", "r2", "reduces"),
            ("e3", "p2", "risk", "r2", "resolves"),
            ("e4", "p2", "risk", "r3", "reduces"),
            ("e5", "p3", "risk", "r4", "resolves"),
            ("e6", "p3", "risk", "r1", "reduces"),
            # Architecture links
            ("e7", "p1", "architecture", "a1", "modified"),
            ("e8", "p1", "architecture", "a3", "version upgrade"),
            ("e9", "p2", "architecture", "a2", "implemented"),
            ("e10", "p2", "architecture", "a3", "modified"),
            ("e11", "p3", "architecture", "a4", "decommissioned"),
            ("e12", "p3", "architecture", "a5", "implemented"),
        ],
    )


def _fetch_by_ids(conn, table, ids):
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    return [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT * FROM {table}
            WHERE id IN ({placeholders})
            ORDER BY id
            """,
            tuple(ids),
        )
    ]


def fetch_timeline_data():
    """Return projects, risks, architecture components, and links for the timeline."""
    init_db()

    with get_connection() as conn:
        edges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, project_id, linked_type, linked_id, relationship
                FROM edges
                ORDER BY id
                """
            )
        ]

        project_ids = {edge["project_id"] for edge in edges}
        risk_ids = {
            edge["linked_id"] for edge in edges if edge["linked_type"] == "risk"
        }
        architecture_ids = {
            edge["linked_id"]
            for edge in edges
            if edge["linked_type"] == "architecture"
        }

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

        risks = _fetch_by_ids(conn, "risks", risk_ids)
        architecture_components = _fetch_by_ids(
            conn, "architecture_components", architecture_ids
        )

    return {
        "projects": projects,
        "risks": risks,
        "architecture_components": architecture_components,
        "edges": edges,
    }


def fetch_all_projects():
    init_db()
    with get_connection() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM projects ORDER BY start_date, id"
            )
        ]


def fetch_all_risks():
    init_db()
    with get_connection() as conn:
        return [
            dict(row)
            for row in conn.execute("SELECT * FROM risks ORDER BY id")
        ]


def fetch_all_architecture():
    init_db()
    with get_connection() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM architecture_components ORDER BY id"
            )
        ]


def fetch_project_detail(project_id):
    """Return one project plus its linked risks and architecture components."""
    init_db()
    with get_connection() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return None

        linked_risks = [
            dict(row)
            for row in conn.execute(
                """
                SELECT r.*, e.relationship
                FROM edges e
                JOIN risks r ON r.id = e.linked_id
                WHERE e.project_id = ? AND e.linked_type = 'risk'
                ORDER BY r.id
                """,
                (project_id,),
            )
        ]
        linked_architecture = [
            dict(row)
            for row in conn.execute(
                """
                SELECT a.*, e.relationship
                FROM edges e
                JOIN architecture_components a ON a.id = e.linked_id
                WHERE e.project_id = ? AND e.linked_type = 'architecture'
                ORDER BY a.id
                """,
                (project_id,),
            )
        ]

    return {
        "project": dict(project),
        "linked_risks": linked_risks,
        "linked_architecture": linked_architecture,
    }


def fetch_risk_detail(risk_id):
    """Return one risk plus the projects linked to it."""
    init_db()
    with get_connection() as conn:
        risk = conn.execute(
            "SELECT * FROM risks WHERE id = ?", (risk_id,)
        ).fetchone()
        if risk is None:
            return None

        linked_projects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT p.*, e.relationship
                FROM edges e
                JOIN projects p ON p.id = e.project_id
                WHERE e.linked_type = 'risk' AND e.linked_id = ?
                ORDER BY p.start_date, p.id
                """,
                (risk_id,),
            )
        ]

    return {
        "risk": dict(risk),
        "linked_projects": linked_projects,
    }


def fetch_architecture_detail(architecture_id):
    """Return one architecture component plus the projects linked to it."""
    init_db()
    with get_connection() as conn:
        component = conn.execute(
            "SELECT * FROM architecture_components WHERE id = ?",
            (architecture_id,),
        ).fetchone()
        if component is None:
            return None

        linked_projects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT p.*, e.relationship
                FROM edges e
                JOIN projects p ON p.id = e.project_id
                WHERE e.linked_type = 'architecture' AND e.linked_id = ?
                ORDER BY p.start_date, p.id
                """,
                (architecture_id,),
            )
        ]

    return {
        "architecture": dict(component),
        "linked_projects": linked_projects,
    }
