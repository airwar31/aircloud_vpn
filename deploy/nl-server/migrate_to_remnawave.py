"""
Legacy SQLite -> RemnaWave migration helper.

Capabilities:
- export active subscriptions/users into RemnaWave-compatible payload JSON
- optional import to RemnaWave via REST API
- dry-run mode by default

Usage examples:
  python migrate_to_remnawave.py export --out remnawave_users.json
  python migrate_to_remnawave.py import --in remnawave_users.json --dry-run
  python migrate_to_remnawave.py import --in remnawave_users.json --live
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


def _parse_expires_at(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    text = str(value).strip()
    if not text:
        return datetime.now(timezone.utc)

    try:
        ts = float(text)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        pass

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _username(seed: str, user_id: int) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    cleaned = "".join(ch if ch in allowed else "_" for ch in seed).strip("_")
    if len(cleaned) < 3:
        cleaned = f"vpn_{user_id}"
    cleaned = cleaned[:28]
    return f"{cleaned}_{user_id}"[:36]


@dataclass
class RemnaWaveClient:
    base_url: str
    api_token: str
    auth_mode: str = "bearer"
    timeout: int = 20

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "x-api-key":
            headers["X-API-KEY"] = self.api_token
        else:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = requests.request(
            method=method,
            url=url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )

        content_type = response.headers.get("Content-Type", "")
        body: Any = response.text
        if "json" in content_type.lower():
            try:
                body = response.json()
            except Exception:
                body = response.text

        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code} {path}: {body}")

        return body

    def get_user_by_email(self, email: str) -> dict | None:
        payload = self._request("GET", f"/api/users/by-email/{quote(email, safe='')}")
        data = payload.get("response", payload) if isinstance(payload, dict) else payload
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict):
            return data
        return None

    def create_user(self, payload: dict) -> dict:
        data = self._request("POST", "/api/users", payload)
        response = data.get("response", data) if isinstance(data, dict) else data
        if not isinstance(response, dict):
            raise RuntimeError(f"Unexpected create_user response: {data}")
        return response

    def update_user(self, payload: dict) -> dict:
        data = self._request("PATCH", "/api/users", payload)
        response = data.get("response", data) if isinstance(data, dict) else data
        if not isinstance(response, dict):
            raise RuntimeError(f"Unexpected update_user response: {data}")
        return response


def export_data(db_path: Path, out_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            u.user_id,
            u.username,
            u.created_at AS user_created_at,
            s.email,
            s.uuid,
            s.tunnel_type,
            s.expires_at
        FROM vpn_subscriptions s
        JOIN users u ON u.user_id = s.user_id
        WHERE s.status = 'active'
        ORDER BY u.user_id, s.expires_at DESC
        """
    ).fetchall()

    dedup: dict[str, dict] = {}
    for row in rows:
        email = row["email"]
        if email in dedup:
            continue

        expires_at = _parse_expires_at(row["expires_at"])
        item = {
            "source": {
                "user_id": int(row["user_id"]),
                "legacy_username": row["username"] or f"user_{row['user_id']}",
                "legacy_tunnel_type": row["tunnel_type"],
                "legacy_uuid": row["uuid"] or "",
            },
            "remnawave": {
                "username": _username(row["username"] or "vpn_user", int(row["user_id"])),
                "email": email,
                "expireAt": _iso(expires_at),
                "status": "ACTIVE",
            },
        }

        # Keep original VLESS UUID where possible to reduce churn during migration.
        if row["uuid"]:
            item["remnawave"]["vlessUuid"] = row["uuid"]

        dedup[email] = item

    payload = {
        "generated_at": _iso(datetime.now(timezone.utc)),
        "source_db": str(db_path),
        "total": len(dedup),
        "items": list(dedup.values()),
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Exported {len(dedup)} users to {out_path}")


def import_data(
    in_path: Path,
    remnawave_url: str,
    remnawave_token: str,
    auth_mode: str,
    timeout: int,
    live: bool,
) -> None:
    data = json.loads(in_path.read_text(encoding="utf-8"))
    items = data.get("items", [])

    if not isinstance(items, list):
        raise RuntimeError("Input JSON must contain 'items' list")

    client = RemnaWaveClient(
        base_url=remnawave_url.rstrip("/"),
        api_token=remnawave_token,
        auth_mode=auth_mode,
        timeout=timeout,
    )

    created = 0
    updated = 0
    failed = 0

    for idx, item in enumerate(items, start=1):
        payload = item.get("remnawave", {})
        email = payload.get("email", "")
        if not email:
            failed += 1
            print(f"[{idx}] skip: missing email")
            continue

        try:
            if not live:
                print(f"[{idx}] dry-run upsert email={email}")
                continue

            existing = client.get_user_by_email(email)
            if existing:
                update_payload = {
                    "uuid": existing.get("uuid"),
                    "expireAt": payload.get("expireAt"),
                    "status": "ACTIVE",
                }
                client.update_user(update_payload)
                updated += 1
                print(f"[{idx}] updated email={email}")
            else:
                client.create_user(payload)
                created += 1
                print(f"[{idx}] created email={email}")

        except Exception as e:
            failed += 1
            print(f"[{idx}] failed email={email}: {e}")

    mode = "LIVE" if live else "DRY-RUN"
    print(f"Done ({mode}): created={created} updated={updated} failed={failed} total={len(items)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate legacy users/subscriptions to RemnaWave")
    sub = parser.add_subparsers(dest="command", required=True)

    export_cmd = sub.add_parser("export", help="Export legacy data to JSON")
    export_cmd.add_argument("--db", default=os.getenv("DB_PATH", "./data/users.db"), help="Path to legacy SQLite DB")
    export_cmd.add_argument("--out", default="remnawave_users.json", help="Output JSON path")

    import_cmd = sub.add_parser("import", help="Import JSON into RemnaWave")
    import_cmd.add_argument("--in", dest="input_path", default="remnawave_users.json", help="Input JSON path")
    import_cmd.add_argument("--url", default=os.getenv("REMNAWAVE_API_URL", ""), help="RemnaWave API URL")
    import_cmd.add_argument("--token", default=os.getenv("REMNAWAVE_API_TOKEN", ""), help="RemnaWave API token")
    import_cmd.add_argument("--auth-mode", choices=["bearer", "x-api-key"], default=os.getenv("REMNAWAVE_AUTH_MODE", "bearer"))
    import_cmd.add_argument("--timeout", type=int, default=int(os.getenv("REMNAWAVE_TIMEOUT_SECONDS", "20")))
    import_cmd.add_argument("--live", action="store_true", help="Perform real API writes")
    import_cmd.add_argument("--dry-run", action="store_true", help="Alias for non-live mode")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export":
        export_data(Path(args.db), Path(args.out))
        return 0

    if args.command == "import":
        live = bool(args.live and not args.dry_run)
        if live and (not args.url or not args.token):
            print("LIVE import requires --url and --token (or env REMNAWAVE_API_URL/REMNAWAVE_API_TOKEN)")
            return 2

        import_data(
            in_path=Path(args.input_path),
            remnawave_url=args.url,
            remnawave_token=args.token,
            auth_mode=args.auth_mode,
            timeout=args.timeout,
            live=live,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
