"""Optional release download with an explicit native installer handoff."""
from PySide6.QtCore import QTimer, QUrl, QObject
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel,
                               QTextBrowser, QDialogButtonBox, QMessageBox)
from controllers.update_controller import UpdateController
from ui.app.async_tasks import AsyncTaskRunner
from ui.app.state.session_state import SessionState
from ui.widgets.responsive import configure_dialog


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Pharma Khaato Update Available')
        configure_dialog(self, 650, 540, minimum_width=420, minimum_height=360)
        layout = QVBoxLayout(self)
        title = QLabel(f"Version {info['latest_version']} is available (installed: {info['current_version']}).")
        title.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(QLabel('What this update changes and fixes:'))
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(False)
        self.notes.setPlainText(info['release_notes'])
        layout.addWidget(self.notes, 1)
        notice = QLabel('You can update later. Before installing the update, finish or hold your bills and make a backup. If the shop has several counters, ask the owner to stop work on all of them first. Choose Later to keep using the app.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        buttons = QDialogButtonBox()
        later = buttons.addButton('Later', QDialogButtonBox.RejectRole)
        self.tasks = AsyncTaskRunner(self)
        self.package_path = None
        self.install_button = buttons.addButton('Download Verified Update', QDialogButtonBox.ActionRole)
        self.install_button.clicked.connect(lambda: self.update_package(info))
        download = buttons.addButton('Release Page', QDialogButtonBox.ActionRole)
        later.clicked.connect(self.reject)
        download.clicked.connect(lambda: self.download(info['download_url']))
        layout.addWidget(buttons)

    def update_package(self, info):
        state = SessionState.get_instance()
        if state.active_cart or state.pending_checkout:
            QMessageBox.information(self, 'Update', 'Finish or hold the current sale first.')
            return
        if self.package_path:
            if QDesktopServices.openUrl(QUrl.fromLocalFile(self.package_path)):
                self.accept()
            else:
                QMessageBox.information(self, 'Update', 'Open the downloaded file: ' + self.package_path)
            return
        self.install_button.setEnabled(False)
        self.install_button.setText('Downloading…')
        self.tasks.run(lambda: UpdateController.download(info), self.downloaded, self.download_failed)

    def downloaded(self, path):
        self.package_path = path
        self.install_button.setText('Open Verified Archive' if path.endswith('.tar.gz') else 'Start Installer')
        self.install_button.setEnabled(True)

    def download_failed(self, _details):
        self.install_button.setText('Retry Update Download')
        self.install_button.setEnabled(True)
        if self.isVisible():
            QMessageBox.warning(self, 'Update', 'Could not download and verify the installer. Check the connection or open the release page.')

    def download(self, url):
        if QDesktopServices.openUrl(QUrl(url)):
            self.accept()
        else:
            QMessageBox.information(self, 'Open Update Page', 'The browser could not open. Try again when internet access is available. You can keep using the POS.')


class UpdateNotifier(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.tasks = AsyncTaskRunner(self)
        self.busy = False
        self.pending = None
        self.shown = set()
        self.timer = QTimer(self)
        self.timer.setInterval(5 * 60_000)
        self.timer.timeout.connect(self.poll)
        # Automated/headless checks must not contact the internet.
        if QApplication.platformName() != "offscreen":
            self.timer.start()
            QTimer.singleShot(12_000, self.poll)

    def poll(self, manual=False):
        if not manual and not UpdateController.enabled():
            return
        if self.busy or not self.window.current_user:
            return
        if self.pending:
            self.offer()
            return
        self.busy = True
        self.tasks.run(lambda: UpdateController.check(force=manual),
                       lambda result: self.completed(result, manual),
                       lambda _error: self.completed({'status': 'offline'}, manual))

    def completed(self, result, manual):
        self.busy = False
        if not self.window.current_user or (not manual and not UpdateController.enabled()):
            return
        if result.get('status') == 'available':
            info = result['update']
            if manual or info['latest_version'] not in self.shown:
                self.pending = info
                self.offer()
        elif manual:
            message = ('You have the latest available release for this computer.' if result.get('status') == 'current'
                       else 'Update information is unavailable. Check again when internet access is available. You can keep using the app without internet.')
            QMessageBox.information(self.window, 'Check for Updates', message)

    def offer(self):
        if getattr(self, "dialog", None) is not None and self.dialog.isVisible():
            return
        state = SessionState.get_instance()
        if not self.pending or not self.window.isVisible() or QApplication.activeModalWidget() or state.active_cart or state.pending_checkout:
            return
        info, self.pending = self.pending, None
        self.shown.add(info['latest_version'])
        dialog = UpdateDialog(info, self.window)
        dialog.setModal(False)
        self.dialog = dialog  # Keep the modeless notice alive while the cashier reads it.
        dialog.show()
