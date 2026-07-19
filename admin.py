"""
Database admin and status endpoints.

Public:
  - GET  /api/db-status
  - POST /api/db/restore-last-safe   (home-page restore for current env)

Admin-token only (Cursor / Cloud Scheduler — never exposed in the UI):
  - POST /internal/db/backup
  - POST /internal/db/reset-to-safe
  - POST /internal/db/mark-safe
  - POST /internal/db/writes
"""

import hmac
import os

from flask import Blueprint, jsonify, request

from db import (
    create_backup,
    get_db_status,
    mark_last_safe,
    restore_last_safe,
    set_writes_enabled,
)

admin_bp = Blueprint("admin", __name__)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


def _require_admin():
    if not ADMIN_TOKEN:
        return jsonify({"error": "ADMIN_TOKEN is not configured on this service"}), 503
    provided = request.headers.get("X-Admin-Token", "")
    if not hmac.compare_digest(provided, ADMIN_TOKEN):
        return jsonify({"error": "unauthorized"}), 401
    return None


@admin_bp.route("/api/db-status")
def db_status():
    return jsonify(get_db_status())


@admin_bp.route("/api/db/restore-last-safe", methods=["POST"])
def api_restore_last_safe():
    """Restore the current environment DB to its last-safe snapshot."""
    ok, message = restore_last_safe()
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify({"ok": True, "message": message, "status": get_db_status()})


@admin_bp.route("/internal/db/backup", methods=["POST"])
def internal_backup():
    denied = _require_admin()
    if denied:
        return denied
    ok, message, filename = create_backup()
    if not ok:
        return jsonify({"error": message, "filename": filename}), 400
    return jsonify({"ok": True, "message": message, "filename": filename})


@admin_bp.route("/internal/db/reset-to-safe", methods=["POST"])
def internal_reset_to_safe():
    denied = _require_admin()
    if denied:
        return denied
    ok, message = restore_last_safe()
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify({"ok": True, "message": message, "status": get_db_status()})


@admin_bp.route("/internal/db/mark-safe", methods=["POST"])
def internal_mark_safe():
    denied = _require_admin()
    if denied:
        return denied
    ok, message = mark_last_safe()
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify({"ok": True, "message": message, "status": get_db_status()})


@admin_bp.route("/internal/db/writes", methods=["POST"])
def internal_set_writes():
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    if "enabled" not in payload:
        return jsonify({"error": "body must include enabled: true|false"}), 400
    ok, message = set_writes_enabled(bool(payload["enabled"]))
    if not ok:
        return jsonify({"error": message}), 400
    return jsonify({"ok": True, "message": message, "status": get_db_status()})
