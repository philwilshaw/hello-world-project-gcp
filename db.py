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
SCHEMA_VERSION = 7

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
BUDGET_RELATIONSHIPS = ("creates", "terminates")
RUN_CONTRACT_RELATIONSHIPS = ("terminates",)
LINKED_TYPES = ("risk", "architecture", "budget", "run_contract")

BUDGET_STATUS_RAG = {
    "Proposed": "Amber",
    "Budget agreed": "Green",
    "in flight": "Green",
    "Budget not agreed": "Red",
    "Completed": "Green",
    "Cancelled": "Red",
}


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
                DROP TABLE IF EXISTS run_contracts;
                DROP TABLE IF EXISTS budgets;
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

            CREATE TABLE IF NOT EXISTS budgets (
                line_id TEXT PRIMARY KEY,
                budget_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                category TEXT NOT NULL,
                spend_type TEXT NOT NULL,
                sub_zone_id TEXT NOT NULL,
                capex_2026 REAL NOT NULL DEFAULT 0,
                opex_2026 REAL NOT NULL DEFAULT 0,
                capex_2027 REAL NOT NULL DEFAULT 0,
                opex_2027 REAL NOT NULL DEFAULT 0,
                capex_2028 REAL NOT NULL DEFAULT 0,
                opex_2028 REAL NOT NULL DEFAULT 0,
                capex_2029 REAL NOT NULL DEFAULT 0,
                opex_2029 REAL NOT NULL DEFAULT 0,
                contact TEXT NOT NULL,
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            CREATE TABLE IF NOT EXISTS projects (
                line_id TEXT PRIMARY KEY,
                budget_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                sub_zone_id TEXT NOT NULL,
                priority_2027 TEXT NOT NULL DEFAULT '',
                outcomes TEXT NOT NULL DEFAULT '',
                compliance_impact TEXT NOT NULL DEFAULT '',
                delivery_approach TEXT NOT NULL DEFAULT '',
                delivery_constraints TEXT NOT NULL DEFAULT '',
                delivery_assumptions TEXT NOT NULL DEFAULT '',
                out_of_scope TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (budget_id) REFERENCES budgets(budget_id),
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            CREATE TABLE IF NOT EXISTS risks (
                id TEXT PRIMARY KEY,
                sub_zone_id TEXT NOT NULL,
                risk_response TEXT NOT NULL,
                status TEXT NOT NULL,
                category TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                risk_owner TEXT NOT NULL,
                proximity_band TEXT NOT NULL,
                current_likelihood TEXT NOT NULL,
                current_impact_band TEXT NOT NULL,
                date_created TEXT NOT NULL,
                date_closed TEXT,
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            CREATE TABLE IF NOT EXISTS architecture_components (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                comments TEXT NOT NULL DEFAULT '',
                sub_zone_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                architect TEXT NOT NULL,
                architecture_outlook TEXT NOT NULL,
                deployment_state TEXT NOT NULL,
                deployment_date TEXT,
                decommission_date TEXT,
                in_scope_of_esa TEXT NOT NULL,
                class_of_service TEXT NOT NULL,
                host_type TEXT NOT NULL,
                replaced_by_arch_id TEXT,
                support_partner_l1 TEXT NOT NULL DEFAULT '',
                support_partner_l2 TEXT NOT NULL DEFAULT '',
                support_partner_l3 TEXT NOT NULL DEFAULT '',
                vendor TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id),
                FOREIGN KEY (capability_id) REFERENCES capabilities(id),
                FOREIGN KEY (replaced_by_arch_id) REFERENCES architecture_components(id)
            );

            CREATE TABLE IF NOT EXISTS run_contracts (
                fin_id TEXT PRIMARY KEY,
                service_type TEXT NOT NULL,
                linked_budget_id TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                contract_name TEXT NOT NULL,
                description TEXT NOT NULL,
                detailed_description TEXT NOT NULL,
                contract_start_date TEXT NOT NULL,
                contract_end_date TEXT NOT NULL,
                po_renewal_date TEXT NOT NULL,
                contract_status TEXT NOT NULL,
                vendor_manager TEXT NOT NULL,
                operational_owner TEXT NOT NULL,
                sub_zone_id TEXT NOT NULL,
                FOREIGN KEY (linked_budget_id) REFERENCES budgets(budget_id),
                FOREIGN KEY (sub_zone_id) REFERENCES sub_zones(id)
            );

            -- Links projects to risks, architecture, budgets, or run contracts.
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                linked_type TEXT NOT NULL,
                linked_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(line_id)
            );

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
    from seed_data import (
        apply_architecture_replacements,
        build_zone_maps,
        generate_architecture,
        generate_architecture_edges,
        generate_budgets,
        generate_edges,
        generate_projects,
        generate_risks,
        generate_run_contracts,
    )

    _seed_zones(conn)
    zone_maps = build_zone_maps(conn)

    budgets = generate_budgets(zone_maps, 50)
    conn.executemany(
        """
        INSERT INTO budgets (
            line_id, budget_id, title, description, status, category,
            spend_type, sub_zone_id, capex_2026, opex_2026, capex_2027,
            opex_2027, capex_2028, opex_2028, capex_2029, opex_2029, contact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                b["line_id"],
                b["budget_id"],
                b["title"],
                b["description"],
                b["status"],
                b["category"],
                b["spend_type"],
                b["sub_zone_id"],
                b["capex_2026"],
                b["opex_2026"],
                b["capex_2027"],
                b["opex_2027"],
                b["capex_2028"],
                b["opex_2028"],
                b["capex_2029"],
                b["opex_2029"],
                b["contact"],
            )
            for b in budgets
        ],
    )

    projects = generate_projects(budgets, zone_maps, 50)
    conn.executemany(
        """
        INSERT INTO projects (
            line_id, budget_id, title, description, sub_zone_id,
            priority_2027, outcomes, compliance_impact, delivery_approach,
            delivery_constraints, delivery_assumptions, out_of_scope
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                p["line_id"],
                p["budget_id"],
                p["title"],
                p["description"],
                p["sub_zone_id"],
                p["priority_2027"],
                p["outcomes"],
                p["compliance_impact"],
                p["delivery_approach"],
                p["delivery_constraints"],
                p["delivery_assumptions"],
                p["out_of_scope"],
            )
            for p in projects
        ],
    )

    risks = generate_risks(zone_maps, 50)
    conn.executemany(
        """
        INSERT INTO risks (
            id, sub_zone_id, risk_response, status, category, risk_score,
            name, description, risk_owner, proximity_band, current_likelihood,
            current_impact_band, date_created, date_closed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["id"],
                r["sub_zone_id"],
                r["risk_response"],
                r["status"],
                r["category"],
                r["risk_score"],
                r["name"],
                r["description"],
                r["risk_owner"],
                r["proximity_band"],
                r["current_likelihood"],
                r["current_impact_band"],
                r["date_created"],
                r["date_closed"],
            )
            for r in risks
        ],
    )

    architecture = generate_architecture(zone_maps, 50)
    conn.executemany(
        """
        INSERT INTO architecture_components (
            id, name, description, comments, sub_zone_id, capability_id,
            architect, architecture_outlook, deployment_state, deployment_date,
            decommission_date, in_scope_of_esa, class_of_service, host_type,
            replaced_by_arch_id, support_partner_l1, support_partner_l2,
            support_partner_l3, vendor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                a["id"],
                a["name"],
                a["description"],
                a["comments"],
                a["sub_zone_id"],
                a["capability_id"],
                a["architect"],
                a["architecture_outlook"],
                a["deployment_state"],
                a["deployment_date"],
                a["decommission_date"],
                a["in_scope_of_esa"],
                a["class_of_service"],
                a["host_type"],
                None,
                a["support_partner_l1"],
                a["support_partner_l2"],
                a["support_partner_l3"],
                a["vendor"],
            )
            for a in architecture
        ],
    )
    apply_architecture_replacements(conn, architecture)

    run_contracts = generate_run_contracts(budgets, zone_maps, 50)
    conn.executemany(
        """
        INSERT INTO run_contracts (
            fin_id, service_type, linked_budget_id, vendor_name, manufacturer,
            contract_name, description, detailed_description, contract_start_date,
            contract_end_date, po_renewal_date, contract_status, vendor_manager,
            operational_owner, sub_zone_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                rc["fin_id"],
                rc["service_type"],
                rc["linked_budget_id"],
                rc["vendor_name"],
                rc["manufacturer"],
                rc["contract_name"],
                rc["description"],
                rc["detailed_description"],
                rc["contract_start_date"],
                rc["contract_end_date"],
                rc["po_renewal_date"],
                rc["contract_status"],
                rc["vendor_manager"],
                rc["operational_owner"],
                rc["sub_zone_id"],
            )
            for rc in run_contracts
        ],
    )

    edges = generate_edges(projects, risks, architecture, budgets, run_contracts)
    conn.executemany(
        """
        INSERT INTO edges (id, project_id, linked_type, linked_id, relationship)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (e["id"], e["project_id"], e["linked_type"], e["linked_id"], e["relationship"])
            for e in edges
        ],
    )

    arch_edges = generate_architecture_edges(architecture)
    conn.executemany(
        """
        INSERT INTO architecture_edges (id, source_id, target_id, relationship)
        VALUES (?, ?, ?, ?)
        """,
        [
            (ae["id"], ae["source_id"], ae["target_id"], ae["relationship"])
            for ae in arch_edges
        ],
    )


def _budget_year_range(budget):
    """Return (start_date, end_date) ISO strings from budget spend years."""
    years = []
    for year in (2026, 2027, 2028, 2029):
        capex = budget.get(f"capex_{year}", 0) or 0
        opex = budget.get(f"opex_{year}", 0) or 0
        if capex + opex > 0:
            years.append(year)
    if not years:
        return "2026-01-01", "2026-12-31"
    return f"{min(years)}-01-01", f"{max(years)}-12-31"


def _budget_totals(budget):
    capex = sum(budget.get(f"capex_{y}", 0) or 0 for y in (2026, 2027, 2028, 2029))
    opex = sum(budget.get(f"opex_{y}", 0) or 0 for y in (2026, 2027, 2028, 2029))
    return capex, opex


def _enrich_project(project, budget=None):
    """Add legacy timeline/display fields derived from the linked budget."""
    row = dict(project)
    row["id"] = row["line_id"]
    if budget:
        start, end = _budget_year_range(budget)
        capex, opex = _budget_totals(budget)
        row["start_date"] = start
        row["end_date"] = end
        row["capex_gbp"] = capex
        row["opex_gbp"] = opex
        row["rag_status"] = BUDGET_STATUS_RAG.get(budget["status"], "Amber")
        row["budget_line_id"] = budget["line_id"]
        row["budget_status"] = budget["status"]
    return row


def _enrich_risk(risk):
    row = dict(risk)
    row["title"] = row["name"]
    row["impact"] = row["current_impact_band"]
    row["proximity"] = row["proximity_band"]
    row["value"] = f"Score {row['risk_score']}/10"
    return row


def _enrich_architecture(component, capability_name=None):
    row = dict(component)
    row["title"] = row["name"]
    row["owner"] = row["architect"]
    row["outlook"] = row["architecture_outlook"]
    row["component_type"] = row["host_type"]
    row["implemented_date"] = row.get("deployment_date")
    row["go_live_date"] = row.get("deployment_date")
    row["decommissioned_date"] = row.get("decommission_date")
    if capability_name:
        row["capability"] = capability_name
    return row


def _budgets_by_id(conn):
    return {
        row["budget_id"]: dict(row)
        for row in conn.execute("SELECT * FROM budgets")
    }


def _capabilities_by_id(conn):
    return {
        row["id"]: row["name"]
        for row in conn.execute("SELECT id, name FROM capabilities")
    }


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

        budgets = _budgets_by_id(conn)
        projects = []
        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            for row in conn.execute(
                f"""
                SELECT
                    p.*,
                    z.name AS zone_name,
                    z.sort_order AS zone_sort,
                    sz.name AS sub_zone_name,
                    sz.sort_order AS sub_zone_sort
                FROM projects p
                JOIN sub_zones sz ON sz.id = p.sub_zone_id
                JOIN zones z ON z.id = sz.zone_id
                WHERE p.line_id IN ({placeholders})
                ORDER BY z.sort_order, z.name, sz.sort_order, sz.name, p.line_id
                """,
                tuple(project_ids),
            ):
                project = dict(row)
                budget = budgets.get(project["budget_id"])
                enriched = _enrich_project(project, budget)
                enriched["zone_name"] = project["zone_name"]
                enriched["sub_zone_name"] = project["sub_zone_name"]
                projects.append(enriched)

        risks = [_enrich_risk(r) for r in _fetch_by_ids(conn, "risks", risk_ids)]
        caps = _capabilities_by_id(conn)
        architecture_components = [
            _enrich_architecture(c, caps.get(c.get("capability_id")))
            for c in _fetch_by_ids(conn, "architecture_components", architecture_ids)
        ]

    return {
        "projects": projects,
        "risks": risks,
        "architecture_components": architecture_components,
        "edges": edges,
    }


def fetch_all_projects():
    init_db()
    with get_connection() as conn:
        budgets = _budgets_by_id(conn)
        return [
            _enrich_project(dict(row), budgets.get(row["budget_id"]))
            for row in conn.execute(
                "SELECT * FROM projects ORDER BY line_id"
            )
        ]


def fetch_all_risks():
    init_db()
    with get_connection() as conn:
        return [
            _enrich_risk(dict(row))
            for row in conn.execute("SELECT * FROM risks ORDER BY id")
        ]


def fetch_all_architecture():
    init_db()
    with get_connection() as conn:
        caps = _capabilities_by_id(conn)
        return [
            _enrich_architecture(dict(row), caps.get(row["capability_id"]))
            for row in conn.execute(
                """
                SELECT a.*
                FROM architecture_components a
                LEFT JOIN capabilities c ON c.id = a.capability_id
                ORDER BY c.name, a.name, a.id
                """
            )
        ]


def _enrich_budget(budget):
    row = dict(budget)
    row["id"] = row["line_id"]
    return row


def _enrich_run_contract(contract):
    row = dict(contract)
    row["id"] = row["fin_id"]
    row["title"] = row["contract_name"]
    return row


def _projects_linked_to(conn, linked_type, linked_id):
    """Projects with a direct edge to the given entity."""
    budgets = _budgets_by_id(conn)
    projects = []
    for row in conn.execute(
        """
        SELECT p.*, e.id AS edge_id, e.relationship
        FROM edges e
        JOIN projects p ON p.line_id = e.project_id
        WHERE e.linked_type = ? AND e.linked_id = ?
        ORDER BY p.line_id
        """,
        (linked_type, linked_id),
    ):
        project = _enrich_project(dict(row), budgets.get(row["budget_id"]))
        project["edge_id"] = row["edge_id"]
        project["relationship"] = row["relationship"]
        projects.append(project)
    return projects


def _cross_links_via_projects(conn, project_ids, *, exclude_type=None, exclude_id=None):
    """
    Collect other entities linked to the given projects (sibling links).

    Items keep edge_id for remove, plus via_project_id / via_project_title.
    """
    if not project_ids:
        return {
            "linked_risks": [],
            "linked_architecture": [],
            "linked_budgets": [],
            "linked_run_contracts": [],
        }

    placeholders = ",".join("?" for _ in project_ids)
    params = tuple(project_ids)
    caps = _capabilities_by_id(conn)
    project_titles = {
        row["line_id"]: row["title"]
        for row in conn.execute(
            f"SELECT line_id, title FROM projects WHERE line_id IN ({placeholders})",
            params,
        )
    }

    risks = []
    for row in conn.execute(
        f"""
        SELECT r.*, e.id AS edge_id, e.relationship, e.project_id AS via_project_id
        FROM edges e
        JOIN risks r ON r.id = e.linked_id
        WHERE e.linked_type = 'risk' AND e.project_id IN ({placeholders})
        ORDER BY r.id
        """,
        params,
    ):
        if exclude_type == "risk" and row["id"] == exclude_id:
            continue
        item = _enrich_risk(dict(row))
        item["edge_id"] = row["edge_id"]
        item["relationship"] = row["relationship"]
        item["via_project_id"] = row["via_project_id"]
        item["via_project_title"] = project_titles.get(row["via_project_id"], "")
        risks.append(item)

    architecture = []
    for row in conn.execute(
        f"""
        SELECT a.*, e.id AS edge_id, e.relationship, e.project_id AS via_project_id
        FROM edges e
        JOIN architecture_components a ON a.id = e.linked_id
        WHERE e.linked_type = 'architecture' AND e.project_id IN ({placeholders})
        ORDER BY a.id
        """,
        params,
    ):
        if exclude_type == "architecture" and row["id"] == exclude_id:
            continue
        item = _enrich_architecture(dict(row), caps.get(row["capability_id"]))
        item["edge_id"] = row["edge_id"]
        item["relationship"] = row["relationship"]
        item["via_project_id"] = row["via_project_id"]
        item["via_project_title"] = project_titles.get(row["via_project_id"], "")
        architecture.append(item)

    budgets = []
    for row in conn.execute(
        f"""
        SELECT b.*, e.id AS edge_id, e.relationship, e.project_id AS via_project_id
        FROM edges e
        JOIN budgets b ON b.line_id = e.linked_id
        WHERE e.linked_type = 'budget' AND e.project_id IN ({placeholders})
        ORDER BY b.line_id
        """,
        params,
    ):
        if exclude_type == "budget" and row["line_id"] == exclude_id:
            continue
        item = _enrich_budget(dict(row))
        item["edge_id"] = row["edge_id"]
        item["relationship"] = row["relationship"]
        item["via_project_id"] = row["via_project_id"]
        item["via_project_title"] = project_titles.get(row["via_project_id"], "")
        budgets.append(item)

    run_contracts = []
    for row in conn.execute(
        f"""
        SELECT rc.*, e.id AS edge_id, e.relationship, e.project_id AS via_project_id
        FROM edges e
        JOIN run_contracts rc ON rc.fin_id = e.linked_id
        WHERE e.linked_type = 'run_contract' AND e.project_id IN ({placeholders})
        ORDER BY rc.fin_id
        """,
        params,
    ):
        if exclude_type == "run_contract" and row["fin_id"] == exclude_id:
            continue
        item = _enrich_run_contract(dict(row))
        item["edge_id"] = row["edge_id"]
        item["relationship"] = row["relationship"]
        item["via_project_id"] = row["via_project_id"]
        item["via_project_title"] = project_titles.get(row["via_project_id"], "")
        run_contracts.append(item)

    return {
        "linked_risks": risks,
        "linked_architecture": architecture,
        "linked_budgets": budgets,
        "linked_run_contracts": run_contracts,
    }


def fetch_all_budgets():
    init_db()
    with get_connection() as conn:
        rows = []
        for row in conn.execute(
            """
            SELECT
                b.*,
                z.name AS zone_name,
                sz.name AS sub_zone_name
            FROM budgets b
            JOIN sub_zones sz ON sz.id = b.sub_zone_id
            JOIN zones z ON z.id = sz.zone_id
            ORDER BY b.line_id
            """
        ):
            item = _enrich_budget(dict(row))
            item["zone_name"] = row["zone_name"]
            item["sub_zone_name"] = row["sub_zone_name"]
            rows.append(item)
        return rows


def fetch_all_run_contracts():
    init_db()
    with get_connection() as conn:
        rows = []
        for row in conn.execute(
            """
            SELECT
                rc.*,
                z.name AS zone_name,
                sz.name AS sub_zone_name
            FROM run_contracts rc
            JOIN sub_zones sz ON sz.id = rc.sub_zone_id
            JOIN zones z ON z.id = sz.zone_id
            ORDER BY rc.fin_id
            """
        ):
            item = _enrich_run_contract(dict(row))
            item["zone_name"] = row["zone_name"]
            item["sub_zone_name"] = row["sub_zone_name"]
            rows.append(item)
        return rows


def fetch_architecture_graph():
    """Return architecture components and inter-component relationships."""
    init_db()
    with get_connection() as conn:
        caps = _capabilities_by_id(conn)
        components = [
            _enrich_architecture(dict(row), caps.get(row["capability_id"]))
            for row in conn.execute(
                """
                SELECT a.*
                FROM architecture_components a
                LEFT JOIN capabilities c ON c.id = a.capability_id
                ORDER BY c.name, a.name, a.id
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
    """Return architecture components grouped by capability (flat)."""
    components = fetch_all_architecture()
    grouped = {}
    for component in components:
        grouped.setdefault(component.get("capability") or "Unassigned", []).append(
            component
        )
    return grouped


def fetch_architecture_model():
    """
    Return architecture components nested as:
    [{zone_name, sub_zones: [{sub_zone_name, capabilities: [{name, components}]}]}]
    """
    init_db()
    with get_connection() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    a.*,
                    c.name AS capability_name,
                    c.sort_order AS capability_sort,
                    sz.name AS sub_zone_name,
                    sz.sort_order AS sub_zone_sort,
                    z.name AS zone_name,
                    z.sort_order AS zone_sort
                FROM architecture_components a
                JOIN sub_zones sz ON sz.id = a.sub_zone_id
                JOIN zones z ON z.id = sz.zone_id
                LEFT JOIN capabilities c ON c.id = a.capability_id
                ORDER BY z.sort_order, z.name, sz.sort_order, sz.name,
                         c.sort_order, c.name, a.name, a.id
                """
            )
        ]

    zones = []
    zone_index = {}
    for row in rows:
        component = _enrich_architecture(row, row.get("capability_name"))
        component["zone_name"] = row["zone_name"]
        component["sub_zone_name"] = row["sub_zone_name"]
        component["capability"] = row.get("capability_name") or "Unassigned"

        zone_name = row["zone_name"]
        if zone_name not in zone_index:
            zone_index[zone_name] = {
                "zone_name": zone_name,
                "sub_zones": [],
                "_sub_index": {},
            }
            zones.append(zone_index[zone_name])
        zone = zone_index[zone_name]

        sub_name = row["sub_zone_name"]
        if sub_name not in zone["_sub_index"]:
            zone["_sub_index"][sub_name] = {
                "sub_zone_name": sub_name,
                "capabilities": [],
                "_cap_index": {},
            }
            zone["sub_zones"].append(zone["_sub_index"][sub_name])
        sub_zone = zone["_sub_index"][sub_name]

        cap_name = component["capability"]
        if cap_name not in sub_zone["_cap_index"]:
            sub_zone["_cap_index"][cap_name] = {
                "name": cap_name,
                "components": [],
            }
            sub_zone["capabilities"].append(sub_zone["_cap_index"][cap_name])
        sub_zone["_cap_index"][cap_name]["components"].append(component)

    for zone in zones:
        for sub_zone in zone["sub_zones"]:
            del sub_zone["_cap_index"]
        del zone["_sub_index"]

    return zones

def fetch_architecture_roadmap():
    """
    Return architecture lifespan bars and project go-live impacts.

    Lifecycle dates come from architecture_components first. Missing
    implemented / go-live / decommissioned dates are inferred from project
    edges (implemented / decommissioned relationships) where possible.
    """
    init_db()

    with get_connection() as conn:
        caps = _capabilities_by_id(conn)
        budgets = _budgets_by_id(conn)
        components = [
            dict(row)
            for row in conn.execute(
                """
                SELECT a.*
                FROM architecture_components a
                LEFT JOIN capabilities c ON c.id = a.capability_id
                ORDER BY c.name, a.name, a.id
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
                    p.line_id AS project_id,
                    p.title AS project_title,
                    p.budget_id,
                    b.status AS budget_status
                FROM edges e
                JOIN projects p ON p.line_id = e.project_id
                JOIN budgets b ON b.budget_id = p.budget_id
                WHERE e.linked_type = 'architecture'
                ORDER BY p.line_id
                """
            )
        ]

    links_by_arch = {}
    for link in project_links:
        budget = budgets.get(link["budget_id"])
        if budget:
            start, end = _budget_year_range(budget)
            link["project_start_date"] = start
            link["project_end_date"] = end
            link["rag_status"] = BUDGET_STATUS_RAG.get(budget["status"], "Amber")
        links_by_arch.setdefault(link["architecture_id"], []).append(link)

    roadmap = []
    for component in components:
        enriched = _enrich_architecture(component, caps.get(component["capability_id"]))
        links = links_by_arch.get(component["id"], [])
        implemented = enriched.get("deployment_date")
        go_live = enriched.get("deployment_date")
        decommissioned = enriched.get("decommission_date")
        date_sources = {
            "implemented_date": "architecture_components" if implemented else None,
            "go_live_date": "architecture_components" if go_live else None,
            "decommissioned_date": "architecture_components"
            if decommissioned
            else None,
        }

        for link in links:
            if link["relationship"] == "implemented":
                if not implemented:
                    implemented = link.get("project_start_date")
                    date_sources["implemented_date"] = (
                        f"project edge {link['project_id']} start"
                    )
                if not go_live:
                    go_live = link.get("project_end_date")
                    date_sources["go_live_date"] = (
                        f"project edge {link['project_id']} end"
                    )
            elif link["relationship"] == "decommissioned":
                if not decommissioned:
                    decommissioned = link.get("project_end_date")
                    date_sources["decommissioned_date"] = (
                        f"project edge {link['project_id']} end"
                    )

        bar_start = implemented or go_live
        bar_end = decommissioned

        golives = [
            {
                "project_id": link["project_id"],
                "project_title": link["project_title"],
                "date": link.get("project_end_date"),
                "relationship": link["relationship"],
                "rag_status": link.get("rag_status", "Amber"),
            }
            for link in links
        ]

        roadmap.append(
            {
                "id": enriched["id"],
                "title": enriched["title"],
                "description": enriched["description"],
                "component_type": enriched["component_type"],
                "owner": enriched["owner"],
                "capability": enriched.get("capability", ""),
                "outlook": enriched["outlook"],
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
            "SELECT * FROM projects WHERE line_id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return None

        budgets = _budgets_by_id(conn)
        budget = budgets.get(project["budget_id"])
        zone_ctx = fetch_sub_zone_context(conn, project["sub_zone_id"])
        project_dict = _enrich_project(project, budget)
        if zone_ctx:
            project_dict.update(zone_ctx)

        linked_risks = [
            {**_enrich_risk(dict(row)), "edge_id": row["edge_id"], "relationship": row["relationship"]}
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
        caps = _capabilities_by_id(conn)
        linked_architecture = [
            {
                **_enrich_architecture(dict(row), caps.get(row["capability_id"])),
                "edge_id": row["edge_id"],
                "relationship": row["relationship"],
            }
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
        linked_budgets = [
            {
                **_enrich_budget(dict(row)),
                "edge_id": row["edge_id"],
                "relationship": row["relationship"],
            }
            for row in conn.execute(
                """
                SELECT b.*, e.id AS edge_id, e.relationship
                FROM edges e
                JOIN budgets b ON b.line_id = e.linked_id
                WHERE e.project_id = ? AND e.linked_type = 'budget'
                ORDER BY b.line_id
                """,
                (project_id,),
            )
        ]
        # Include the project's owning budget (FK) if not already edge-linked.
        if budget and budget["line_id"] not in {b["id"] for b in linked_budgets}:
            owning = _enrich_budget(budget)
            owning["edge_id"] = None
            owning["relationship"] = "owns"
            linked_budgets.insert(0, owning)

        linked_run_contracts = [
            {
                **_enrich_run_contract(dict(row)),
                "edge_id": row["edge_id"],
                "relationship": row["relationship"],
            }
            for row in conn.execute(
                """
                SELECT rc.*, e.id AS edge_id, e.relationship
                FROM edges e
                JOIN run_contracts rc ON rc.fin_id = e.linked_id
                WHERE e.project_id = ? AND e.linked_type = 'run_contract'
                ORDER BY rc.fin_id
                """,
                (project_id,),
            )
        ]

    return {
        "project": project_dict,
        "linked_risks": linked_risks,
        "linked_architecture": linked_architecture,
        "linked_budgets": linked_budgets,
        "linked_run_contracts": linked_run_contracts,
        "linked_projects": [],
    }


def fetch_risk_detail(risk_id):
    """Return one risk plus linked projects and cross-linked siblings."""
    init_db()
    with get_connection() as conn:
        risk = conn.execute(
            "SELECT * FROM risks WHERE id = ?", (risk_id,)
        ).fetchone()
        if risk is None:
            return None

        zone_ctx = fetch_sub_zone_context(conn, risk["sub_zone_id"])
        risk_dict = _enrich_risk(risk)
        if zone_ctx:
            risk_dict.update(zone_ctx)

        linked_projects = _projects_linked_to(conn, "risk", risk_id)
        cross = _cross_links_via_projects(
            conn,
            [p["id"] for p in linked_projects],
            exclude_type="risk",
            exclude_id=risk_id,
        )

    return {
        "risk": risk_dict,
        "linked_projects": linked_projects,
        **cross,
    }


def fetch_architecture_detail(architecture_id):
    """Return one architecture component plus linked projects and siblings."""
    init_db()
    with get_connection() as conn:
        component = conn.execute(
            "SELECT * FROM architecture_components WHERE id = ?",
            (architecture_id,),
        ).fetchone()
        if component is None:
            return None

        caps = _capabilities_by_id(conn)
        zone_ctx = fetch_sub_zone_context(conn, component["sub_zone_id"])
        component_dict = _enrich_architecture(
            component, caps.get(component["capability_id"])
        )
        if zone_ctx:
            component_dict.update(zone_ctx)

        linked_projects = _projects_linked_to(conn, "architecture", architecture_id)
        cross = _cross_links_via_projects(
            conn,
            [p["id"] for p in linked_projects],
            exclude_type="architecture",
            exclude_id=architecture_id,
        )

    return {
        "architecture": component_dict,
        "linked_projects": linked_projects,
        **cross,
    }


def fetch_budget_detail(budget_line_id):
    """Return one budget plus linked projects, FK run contracts, and siblings."""
    init_db()
    with get_connection() as conn:
        budget = conn.execute(
            "SELECT * FROM budgets WHERE line_id = ?", (budget_line_id,)
        ).fetchone()
        if budget is None:
            return None

        zone_ctx = fetch_sub_zone_context(conn, budget["sub_zone_id"])
        budget_dict = _enrich_budget(budget)
        if zone_ctx:
            budget_dict.update(zone_ctx)

        linked_projects = _projects_linked_to(conn, "budget", budget_line_id)

        # Projects that own this budget via FK.
        budgets_map = _budgets_by_id(conn)
        owning_ids = {p["id"] for p in linked_projects}
        for row in conn.execute(
            "SELECT * FROM projects WHERE budget_id = ? ORDER BY line_id",
            (budget["budget_id"],),
        ):
            if row["line_id"] in owning_ids:
                continue
            project = _enrich_project(dict(row), budgets_map.get(row["budget_id"]))
            project["edge_id"] = None
            project["relationship"] = "owns"
            linked_projects.append(project)

        # Run contracts that reference this budget ID.
        linked_run_contracts = [
            {
                **_enrich_run_contract(dict(row)),
                "edge_id": None,
                "relationship": "funded by",
            }
            for row in conn.execute(
                """
                SELECT * FROM run_contracts
                WHERE linked_budget_id = ?
                ORDER BY fin_id
                """,
                (budget["budget_id"],),
            )
        ]

        cross = _cross_links_via_projects(
            conn,
            [p["id"] for p in linked_projects if p.get("edge_id")],
            exclude_type="budget",
            exclude_id=budget_line_id,
        )
        # Merge FK run contracts with edge-based ones (dedupe by id).
        seen_rc = {rc["id"] for rc in linked_run_contracts}
        for rc in cross["linked_run_contracts"]:
            if rc["id"] not in seen_rc:
                linked_run_contracts.append(rc)
                seen_rc.add(rc["id"])

    return {
        "budget": budget_dict,
        "linked_projects": linked_projects,
        "linked_risks": cross["linked_risks"],
        "linked_architecture": cross["linked_architecture"],
        "linked_budgets": cross["linked_budgets"],
        "linked_run_contracts": linked_run_contracts,
    }


def fetch_run_contract_detail(fin_id):
    """Return one run contract plus linked projects, budget, and siblings."""
    init_db()
    with get_connection() as conn:
        contract = conn.execute(
            "SELECT * FROM run_contracts WHERE fin_id = ?", (fin_id,)
        ).fetchone()
        if contract is None:
            return None

        zone_ctx = fetch_sub_zone_context(conn, contract["sub_zone_id"])
        contract_dict = _enrich_run_contract(contract)
        if zone_ctx:
            contract_dict.update(zone_ctx)

        linked_projects = _projects_linked_to(conn, "run_contract", fin_id)

        linked_budgets = []
        budget_row = conn.execute(
            "SELECT * FROM budgets WHERE budget_id = ?",
            (contract["linked_budget_id"],),
        ).fetchone()
        if budget_row:
            item = _enrich_budget(dict(budget_row))
            item["edge_id"] = None
            item["relationship"] = "funds"
            linked_budgets.append(item)

        cross = _cross_links_via_projects(
            conn,
            [p["id"] for p in linked_projects],
            exclude_type="run_contract",
            exclude_id=fin_id,
        )
        seen_budgets = {b["id"] for b in linked_budgets}
        for budget in cross["linked_budgets"]:
            if budget["id"] not in seen_budgets:
                linked_budgets.append(budget)
                seen_budgets.add(budget["id"])

    return {
        "run_contract": contract_dict,
        "linked_projects": linked_projects,
        "linked_risks": cross["linked_risks"],
        "linked_architecture": cross["linked_architecture"],
        "linked_budgets": linked_budgets,
        "linked_run_contracts": cross["linked_run_contracts"],
    }


def _item_exists(conn, linked_type, linked_id):
    table_map = {
        "risk": "risks",
        "architecture": "architecture_components",
        "budget": "budgets",
        "run_contract": "run_contracts",
    }
    id_column_map = {
        "risk": "id",
        "architecture": "id",
        "budget": "line_id",
        "run_contract": "fin_id",
    }
    table = table_map.get(linked_type)
    id_column = id_column_map.get(linked_type)
    if not table:
        return False
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE {id_column} = ?", (linked_id,)
    ).fetchone()
    return row is not None


def add_link(project_id, linked_type, linked_id, relationship):
    """Create a persistent edge. Returns (ok, message, edge)."""
    if not get_writes_enabled():
        return False, "database changes are currently disabled", None

    if linked_type not in LINKED_TYPES:
        return False, f"linked_type must be one of {LINKED_TYPES}", None

    if linked_type == "risk" and relationship not in RISK_RELATIONSHIPS:
        return False, f"relationship must be one of {RISK_RELATIONSHIPS}", None
    if linked_type == "architecture" and relationship not in ARCHITECTURE_RELATIONSHIPS:
        return (
            False,
            f"relationship must be one of {ARCHITECTURE_RELATIONSHIPS}",
            None,
        )
    if linked_type == "budget" and relationship not in BUDGET_RELATIONSHIPS:
        return False, f"relationship must be one of {BUDGET_RELATIONSHIPS}", None
    if linked_type == "run_contract" and relationship not in RUN_CONTRACT_RELATIONSHIPS:
        return (
            False,
            f"relationship must be one of {RUN_CONTRACT_RELATIONSHIPS}",
            None,
        )

    init_db()
    with get_connection() as conn:
        project = conn.execute(
            "SELECT line_id FROM projects WHERE line_id = ?", (project_id,)
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

