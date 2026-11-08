"""Regression guards for the preferred Pharma-Khaato cashier workspace.

These source-level checks remain runnable without a Qt runtime. Native GUI
interaction and device tests are separately required before a shop release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = (ROOT / "ui/screens/pos_screen.py").read_text(encoding="utf-8")
STATE = (ROOT / "ui/app/state/session_state.py").read_text(encoding="utf-8")


def _between(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


def test_cash_entry_and_discount_do_not_rebuild_the_cart():
    assert "self.spn_discount.valueChanged.connect(self.refresh_payment_totals)" in POS
    assert "self.spn_cash_received.valueChanged.connect(self.refresh_payment_totals)" in POS
    totals = _between(POS, "    def refresh_payment_totals(self):", "    def _change_cart_unit(")
    assert "self.cart_table.setRowCount" not in totals
    assert "self.cart_table.setCellWidget" not in totals
    assert "self.lbl_change.setText" in totals
    assert "self.lbl_total.setText" in totals


def test_cart_shows_expiry_preview_without_exposing_internal_batch_id():
    assert '"expiry_date": str(batch_expiry or "")' in POS
    assert '"Product", "Expiry", "Price", "Qty", "Amount", "In Stock", "Unit"' in POS
    assert 'QTableWidgetItem(str(item.get("expiry_date") or "Review"))' in POS
    assert "selected batch expiry as a preview" in POS.lower()
    assert '"batch_id": batch_id' in POS  # authoritative backend still receives it
    assert '"expiry_date": str(product_item.get("expiry_date") or "")' in STATE
    assert 'item["expiry_date"] = "Verify at checkout"' in STATE


def test_payment_remains_backend_validated_and_recoverable():
    assert "self.session.save_pending_checkout(request, draft)" in POS
    assert "self.session.pending_checkout" in POS
    assert "self._tax_ready" in POS
    assert "self._cash_shift_open" in POS
    assert 'QShortcut(QKeySequence("F12")' in POS
    assert "os.fsync(stream.fileno())" in STATE
