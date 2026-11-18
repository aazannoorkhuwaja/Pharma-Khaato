"""Standalone installed owner utility; closes before normal shop startup."""
from pathlib import Path
import sys

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)
from ui.app.async_tasks import AsyncTaskRunner
from controllers.recovery_bundle_controller import perform_recovery



class RecoveryBundleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Pharma Khaato — Owner Recovery')
        self.resize(650, 480)
        self.tasks = AsyncTaskRunner(self)
        self.busy = False
        self.completed = False
        layout = QVBoxLayout(self)
        intro = QLabel('Close the pharmacy app and shop server first. Export creates an encrypted recovery copy. '
                       'Import restores that copy into a new folder without replacing existing records.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.form_widget = QWidget()
        form = QFormLayout(self.form_widget)
        self.mode = QComboBox()
        self.mode.addItem('Export owner recovery copy', 'export')
        self.mode.addItem('Import onto a replacement computer', 'import')
        form.addRow('Operation', self.mode)
        self.source = QLineEdit()
        self.destination = QLineEdit()
        for title, field, callback in (
            ('Source', self.source, self.choose_source), ('Destination', self.destination, self.choose_destination),
        ):
            row = QWidget()
            box = QHBoxLayout(row)
            box.setContentsMargins(0, 0, 0, 0)
            box.addWidget(field)
            button = QPushButton('Browse…')
            button.setAccessibleName('Choose recovery ' + title.lower())
            button.clicked.connect(callback)
            box.addWidget(button)
            field.setAccessibleName('Recovery ' + title.lower())
            form.addRow(title, row)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.passphrase = QLineEdit()
        self.confirm = QLineEdit()
        for title, field in (('Owner username', self.username), ('Owner password', self.password),
                             ('Recovery passphrase', self.passphrase), ('Repeat passphrase', self.confirm)):
            field.setAccessibleName(title)
            if field is not self.username:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(title, field)
        layout.addWidget(self.form_widget)
        self.status = QLabel('Use at least 16 characters for the recovery passphrase. Keep it separate from the recovery file.')
        self.status.setWordWrap(True)
        self.status.setAccessibleName('Recovery operation status')
        layout.addWidget(self.status)
        self.run_button = QPushButton('Create Recovery Copy')
        self.run_button.clicked.connect(self.start)
        layout.addWidget(self.run_button)
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.mode_changed()

    def mode_changed(self):
        exporting = self.mode.currentData() == 'export'
        for field in (self.username, self.password, self.confirm):
            field.setEnabled(exporting)
        self.source.clear()
        self.destination.clear()
        self.source.setPlaceholderText('Existing shop data folder' if exporting else 'Encrypted recovery file')
        self.destination.setPlaceholderText('New recovery file (.pkrecovery)' if exporting else 'New, nonexistent shop folder')
        self.run_button.setText('Create Recovery Copy' if exporting else 'Recover into New Folder')

    def choose_source(self):
        if self.mode.currentData() == 'export':
            value = QFileDialog.getExistingDirectory(self, 'Choose Existing Shop Data Folder')
        else:
            value, _ = QFileDialog.getOpenFileName(self, 'Choose Recovery Copy', '', 'Recovery copies (*.pkrecovery);;All files (*)')
        if value:
            self.source.setText(value)

    def choose_destination(self):
        # Import needs a nonexistent directory, so choose its parent and append a
        # new name. The backend still refuses any existing destination.
        if self.mode.currentData() == 'export':
            value, _ = QFileDialog.getSaveFileName(self, 'Save New Recovery Copy', 'shop.pkrecovery', 'Recovery copies (*.pkrecovery)')
        else:
            parent = QFileDialog.getExistingDirectory(self, 'Choose Parent for New Recovered Shop Folder')
            value = str(Path(parent) / 'recovered-shop') if parent else ''
        if value:
            self.destination.setText(value)

    def start(self):
        if self.busy or self.completed:
            return
        mode = self.mode.currentData()
        source, destination = self.source.text().strip(), self.destination.text().strip()
        username, password, phrase = self.username.text().strip(), self.password.text(), self.passphrase.text()
        if not source or not destination or len(phrase) < 16:
            self.status.setText('Choose source and destination, and enter a passphrase of at least 16 characters.')
            return
        if mode == 'export' and (not username or not password or phrase != self.confirm.text()):
            self.status.setText('Enter the owner credentials and matching recovery passphrases.')
            return
        self.busy = True
        self.form_widget.setEnabled(False)
        self.run_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.status.setText('Verifying and processing recovery data… Keep this window open.')
        for field in (self.password, self.passphrase, self.confirm):
            field.clear()

        def work():
            try:
                return True, perform_recovery(mode, source, destination, username, password, phrase)
            except (ValueError, PermissionError, RuntimeError, OSError) as exc:
                return False, str(exc)

        self.tasks.run(work, self.operation_finished,
                       lambda _details: self.operation_finished((False, 'Recovery failed. Keep the original copy and contact support.')))

    def operation_finished(self, result):
        self.busy = False
        self.completed, message = result
        self.close_button.setEnabled(True)
        self.form_widget.setEnabled(not self.completed)
        self.run_button.setEnabled(not self.completed)
        if self.completed:
            self.status.setText('Completed: ' + str(message) + '\nClose this utility. Before trading on a recovered host, '
                                'verify the shop connection, backup destination and financial reconciliation. Keep the original host offline.')
        else:
            self.status.setText(str(message))

    def reject(self):
        if not self.busy:
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)


def run_recovery_tool():
    app = QApplication.instance() or QApplication([sys.argv[0]])
    dialog = RecoveryBundleDialog()
    dialog.exec()
    return 0
