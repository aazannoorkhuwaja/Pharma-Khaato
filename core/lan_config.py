"""Local counter connection settings; credentials are never saved here."""
from __future__ import annotations

import json
import os
import re
import shutil
import ssl
from pathlib import Path
from urllib.parse import urlsplit


def configuration_path() -> Path:
    from core.path_manager import PathManager
    return Path(PathManager.get_config_dir()) / "counter_connection.json"


def validate_connection(server_url: str, certificate_path: str, terminal_id: str) -> dict:
    url = urlsplit(str(server_url).strip().rstrip("/"))
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
        raise ValueError("Enter the shop address as https://MAIN-PC:8765 or https://192.168.1.10:8765.")
    try:
        _ = url.port
    except ValueError as exc:
        raise ValueError("Enter a valid shop port number.") from exc
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(terminal_id)):
        raise ValueError("Use a counter name with letters, numbers, underscores or dashes (for example Counter-2).")
    certificate = Path(certificate_path).expanduser().resolve()
    if not certificate.is_file():
        raise ValueError("Choose the shop certificate copied from the main computer.")
    return {"server_url": url.geturl(), "certificate_path": str(certificate), "terminal_id": str(terminal_id)}


def load_counter_config() -> dict | None:
    # The host process must never route its own database operations back to LAN.
    if os.environ.get("PHARMA_KHAATO_SHOP_SERVER") == "1":
        return None
    if os.environ.get("PHARMA_KHAATO_SERVER_URL"):
        return validate_connection(os.environ["PHARMA_KHAATO_SERVER_URL"],
                                   os.environ.get("PHARMA_KHAATO_SERVER_CERT", ""),
                                   os.environ.get("PHARMA_KHAATO_TERMINAL_ID", "Counter-1"))
    path = configuration_path()
    if not path.exists():
        return None
    values = json.loads(path.read_text(encoding="utf-8"))
    if values.get("mode") in {"standalone", "host"}:
        return None
    return validate_connection(values["server_url"], values["certificate_path"], values["terminal_id"])


def save_counter_config(server_url: str, certificate_path: str, terminal_id: str) -> dict:
    values = validate_connection(server_url, certificate_path, terminal_id)
    path = configuration_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ssl.create_default_context(cafile=values["certificate_path"])
    local_certificate = path.parent / "trusted-shop.pem"
    if Path(values["certificate_path"]) != local_certificate:
        shutil.copyfile(values["certificate_path"], local_certificate)
    values["certificate_path"] = str(local_certificate)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"mode": "counter", **values}, indent=2), encoding="utf-8")
    temporary.replace(path)
    reset_client()
    return values


def use_standalone() -> None:
    path = configuration_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text('{"mode": "standalone"}\n', encoding="utf-8")
    temporary.replace(path)
    reset_client()


def save_host_config(shop_address: str, port: int = 8765) -> dict:
    from core.lan_service import ensure_shop_certificate
    path = configuration_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    port = int(port)
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a shop port between 1024 and 65535.")
    cert, key = ensure_shop_certificate(path.parent / "shop-tls", [shop_address])
    values = {"mode": "host", "port": port, "shop_address": shop_address,
              "certificate_path": str(cert), "key_path": str(key)}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, indent=2), encoding="utf-8")
    temporary.replace(path)
    reset_client()
    return values


_shop_server = None


def start_configured_shop_server():
    """Share the main application's local database while this app is open."""
    global _shop_server
    if _shop_server is not None:
        return _shop_server
    path = configuration_path()
    if not path.exists():
        return None
    values = json.loads(path.read_text(encoding="utf-8"))
    if values.get("mode") != "host":
        return None
    import threading
    from core.lan_service import create_shop_server
    _shop_server = create_shop_server(("0.0.0.0", int(values["port"])), values["certificate_path"], values["key_path"])
    threading.Thread(target=_shop_server.serve_forever, name="pharma-shop-service", daemon=True).start()
    return _shop_server


_client = None
_client_config = None


def reset_client() -> None:
    global _client, _client_config
    if _client is not None:
        _client.logout()
    _client = _client_config = None


def enabled_counter_client():
    global _client, _client_config
    values = load_counter_config()
    if values is None:
        return None
    if _client is None or values != _client_config:
        from core.lan_client import LanClient
        _client = LanClient(**values)
        _client_config = values
    return _client
