"""Operator-facing thermal printer setup for Pharma Khaato."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from controllers.settings_controller import SettingsController
from ui.app.async_tasks import AsyncTaskRunner
from ui.theme.tokens import ThemeTokens
from ui.widgets.card import Card
from ui.widgets.responsive import configure_dialog


class PrinterSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = SettingsController()
        self.tasks = AsyncTaskRunner(self)

        self.setWindowTitle("Receipt Printer Setup")
        configure_dialog(self, 560, 440, minimum_width=420, minimum_height=360)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Receipt Printer")
        title.setObjectName("h1")
        root.addWidget(title)

        intro = QLabel(
            "Choose the printer used for thermal receipts. Printing happens only after a sale has been safely recorded, so a disconnected printer cannot undo or duplicate a transaction."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        root.addWidget(intro)

        card = Card()
        layout = card.layout()
        layout.setSpacing(10)

        layout.addWidget(QLabel("Printer"))
        self.cmb_printer = QComboBox()
        self.cmb_printer.setAccessibleName("Receipt printer")
        self.cmb_printer.addItem("System default printer", "")
        layout.addWidget(self.cmb_printer)

        self.chk_auto_print = QCheckBox("Print receipt automatically after each completed sale")
        self.chk_auto_print.setAccessibleName("Automatic receipt printing")
        layout.addWidget(self.chk_auto_print)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        layout.addWidget(self.lbl_status)

        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Printers")
        self.btn_refresh.clicked.connect(self.load_printers)
        self.btn_test = QPushButton("Print Test Receipt")
        self.btn_test.clicked.connect(self.print_test)
        actions.addWidget(self.btn_refresh)
        actions.addWidget(self.btn_test)
        actions.addStretch(1)
        layout.addLayout(actions)
        root.addWidget(card, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Printer Setup")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_and_accept)
        footer.addWidget(cancel)
        footer.addWidget(save)
        root.addLayout(footer)

        self._load_saved_settings()
        self.load_printers()

    @staticmethod
    def _truthy(value) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _load_saved_settings(self):
        values = self.controller.get_many(
            ("preferred_printer", "receipt_auto_print", "receipt_template"),
            {
                "preferred_printer": "",
                "receipt_auto_print": "0",
                "receipt_template": "professional_80",
            },
        )
        self.saved_printer = str(values.get("preferred_printer") or "")
        self.receipt_template = str(values.get("receipt_template") or "professional_80")
        self.chk_auto_print.setChecked(self._truthy(values.get("receipt_auto_print")))

    def load_printers(self):
        selected = self.cmb_printer.currentData()
        preferred = selected if selected is not None else self.saved_printer
        self.cmb_printer.clear()
        self.cmb_printer.addItem("System default printer", "")

        printers = self.controller.available_printers()
        for name in printers:
            self.cmb_printer.addItem(name, name)

        wanted = self.saved_printer or str(preferred or "")
        index = self.cmb_printer.findData(wanted)
        if index >= 0:
            self.cmb_printer.setCurrentIndex(index)
            self.lbl_status.setText(f"{len(printers)} printer(s) available to Pharma Khaato.")
        elif wanted:
            self.lbl_status.setText(
                f"Saved printer “{wanted}” is not currently available. Connect/install it, then choose Refresh Printers."
            )
        elif printers:
            self.lbl_status.setText(f"{len(printers)} printer(s) detected. You can keep the system default or choose one explicitly.")
        else:
            self.lbl_status.setText(
                "No OS printer was detected. You can save with automatic printing off and continue using saved receipt files until the printer is installed."
            )

        self.btn_test.setEnabled(bool(printers) or self.cmb_printer.currentData() == "")

    def print_test(self):
        printer_name = str(self.cmb_printer.currentData() or "")
        self.btn_test.setEnabled(False)
        self.btn_test.setText("Sending Test…")
        self.lbl_status.setText("Sending a sample receipt through the operating-system print spooler…")

        def complete(ok):
            self.btn_test.setEnabled(True)
            self.btn_test.setText("Print Test Receipt")
            if ok:
                self.lbl_status.setText("Test receipt was sent to the printer successfully.")
            else:
                self.lbl_status.setText("The test receipt could not be sent. Check that the printer is installed, online, and selected correctly.")
                QMessageBox.warning(
                    self,
                    "Printer Test Failed",
                    "Pharma Khaato could not send the test receipt. Sales can still be recorded safely; automatic printing should remain off until the printer test succeeds.",
                )

        self.tasks.run(
            lambda: self.controller.print_test_receipt(printer_name, self.receipt_template),
            complete,
            lambda _details: complete(False),
        )

    def save_and_accept(self):
        printer_name = str(self.cmb_printer.currentData() or "")
        auto_print = self.chk_auto_print.isChecked()

        if auto_print and printer_name and printer_name not in self.controller.available_printers():
            QMessageBox.warning(
                self,
                "Printer Not Available",
                "The selected printer is not currently available. Reconnect it or choose another printer before enabling automatic printing.",
            )
            return

        ok = self.controller.update(
            {
                "preferred_printer": printer_name,
                "receipt_auto_print": "1" if auto_print else "0",
            }
        )
        if not ok:
            QMessageBox.critical(self, "Could Not Save Printer Setup", "The printer settings could not be saved. Your previous configuration was kept.")
            return
        self.accept()
