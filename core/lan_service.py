"""Shop-local HTTPS API with explicit operations and one authoritative SQLite.

No SQL, Python names, filesystem paths or executable code are accepted from a
counter. Staff identity and counter identity come from the authenticated session.
"""
from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import re
import secrets
import socket
import ssl
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.lan_client import json_value

_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")


class ShopAPIError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


# (required permission, mutation). A new model method is private until explicitly
# reviewed here. A property is likewise individually listed.
OPERATIONS = {
    "AppModel": {"health": ("pos.sell", False)},
    "AuthModel": {"employees": ("staff.manage", False), "create_employee": ("staff.manage", True), "reset_password": ("staff.manage", True)},
    "CustomerModel": {"validate_cnic": ("customer.read", False), "register": ("customer.create", True), "search": ("customer.read", False), "search_with_debt": ("credit.read", False), "total_debt": ("credit.read", False), "debt_aging": ("credit.read", False), "khatoo_summary": ("credit.read", False)},
    "InventoryModel": {"search_products": ("pos.sell", False), "product_by_barcode": ("pos.sell", False), "products": ("inventory.read", False), "suppliers": ("inventory.read", False), "register_product": ("inventory.manage", True), "register_supplier": ("inventory.manage", True), "add_batch": ("inventory.manage", True), "near_expiry": ("inventory.read", False), "expired_stock": ("inventory.read", False), "low_stock": ("inventory.read", False), "active_batches": ("inventory.read", False)},
    "POSModel": {"hold_sale": ("pos.hold", True), "held_sales": ("pos.hold", False), "recall_sale": ("pos.hold", True), "active_session": ("cash.own_shift", False), "tax_rate": ("pos.sell", False), "process_checkout": ("pos.sell", True), "lookup_checkout": ("pos.sell", False), "discount_threshold_pct": ("pos.sell", False)},
    "ManagerAuthModel": {"verify": ("pos.sell", False), "issue_approval": ("pos.sell", True), "discount_threshold_pct": ("pos.sell", False)},
    "KhatooModel": {"load": ("credit.read", False), "record_payment": ("credit.collect", True), "payment_history": ("credit.read", False), "summary": ("credit.read", False)},
    "CashSessionModel": {"active_session": ("cash.own_shift", False), "open_session": ("cash.own_shift", True), "close_session": ("cash.own_shift", True), "record_movement": ("cash.own_shift", True), "expected_cash": ("cash.own_shift", False), "cash_summary": ("cash.own_shift", False), "recent_movements": ("cash.own_shift", False)},
    "ReportsModel": {"daily_sales": ("reports.read", False), "credit_collections": ("reports.read", False), "expiry_alert": ("reports.read", False), "reorder_stock": ("reports.read", False), "audit_log": ("reports.read", False)},
    "SettingsModel": {"get": ("pos.sell", False), "get_many": ("pos.sell", False), "set": ("settings.manage", True), "update": ("settings.manage", True), "backups": ("backups.manage", False), "create_backup": ("backups.manage", True)},
    "ReturnModel": {"lookup": ("returns.process", False), "process": ("returns.process", True), "get_returnable_sale": ("returns.process", False), "process_return": ("returns.process", True)},
}

OPERATIONS["CustomerModel"].update({"create": ("customer.create", True), "count": ("customer.read", False)})
OPERATIONS["ManagerAuthModel"]["issue_discount_approval"] = ("pos.sell", True)
OPERATIONS["KhatooModel"].update({"accounts": ("credit.read", False), "account_count": ("credit.read", False),
    "collect": ("credit.collect", True), "reverse": ("credit.reverse", True), "payment_count": ("credit.read", False),
    "statement": ("credit.read", False), "receipt": ("credit.read", False)})
OPERATIONS["ReturnModel"].update({"sale": ("returns.process", False), "operation_status": ("returns.process", False)})
OPERATIONS["POSModel"].update({"lookup_checkout_result": ("pos.sell", False), "sell_units": ("pos.sell", False),
    "receipt_for_sale": ("pos.sell", False)})
OPERATIONS["InventoryModel"].update({"catalog_snapshot": ("inventory.read", False), "catalog_search": ("inventory.read", False),
    "sell_units": ("pos.sell", False), "product_details": ("inventory.read", False), "stock_batches": ("inventory.read", False),
    "update_product": ("inventory.manage", True), "set_batch_count": ("inventory.manage", True)})

# These canonical services store their operation identity in the same database
# transaction as their financial or stock change. A pending transport record can
# therefore be reconciled after a host restart without creating a new operation.
OPERATIONS['InventoryModel'].update({
    'supplier_accounts':('inventory.manage',False),'supplier_history':('inventory.manage',False),
    'supplier_invoice_lines':('inventory.manage',False),'receive_invoice':('inventory.manage',True),
    'pay_supplier':('inventory.manage',True),'return_to_supplier':('inventory.manage',True),
})
OPERATIONS['POSModel']['catalog_matches']=('pos.sell',False)
OPERATIONS['CashSessionModel']['last_closed_session']=('cash.own_shift',False)
OPERATIONS['CashSessionModel']['session_movements']=('cash.own_shift',False)

REPLAY_SAFE = {
    ('InventoryModel','receive_invoice'),('InventoryModel','pay_supplier'),('InventoryModel','return_to_supplier'),
    ('CashSessionModel','open_session'),
    ("POSModel", "process_checkout"),
    ("InventoryModel", "register_product"), ("InventoryModel", "register_supplier"),
    ("InventoryModel", "add_batch"), ("InventoryModel", "update_product"), ("InventoryModel", "set_batch_count"),
    ("KhatooModel", "collect"), ("KhatooModel", "record_payment"), ("KhatooModel", "reverse"),
    ("ReturnModel", "process"), ("CashSessionModel", "record_movement"), ("CashSessionModel", "close_session"),
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _invoke_remote(function):
    from core.runtime_context import remote_request
    token=remote_request.set(True)
    try:
        return function()
    finally:
        remote_request.reset(token)


class ShopService:
    def __init__(self, *, session_seconds: int = 12 * 60 * 60):
        self.session_seconds = max(60, min(int(session_seconds), 24 * 60 * 60))
        self._mutation_lock = threading.RLock()
        self._models = {}

    def status(self):
        from core.auth_service import has_registered_employees
        return {"ready": True, "configured": has_registered_employees(), "protocol": 1}

    def login(self, username: str, password: str, terminal_id: str):
        from core.auth_service import login_user
        from core.db_engine import get_db
        if not _SAFE_ID.fullmatch(str(terminal_id)) or len(str(terminal_id)) > 64:
            raise ShopAPIError(400, "Choose a valid counter name.")
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 200 or len(password) > 1024:
            raise ShopAPIError(400, "Enter a valid staff username and password.")
        try:
            employee = login_user(username, password)
        except PermissionError as exc:
            raise ShopAPIError(401, str(exc)) from exc
        if employee is None:
            return None
        token = secrets.token_urlsafe(32)
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("SELECT password FROM Employee WHERE Employee_id = %s", (int(employee[0]),))
            revision = _digest(str(cur.fetchone()[0]))
            cur.execute("DELETE FROM Shop_Session WHERE expires_at < %s", (time.time(),))
            cur.execute("INSERT INTO Shop_Session(token_hash,employee_id,terminal_id,password_revision,expires_at) VALUES(%s,%s,%s,%s,%s)",
                        (_digest(token), int(employee[0]), terminal_id, revision, time.time() + self.session_seconds))
        return {"token": token, "employee": list(employee)}

    def session(self, token: str):
        from core.db_engine import get_db
        if not token or len(token) > 200:
            raise ShopAPIError(401, "Sign in to the shop again.")
        with get_db() as (_conn, cur):
            cur.execute("SELECT s.employee_id,s.terminal_id,s.password_revision,s.expires_at,e.password FROM Shop_Session s JOIN Employee e ON e.Employee_id=s.employee_id WHERE s.token_hash=%s", (_digest(token),))
            row = cur.fetchone()
        if not row or float(row[3]) <= time.time() or not hmac.compare_digest(str(row[2]), _digest(str(row[4]))):
            raise ShopAPIError(401, "Your shop sign-in has expired. Sign in again.")
        return {"employee_id": int(row[0]), "terminal_id": str(row[1]), "session_id": _digest(token)}

    def logout(self, token: str):
        from core.db_engine import get_db
        with get_db(immediate=True) as (_conn, cur):
            cur.execute("DELETE FROM Shop_Session WHERE token_hash=%s", (_digest(token),))
        with self._mutation_lock:
            for key in list(self._models):
                if key[0] == _digest(token):
                    self._models.pop(key, None)
        return True

    def _model(self, model_name: str, session: dict):
        # Stateful POS recall state belongs to one signed-in counter, never all
        # HTTP requests or all terminals sharing an employee account.
        key = (session["session_id"], model_name)
        with self._mutation_lock:
            if key not in self._models:
                from models import services
                local_models = getattr(services, "LOCAL_MODELS", {})
                if model_name == "ReturnModel":
                    from models import return_model
                    cls = getattr(return_model, "LOCAL_RETURN_MODEL", return_model.ReturnModel)
                else:
                    cls = local_models.get(model_name)
                    if cls is None:
                        cls = getattr(services, model_name)
                self._models[key] = cls()
            return self._models[key]

    def _prepare(self, session, model_name, method_name, args, kwargs, request_id=""):
        from core.permission_service import clear_permission_cache, has_permission
        specification = OPERATIONS.get(model_name, {}).get(method_name)
        if specification is None:
            raise ShopAPIError(404, "This shop operation is not available.")
        actor = session["employee_id"]
        clear_permission_cache(actor)
        if not has_permission(actor, specification[0]):
            raise ShopAPIError(403, "Your staff account does not have permission for this action.")
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise ShopAPIError(400, "The counter sent invalid request information.")
        model = self._model(model_name, session)
        if method_name == "process_checkout" and model_name == "POSModel":
            from core.pos_service import CheckoutRequest
            if len(args) != 1 or kwargs or not isinstance(args[0], dict):
                raise ShopAPIError(400, "The sale request is invalid.")
            values = dict(args[0])
            if int(values.get("employee_id", actor)) != actor:
                raise ShopAPIError(403, "A sale cannot be submitted for another staff member.")
            values["employee_id"] = actor
            values["terminal_id"] = session["terminal_id"]
            values.pop("manager_authorized", None)
            request = CheckoutRequest(**values)
            if not _SAFE_ID.fullmatch(str(getattr(request, "checkout_token", ""))):
                raise ShopAPIError(400, "The sale needs a valid checkout identity before it can be sent.")
            from core.checkout_idempotency_service import process_checkout_idempotently
            return lambda: process_checkout_idempotently(request, model.process_checkout), specification[1]
        if model_name == "POSModel" and method_name == "lookup_checkout":
            from core.checkout_idempotency_service import lookup_checkout_result
            token = args[0] if args else kwargs.get("token")
            return lambda: lookup_checkout_result(token, actor), False
        # Sensitive account methods get their authenticated actor even if their
        # caller tried to omit it. Target employee_id for reset is independent.
        if model_name == "AuthModel" and method_name in {"create_employee", "reset_password"}:
            from core.auth_service import create_employee, update_employee_password
            method = create_employee if method_name == "create_employee" else update_employee_password
        else:
            method = getattr(model, method_name)
        if not callable(method):
            if args or kwargs:
                raise ShopAPIError(400, "This shop setting does not take arguments.")
            return lambda: method, False
        try:
            bound = inspect.signature(method).bind(*args, **kwargs)
        except TypeError as exc:
            raise ShopAPIError(400, "The counter sent invalid operation details.") from exc
        # Account reset's employee_id is the target; every other actor field is
        # verified against the session and then authoritatively supplied.
        target_employee = model_name == "AuthModel" and method_name == "reset_password"
        for field in ("employee_id", "operator_id", "actor_id"):
            if field == "employee_id" and target_employee:
                continue
            if field in inspect.signature(method).parameters:
                supplied = bound.arguments.get(field, actor)
                if supplied is not None and int(supplied) != actor:
                    raise ShopAPIError(403, "This request belongs to another staff member.")
                bound.arguments[field] = actor
        if "terminal_id" in inspect.signature(method).parameters:
            bound.arguments["terminal_id"] = session["terminal_id"]
        if "operation_id" in inspect.signature(method).parameters and not bound.arguments.get("operation_id"):
            bound.arguments["operation_id"] = request_id
        if model_name == "CashSessionModel" and "session_id" in bound.arguments:
            from core.db_engine import get_db
            with get_db() as (_conn, cur):
                cur.execute("SELECT employee_id,terminal_id FROM Cash_Register_Session WHERE id=%s", (bound.arguments["session_id"],))
                owner = cur.fetchone()
            if not owner or int(owner[0]) != actor or str(owner[1]) != session['terminal_id']:
                raise ShopAPIError(403, "That cash shift belongs to another staff member.")
        if model_name == "CashSessionModel" and method_name == "recent_movements":
            # The historical facade returns all drawers; filter at the host.
            from core.db_engine import get_db
            limit = max(1, min(int(bound.arguments.get("limit", 50)), 500))
            def own_movements():
                with get_db() as (_conn, cur):
                    cur.execute("SELECT m.id,m.session_id,m.movement_type,m.amount,m.reason,m.created_at FROM Cash_Movement m JOIN Cash_Register_Session s ON s.id=m.session_id WHERE m.employee_id=%s AND s.terminal_id=%s ORDER BY m.id DESC LIMIT %s", (actor, session["terminal_id"], limit))
                    return cur.fetchall()
            return own_movements, False
        return lambda: method(*bound.args, **bound.kwargs), specification[1]

    def call(self, token: str, model: str, method: str, args=None, kwargs=None, request_id: str = ""):
        session = self.session(token)
        args, kwargs = args or [], kwargs or {}
        invocation, mutation = self._prepare(session, str(model), str(method), args, kwargs, request_id)
        if not mutation:
            return json_value(_invoke_remote(invocation))
        if not _SAFE_ID.fullmatch(str(request_id)):
            raise ShopAPIError(400, "A mutation must have a valid operation identity.")
        business = json.dumps({"model": model, "method": method, "args": args, "kwargs": kwargs}, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = _digest(business)
        from core.db_engine import get_db
        with self._mutation_lock:
            with get_db(immediate=True) as (_conn, cur):
                cur.execute("SELECT employee_id,terminal_id,fingerprint,response_json FROM Shop_Request WHERE request_id=%s", (request_id,))
                old = cur.fetchone()
                if old:
                    if int(old[0]) != session["employee_id"] or str(old[1]) != session["terminal_id"] or not hmac.compare_digest(str(old[2]), fingerprint):
                        raise ShopAPIError(409, "This operation identity was already used for different information.")
                    if old[3] is not None:
                        return json.loads(old[3])
                    if (model, method) not in REPLAY_SAFE:
                        raise ShopAPIError(409, "The earlier operation has an uncertain outcome. Check the shop history before creating a new operation.")
                else:
                    cur.execute("INSERT INTO Shop_Request(request_id,employee_id,terminal_id,fingerprint) VALUES(%s,%s,%s,%s)",
                                (request_id, session["employee_id"], session["terminal_id"], fingerprint))
            # Canonical service owns its commit; a POS receipt can only print
            # after that commit. The intent record prevents blind replay of a
            # non-POS mutation if the process stops before response persistence.
            result = json_value(_invoke_remote(invocation))
            if isinstance(result, dict) and result.get("outcome") == "unknown":
                return result
            response = json.dumps(result, allow_nan=False)
            with get_db(immediate=True) as (_conn, cur):
                cur.execute("UPDATE Shop_Request SET response_json=%s WHERE request_id=%s", (response, request_id))
            return result


def create_shop_server(address: tuple[str, int], certificate_path: str, key_path: str, *, service=None):
    service = service or ShopService()

    class Handler(BaseHTTPRequestHandler):
        server_version = "PharmaShop/1"
        sys_version = ""

        def log_message(self, format, *args):
            # HTTP headers and request bodies may contain credentials; do not
            # write them into diagnostics, stdout or inherited access logs.
            return

        def do_POST(self):
            self.connection.settimeout(20)
            try:
                import ipaddress
                peer = ipaddress.ip_address(self.client_address[0])
                if not (peer.is_private or peer.is_loopback):
                    raise ShopAPIError(403, "This service is available only on the private shop network.")
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 2 * 1024 * 1024:
                    raise ShopAPIError(413, "The counter request is too large or empty.")
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    raise ShopAPIError(415, "Use the shop application to connect.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ShopAPIError(400, "Invalid shop request.")
                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                if self.path == "/v1/status":
                    result = service.status()
                elif self.path == "/v1/login":
                    result = service.login(payload.get("username", ""), payload.get("password", ""), payload.get("terminal_id", ""))
                elif self.path == "/v1/logout":
                    service.session(token)
                    result = service.logout(token)
                elif self.path == "/v1/call":
                    result = service.call(token, payload.get("model", ""), payload.get("method", ""), payload.get("args"), payload.get("kwargs"), payload.get("request_id", ""))
                else:
                    raise ShopAPIError(404, "Unknown shop operation.")
                self._reply(200, {"result": result})
            except ShopAPIError as exc:
                self._reply(exc.status, {"error": exc.message})
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
                self._reply(400, {"error": "The counter sent invalid operation information."})
            except Exception:
                # No exception repr: database internals and local paths are not
                # useful to counter operators or unauthenticated callers.
                self._reply(503, {"error": "The shop could not confirm this operation. Keep the sale open and check the shop history before retrying."})
            finally:
                from core.db_engine import reset_thread_connections
                reset_thread_connections()

        def _reply(self, status, payload):
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                pass  # A response loss is handled by the durable request identity.

    server = ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate_path, key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def ensure_shop_certificate(directory: str | Path, names=()):
    """Generate one shop CA/server certificate; never replace an existing pin."""
    import ipaddress
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cert, key = directory / "shop-certificate.pem", directory / "shop-private-key.pem"
    if cert.exists() and key.exists():
        return cert, key
    if cert.exists() or key.exists():
        raise ValueError("The shop certificate is incomplete. Restore both certificate files from the shop backup.")
    requested = {"localhost", "127.0.0.1", socket.gethostname(), *map(str, names)}
    try:
        requested.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    alternatives = []
    for name in sorted(requested):
        try:
            alternatives.append("IP:" + str(ipaddress.ip_address(name)))
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", name):
                raise ValueError("Enter a valid main-computer hostname or LAN IP address.")
            alternatives.append("DNS:" + name)
    try:
        from datetime import datetime, timedelta, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        private = rsa.generate_private_key(public_exponent=65537,key_size=3072)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Pharma Khaato Shop')])
        now = datetime.now(timezone.utc)
        san = [x509.IPAddress(ipaddress.ip_address(value[3:])) if value.startswith('IP:') else x509.DNSName(value[4:]) for value in alternatives]
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(private.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san),critical=False)
            .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=True,
                data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
            .sign(private,hashes.SHA256()))
        import os
        fd = os.open(key,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            stream.flush()
            os.fsync(stream.fileno())
        cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key.chmod(0o600)
        cert.chmod(0o644)
    except Exception as exc:
        key.unlink(missing_ok=True)
        cert.unlink(missing_ok=True)
        raise ValueError("The shop connection could not be prepared. Check that this computer's setup is complete and its settings folder is writable.") from exc
    return cert, key
