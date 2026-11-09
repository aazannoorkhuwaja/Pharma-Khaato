"""Simulated hardware failure cases: keyboard-wedge scanner and receipt spooler.

These do NOT test real USB scanners, printer paper/feed, Bluetooth or driver
reliability. They run with an isolated pytest pharmacy and monkeypatched
printer boundary; real shop trials remain required.
"""
import uuid

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from tests.test_recording_review import owner, settle  # noqa: F401


def test_keyboard_wedge_scans_are_queued_without_losing_items(owner, qtbot):
    from ui.screens.pos_screen import POSScreen

    screen = POSScreen(show_message_box=False)
    qtbot.addWidget(screen)
    screen.resize(1150, 700)
    screen.show()
    settle(qtbot, screen)
    screen.txt_search.setFocus()
    # Two fast scanner wedge sequences, each terminated by Enter, must never
    # depend on 150ms debounce/search timing for product selection.
    for _ in range(2):
        QTest.keyClicks(screen.txt_search, "BC1")
        QTest.keyClick(screen.txt_search, Qt.Key.Key_Return)
    qtbot.waitUntil(
        lambda: sum(item.get("qty", 0) for item in owner.active_cart) == 2,
        timeout=10000,
    )
    assert len(owner.active_cart) == 1
    assert owner.active_cart[0]["qty"] == 2
    assert not screen._submitted_terms and not screen._product_submit_active
    screen.close()
    settle(qtbot, screen)


def test_disconnected_receipt_spooler_never_duplicates_a_sale(
    cash_shift, seeded_shop, admin_emp_id, monkeypatch
):
    from core import receipt_service
    from core.pos_service import CheckoutRequest, POSTransactionEngine

    request = CheckoutRequest(
        "WALKIN", admin_emp_id,
        [{"prod_id": 1, "name": "TestMed", "price": 15, "qty": 2}],
        payment_method="Cash", checkout_token=uuid.uuid4().hex,
    )
    sale = POSTransactionEngine.process_checkout(request)
    assert sale.success, sale.message
    purchase_id = sale.purchase_id
    saved_receipt = receipt_service.receipt_for_sale(purchase_id)["receipt_text"]

    attempts = []
    monkeypatch.setattr(
        receipt_service, "print_receipt_spooler",
        lambda *args, **kwargs: attempts.append((args, kwargs)) or False,
    )
    ok, message = receipt_service.reprint_sale_receipt(purchase_id)
    assert not ok
    assert "saved" in message.lower()
    assert len(attempts) == 1
    assert saved_receipt in attempts[0][0][0]

    # The failed paper/spooler operation cannot alter accounting or stock.
    cur = seeded_shop.get_conn().cursor()
    assert cur.execute("SELECT COUNT(*) FROM Purchase").fetchone()[0] == 1
    assert cur.execute("SELECT quantity FROM Batch WHERE id=1").fetchone()[0] == 98

    monkeypatch.setattr(receipt_service, "print_receipt_spooler", lambda *a, **k: True)
    ok, _ = receipt_service.reprint_sale_receipt(purchase_id)
    assert ok
    assert cur.execute("SELECT COUNT(*) FROM Purchase").fetchone()[0] == 1
    assert cur.execute("SELECT quantity FROM Batch WHERE id=1").fetchone()[0] == 98


def test_receipt_test_for_58_and_80mm_never_creates_sales(
    seeded_shop, monkeypatch
):
    from core import receipt_service

    samples = []
    monkeypatch.setattr(
        receipt_service, "print_receipt_spooler",
        lambda sample, printer_name=None: samples.append(sample) or True,
    )
    for template in ("compact_58", "professional_80"):
        assert receipt_service.print_test_receipt("Simulated-Printer", template)
    assert len(samples) == 2
    assert all("TEST" in sample for sample in samples)
    cur = seeded_shop.get_conn().cursor()
    assert cur.execute("SELECT COUNT(*) FROM Purchase").fetchone()[0] == 0
