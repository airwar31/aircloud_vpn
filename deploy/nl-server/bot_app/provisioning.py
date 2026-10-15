"""
Provisioning adapter layer for VPN client lifecycle.

This module is the migration seam between legacy 3x-ui operations and future
RemnaWave-backed provisioning.
"""

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import quote

import aiohttp

from bot_app.config import MigrationConfig, ServerConfig, XrayConfig
from bot_app.xray_api import XrayAPI, generate_vless_link

logger = logging.getLogger(__name__)


class ProvisioningError(Exception):
    """Provisioning operation failure with machine-friendly code."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class ProvisioningResult:
    """Provisioning operation result for create/renew paths."""

    email: str
    uuid: str
    vless_link: str


class Provisioner(ABC):
    """Abstract provisioner interface for migration-ready activation flow."""

    @abstractmethod
    async def create_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        user_id: int | None = None,
    ) -> ProvisioningResult:
        pass

    @abstractmethod
    async def renew_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        client_uuid: str = "",
        user_id: int | None = None,
    ) -> ProvisioningResult:
        pass


class LegacyProvisioner(Provisioner):
    """3x-ui based provisioner (current production behavior)."""

    @staticmethod
    def _target(tunnel_type: str) -> dict:
        if tunnel_type == "single":
            return {
                "cfg": XrayConfig.NL_PANEL,
                "inbound_id": XrayConfig.INBOUND_IDS["nl"]["single"],
                "server_ip": ServerConfig.NL_SERVER["ip"],
                "port": 8443,
                "pub_key": XrayConfig.NL_REALITY_PARAMS.get("public_key", ""),
                "short_id": XrayConfig.NL_REALITY_PARAMS.get("short_id", ""),
                "sni": XrayConfig.NL_REALITY_PARAMS.get("sni", "dl.google.com"),
                "prefer_security": "reality",
            }

        if tunnel_type == "double":
            return {
                "cfg": XrayConfig.VK_PANEL,
                "inbound_id": XrayConfig.INBOUND_IDS["vk"]["reality"],
                "server_ip": ServerConfig.VK_SERVER["ip"],
                "port": 443,
                "pub_key": XrayConfig.REALITY_PARAMS.get("public_key", ""),
                "short_id": XrayConfig.REALITY_PARAMS.get("short_id", ""),
                "sni": XrayConfig.REALITY_PARAMS.get("sni", "dl.google.com"),
                "prefer_security": "reality",
            }

        raise ProvisioningError("unsupported_tunnel_type", tunnel_type)

    async def create_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        user_id: int | None = None,
    ) -> ProvisioningResult:
        target = self._target(tunnel_type)
        cfg = target["cfg"]
        inbound_id = target["inbound_id"]

        async with XrayAPI(
            host=cfg["host"],
            port=cfg["port"],
            username=cfg["username"],
            password=cfg["password"],
        ) as xray_api:
            working_inbound_id = inbound_id
            result = await xray_api.add_client(
                inbound_id=working_inbound_id,
                email=email,
                expiry_days=expiry_days,
                tunnel_type=tunnel_type,
            )
            if not result:
                fallback_inbound_id = await xray_api.find_inbound_id(
                    prefer_security=target["prefer_security"],
                    prefer_port=target["port"],
                )
                if fallback_inbound_id and fallback_inbound_id != working_inbound_id:
                    logger.warning(
                        "Retrying add_client with auto-detected inbound id %s (was %s)",
                        fallback_inbound_id,
                        working_inbound_id,
                    )
                    working_inbound_id = fallback_inbound_id
                    result = await xray_api.add_client(
                        inbound_id=working_inbound_id,
                        email=email,
                        expiry_days=expiry_days,
                        tunnel_type=tunnel_type,
                    )

            if result and result.get("uuid"):
                client_uuid = result["uuid"]
            else:
                existing_client = await xray_api.get_client_by_email(working_inbound_id, email)
                client_uuid = existing_client.get("id") if existing_client else ""
                if not client_uuid:
                    detail = xray_api.last_error or f"inbound_id={working_inbound_id}"
                    raise ProvisioningError("add_client_failed", detail)

        vless_link = generate_vless_link(
            uuid=client_uuid,
            server_ip=target["server_ip"],
            port=target["port"],
            email=email,
            tunnel_type=tunnel_type,
            reality_public_key=target["pub_key"],
            reality_short_id=target["short_id"],
            sni=target["sni"],
        )
        return ProvisioningResult(email=email, uuid=client_uuid, vless_link=vless_link)

    async def renew_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        client_uuid: str = "",
        user_id: int | None = None,
    ) -> ProvisioningResult:
        target = self._target(tunnel_type)
        cfg = target["cfg"]

        async with XrayAPI(
            host=cfg["host"],
            port=cfg["port"],
            username=cfg["username"],
            password=cfg["password"],
        ) as xray_api:
            working_inbound_id = target["inbound_id"]
            resolved_uuid = (client_uuid or "").strip()

            if not resolved_uuid:
                existing_client = await xray_api.get_client_by_email(working_inbound_id, email)
                if existing_client:
                    resolved_uuid = (existing_client.get("id") or "").strip()
                else:
                    fallback_inbound_id = await xray_api.find_inbound_id(
                        prefer_security=target["prefer_security"],
                        prefer_port=target["port"],
                    )
                    if fallback_inbound_id and fallback_inbound_id != working_inbound_id:
                        working_inbound_id = fallback_inbound_id
                        existing_client = await xray_api.get_client_by_email(working_inbound_id, email)
                        if existing_client:
                            resolved_uuid = (existing_client.get("id") or "").strip()

            if not resolved_uuid:
                raise ProvisioningError("uuid_not_found", f"email={email}")

            updated = await xray_api.update_client(
                inbound_id=working_inbound_id,
                email=email,
                expiry_days=expiry_days,
                client_uuid=resolved_uuid,
            )

            if not updated:
                fallback_inbound_id = await xray_api.find_inbound_id(
                    prefer_security=target["prefer_security"],
                    prefer_port=target["port"],
                )
                if fallback_inbound_id and fallback_inbound_id != working_inbound_id:
                    working_inbound_id = fallback_inbound_id
                    updated = await xray_api.update_client(
                        inbound_id=working_inbound_id,
                        email=email,
                        expiry_days=expiry_days,
                        client_uuid=resolved_uuid,
                    )

            if not updated:
                existing_client = await xray_api.get_client_by_email(working_inbound_id, email)
                fallback_uuid = (existing_client.get("id") or "").strip() if existing_client else ""
                if fallback_uuid and fallback_uuid != resolved_uuid:
                    resolved_uuid = fallback_uuid
                    updated = await xray_api.update_client(
                        inbound_id=working_inbound_id,
                        email=email,
                        expiry_days=expiry_days,
                        client_uuid=resolved_uuid,
                    )

            if not updated:
                raise ProvisioningError("update_client_failed", xray_api.last_error)

        vless_link = generate_vless_link(
            uuid=resolved_uuid,
            server_ip=target["server_ip"],
            port=target["port"],
            email=email,
            tunnel_type=tunnel_type,
            reality_public_key=target["pub_key"],
            reality_short_id=target["short_id"],
            sni=target["sni"],
        )
        return ProvisioningResult(email=email, uuid=resolved_uuid, vless_link=vless_link)


class RemnaWaveProvisioner(Provisioner):
    """RemnaWave REST API-based provisioner implementation."""

    def __init__(self):
        self.base_url = MigrationConfig.REMNAWAVE_API_URL
        self.api_token = MigrationConfig.REMNAWAVE_API_TOKEN
        self.timeout = max(5, MigrationConfig.REMNAWAVE_TIMEOUT_SECONDS)
        self.retries = max(1, MigrationConfig.REMNAWAVE_HTTP_RETRIES)
        self.auth_mode = MigrationConfig.REMNAWAVE_AUTH_MODE

    @staticmethod
    def _target(tunnel_type: str) -> dict:
        return LegacyProvisioner._target(tunnel_type)

    @staticmethod
    def _squads_for_tunnel(tunnel_type: str) -> list[str]:
        if tunnel_type == "single":
            return MigrationConfig.REMNAWAVE_SINGLE_SQUADS
        if tunnel_type == "double":
            return MigrationConfig.REMNAWAVE_DOUBLE_SQUADS
        return []

    @staticmethod
    def _sanitize_username_seed(value: str) -> str:
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        cleaned = "".join(ch if ch in allowed else "_" for ch in value)
        cleaned = cleaned.strip("_")
        if len(cleaned) < 3:
            cleaned = f"vpn_{cleaned}".strip("_")
        return cleaned[:28]

    @staticmethod
    def _build_username(email: str, user_id: int | None) -> str:
        local = email.split("@", 1)[0]
        seed = RemnaWaveProvisioner._sanitize_username_seed(local)
        suffix_base = str(user_id) if user_id is not None else secrets.token_hex(3)
        digest = hashlib.sha1(suffix_base.encode("utf-8")).hexdigest()[:6]
        username = f"{seed}_{digest}"[:36]
        if len(username) < 3:
            username = f"vpn_{digest}"
        return username

    @staticmethod
    def _expire_at_iso(expiry_days: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()

    @staticmethod
    def _extract_user(data: dict | list | None) -> dict | None:
        if isinstance(data, dict):
            response = data.get("response")
            if isinstance(response, dict):
                return response
            if isinstance(response, list):
                return response[0] if response else None
            return data
        if isinstance(data, list):
            return data[0] if data else None
        return None

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "x-api-key":
            headers["X-API-KEY"] = self.api_token
        else:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict | None = None,
        expect_json: bool = True,
    ):
        if not self.base_url:
            raise ProvisioningError("remnawave_config_missing", "REMNAWAVE_API_URL is empty")
        if not self.api_token:
            raise ProvisioningError("remnawave_config_missing", "REMNAWAVE_API_TOKEN is empty")

        url = f"{self.base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=self._auth_headers()) as session:
                    async with session.request(method, url, json=json_payload) as response:
                        raw = await response.text()
                        content_type = (response.headers.get("Content-Type") or "").lower()

                        payload = None
                        if "json" in content_type:
                            try:
                                payload = await response.json(content_type=None)
                            except Exception:
                                payload = None

                        if response.status >= 400:
                            detail = raw
                            if isinstance(payload, dict):
                                detail = str(payload.get("message") or payload.get("errorCode") or payload)
                            raise ProvisioningError(
                                "remnawave_http_error",
                                f"{response.status} {path}: {detail[:280]}",
                            )

                        if expect_json:
                            if payload is not None:
                                return payload
                            raise ProvisioningError(
                                "remnawave_invalid_response",
                                f"Expected JSON for {path}, got: {raw[:120]}",
                            )

                        return payload if payload is not None else raw
            except ProvisioningError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(
                    "RemnaWave request failed attempt=%s/%s method=%s path=%s error=%s",
                    attempt,
                    self.retries,
                    method,
                    path,
                    e,
                )
                if attempt < self.retries:
                    await asyncio.sleep(min(2 * attempt, 5))

        raise ProvisioningError("remnawave_request_failed", f"{method} {path}: {last_error}")

    async def _get_user_by_email(self, email: str) -> dict | None:
        encoded_email = quote(email, safe="")
        payload = await self._request("GET", f"/api/users/by-email/{encoded_email}")
        return self._extract_user(payload)

    async def _create_user(self, body: dict) -> dict:
        payload = await self._request("POST", "/api/users", json_payload=body)
        user = self._extract_user(payload)
        if not user:
            raise ProvisioningError("remnawave_invalid_response", "create_user returned empty response")
        return user

    async def _update_user(self, body: dict) -> dict:
        payload = await self._request("PATCH", "/api/users", json_payload=body)
        user = self._extract_user(payload)
        if not user:
            raise ProvisioningError("remnawave_invalid_response", "update_user returned empty response")
        return user

    async def _get_primary_vless_link(self, short_uuid: str) -> str:
        encoded = quote(short_uuid, safe="")
        payload = await self._request(
            "GET",
            f"/api/subscriptions/by-short-uuid/{encoded}/raw",
            expect_json=False,
        )

        text = ""
        if isinstance(payload, str):
            text = payload
        elif isinstance(payload, dict):
            response = payload.get("response")
            if isinstance(response, str):
                text = response

        for line in text.splitlines():
            candidate = line.strip()
            if candidate.startswith("vless://"):
                return candidate
        raise ProvisioningError("remnawave_subscription_empty", f"short_uuid={short_uuid}")

    def _build_fallback_link(self, tunnel_type: str, email: str, client_uuid: str) -> str:
        target = self._target(tunnel_type)
        return generate_vless_link(
            uuid=client_uuid,
            server_ip=target["server_ip"],
            port=target["port"],
            email=email,
            tunnel_type=tunnel_type,
            reality_public_key=target["pub_key"],
            reality_short_id=target["short_id"],
            sni=target["sni"],
        )

    @staticmethod
    def _extract_vless_uuid(user: dict) -> str:
        for key in ("vlessUuid", "vlessUUID", "uuid"):
            value = user.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    async def create_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        user_id: int | None = None,
    ) -> ProvisioningResult:
        _ = self._target(tunnel_type)  # validates tunnel type
        existing = await self._get_user_by_email(email)
        if existing:
            user = existing
        else:
            payload = {
                "username": self._build_username(email, user_id),
                "email": email,
                "expireAt": self._expire_at_iso(expiry_days),
                "status": "ACTIVE",
            }
            squads = self._squads_for_tunnel(tunnel_type)
            if squads:
                payload["activeInternalSquads"] = squads

            user = await self._create_user(payload)

        client_uuid = self._extract_vless_uuid(user)
        if not client_uuid:
            raise ProvisioningError("remnawave_user_missing_vless_uuid", email)

        short_uuid = str(user.get("shortUuid") or "").strip()
        vless_link = ""
        if short_uuid:
            try:
                vless_link = await self._get_primary_vless_link(short_uuid)
            except ProvisioningError as e:
                logger.warning("RemnaWave raw subscription fetch failed for %s: %s", email, e.detail)

        if not vless_link:
            vless_link = self._build_fallback_link(tunnel_type, email, client_uuid)

        return ProvisioningResult(email=email, uuid=client_uuid, vless_link=vless_link)

    async def renew_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        client_uuid: str = "",
        user_id: int | None = None,
    ) -> ProvisioningResult:
        _ = user_id  # retained for future routing/analytics use
        _ = self._target(tunnel_type)  # validates tunnel type

        user = await self._get_user_by_email(email)
        if not user:
            raise ProvisioningError("remnawave_user_not_found", email)

        user_uuid = str(user.get("uuid") or "").strip()
        if not user_uuid:
            raise ProvisioningError("remnawave_user_missing_uuid", email)

        updated = await self._update_user(
            {
                "uuid": user_uuid,
                "expireAt": self._expire_at_iso(expiry_days),
                "status": "ACTIVE",
            }
        )

        effective_user = updated or user
        effective_uuid = client_uuid.strip() or self._extract_vless_uuid(effective_user) or self._extract_vless_uuid(user)
        if not effective_uuid:
            raise ProvisioningError("remnawave_user_missing_vless_uuid", email)

        short_uuid = str(effective_user.get("shortUuid") or user.get("shortUuid") or "").strip()
        vless_link = ""
        if short_uuid:
            try:
                vless_link = await self._get_primary_vless_link(short_uuid)
            except ProvisioningError as e:
                logger.warning("RemnaWave raw subscription fetch failed for %s: %s", email, e.detail)

        if not vless_link:
            vless_link = self._build_fallback_link(tunnel_type, email, effective_uuid)

        return ProvisioningResult(email=email, uuid=effective_uuid, vless_link=vless_link)


class RoutedProvisioner(Provisioner):
    """Routes provisioning between primary and optional canary/shadow providers."""

    def __init__(
        self,
        legacy: Provisioner,
        remnawave: Provisioner,
        mode: str,
        canary_percent: int,
        shadow_write_enabled: bool,
        fallback_to_legacy: bool,
    ):
        self.legacy = legacy
        self.remnawave = remnawave
        self.mode = mode
        self.canary_percent = max(0, min(canary_percent, 100))
        self.shadow_write_enabled = shadow_write_enabled
        self.fallback_to_legacy = fallback_to_legacy

    @staticmethod
    def _bucket(user_id: int | None, email: str) -> int:
        if user_id is not None:
            return abs(int(user_id)) % 100
        digest = hashlib.sha1(email.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100

    def _use_remnawave_primary(self, user_id: int | None, email: str) -> bool:
        if self.mode == "remnawave":
            return True
        if self.mode == "hybrid" and self.canary_percent > 0:
            return self._bucket(user_id, email) < self.canary_percent
        return False

    def _spawn_shadow(self, coro, action: str, tunnel_type: str, email: str):
        async def _runner():
            try:
                await coro
            except Exception as e:
                logger.warning(
                    "Shadow write failed action=%s tunnel=%s email=%s error=%s",
                    action,
                    tunnel_type,
                    email,
                    e,
                )

        asyncio.create_task(_runner())

    async def _execute_with_routing(
        self,
        action: str,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        client_uuid: str = "",
        user_id: int | None = None,
    ) -> ProvisioningResult:
        use_remnawave = self._use_remnawave_primary(user_id, email)
        primary = self.remnawave if use_remnawave else self.legacy
        secondary = self.legacy if use_remnawave else self.remnawave

        if action == "create":
            primary_call = primary.create_client(
                tunnel_type=tunnel_type,
                email=email,
                expiry_days=expiry_days,
                user_id=user_id,
            )
        else:
            primary_call = primary.renew_client(
                tunnel_type=tunnel_type,
                email=email,
                expiry_days=expiry_days,
                client_uuid=client_uuid,
                user_id=user_id,
            )

        try:
            result = await primary_call
        except ProvisioningError as e:
            if use_remnawave and self.fallback_to_legacy:
                logger.warning(
                    "RemnaWave primary failed action=%s tunnel=%s email=%s, fallback to legacy. error=%s",
                    action,
                    tunnel_type,
                    email,
                    e,
                )
                if action == "create":
                    result = await self.legacy.create_client(
                        tunnel_type=tunnel_type,
                        email=email,
                        expiry_days=expiry_days,
                        user_id=user_id,
                    )
                else:
                    result = await self.legacy.renew_client(
                        tunnel_type=tunnel_type,
                        email=email,
                        expiry_days=expiry_days,
                        client_uuid=client_uuid,
                        user_id=user_id,
                    )
            else:
                raise

        if self.mode == "hybrid" and self.shadow_write_enabled:
            if action == "create":
                self._spawn_shadow(
                    secondary.create_client(
                        tunnel_type=tunnel_type,
                        email=email,
                        expiry_days=expiry_days,
                        user_id=user_id,
                    ),
                    action,
                    tunnel_type,
                    email,
                )
            else:
                self._spawn_shadow(
                    secondary.renew_client(
                        tunnel_type=tunnel_type,
                        email=email,
                        expiry_days=expiry_days,
                        client_uuid=client_uuid,
                        user_id=user_id,
                    ),
                    action,
                    tunnel_type,
                    email,
                )

        return result

    async def create_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        user_id: int | None = None,
    ) -> ProvisioningResult:
        return await self._execute_with_routing(
            action="create",
            tunnel_type=tunnel_type,
            email=email,
            expiry_days=expiry_days,
            user_id=user_id,
        )

    async def renew_client(
        self,
        tunnel_type: str,
        email: str,
        expiry_days: int,
        client_uuid: str = "",
        user_id: int | None = None,
    ) -> ProvisioningResult:
        return await self._execute_with_routing(
            action="renew",
            tunnel_type=tunnel_type,
            email=email,
            expiry_days=expiry_days,
            client_uuid=client_uuid,
            user_id=user_id,
        )


def build_provisioner() -> Provisioner:
    """Build provisioner based on migration flags with canary/shadow support."""
    legacy = LegacyProvisioner()
    mode = MigrationConfig.PROVISIONER_MODE

    if mode == "legacy":
        return legacy

    if mode in {"hybrid", "remnawave"}:
        remnawave = RemnaWaveProvisioner()
        logger.info(
            "Provisioner routing enabled mode=%s canary=%s%% shadow=%s fallback_to_legacy=%s",
            mode,
            MigrationConfig.CANARY_PERCENT,
            MigrationConfig.SHADOW_WRITE_ENABLED,
            MigrationConfig.REMNAWAVE_FALLBACK_TO_LEGACY,
        )
        return RoutedProvisioner(
            legacy=legacy,
            remnawave=remnawave,
            mode=mode,
            canary_percent=MigrationConfig.CANARY_PERCENT,
            shadow_write_enabled=MigrationConfig.SHADOW_WRITE_ENABLED,
            fallback_to_legacy=MigrationConfig.REMNAWAVE_FALLBACK_TO_LEGACY,
        )

    logger.warning("Unknown PROVISIONER_MODE=%s. Using legacy 3x-ui provisioner.", mode)
    return legacy
