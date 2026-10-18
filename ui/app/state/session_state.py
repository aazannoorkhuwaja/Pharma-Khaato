"""
Pharma-Khaato Native State Manager
Maintains in-memory session state, current user context, cash register session,
and the active POS cart/request identity.
"""

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List


class SessionState:
    _instance = None

    def __init__(self):
        self.current_user: Optional[Dict[str, Any]] = None
        self.active_cash_session: Optional[Dict[str, Any]] = None
        self.active_cart: List[Dict[str, Any]] = []
        self.selected_customer: Optional[Dict[str, Any]] = None
        self.discount_amount: float = 0.0
        self.payment_method: str = "Cash"
        # Created when checkout is first attempted and reused across safe retries.
        self.checkout_token: Optional[str] = None
        self.pending_checkout: Optional[Dict[str, Any]] = None
        self.held_sale_id: Optional[int] = None

    @classmethod
    def get_instance(cls) -> "SessionState":
        if cls._instance is None:
            cls._instance = SessionState()
        return cls._instance

    def set_user(self, user_dict: Dict[str, Any]):
        self.current_user = user_dict
        self.pending_checkout = None
        self.load_pending_checkout()

    def clear_user(self):
        self.current_user = None
        self.active_cash_session = None
        self.clear_cart()
        self.pending_checkout = None

    def set_cash_session(self, session_dict: Optional[Dict[str, Any]]):
        self.active_cash_session = session_dict

    def add_to_cart(self, product_item: Dict[str, Any], qty: int = 1):
        p_id = product_item.get("id") or product_item.get("prod_id")
        for item in self.active_cart:
            if (
                (item.get("id") == p_id or item.get("prod_id") == p_id)
                and item.get("unit_code", "base") == product_item.get("unit_code", "base")
            ):
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                return

        cart_entry = {
            "id": p_id,
            "prod_id": p_id,
            "name": product_item.get("name"),
            "price": float(product_item.get("price", 0.0)),
            "batch_id": product_item.get("batch_id"),
            "stock": product_item.get("stock", 0),
            "qty": qty,
            "subtotal": qty * float(product_item.get("price", 0.0)),
            "barcode": product_item.get("barcode", ""),
            "unit_code": product_item.get("unit_code", "base"),
            "unit_label": product_item.get("unit_label", "unit"),
            "unit_multiplier": int(product_item.get("unit_multiplier", 1)),
            "units": copy.deepcopy(product_item.get("units", [])),
            "base_stock": product_item.get("base_stock", product_item.get("stock", 0)),
        }
        self.active_cart.append(cart_entry)

    def update_cart_qty(self, index: int, qty: int):
        if 0 <= index < len(self.active_cart):
            if qty <= 0:
                self.active_cart.pop(index)
            else:
                self.active_cart[index]["qty"] = qty
                self.active_cart[index]["subtotal"] = qty * self.active_cart[index]["price"]

    def remove_from_cart(self, index: int):
        if 0 <= index < len(self.active_cart):
            self.active_cart.pop(index)

    def clear_cart(self):
        self.active_cart = []
        self.selected_customer = None
        self.discount_amount = 0.0
        self.payment_method = "Cash"
        self.checkout_token = None
        self.held_sale_id = None

    @staticmethod
    def _pending_path(employee_id):
        from controllers.pos_controller import POSController
        return Path(POSController.pending_checkout_path(employee_id))

    def save_pending_checkout(self, request, draft):
        """Durably save the exact request before submitting any financial work."""
        from dataclasses import asdict, is_dataclass
        payload = asdict(request) if is_dataclass(request) else copy.deepcopy(vars(request))
        employee_id = int(payload["employee_id"])
        record = {"request": payload, "draft": copy.deepcopy(draft)}
        path = self._pending_path(employee_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".pending-checkout-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.pending_checkout = record
        self.checkout_token = payload["checkout_token"]

    def load_pending_checkout(self):
        if not self.current_user:
            return None
        path = self._pending_path(self.current_user["id"])
        if not path.exists():
            return None
        # A damaged recovery record must stay visible; never silently start a
        # replacement sale after an unknown checkout outcome.
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            request = record["request"]
            if int(request["employee_id"]) != int(self.current_user["id"]) or not request["checkout_token"]:
                raise ValueError("Invalid checkout recovery identity")
            self.pending_checkout = record
            self.checkout_token = request["checkout_token"]
        except (OSError, ValueError, KeyError, TypeError):
            self.pending_checkout = {"recovery_error": True}
        return self.pending_checkout

    def clear_pending_checkout(self, employee_id, token):
        path = self._pending_path(employee_id)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            record = None
        if record is not None:
            if record.get("request", {}).get("checkout_token") != token:
                raise ValueError("A different checkout is awaiting recovery")
            path.unlink()
        if (self.pending_checkout or {}).get("request", {}).get("checkout_token") == token:
            self.pending_checkout = None
            self.checkout_token = None

    def get_cart_subtotal(self) -> float:
        return sum(item["subtotal"] for item in self.active_cart)

    def get_cart_total(self) -> float:
        subtotal = self.get_cart_subtotal()
        return max(0.0, subtotal - self.discount_amount)
