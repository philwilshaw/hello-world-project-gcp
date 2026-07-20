"""
SQLite database for projects, risks, architecture components, and links.

Each environment (local/dev/prod) uses its own database file. When
DATABASE_BUCKET is set, the live DB plus control files are synced to that
environment's GCS bucket.
"""

import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local").strip() or "local"
SCHEMA_VERSION = 6

# Prefer explicit bucket; otherwise derive a per-environment default name when
# running in GCP-style envs. Local keeps files on disk only unless overridden.
_DEFAULT_BUCKET = {
    "dev": os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    and f"{os.environ.get('GOOGLE_CLOUD_PROJECT').strip()}-hello-world-data-dev",
    "prod": os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    and f"{os.environ.get('GOOGLE_CLOUD_PROJECT').strip()}-hello-world-data-prod",
}.get(ENVIRONMENT, "")

DATABASE_BUCKET = (
    os.environ.get("DATABASE_BUCKET", "").strip() or _DEFAULT_BUCKET or ""
)

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "app.db"))
LAST_SAFE_PATH = Path(
    os.environ.get("LAST_SAFE_PATH", DB_PATH.with_name("app.last-safe.db"))
)
WRITES_FLAG_PATH = Path(
    os.environ.get("WRITES_FLAG_PATH", DB_PATH.with_name("app.writes-enabled"))
)
BACKUPS_DIR = Path(os.environ.get("BACKUPS_DIR", DB_PATH.parent / "backups"))

GCS_LIVE_OBJECT = "app.db"
GCS_LAST_SAFE_OBJECT = "last-safe.db"
GCS_WRITES_OBJECT = "writes-enabled"
GCS_BACKUPS_PREFIX = "backups/"

RISK_RELATIONSHIPS = ("resolves", "reduces")
ARCHITECTURE_RELATIONSHIPS = (
    "implemented",
    "modified",
    "version upgrade",
    "decommissioned",
)
ARCHITECTURE_OUTLOOKS = (
    "to be implemented",
    "continue",
    "to be decommissioned",
    "upgrade",
    "decommissioned",
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _gcs_client_and_bucket():
    if not DATABASE_BUCKET:
        return None, None
    try:
        from google.cloud import storage
    except ImportError:
        return None, None
    try:
        client = storage.Client()
        return client, client.bucket(DATABASE_BUCKET)
    except Exception as exc:
        print(f"GCS unavailable: {exc}")
        return None, None


def _download_db_from_gcs():
    client, bucket = _gcs_client_and_bucket()
    if bucket is None:
        return
    try:
        blob = bucket.blob(GCS_LIVE_OBJECT)
        if blob.exists():
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(DB_PATH))
    except Exception as exc:
        print(f"GCS download skipped: {exc}")


def _upload_db_to_gcs():
    client, bucket = _gcs_client_and_bucket()
    if bucket is None:
        return
    try:
        bucket.blob(GCS_LIVE_OBJECT).upload_from_filename(str(DB_PATH))
    except Exception as exc:
        print(f"GCS upload skipped: {exc}")


def persist_db():
    """Push the local SQLite file to GCS when configured."""
    _upload_db_to_gcs()


def _read_writes_flag_local():
    if not WRITES_FLAG_PATH.exists():
        return True
    return WRITES_FLAG_PATH.read_text(encoding="utf-8").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _write_writes_flag_local(enabled):
    WRITES_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WRITES_FLAG_PATH.write_text("true" if enabled else "false", encoding="utf-8")


def get_writes_enabled():
    """Whether mutating link edits are currently allowed."""
    client, bucket = _gcs_client_and_bucket()
    if bucket is not None:
        try:
            blob = bucket.blob(GCS_WRITES_OBJECT)
            if blob.exists():
                value = blob.download_as_text(encoding="utf-8").strip().lower()
                return value in {"1", "true", "yes", "on"}
        except Exception as exc:
            print(f"GCS writes-flag read skipped: {exc}")
    return _read_writes_flag_local()


def set_writes_enabled(enabled):
    """Cursor/admin only: allow or block database mutations from the app."""
    enabled = bool(enabled)
    _write_writes_flag_local(enabled)
    client, bucket = _gcs_client_and_bucket()
    if bucket is not None:
        try:
            bucket.blob(GCS_WRITES_OBJECT).upload_from_string(
                "true" if enabled else "false",
                content_type="text/plain",
            )
        except Exception as exc:
            print(f"GCS writes-flag write skipped: {exc}")
            return False, f"local updated; GCS sync failed: {exc}"
    return True, "writes enabled" if enabled else "writes disabled"


def has_last_safe():
    if LAST_SAFE_PATH.exists():
        return True
    client, bucket = _gcs_client_and_bucket()
    if bucket is None:
        return False
    try:
        return bucket.blob(GCS_LAST_SAFE_OBJECT).exists()
    except Exception:
        return False


def _snapshot_last_safe():
    """Copy the current live DB file to the last-safe locations."""
    if not DB_PATH.exists():
        return False, "live database missing"
    LAST_SAFE_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, LAST_SAFE_PATH)
    client, bucket = _gcs_client_and_bucket()
    if bucket is not None:
        try:
            bucket.blob(GCS_LAST_SAFE_OBJECT).upload_from_filename(str(LAST_SAFE_PATH))
        except Exception as exc:
            print(f"GCS last-safe upload skipped: {exc}")
            return False, f"local last-safe saved; GCS sync failed: {exc}"
    return True, "last-safe updated"


def mark_last_safe():
    """Cursor/admin only: snapshot the current DB as the last safe copy."""
    init_db()
    return _snapshot_last_safe()


def restore_last_safe():
    """Replace the live DB with the last safe copy for this environment."""
    client, bucket = _gcs_client_and_bucket()
    if bucket is not None:
        try:
            blob = bucket.blob(GCS_LAST_SAFE_OBJECT)
            if blob.exists():
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                blob.download_to_filename(str(DB_PATH))
                shutil.copy2(DB_PATH, LAST_SAFE_PATH)
                persist_db()
                return True, "restored from GCS last-safe"
        except Exception as exc:
            print(f"GCS last-safe restore failed: {exc}")

    if not LAST_SAFE_PATH.exists():
        return False, "no last-safe copy available"
    shutil.copy2(LAST_SAFE_PATH, DB_PATH)
    persist_db()
    return True, "restored from local last-safe"


def create_backup():
    """Copy the live DB into a timestamped hourly backup location."""
    init_db()
    if not DB_PATH.exists():
        return False, "live database missing", None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"app-{stamp}.db"
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    local_backup = BACKUPS_DIR / filename
    shutil.copy2(DB_PATH, local_backup)

    client, bucket = _gcs_client_and_bucket()
    if bucket is not None:
        try:
            bucket.blob(f"{GCS_BACKUPS_PREFIX}{filename}").upload_from_filename(
                str(local_backup)
            )
        except Exception as exc:
            print(f"GCS backup upload skipped: {exc}")
            return False, f"local backup saved; GCS sync failed: {exc}", filename
    return True, "backup created", filename


def get_db_status():
    init_db()
    return {
        "environment": ENVIRONMENT,
        "writes_enabled": get_writes_enabled(),
        "has_last_safe": has_last_safe(),
        "database_bucket": DATABASE_BUCKET or None,
    }


def init_db():
    """Create tables and load mock data; refresh when the schema version changes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        _download_db_from_gcs()

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
                DROP TABLE IF EXISTS architecture_edges;
                DROP TABLE IF EXISTS edges;
                DROP TABLE IF EXISTS architecture_components;
                DROP TABLE IF EXISTS risks;
                DROP TABLE IF EXISTS projects;
                DROP TABLE IF EXISTS capabilities;
                DROP TABLE IF EXISTS sub_zones;
                DROP TABLE IF EXISTS zones;
                """
            )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS zones (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                owner_image TEXT NOT NULL,
                description TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sub_zones (
                id TEXT PRIMARY KEY,
                zone_id TEXT NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                FOREIGN KEY (zone_id) REFERENCES zones(id)
            );

            CREATE TABLE IF NOT EXISTS capabilities (
                id TEXT PRIMARY KEY,
                sub_zone_id TEXT NOT NULL,
                name TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'L3',
                sort_order INTEGER NOT NULL,
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

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
                sub_zone_id TEXT NOT NULL,
                CHECK (start_date < end_date),
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            CREATE TABLE IF NOT EXISTS risks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                impact TEXT NOT NULL,
                proximity TEXT NOT NULL,
                value TEXT NOT NULL,
                sub_zone_id TEXT NOT NULL,
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            CREATE TABLE IF NOT EXISTS architecture_components (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                component_type TEXT NOT NULL,
                owner TEXT NOT NULL,
                capability TEXT NOT NULL,
                outlook TEXT NOT NULL,
                implemented_date TEXT,
                go_live_date TEXT,
                decommissioned_date TEXT,
                sub_zone_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id),
                FOREIGN KEY (capability_id) REFERENCES capabilities(id)
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

            -- Relationships between architecture components.
            CREATE TABLE IF NOT EXISTS architecture_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES architecture_components(id),
                FOREIGN KEY (target_id) REFERENCES architecture_components(id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_unique_link
            ON edges (project_id, linked_type, linked_id);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_architecture_edges_unique
            ON architecture_edges (source_id, target_id, relationship);
            """
        )

        seeded = False
        if current_version != SCHEMA_VERSION:
            _seed(conn)
            conn.execute(
                """
                INSERT INTO meta (key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )
            seeded = True

    if seeded:
        persist_db()
        # Fresh seed becomes the baseline safe copy; writes start enabled.
        set_writes_enabled(True)
        _snapshot_last_safe()
    elif not WRITES_FLAG_PATH.exists() and not DATABASE_BUCKET:
        set_writes_enabled(True)


def _seed_zones(conn):
    """Load zones, sub-zones, and L3 capabilities; return lookup maps."""
    from zones_data import ZONES

    sub_zone_by_name = {}
    capability_by_pair = {}

    for zone_index, zone in enumerate(ZONES, start=1):
        conn.execute(
            """
            INSERT INTO zones (
                id, name, owner_name, owner_image, description, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                zone["id"],
                zone["name"],
                zone["owner_name"],
                zone["owner_image"],
                zone["description"],
                zone_index,
            ),
        )
        for sub_index, sub_zone in enumerate(zone["sub_zones"], start=1):
            sub_zone_id = f"{zone['id']}-sz{sub_index}"
            conn.execute(
                """
                INSERT INTO sub_zones (id, zone_id, name, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (sub_zone_id, zone["id"], sub_zone["name"], sub_index),
            )
            sub_zone_by_name[sub_zone["name"]] = sub_zone_id
            for cap_index, capability_name in enumerate(
                sub_zone["capabilities"], start=1
            ):
                capability_id = f"{sub_zone_id}-c{cap_index}"
                conn.execute(
                    """
                    INSERT INTO capabilities (
                        id, sub_zone_id, name, level, sort_order
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (capability_id, sub_zone_id, capability_name, "L3", cap_index),
                )
                capability_by_pair[(sub_zone["name"], capability_name)] = (
                    capability_id
                )

    return sub_zone_by_name, capability_by_pair


def _seed(conn):
    from zones_data import (
        ARCHITECTURE_ASSIGNMENTS,
        PROJECT_SUB_ZONES,
        RISK_SUB_ZONES,
    )

    sub_zone_by_name, capability_by_pair = _seed_zones(conn)

    conn.executemany(
        """
        INSERT INTO projects (
            id, title, description, accountable_contact_name,
            start_date, end_date, rag_status, capex_gbp, opex_gbp, sub_zone_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                sub_zone_by_name[PROJECT_SUB_ZONES["p1"]],
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
                sub_zone_by_name[PROJECT_SUB_ZONES["p2"]],
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
                sub_zone_by_name[PROJECT_SUB_ZONES["p3"]],
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO risks (
            id, title, description, impact, proximity, value, sub_zone_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "r1",
                "Outdated Digital Presence",
                "Corporate website no longer reflects current products or accessibility standards.",
                "High — damages trust and conversion across public channels.",
                "Immediate — customer feedback already cites confusing content.",
                "Estimated brand and conversion impact around £120,000 a year.",
                sub_zone_by_name[RISK_SUB_ZONES["r1"]],
            ),
            (
                "r2",
                "Weak Customer Self-Service",
                "Customers cannot complete common tasks online and default to phone support.",
                "Medium — keeps operating cost and queue times elevated.",
                "Near-term — volumes rise further during seasonal peaks.",
                "Avoidable support cost estimated at £90,000 a year.",
                sub_zone_by_name[RISK_SUB_ZONES["r2"]],
            ),
            (
                "r3",
                "Critical Skills Concentration",
                "Essential digital delivery knowledge sits with too few specialists.",
                "High — absence would slow several corporate change programmes.",
                "Ongoing until knowledge is shared and documented.",
                "Contingency cover and delay exposure roughly £45,000.",
                sub_zone_by_name[RISK_SUB_ZONES["r3"]],
            ),
            (
                "r4",
                "Fragile Legacy Finance Data",
                "Core finance reporting depends on unsupported on-premise systems.",
                "High — audit and decision-making risk if systems fail.",
                "Closer to year-end reporting cycles in early 2027.",
                "Potential remediation and audit cost near £150,000.",
                sub_zone_by_name[RISK_SUB_ZONES["r4"]],
            ),
        ],
    )

    def _arch_row(
        arch_id,
        title,
        description,
        component_type,
        owner,
        outlook,
        implemented_date,
        go_live_date,
        decommissioned_date,
    ):
        sub_zone_name, capability_name = ARCHITECTURE_ASSIGNMENTS[arch_id]
        return (
            arch_id,
            title,
            description,
            component_type,
            owner,
            capability_name,
            outlook,
            implemented_date,
            go_live_date,
            decommissioned_date,
            sub_zone_by_name[sub_zone_name],
            capability_by_pair[(sub_zone_name, capability_name)],
        )

    conn.executemany(
        """
        INSERT INTO architecture_components (
            id, title, description, component_type, owner, capability, outlook,
            implemented_date, go_live_date, decommissioned_date,
            sub_zone_id, capability_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            _arch_row(
                "a1",
                "Public Website",
                "Customer-facing web presence and content delivery stack.",
                "Application",
                "Digital Channels",
                "upgrade",
                "2020-01-15",
                "2020-06-01",
                None,
            ),
            _arch_row(
                "a2",
                "Mobile Banking App",
                "iOS and Android app for authenticated customer journeys.",
                "Application",
                "Digital Channels",
                "to be implemented",
                None,
                None,
                None,
            ),
            _arch_row(
                "a3",
                "Customer API Gateway",
                "API layer used by web and mobile channels.",
                "Integration",
                "Platform Engineering",
                "continue",
                "2023-01-10",
                "2023-06-30",
                None,
            ),
            _arch_row(
                "a4",
                "Legacy Finance Ledger",
                "On-premise finance system due to be retired after migration.",
                "System",
                "Finance Technology",
                "to be decommissioned",
                "2015-03-01",
                "2015-09-01",
                None,
            ),
            _arch_row(
                "a5",
                "Cloud Finance Warehouse",
                "Target cloud data platform for finance reporting.",
                "Data Platform",
                "Data Engineering",
                "to be implemented",
                None,
                None,
                None,
            ),
            _arch_row(
                "a6",
                "Contact Centre Desktop",
                "Agent desktop used for phone-based customer support.",
                "Application",
                "Customer Operations",
                "continue",
                "2019-02-01",
                "2019-08-15",
                None,
            ),
            _arch_row(
                "a7",
                "Batch File Hub",
                "Legacy overnight file transfer service between channels and finance.",
                "Integration",
                "Platform Engineering",
                "to be decommissioned",
                "2016-05-01",
                "2016-11-01",
                None,
            ),
            _arch_row(
                "a8",
                "Event Streaming Bus",
                "Near-real-time event backbone replacing batch file transfers.",
                "Integration",
                "Platform Engineering",
                "upgrade",
                "2025-01-15",
                "2025-09-01",
                None,
            ),
            _arch_row(
                "a9",
                "On-prem Reporting Mart",
                "Historic reporting database retained only for audit archive access.",
                "Data Platform",
                "Data Engineering",
                "decommissioned",
                "2014-04-01",
                "2014-10-01",
                "2024-12-31",
            ),
            _arch_row(
                "a10",
                "Identity Service",
                "Central authentication and authorisation for customer apps.",
                "Platform",
                "Security Engineering",
                "continue",
                "2022-01-01",
                "2022-06-01",
                None,
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO edges (id, project_id, linked_type, linked_id, relationship)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("e1", "p1", "risk", "r1", "resolves"),
            ("e2", "p1", "risk", "r2", "reduces"),
            ("e3", "p2", "risk", "r2", "resolves"),
            ("e4", "p2", "risk", "r3", "reduces"),
            ("e5", "p3", "risk", "r4", "resolves"),
            ("e6", "p3", "risk", "r1", "reduces"),
            ("e7", "p1", "architecture", "a1", "modified"),
            ("e8", "p1", "architecture", "a3", "version upgrade"),
            ("e9", "p2", "architecture", "a2", "implemented"),
            ("e10", "p2", "architecture", "a3", "modified"),
            ("e11", "p3", "architecture", "a4", "decommissioned"),
            ("e12", "p3", "architecture", "a5", "implemented"),
            ("e13", "p1", "architecture", "a8", "modified"),
            ("e14", "p2", "architecture", "a10", "implemented"),
            ("e15", "p3", "architecture", "a7", "decommissioned"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO architecture_edges (id, source_id, target_id, relationship)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("ae1", "a1", "a3", "calls"),
            ("ae2", "a2", "a3", "calls"),
            ("ae3", "a1", "a10", "authenticates via"),
            ("ae4", "a2", "a10", "authenticates via"),
            ("ae5", "a6", "a3", "calls"),
            ("ae6", "a3", "a8", "publishes to"),
            ("ae7", "a7", "a4", "feeds"),
            ("ae8", "a8", "a5", "feeds"),
            ("ae9", "a5", "a4", "replaces"),
            ("ae10", "a8", "a7", "replaces"),
            ("ae11", "a9", "a4", "was sourced from"),
            ("ae12", "a3", "a5", "reads"),
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
                """
                SELECT * FROM architecture_components
                ORDER BY capability, title, id
                """
            )
        ]


def fetch_architecture_graph():
    """Return architecture components and inter-component relationships."""
    init_db()
    with get_connection() as conn:
        components = [
            dict(row)
            for row in conn.execute(
                """
                SELECT * FROM architecture_components
                ORDER BY capability, title, id
                """
            )
        ]
        edges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, source_id, target_id, relationship
                FROM architecture_edges
                ORDER BY id
                """
            )
        ]
    return {"components": components, "edges": edges}


def fetch_architecture_by_capability():
    """Return architecture components grouped by capability."""
    components = fetch_all_architecture()
    grouped = {}
    for component in components:
        grouped.setdefault(component["capability"], []).append(component)
    return grouped


def fetch_architecture_roadmap():
    """
    Return architecture lifespan bars and project go-live impacts.

    Lifecycle dates come from architecture_components first. Missing
    implemented / go-live / decommissioned dates are inferred from project
    edges (implemented / decommissioned relationships) where possible.
    """
    init_db()

    with get_connection() as conn:
        components = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM architecture_components
                ORDER BY capability, title, id
                """
            )
        ]
        project_links = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    e.id AS edge_id,
                    e.linked_id AS architecture_id,
                    e.relationship,
                    p.id AS project_id,
                    p.title AS project_title,
                    p.start_date AS project_start_date,
                    p.end_date AS project_end_date,
                    p.rag_status
                FROM edges e
                JOIN projects p ON p.id = e.project_id
                WHERE e.linked_type = 'architecture'
                ORDER BY p.end_date, p.id
                """
            )
        ]

    links_by_arch = {}
    for link in project_links:
        links_by_arch.setdefault(link["architecture_id"], []).append(link)

    roadmap = []
    for component in components:
        links = links_by_arch.get(component["id"], [])
        implemented = component.get("implemented_date")
        go_live = component.get("go_live_date")
        decommissioned = component.get("decommissioned_date")
        date_sources = {
            "implemented_date": "architecture_components"
            if implemented
            else None,
            "go_live_date": "architecture_components" if go_live else None,
            "decommissioned_date": "architecture_components"
            if decommissioned
            else None,
        }

        for link in links:
            if link["relationship"] == "implemented":
                if not implemented:
                    implemented = link["project_start_date"]
                    date_sources["implemented_date"] = (
                        f"project edge {link['project_id']} start"
                    )
                if not go_live:
                    go_live = link["project_end_date"]
                    date_sources["go_live_date"] = (
                        f"project edge {link['project_id']} end"
                    )
            elif link["relationship"] == "decommissioned":
                if not decommissioned:
                    decommissioned = link["project_end_date"]
                    date_sources["decommissioned_date"] = (
                        f"project edge {link['project_id']} end"
                    )

        bar_start = implemented or go_live
        bar_end = decommissioned  # None means still active

        golives = [
            {
                "project_id": link["project_id"],
                "project_title": link["project_title"],
                "date": link["project_end_date"],
                "relationship": link["relationship"],
                "rag_status": link["rag_status"],
            }
            for link in links
        ]

        roadmap.append(
            {
                "id": component["id"],
                "title": component["title"],
                "description": component["description"],
                "component_type": component["component_type"],
                "owner": component["owner"],
                "capability": component["capability"],
                "outlook": component["outlook"],
                "implemented_date": implemented,
                "go_live_date": go_live,
                "decommissioned_date": decommissioned,
                "bar_start": bar_start,
                "bar_end": bar_end,
                "date_sources": date_sources,
                "project_golives": golives,
            }
        )

    return {"components": roadmap}


def fetch_project_detail(project_id):
    """Return one project plus its linked risks and architecture components."""
    init_db()
    with get_connection() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return None

        zone_ctx = fetch_sub_zone_context(conn, project["sub_zone_id"])
        project_dict = dict(project)
        if zone_ctx:
            project_dict.update(zone_ctx)

        linked_risks = [
            dict(row)
            for row in conn.execute(
                """
                SELECT r.*, e.id AS edge_id, e.relationship
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
                SELECT a.*, e.id AS edge_id, e.relationship
                FROM edges e
                JOIN architecture_components a ON a.id = e.linked_id
                WHERE e.project_id = ? AND e.linked_type = 'architecture'
                ORDER BY a.id
                """,
                (project_id,),
            )
        ]

    return {
        "project": project_dict,
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

        zone_ctx = fetch_sub_zone_context(conn, risk["sub_zone_id"])
        risk_dict = dict(risk)
        if zone_ctx:
            risk_dict.update(zone_ctx)

        linked_projects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT p.*, e.id AS edge_id, e.relationship
                FROM edges e
                JOIN projects p ON p.id = e.project_id
                WHERE e.linked_type = 'risk' AND e.linked_id = ?
                ORDER BY p.start_date, p.id
                """,
                (risk_id,),
            )
        ]

    return {
        "risk": risk_dict,
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

        zone_ctx = fetch_sub_zone_context(conn, component["sub_zone_id"])
        component_dict = dict(component)
        if zone_ctx:
            component_dict.update(zone_ctx)

        linked_projects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT p.*, e.id AS edge_id, e.relationship
                FROM edges e
                JOIN projects p ON p.id = e.project_id
                WHERE e.linked_type = 'architecture' AND e.linked_id = ?
                ORDER BY p.start_date, p.id
                """,
                (architecture_id,),
            )
        ]

    return {
        "architecture": component_dict,
        "linked_projects": linked_projects,
    }


def _item_exists(conn, linked_type, linked_id):
    table = "risks" if linked_type == "risk" else "architecture_components"
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE id = ?", (linked_id,)
    ).fetchone()
    return row is not None


def add_link(project_id, linked_type, linked_id, relationship):
    """Create a persistent edge. Returns (ok, message, edge)."""
    if not get_writes_enabled():
        return False, "database changes are currently disabled", None

    if linked_type not in ("risk", "architecture"):
        return False, "linked_type must be risk or architecture", None

    if linked_type == "risk" and relationship not in RISK_RELATIONSHIPS:
        return False, f"relationship must be one of {RISK_RELATIONSHIPS}", None
    if (
        linked_type == "architecture"
        and relationship not in ARCHITECTURE_RELATIONSHIPS
    ):
        return (
            False,
            f"relationship must be one of {ARCHITECTURE_RELATIONSHIPS}",
            None,
        )

    init_db()
    with get_connection() as conn:
        project = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return False, "project not found", None
        if not _item_exists(conn, linked_type, linked_id):
            return False, f"{linked_type} not found", None

        existing = conn.execute(
            """
            SELECT id FROM edges
            WHERE project_id = ? AND linked_type = ? AND linked_id = ?
            """,
            (project_id, linked_type, linked_id),
        ).fetchone()
        if existing:
            return False, "link already exists", None

        edge_id = f"e-{uuid.uuid4().hex[:10]}"
        conn.execute(
            """
            INSERT INTO edges (id, project_id, linked_type, linked_id, relationship)
            VALUES (?, ?, ?, ?, ?)
            """,
            (edge_id, project_id, linked_type, linked_id, relationship),
        )
        edge = {
            "id": edge_id,
            "project_id": project_id,
            "linked_type": linked_type,
            "linked_id": linked_id,
            "relationship": relationship,
        }

    persist_db()
    return True, "created", edge


def remove_link(edge_id):
    """Delete a persistent edge. Returns (ok, message)."""
    if not get_writes_enabled():
        return False, "database changes are currently disabled"

    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM edges WHERE id = ?", (edge_id,)
        ).fetchone()
        if row is None:
            return False, "link not found"
        conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))

    persist_db()
    return True, "deleted"


def fetch_sub_zone_context(conn, sub_zone_id):
    """Return zone and sub-zone labels for a sub_zone_id."""
    row = conn.execute(
        """
        SELECT
            z.id AS zone_id,
            z.name AS zone_name,
            z.owner_name,
            sz.id AS sub_zone_id,
            sz.name AS sub_zone_name
        FROM sub_zones sz
        JOIN zones z ON z.id = sz.zone_id
        WHERE sz.id = ?
        """,
        (sub_zone_id,),
    ).fetchone()
    return dict(row) if row else None


def fetch_zones_tree():
    """Return zones with nested sub-zones, capabilities, and entity counts."""
    init_db()
    with get_connection() as conn:
        zones = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM zones ORDER BY sort_order, id"
            )
        ]
        sub_zones = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM sub_zones ORDER BY zone_id, sort_order, id"
            )
        ]
        capabilities = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM capabilities ORDER BY sub_zone_id, sort_order, id"
            )
        ]

        def count_map(table):
            return {
                row["sub_zone_id"]: row["count"]
                for row in conn.execute(
                    f"""
                    SELECT sub_zone_id, COUNT(*) AS count
                    FROM {table}
                    GROUP BY sub_zone_id
                    """
                )
            }

        project_counts = count_map("projects")
        risk_counts = count_map("risks")
        architecture_counts = count_map("architecture_components")

        caps_by_sub_zone = {}
        for capability in capabilities:
            caps_by_sub_zone.setdefault(capability["sub_zone_id"], []).append(
                capability
            )

        subs_by_zone = {}
        for sub_zone in sub_zones:
            sub_zone["capabilities"] = caps_by_sub_zone.get(sub_zone["id"], [])
            sub_zone["project_count"] = project_counts.get(sub_zone["id"], 0)
            sub_zone["risk_count"] = risk_counts.get(sub_zone["id"], 0)
            sub_zone["architecture_count"] = architecture_counts.get(
                sub_zone["id"], 0
            )
            subs_by_zone.setdefault(sub_zone["zone_id"], []).append(sub_zone)

        for zone in zones:
            zone_subs = subs_by_zone.get(zone["id"], [])
            zone["sub_zones"] = zone_subs
            zone["sub_zone_count"] = len(zone_subs)
            zone["capability_count"] = sum(
                len(sub_zone["capabilities"]) for sub_zone in zone_subs
            )
            zone["project_count"] = sum(
                sub_zone["project_count"] for sub_zone in zone_subs
            )
            zone["risk_count"] = sum(
                sub_zone["risk_count"] for sub_zone in zone_subs
            )
            zone["architecture_count"] = sum(
                sub_zone["architecture_count"] for sub_zone in zone_subs
            )

    return {"zones": zones}

