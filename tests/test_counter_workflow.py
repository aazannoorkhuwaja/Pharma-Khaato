"""Operator-level Qt regressions for scan, identity, tender and recovery safety."""
import copy
from pathlib import Path

import pytest


class ImmediateTasks:
    def __init__(self, *_args):
        pass

    def invalidate(self, _key):
        pass

    def run(self, fn, complete, failed=None):
        try:
            result = fn()
        except Exception as error:
            if failed is None:
                raise
            failed(str(error))
        else:
            complete(result)

    def run_latest(self, _key, fn, complete, failed=None):
        self.run(fn, complete, failed)


class DeferredTasks(ImmediateTasks):
    def __init__(self):
        self.pending = []

    def run(self, fn, complete, failed=None):
        self.pending.append((fn, complete, failed))

    def finish(self, result=None, error=None, execute=False):
        fn, complete, failed = self.pending.pop(0)
        if error:
            failed(error)
        else:
            complete(fn() if execute else result)


@pytest.fixture
def counter(fresh_db, monkeypatch):
    from PySide6.QtWidgets import QApplication
    from ui.app.state.session_state import SessionState
    from ui.screens import pos_screen
    from core.pos_service import CheckoutRequest, CheckoutResult

    app = QApplication.instance() or QApplication([])
    SessionState._instance = None
    state = SessionState.get_instance()
    state.set_user({"id": 1, "username": "cashier"})

    class Controller:
        discount_threshold_pct = 100
        submitted = []
        saved_result = None
        units = [{"code": "base", "label": "tablet", "multiplier": 1, "price": 10},
                 {"code": "strip", "label": "strip (10 tablets)", "multiplier": 10, "price": 100}]
        a = (1, "Medicine A", 10, 1, 100, "2099-01-01")
        b = (2, "Medicine B", 20, 2, 100, "2099-01-01")

        def active_session(self, _employee):
            return True

        def tax_rate(self):
            return 0

        def product_by_barcode(self, term):
            return self.a if term == "12345678" else (self.b if term == "1234567890123" else None)

        def search_products(self, term):
            return [self.a] if term == "A" else [self.b]

        def search_customers(self, _term):
            return [("CUST_one", "Ali", "Ahmed", "03001111111", "North"),
                    ("CUST_two", "Ali", "Raza", "03002222222", "South")]

        def customer_total_debt(self, _customer):
            return 0

        def checkout_request(self, **kwargs):
            import uuid
            kwargs.setdefault("checkout_token", uuid.uuid4().hex)
            return CheckoutRequest(**copy.deepcopy(kwargs))

        def process_checkout(self, request):
            self.submitted.append(copy.deepcopy(request))
            return CheckoutResult(True, "Saved", purchase_id=10, total=request.total,
                                  payment_method=request.payment_method, outcome="completed")

        def lookup_checkout_result(self, _token, _employee):
            return self.saved_result

        def held_sales(self, _employee=None):
            return [(1,)]

        def recall_sale(self, _hold, _employee=None):
            return True, {"cart": [{"prod_id": 2, "name": "Held B", "price": 20,
                "batch_id": 2, "qty": 2, "subtotal": 40}], "customer_id": "CUST_two",
                "draft": {"customer_name": "Ali Raza", "discount": 5,
                          "payment_method": "Khatoo Credit", "cash_received": None}}

        def reprint_receipt(self, _purchase_id):
            return True, "Receipt sent to printer"

        def receipt_for_sale(self, purchase_id):
            return {"purchase_id": purchase_id, "print_status": "SAVED"}

    controller = Controller()
    monkeypatch.setattr(pos_screen, "_POS_CONTROLLER", controller)
    monkeypatch.setattr(pos_screen, "AsyncTaskRunner", ImmediateTasks)
    screen = pos_screen.POSScreen(show_message_box=False)
    screen.resize(1150, 760)
    screen.show()
    app.processEvents()
    yield screen, controller, app
    screen.close()
    screen.deleteLater()
    app.processEvents()
    SessionState._instance = None


def test_scan_commits_only_complete_barcode(counter):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    screen, _controller, _app = counter
    QTest.keyClicks(screen.txt_search, "1234567890123")
    assert not screen.session.active_cart
    QTest.keyClick(screen.txt_search, Qt.Key_Return)
    assert [item["name"] for item in screen.session.active_cart] == ["Medicine B"]
    assert screen.txt_search.text() == ""


def test_rapid_scans_survive_slow_lookup(counter):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    screen, _controller, _app = counter
    tasks = DeferredTasks()
    screen._tasks = tasks
    for barcode in ("12345678", "1234567890123"):
        QTest.keyClicks(screen.txt_search, barcode)
        QTest.keyClick(screen.txt_search, Qt.Key_Return)
    assert screen.txt_search.text() == ""
    tasks.finish(execute=True)
    tasks.finish(execute=True)
    assert [item["name"] for item in screen.session.active_cart] == ["Medicine A", "Medicine B"]


def test_enter_cannot_add_previous_search_result(counter):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    screen, _controller, app = counter
    screen.txt_search.setText("A")
    screen.perform_live_search()
    app.processEvents()
    assert screen.search_table.isVisible()
    screen.txt_search.setText("B")
    QTest.keyClick(screen.txt_search, Qt.Key_Return)
    assert [item["name"] for item in screen.session.active_cart] == ["Medicine B"]


def test_customer_requires_selection_and_any_edit_invalidates_identity(counter):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    screen, _controller, app = counter
    screen.txt_customer.setText("Ali")
    screen.perform_customer_search()
    screen.txt_customer.clearFocus()
    app.processEvents()
    assert screen.selected_customer_cnic is None
    assert not screen.is_customer_verified
    screen.cust_table.setCurrentCell(1, 0)
    QTest.keyClick(screen.cust_table, Qt.Key_Return)
    assert screen.selected_customer_cnic == "CUST_two"
    screen.txt_customer.setText("Different Ali")
    assert screen.selected_customer_cnic is None
    assert not screen.is_customer_verified


def test_new_sale_resets_tender_discount_and_exact_cash(counter):
    screen, _controller, _app = counter
    screen.cmb_pay_method.setCurrentIndex(screen.cmb_pay_method.findData("Easypaisa"))
    screen.spn_discount.setValue(5)
    screen.chk_exact_cash.setChecked(False)
    screen.on_clear_cart()
    assert screen.cmb_pay_method.currentData() == "Cash"
    assert screen.spn_discount.value() == 0
    assert screen.chk_exact_cash.isChecked()


def test_short_cash_does_not_submit_and_exact_cash_does(counter):
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a)
    screen.chk_exact_cash.setChecked(False)
    screen.spn_cash_received.setValue(1)
    screen.on_checkout()
    assert controller.submitted == []
    assert "short" in screen.lbl_checkout_state.text().lower()
    screen.chk_exact_cash.setChecked(True)
    screen.on_checkout()
    assert len(controller.submitted) == 1
    assert controller.submitted[0].cash_received is None
    assert not screen.session.pending_checkout
    assert screen._last_sale_id == 10


def test_checkout_is_immutable_locked_and_unknown_outcome_recovered(counter):
    from core.pos_service import CheckoutResult
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a)
    tasks = DeferredTasks()
    screen._tasks = tasks
    screen.on_checkout()
    pending = copy.deepcopy(screen.session.pending_checkout)
    assert pending and not screen.txt_search.isEnabled()
    assert Path(screen.session._pending_path(1)).exists()
    screen.session.active_cart[0]["qty"] = 99  # hostile external edit cannot alter submitted snapshot
    tasks.finish(error="network result lost")
    assert screen.session.pending_checkout["request"]["cart"][0]["qty"] == 1
    assert screen.btn_checkout.text() == "Check This Bill"
    controller.saved_result = CheckoutResult(True, "Saved", purchase_id=10, total=10,
                                             payment_method="Cash", outcome="completed")
    screen.on_checkout()
    tasks.finish(execute=True)
    assert not screen.session.pending_checkout
    assert screen._last_sale_id == 10
    assert not Path(screen.session._pending_path(1)).exists()


def test_pending_checkout_survives_new_session(counter):
    from ui.app.state.session_state import SessionState
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a)
    screen._tasks = DeferredTasks()
    screen.on_checkout()
    token = screen.session.pending_checkout["request"]["checkout_token"]
    replacement = SessionState()
    replacement.set_user({"id": 1})
    assert replacement.pending_checkout["request"]["checkout_token"] == token
    assert replacement.pending_checkout["draft"]["cart"][0]["name"] == "Medicine A"


def test_resume_does_not_destroy_live_cart_and_restores_complete_held_draft(counter, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a)
    monkeypatch.setattr(QMessageBox, "question", lambda *_args, **_kwargs: QMessageBox.StandardButton.Cancel)
    screen.on_recall_sale()
    assert screen.session.active_cart[0]["name"] == "Medicine A"
    screen.on_clear_cart()
    screen.on_recall_sale()
    assert screen.session.active_cart[0]["name"] == "Held B"
    assert screen.selected_customer_cnic == "CUST_two"
    assert screen.txt_customer.text() == "Ali Raza"
    assert screen.spn_discount.value() == 5
    assert screen.cmb_pay_method.currentData() == "Khatoo Credit"
    assert screen.session.held_sale_id == 1


def test_cart_unit_choice_changes_price_and_preserves_explicit_multiplier(counter):
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a + ({"unit_code": "base", "unit_label": "tablet",
        "unit_multiplier": 1, "base_stock": 100, "units": controller.units},))
    combo = screen.cart_table.cellWidget(0, 6)
    combo.setCurrentIndex(1)
    item = screen.session.active_cart[0]
    assert (item["qty"], item["unit_multiplier"], item["price"], item["subtotal"]) == (1, 10, 100, 100)


def test_return_lookup_invalidates_previous_sale_and_recovers_button(fresh_db, monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from ui.app.state.session_state import SessionState
    from ui.screens import returns_screen
    app = QApplication.instance() or QApplication([])
    SessionState._instance = None
    SessionState.get_instance().set_user({"id": 1})
    screen = returns_screen.ReturnsScreen(show_message_box=False)
    tasks = DeferredTasks()
    screen._tasks = tasks
    screen.current_sale = {"purchase_id": 1}
    screen.btn_process.setEnabled(True)
    screen.txt_sale_id.setText("2")
    screen.find_sale()
    assert screen.current_sale is None
    assert not screen.btn_process.isEnabled()
    screen.txt_sale_id.selectAll()
    QTest.keyClicks(screen.txt_sale_id, "3")
    tasks.finish(None)
    assert screen.btn_find.isEnabled()
    assert screen.btn_find.text() == "Find Sale"
    assert screen.current_sale is None
    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_checkout_runs_off_ui_thread_and_keeps_event_loop_alive(counter, qtbot):
    import threading
    from PySide6.QtCore import QTimer
    from ui.app.async_tasks import AsyncTaskRunner
    screen, controller, _app = counter
    screen._add_result_tuple_to_cart(controller.a)
    started, release, ui_pulse = threading.Event(), threading.Event(), threading.Event()
    original = controller.process_checkout
    worker_ids = []
    def checkout(request):
        worker_ids.append(threading.get_ident())
        started.set()
        release.wait(3)
        return original(request)
    controller.process_checkout = checkout
    screen._tasks = AsyncTaskRunner(screen)
    try:
        screen.on_checkout()
        qtbot.waitUntil(started.is_set, timeout=2000)
        QTimer.singleShot(0, ui_pulse.set)
        qtbot.waitUntil(ui_pulse.is_set, timeout=1000)
        assert worker_ids[0] != threading.get_ident()
        assert screen.session.pending_checkout
        assert not screen.btn_checkout.isEnabled()
    finally:
        release.set()
    qtbot.waitUntil(lambda: screen.session.pending_checkout is None, timeout=3000)


def test_pending_return_recovers_committed_result_without_another_refund(fresh_db, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from ui.app.state.session_state import SessionState
    from ui.screens import returns_screen
    from controllers.pos_controller import POSController
    app = QApplication.instance() or QApplication([])
    SessionState._instance = None
    SessionState.get_instance().set_user({"id": 1})
    class Returns:
        calls = 0
        def pending_path(self, employee_id):
            return Path(POSController.pending_checkout_path(employee_id)).with_name("return-test.json")
        def operation_status(self, operation_id, employee_id):
            assert (operation_id, employee_id) == ("saved-return-token", 1)
            return {"return_id": 9, "refund_amount": 10, "refund_tenders": [("Cash", 10)]}
        def sale(self, _purchase):
            return None
        def process(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("Recovery must never submit another refund")
    controller = Returns()
    monkeypatch.setattr(returns_screen, "_RETURN_CONTROLLER", controller)
    monkeypatch.setattr(returns_screen, "AsyncTaskRunner", ImmediateTasks)
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: None)
    original = returns_screen.ReturnsScreen(show_message_box=False)
    sale = {"purchase_id": 2, "sale_date": "2026-01-01", "sale_time": "10:00", "customer_name": "Walk-in",
            "payment_method": "Cash", "gross_total": 10, "already_refunded": 0,
            "lines": [{"batch_id": 1, "product_name": "Medicine", "sold_qty": 1,
                       "already_returned": 0, "remaining_returnable": 1, "unit_price": 10,
                       "line_base": 10, "expiry_date": "2099-01-01"}]}
    original._save_pending_return({"operation_id": "saved-return-token", "employee_id": 1,
        "purchase_id": 2, "items": [{"batch_id": 1, "qty": 1}], "reason": "Unopened",
        "condition": "QUARANTINE", "sale": sale})
    recovered = returns_screen.ReturnsScreen(show_message_box=False)
    assert recovered.btn_process.text() == "Check Return Status"
    assert not recovered.txt_sale_id.isEnabled()
    recovered.process_return()
    assert recovered._pending_return is None
    assert controller.calls == 0
    assert not controller.pending_path(1).exists()
    for widget in (original, recovered):
        widget.close()
        widget.deleteLater()
    app.processEvents()
