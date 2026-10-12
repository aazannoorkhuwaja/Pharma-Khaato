"""Architecture guardrails for the MVC boundary."""

import ast
from pathlib import Path

from controllers.auth_controller import AuthController
from controllers.customer_controller import CustomerController
from controllers.inventory_controller import InventoryController


ROOT = Path(__file__).resolve().parents[1]


def test_views_do_not_import_core_services_directly():
    violations = []
    allowed_infrastructure = {"core.logger"}
    for path in (ROOT / "ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("core"):
                if node.module not in allowed_infrastructure:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("core") and alias.name not in allowed_infrastructure:
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{alias.name}")
    assert violations == [], f"Views bypass MVC controllers: {violations}"


class FakeAuthModel:
    def login(self, username, password):
        return username, password


class FakeCustomerModel:
    def search(self, text):
        return [text]


class FakeInventoryModel:
    def search_products(self, term):
        return [term]


def test_auth_controller_normalizes_username():
    assert AuthController(FakeAuthModel()).login("  cashier  ", "secret") == ("cashier", "secret")


def test_customer_controller_normalizes_search():
    assert CustomerController(FakeCustomerModel()).search("  ali  ") == ["ali"]


def test_inventory_controller_normalizes_search():
    assert InventoryController(FakeInventoryModel()).search_products("  panadol  ") == ["panadol"]
