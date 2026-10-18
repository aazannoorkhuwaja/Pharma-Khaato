"""Pre-login recovery remains usable when the pharmacy database cannot open."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit,
    QFileDialog, QDialogButtonBox, QMessageBox,
)

from controllers.application_controller import ApplicationController
from ui.app.async_tasks import AsyncTaskRunner


class RecoveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recover Pharmacy Data")
        self.resize(570, 420)
        self.controller = ApplicationController()
        self.tasks = AsyncTaskRunner(self)
        layout = QVBoxLayout(self)
        explanation = QLabel("Pharma Khaato could not open the pharmacy records. No sale was started.\n\n"
                             "Choose a backup and enter a manager account from that backup. Previous data will be preserved before recovery.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.backups = QComboBox()
        for backup in self.controller.recovery_backups():
            self.backups.addItem(backup["created_at"] + " — " + backup["filename"], backup["filepath"])
        layout.addWidget(self.backups)
        browse = QPushButton("Choose Backup from Another Location")
        browse.clicked.connect(self.choose_backup)
        layout.addWidget(browse)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Manager username from this backup")
        layout.addWidget(self.username)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Manager password")
        layout.addWidget(self.password)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.restore = QPushButton("Restore Selected Backup")
        self.restore.clicked.connect(self.start_restore)
        layout.addWidget(self.restore)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_backup(self):
        filepath, _kind = QFileDialog.getOpenFileName(self, "Choose Pharma Khaato Backup", "", "SQLite backup (*.sqlite);;All files (*)")
        if filepath:
            self.backups.addItem(filepath, filepath)
            self.backups.setCurrentIndex(self.backups.count() - 1)

    def start_restore(self):
        filepath = self.backups.currentData()
        if not filepath or not self.username.text().strip() or not self.password.text():
            self.status.setText("Choose a backup and enter the manager username and password.")
            return
        if QMessageBox.question(self, "Restore Pharmacy Records", "Replace the current records with this backup? Current files will be preserved. Work recorded after the backup will not appear in the restored records.") != QMessageBox.StandardButton.Yes:
            return
        username, password = self.username.text(), self.password.text()
        self.password.clear()
        self.restore.setEnabled(False)
        self.status.setText("Checking and restoring the backup…")
        self.tasks.run(lambda: self.controller.recover_from_backup(filepath, username, password), self.finished_restore,
                       lambda _details: self.finished_restore((False, "Recovery could not finish. Contact support with the application logs.")))

    def finished_restore(self, result):
        ok, message = result
        self.restore.setEnabled(True)
        self.status.setText(str(message))
        if ok:
            QMessageBox.information(self, "Recovery Complete", "Your backup was restored. Reopen Pharma Khaato to continue.")
            self.accept()
