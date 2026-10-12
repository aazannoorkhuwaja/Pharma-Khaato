"""
Pharma-Khaato Native State Manager
Maintains in-memory session state, current user context, cash register session, and active cart.
"""

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

    @classmethod
    def get_instance(cls) -> "SessionState":
        if cls._instance is None:
            cls._instance = SessionState()
        return cls._instance

    def set_user(self, user_dict: Dict[str, Any]):
        self.current_user = user_dict

    def clear_user(self):
        self.current_user = None
        self.active_cash_session = None
        self.clear_cart()

    def set_cash_session(self, session_dict: Optional[Dict[str, Any]]):
        self.active_cash_session = session_dict

    def add_to_cart(self, product_item: Dict[str, Any], qty: int = 1):
        p_id = product_item.get("id") or product_item.get("prod_id")
        for item in self.active_cart:
            if (item.get("id") == p_id or item.get("prod_id") == p_id) and item.get("batch_id") == product_item.get("batch_id"):
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                return
        
        # New item entry
        cart_entry = {
            "id": p_id,
            "prod_id": p_id,
            "name": product_item.get("name"),
            "price": float(product_item.get("price", 0.0)),
            "batch_id": product_item.get("batch_id"),
            "stock": product_item.get("stock", 0),
            "qty": qty,
            "subtotal": qty * float(product_item.get("price", 0.0)),
            "barcode": product_item.get("barcode", "")
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

    def get_cart_subtotal(self) -> float:
        return sum(item["subtotal"] for item in self.active_cart)

    def get_cart_total(self) -> float:
        subtotal = self.get_cart_subtotal()
        return max(0.0, subtotal - self.discount_amount)
