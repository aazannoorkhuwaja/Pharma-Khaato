#!/usr/bin/env python3
"""Start the main-computer service. Other counters never open its SQLite file."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep this running on the main shop computer while counters are open")
    parser.add_argument("--bind", default="0.0.0.0", help="LAN address to listen on")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--name", action="append", default=[], help="Main-computer LAN IP or hostname counters will use (repeat for several)")
    parser.add_argument("--data-dir", help="Local shop data folder; never use a network share")
    args = parser.parse_args(argv)
    os.environ["PHARMA_KHAATO_SHOP_SERVER"] = "1"
    if args.data_dir:
        os.environ["PHARMA_KHAATO_DATA_DIR"] = str(Path(args.data_dir).expanduser().resolve())
    from core.path_manager import PathManager
    from core.lan_service import create_shop_server, ensure_shop_certificate
    from core.auth_service import has_registered_employees
    from core.db_engine import get_conn
    get_conn().close()
    if not has_registered_employees():
        print("Open Pharma Khaato on this main computer first and create the owner account. Then start the shop service again.", file=sys.stderr)
        return 2
    cert, key = ensure_shop_certificate(Path(PathManager.get_config_dir()) / "shop-tls", args.name)
    server = create_shop_server((args.bind, args.port), str(cert), str(key))
    print(f"Shop service is ready on port {server.server_address[1]}.")
    print(f"For each counter, copy only this shop certificate: {cert}")
    print("Choose Connect to shop on that counter, enter https://MAIN-COMPUTER:" + str(server.server_address[1]) + ", and select the copied certificate.")
    print("Keep the main computer on and this service running. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        from core.db_engine import reset_thread_connections
        reset_thread_connections()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
