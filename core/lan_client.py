"""Small TLS-verified JSON transport for the existing desktop model layer."""
from __future__ import annotations

import dataclasses
import hashlib
import http.client
import json
import ssl
import threading
import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlsplit


class ShopConnectionError(ConnectionError):
    """An unavailable host never changes a counter to a separate local database."""


class ShopAuthorizationError(PermissionError):
    pass


class ShopOperationError(ValueError):
    """A rejected or uncertain operation must not silently create a new request."""


def json_value(value):
    if isinstance(value, SimpleNamespace):
        return json_value(vars(value))
    if dataclasses.is_dataclass(value):
        return {key: json_value(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported shop response type: {type(value).__name__}")


class LanClient:
    def __init__(self, server_url: str, certificate_path: str, terminal_id: str, timeout: float = 15):
        from core.lan_config import validate_connection
        values = validate_connection(server_url, certificate_path, terminal_id)
        self.server_url = values["server_url"]
        parsed = urlsplit(self.server_url)
        self.host, self.port = parsed.hostname, parsed.port or 443
        self.terminal_id = values["terminal_id"]
        self.context = ssl.create_default_context(cafile=values["certificate_path"])
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.timeout = timeout
        self._token = None
        self._pending: dict[str, str] = {}
        self._lock = threading.RLock()

    def _post(self, path: str, values: dict, *, authenticated: bool = True):
        data = json.dumps(json_value(values), allow_nan=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if authenticated:
            if not self._token:
                raise ShopAuthorizationError("Sign in to the shop before using this counter.")
            headers["Authorization"] = "Bearer " + self._token
        connection = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            connection.request("POST", path, data, headers)
            response = connection.getresponse()
            raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ShopConnectionError("The shop response was too large. Contact support.")
            payload = json.loads(raw.decode("utf-8"))
            if response.status in (401, 403):
                raise ShopAuthorizationError(payload.get("error", "Sign in to the shop again."))
            if response.status in (400, 404, 409, 413, 415):
                raise ShopOperationError(payload.get("error", "The shop rejected this operation."))
            if response.status != 200:
                raise ShopConnectionError(payload.get("error", "The shop could not complete this request."))
            return payload["result"]
        except ShopAuthorizationError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException, UnicodeError, json.JSONDecodeError) as exc:
            raise ShopConnectionError("The main shop computer could not be reached securely. Keep this sale open and retry when the connection returns.") from exc
        finally:
            connection.close()

    def public_status(self):
        return self._post("/v1/status", {}, authenticated=False)

    def login(self, username: str, password: str):
        self._token = None
        result = self._post("/v1/login", {"username": username, "password": password, "terminal_id": self.terminal_id}, authenticated=False)
        if not result:
            return None
        self._token = result["token"]
        return tuple(result["employee"])

    def logout(self):
        try:
            if self._token:
                self._post("/v1/logout", {})
        except (ShopConnectionError, ShopAuthorizationError):
            pass
        finally:
            self._token = None

    def call(self, model_name: str, method_name: str, *args, request_id: str | None = None, **kwargs):
        business = json_value({"model": model_name, "method": method_name, "args": args, "kwargs": kwargs})
        identity = hashlib.sha256(json.dumps(business, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        with self._lock:
            operation_id = request_id or self._pending.setdefault(identity, uuid.uuid4().hex)
        values = {**business, "request_id": operation_id}
        # An interrupted response may follow a successful commit. Reuse the same
        # identity for transport retry and subsequent operator retry.
        for attempt in range(2):
            try:
                result = self._post("/v1/call", values)
                with self._lock:
                    self._pending.pop(identity, None)
                return result
            except ShopConnectionError:
                if attempt:
                    raise
