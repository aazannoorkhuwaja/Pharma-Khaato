"""Fast, authoritative sales return and refund screen."""

import copy
import json
import os
import tempfile
import uuid
from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QComboBox,
    QMessageBox, QFormLayout,
)

from controllers.return_controller import ReturnController
from ui.app.async_tasks import AsyncTaskRunner
from ui.app.state.session_state import SessionState
from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.table_polish import polish_table
from ui.widgets.toast import ToastType, show_toast

_RETURN_CONTROLLER = ReturnController()


class ReturnsScreen(QWidget):
    """Exact sale lookup with non-blocking database and refund work."""

    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self.current_sale = None
        self._qty_widgets: dict[int, QSpinBox] = {}
        self._tasks = AsyncTaskRunner(self)
        self._processing = False
        self._pending_return = None
        self._pending_retry_ready = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header = ScreenHeader(
            "Returns & Refunds",
            "Find the original sale, select returned items, and refund the correct payment method."
        )
        layout.addWidget(header)

        lookup_card = Card()
        lookup_layout = lookup_card.layout()
        lookup_layout.setSpacing(10)
        lookup_row = QHBoxLayout()
        self.txt_sale_id = QLineEdit()
        self.txt_sale_id.setPlaceholderText("Enter Sale #, e.g. 1842")
        self.txt_sale_id.setAccessibleName("Sale number to return")
        self.txt_sale_id.returnPressed.connect(self.find_sale)
        self.txt_sale_id.textEdited.connect(self._lookup_text_edited)
        self.btn_find = QPushButton("Find Sale")
        self.btn_find.setObjectName("primaryButton")
        self.btn_find.clicked.connect(self.find_sale)
        lookup_row.addWidget(self.txt_sale_id, 1)
        lookup_row.addWidget(self.btn_find)
        lookup_layout.addLayout(lookup_row)

        self.lbl_sale_summary = QLabel("Enter a sale number to begin.")
        self.lbl_sale_summary.setWordWrap(True)
        self.lbl_sale_summary.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        lookup_layout.addWidget(self.lbl_sale_summary)
        layout.addWidget(lookup_card)

        items_card = Card()
        items_layout = items_card.layout()
        title = QLabel("Return Items")
        title.setObjectName("h2")
        items_layout.addWidget(title)

        self.tbl_items = QTableWidget(0, 6)
        self.tbl_items.setHorizontalHeaderLabels(
            ["Product", "Sold", "Already Returned", "Available", "Return Qty", "Expiry"]
        )
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 6):
            self.tbl_items.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        polish_table(self.tbl_items, min_row_height=42)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setEditTriggers(QTableWidget.NoEditTriggers)
        items_layout.addWidget(self.tbl_items, 1)
        layout.addWidget(items_card, 1)

        action_card = Card()
        action_layout = action_card.layout()
        form = QFormLayout()
        form.setSpacing(10)

        self.cmb_condition = QComboBox()
        self.cmb_condition.addItem("Unopened & sellable", "SELLABLE")
        self.cmb_condition.addItem("Opened / damaged", "DAMAGED")
        self.cmb_condition.addItem("Quarantine for inspection", "QUARANTINE")
        self.cmb_condition.setCurrentIndex(2)
        self.cmb_condition.setAccessibleName("Returned stock condition")
        form.addRow("Returned stock:", self.cmb_condition)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("e.g. Wrong medicine, customer changed mind, damaged pack")
        self.txt_reason.setMaxLength(250)
        self.txt_reason.setAccessibleName("Reason for return")
        form.addRow("Reason:", self.txt_reason)
        action_layout.addLayout(form)

        self.lbl_refund_help = QLabel(
            "Refund value is calculated from the original recorded sale, including its discount and tax. "
            "Cash refunds require an open cash shift; card and wallet refunds never change drawer cash."
        )
        self.lbl_refund_help.setWordWrap(True)
        self.lbl_refund_help.setObjectName("caption")
        action_layout.addWidget(self.lbl_refund_help)

        buttons = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_sale)
        self.btn_process = QPushButton("Process Return")
        self.btn_process.setObjectName("dangerButton")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.process_return)
        buttons.addStretch()
        buttons.addWidget(self.btn_clear)
        buttons.addWidget(self.btn_process)
        action_layout.addLayout(buttons)
        layout.addWidget(action_card)
        self._load_pending_return()

    @staticmethod
    def _employee_id():
        user = SessionState.get_instance().current_user or {}
        try:
            return int(user.get("id"))
        except (TypeError, ValueError):
            return None

    def clear_sale(self):
        if self._processing or self._pending_return:
            return
        self._tasks.invalidate("return-lookup")
        self.current_sale = None
        self._qty_widgets.clear()
        self.tbl_items.setRowCount(0)
        self.lbl_sale_summary.setText("Enter a sale number to begin.")
        self.btn_process.setEnabled(False)
        self.txt_reason.clear()
        self.cmb_condition.setCurrentIndex(2)
        self.txt_sale_id.selectAll()
        self.txt_sale_id.setFocus()

    def _lookup_text_edited(self, _text):
        if self._pending_return or self._processing:
            return
        self._tasks.invalidate("return-lookup")
        self.current_sale = None
        self._qty_widgets.clear()
        self.tbl_items.setRowCount(0)
        self.btn_process.setEnabled(False)
        self.btn_find.setEnabled(True)
        self.btn_find.setText("Find Sale")
        self.lbl_sale_summary.setText("Press Find Sale to load this receipt.")

    def find_sale(self):
        if self._processing or self._pending_return:
            return
        raw = self.txt_sale_id.text().strip().replace("Sale", "").replace("#", "").strip()
        if not raw.isdigit():
            show_toast(self, "Enter a valid sale number.", ToastType.WARNING)
            return

        self.btn_find.setEnabled(False)
        self.current_sale = None
        self._qty_widgets.clear()
        self.tbl_items.setRowCount(0)
        self.btn_process.setEnabled(False)
        self.btn_find.setText("Finding…")
        self.lbl_sale_summary.setText(f"Finding Sale #{raw}…")

        def complete(sale):
            self.btn_find.setEnabled(True)
            self.btn_find.setText("Find Sale")
            if self.txt_sale_id.text().strip().replace("Sale", "").replace("#", "").strip() != raw:
                return
            self._apply_sale_lookup(raw, sale)

        def failed(_details):
            self.btn_find.setEnabled(True)
            self.btn_find.setText("Find Sale")
            self.lbl_sale_summary.setText("Could not load that sale. Try again.")

        self._tasks.run_latest(
            "return-lookup",
            lambda: _RETURN_CONTROLLER.sale(raw),
            complete,
            failed,
        )

    def _apply_sale_lookup(self, raw, sale):
        if not sale:
            self.current_sale = None
            self._qty_widgets.clear()
            self.tbl_items.setRowCount(0)
            self.btn_process.setEnabled(False)
            self.lbl_sale_summary.setText(f"Sale #{raw} was not found.")
            show_toast(self, f"Sale #{raw} was not found.", ToastType.WARNING)
            return

        self.current_sale = sale
        self.lbl_sale_summary.setText(
            f"Sale #{sale['purchase_id']} • {sale['sale_date']} {sale['sale_time']}\n"
            f"Customer: {sale['customer_name']} • Payment: {sale['payment_method']} • "
            f"Original total: Rs. {sale['gross_total']:.2f} • "
            f"Already refunded: Rs. {sale['already_refunded']:.2f}"
        )
        self.populate_items(sale["lines"])
        self.btn_process.setEnabled(any(line["remaining_returnable"] > 0 for line in sale["lines"]))

    def populate_items(self, lines):
        self._qty_widgets.clear()
        self.tbl_items.setUpdatesEnabled(False)
        try:
            self.tbl_items.setRowCount(len(lines))
            for row, line in enumerate(lines):
                self.tbl_items.setItem(row, 0, QTableWidgetItem(line["product_name"]))
                self.tbl_items.setItem(row, 1, QTableWidgetItem(str(line["sold_qty"])))
                self.tbl_items.setItem(row, 2, QTableWidgetItem(str(line["already_returned"])))
                self.tbl_items.setItem(row, 3, QTableWidgetItem(str(line["remaining_returnable"])))
                self.tbl_items.setItem(row, 5, QTableWidgetItem(str(line["expiry_date"])))

                # A sale contains a small number of lines, so an inline quantity
                # control is appropriate here and does not create the hundreds
                # of QWidget instances that hurt ledger/catalog performance.
                qty = QSpinBox()
                qty.setRange(0, int(line["remaining_returnable"]))
                qty.setValue(0)
                qty.setAccessibleName(f"Return quantity for {line['product_name']}")
                qty.setEnabled(line["remaining_returnable"] > 0)
                self.tbl_items.setCellWidget(row, 4, qty)
                self._qty_widgets[int(line["batch_id"])] = qty
        finally:
            self.tbl_items.setUpdatesEnabled(True)

    def process_return(self):
        if self._pending_return and not self._processing:
            if self._pending_retry_ready:
                self._submit_saved_return()
            else:
                self._check_saved_return()
            return
        if not self.current_sale or self._processing:
            return
        employee_id = self._employee_id()
        if employee_id is None:
            QMessageBox.critical(self, "Sign In Required", "Sign in again before processing a return.")
            return

        items = [
            {"batch_id": batch_id, "qty": widget.value()}
            for batch_id, widget in self._qty_widgets.items()
            if widget.value() > 0
        ]
        if not items:
            show_toast(self, "Choose a return quantity for at least one item.", ToastType.WARNING)
            return
        reason = self.txt_reason.text().strip()
        if not reason:
            show_toast(self, "Enter a short reason for this return.", ToastType.WARNING)
            self.txt_reason.setFocus()
            return

        selected = {item["batch_id"]: item["qty"] for item in items}
        base = sum(Decimal(str(line["line_base"])) for line in self.current_sale["lines"])
        selected_base = sum(Decimal(str(line["unit_price"])) * selected.get(line["batch_id"], 0)
                            for line in self.current_sale["lines"])
        remaining = sum(line["remaining_returnable"] - selected.get(line["batch_id"], 0)
                        for line in self.current_sale["lines"])
        refundable = Decimal(str(self.current_sale["gross_total"])) - Decimal(str(self.current_sale["already_refunded"]))
        preview = refundable if remaining == 0 else min(refundable,
            (Decimal(str(self.current_sale["gross_total"])) * selected_base / base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        reply = QMessageBox.question(
            self,
            "Confirm Return",
            f"Return items from Sale #{self.current_sale['purchase_id']}?\n"
            f"Refund value: Rs. {preview:,.2f}\nOriginal payment: {self.current_sale['payment_method']}\n"
            f"Stock condition: {self.cmb_condition.currentText()}\n\n"
            "The final refund uses the saved sale and payment history. Customer credit may be reduced before a payout.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        record = {"purchase_id": self.current_sale["purchase_id"], "items": items,
                  "employee_id": employee_id, "reason": reason,
                  "condition": self.cmb_condition.currentData(), "operation_id": uuid.uuid4().hex,
                  "sale": copy.deepcopy(self.current_sale)}
        try:
            self._save_pending_return(record)
        except OSError:
            QMessageBox.critical(self, "Return Not Submitted", "Could not save this return safely. Check disk space and try again.")
            return
        self._submit_saved_return()

    def _save_pending_return(self, record):
        path = _RETURN_CONTROLLER.pending_path(record["employee_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".pending-return-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self._pending_return = record

    def _load_pending_return(self):
        employee_id = self._employee_id()
        if employee_id is None or self._processing:
            return
        path = _RETURN_CONTROLLER.pending_path(employee_id)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if int(record["employee_id"]) != employee_id or not record["operation_id"]:
                raise ValueError("Invalid recovery identity")
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError):
            self._pending_return = {"recovery_error": True}
            self._lock_return(True)
            self.btn_process.setEnabled(False)
            self.lbl_sale_summary.setText("The saved return could not be read. Ask the owner to check its refund before continuing.")
            return
        self._pending_return = record
        self.txt_sale_id.setText(str(record["purchase_id"]))
        self._apply_sale_lookup(str(record["purchase_id"]), record.get("sale"))
        quantities = {item["batch_id"]: item["qty"] for item in record["items"]}
        for batch_id, widget in self._qty_widgets.items():
            widget.setValue(quantities.get(batch_id, 0))
        self.txt_reason.setText(record["reason"])
        self.cmb_condition.setCurrentIndex(max(0, self.cmb_condition.findData(record["condition"])))
        self._pending_retry_ready = False
        self._lock_return(True)
        self.btn_process.setEnabled(True)
        self.btn_process.setText("Check Return Status")
        self.lbl_sale_summary.setText(f"Sale #{record['purchase_id']}: a previous return needs checking. Its saved items and refund request are kept safely.")

    def _lock_return(self, locked):
        for control in (self.txt_sale_id, self.btn_find, self.tbl_items,
                        self.cmb_condition, self.txt_reason, self.btn_clear):
            control.setEnabled(not locked)

    def _clear_pending_return(self):
        if self._pending_return and not self._pending_return.get("recovery_error"):
            path = _RETURN_CONTROLLER.pending_path(self._pending_return["employee_id"])
            path.unlink(missing_ok=True)
        self._pending_return = None

    def _submit_saved_return(self):
        if not self._pending_return or self._pending_return.get("recovery_error"):
            return
        record = copy.deepcopy(self._pending_return)
        self._processing = True
        self._pending_retry_ready = False
        self._lock_return(True)
        self.btn_process.setEnabled(False)
        self.btn_process.setText("Processing…")
        def complete(payload):
            if self._employee_id() == record["employee_id"]:
                self._return_complete(payload)
        def failed(_details):
            if self._employee_id() == record["employee_id"]:
                self._return_failed()
        self._tasks.run(
            lambda: _RETURN_CONTROLLER.process(record["purchase_id"], record["items"], record["employee_id"],
                record["reason"], record["condition"], operation_id=record["operation_id"]),
            complete, failed,
        )

    def _check_saved_return(self, rejection_message=None):
        if not self._pending_return or self._pending_return.get("recovery_error"):
            return
        record = copy.deepcopy(self._pending_return)
        self._processing = True
        self.btn_process.setEnabled(False)
        self.btn_process.setText("Checking…")
        def complete(result):
            if self._employee_id() != record["employee_id"]:
                return
            self._processing = False
            if result is not None:
                self._return_complete((True, result))
            elif rejection_message is not None:
                try:
                    self._clear_pending_return()
                except OSError:
                    self._return_failed()
                    return
                self._lock_return(False)
                self.btn_process.setEnabled(True)
                self.btn_process.setText("Process Return")
                QMessageBox.critical(self, "Return Not Saved", rejection_message)
            else:
                self._pending_retry_ready = True
                self.btn_process.setEnabled(True)
                self.btn_process.setText("Retry Saved Return")
                self.lbl_sale_summary.setText("No saved return was found. Retry the original request safely; do not pay the refund twice.")
        self._tasks.run(lambda: _RETURN_CONTROLLER.operation_status(record["operation_id"], record["employee_id"]),
                        complete, lambda _details: self._return_failed())

    def _return_complete(self, payload):
        self._processing = False
        ok, result = payload
        if not ok:
            self._check_saved_return(rejection_message=str(result))
            return
        try:
            self._clear_pending_return()
        except OSError:
            self._return_failed()
            return
        self._lock_return(False)
        self.btn_process.setText("Process Return")

        tender_text = ", ".join(
            f"{name}: Rs. {amount:.2f}" for name, amount in result.get("refund_tenders", [])
        ) or "No cash payout required"
        QMessageBox.information(
            self,
            "Return Completed",
            f"Return #{result['return_id']} completed.\n"
            f"Refund value: Rs. {result['refund_amount']:.2f}\n"
            f"Settlement: {tender_text}",
        )
        self.find_sale()

    def _return_failed(self):
        self._processing = False
        self._pending_retry_ready = False
        self._lock_return(True)
        self.btn_process.setText("Check Return Status")
        self.btn_process.setEnabled(True)
        self.lbl_sale_summary.setText("The return result is not known. Check Return Status before paying a refund again. The original request is kept safely.")

    def on_screen_show(self):
        self._load_pending_return()
        if self._pending_return:
            return
        if self.current_sale:
            self.find_sale()
