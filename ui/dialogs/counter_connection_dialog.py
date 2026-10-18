"""Plain-language, one-time main-computer/counter setup."""
from __future__ import annotations

import socket
from controllers.shop_connection_controller import ShopConnectionController

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QFileDialog,
                              QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                              QMessageBox, QPushButton, QRadioButton, QSpinBox,
                              QVBoxLayout, QWidget)


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _SetupJob(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = _Signals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class CounterConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set up this shop computer")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        intro = QLabel("Choose where your shop records are kept. Every counter in one shop must connect to the same main computer.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.single = QRadioButton("One computer only")
        self.host = QRadioButton("Main computer — keep the shop records here and connect other counters")
        self.counter = QRadioButton("Another counter — connect to the main computer")
        self.group = QButtonGroup(self)
        for choice in (self.single, self.host, self.counter):
            self.group.addButton(choice)
            layout.addWidget(choice)
            choice.toggled.connect(self._mode_changed)
        self.single.setChecked(True)
        self.host_fields = QWidget()
        host_form = QFormLayout(self.host_fields)
        self.host_address = QLineEdit(socket.gethostname())
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(8765)
        host_form.addRow("Main computer name or LAN address", self.host_address)
        host_form.addRow("Shop port", self.port)
        host_note = QLabel("Keep this app and the main computer open while counters are working. Allow Pharma Khaato through the firewall on your private shop network. Never share the database folder.")
        host_note.setWordWrap(True)
        host_form.addRow(host_note)
        layout.addWidget(self.host_fields)
        self.counter_fields = QWidget()
        form = QFormLayout(self.counter_fields)
        self.address = QLineEdit()
        self.address.setPlaceholderText("https://MAIN-PC:8765")
        self.counter_name = QLineEdit("Counter-2")
        self.certificate = QLineEdit()
        self.certificate.setReadOnly(True)
        choose = QPushButton("Choose shop certificate…")
        choose.clicked.connect(self._browse)
        certificate_row = QHBoxLayout()
        certificate_row.addWidget(self.certificate)
        certificate_row.addWidget(choose)
        form.addRow("Shop address", self.address)
        form.addRow("This counter's name", self.counter_name)
        form.addRow("Shop certificate", certificate_row)
        note = QLabel("Copy shop-certificate.pem from the main computer using a USB drive or another trusted method. Choose that file here. Each staff member then signs in with their own shop account.")
        note.setWordWrap(True)
        form.addRow(note)
        layout.addWidget(self.counter_fields)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._mode_changed()

    def _mode_changed(self):
        if hasattr(self, "counter_fields"):
            self.counter_fields.setVisible(self.counter.isChecked())
            self.host_fields.setVisible(self.host.isChecked())

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose the shop certificate", "", "Shop certificate (*.pem *.crt)")
        if path:
            self.certificate.setText(path)

    def _save(self):
        if self.single.isChecked():
            ShopConnectionController.standalone()
            self.accept()
            return
        is_host = self.host.isChecked()
        host_address, port = self.host_address.text().strip(), self.port.value()
        server_url, cert, terminal = self.address.text().strip(), self.certificate.text(), self.counter_name.text().strip()
        def configure():
            if is_host:
                return ShopConnectionController.host(host_address, port)
            return ShopConnectionController.connect(server_url, cert, terminal)
        self.status.setText("Checking the shop connection…" if not is_host else "Preparing the main computer…")
        self.buttons.setEnabled(False)
        self._job = _SetupJob(configure)
        def done(values):
            self.buttons.setEnabled(True)
            if is_host:
                QMessageBox.information(self, "Main computer ready", f"Shop address: https://{host_address}:{port}\n\nCopy only this certificate to each counter:\n{values['certificate_path']}\n\nDo not copy the private key. Keep this app open for other counters.")
            self.accept()
        def failed(message):
            self.buttons.setEnabled(True)
            self.status.setText(message)
        self._job.signals.done.connect(done)
        self._job.signals.failed.connect(failed)
        QThreadPool.globalInstance().start(self._job)


def configure_shop_connection(parent=None) -> bool:
    return CounterConnectionDialog(parent).exec() == QDialog.Accepted
