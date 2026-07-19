#!/usr/bin/env python3
"""
Cursor/admin controls for the environment database.

These actions are intentionally NOT available in the web UI.

Examples:
  python3 scripts/db_admin.py --env dev status
  python3 scripts/db_admin.py --env dev disable-writes
  python3 scripts/db_admin.py --env dev enable-writes
  python3 scripts/db_admin.py --env dev mark-safe
  python3 scripts/db_admin.py --env dev backup
  python3 scripts/db_admin.py --env dev reset

Requires:
  ADMIN_TOKEN  - must match the Cloud Run service env var
  Optional overrides:
  DEV_APP_URL  - default https://hello-world-dev-859465631308.europe-west1.run.app
  PROD_APP_URL - default https://hello-world-859465631308.europe-west1.run.app
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URLS = {
    "dev": os.environ.get(
        "DEV_APP_URL",
        "https://hello-world-dev-859465631308.europe-west1.run.app",
    ),
    "prod": os.environ.get(
        "PROD_APP_URL",
        "https://hello-world-859465631308.europe-west1.run.app",
    ),
    "local": os.environ.get("LOCAL_APP_URL", "http://127.0.0.1:5000"),
}


def _request(method, url, token=None, payload=None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Admin-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed


def main():
    parser = argparse.ArgumentParser(description="Database admin controls for Cursor")
    parser.add_argument(
        "--env",
        choices=sorted(DEFAULT_URLS),
        default="dev",
        help="Target environment",
    )
    parser.add_argument(
        "--url",
        help="Override app base URL",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("ADMIN_TOKEN", ""),
        help="Admin token (or set ADMIN_TOKEN)",
    )
    parser.add_argument(
        "command",
        choices=["status", "enable-writes", "disable-writes", "mark-safe", "backup", "reset"],
    )
    args = parser.parse_args()

    base = (args.url or DEFAULT_URLS[args.env]).rstrip("/")
    token = args.token.strip()

    if args.command == "status":
        status_code, body = _request("GET", f"{base}/api/db-status")
    elif args.command == "enable-writes":
        if not token:
            print("ADMIN_TOKEN is required for this command", file=sys.stderr)
            return 2
        status_code, body = _request(
            "POST", f"{base}/internal/db/writes", token=token, payload={"enabled": True}
        )
    elif args.command == "disable-writes":
        if not token:
            print("ADMIN_TOKEN is required for this command", file=sys.stderr)
            return 2
        status_code, body = _request(
            "POST",
            f"{base}/internal/db/writes",
            token=token,
            payload={"enabled": False},
        )
    elif args.command == "mark-safe":
        if not token:
            print("ADMIN_TOKEN is required for this command", file=sys.stderr)
            return 2
        status_code, body = _request(
            "POST", f"{base}/internal/db/mark-safe", token=token
        )
    elif args.command == "backup":
        if not token:
            print("ADMIN_TOKEN is required for this command", file=sys.stderr)
            return 2
        status_code, body = _request("POST", f"{base}/internal/db/backup", token=token)
    elif args.command == "reset":
        if not token:
            print("ADMIN_TOKEN is required for this command", file=sys.stderr)
            return 2
        status_code, body = _request(
            "POST", f"{base}/internal/db/reset-to-safe", token=token
        )
    else:
        print("unknown command", file=sys.stderr)
        return 2

    print(json.dumps({"http_status": status_code, "body": body}, indent=2))
    return 0 if 200 <= status_code < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
