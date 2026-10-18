"""Product identity, authorship and optional workstation update preferences."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                               QCheckBox, QDialogButtonBox, QMessageBox)
from config import ApplicationSettings
from controllers.update_controller import UpdateController
from ui.widgets.responsive import configure_dialog


class AboutDialog(QDialog):
    def __init__(self, notifier, parent=None):
        super().__init__(parent)
        self.setWindowTitle('About Pharma Khaato')
        configure_dialog(self, 580, 470, minimum_width=400, minimum_height=350)
        layout = QVBoxLayout(self)
        for text in (ApplicationSettings.version_label(), ApplicationSettings.PRODUCT_DESCRIPTION,
                     ApplicationSettings.CREDITS, 'MIT License · Copyright 2026',
                     ApplicationSettings.DATA_NOTICE):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)
        self.automatic = QCheckBox('Check for updates automatically when internet is available')
        self.automatic.setChecked(UpdateController.enabled())
        self.automatic.toggled.connect(self.save_preference)
        layout.addWidget(self.automatic)
        button = QPushButton('Check for Updates')
        def check():
            self.accept()
            notifier.poll(manual=True)
        button.clicked.connect(check)
        layout.addWidget(button)
        support = ApplicationSettings.SUPPORT_EMAIL or 'Contact the person who supplied your installation.'
        label = QLabel('Support: ' + support)
        label.setWordWrap(True)
        layout.addWidget(label)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def save_preference(self, enabled):
        try:
            UpdateController.set_enabled(enabled)
        except (OSError, ValueError):
            self.automatic.blockSignals(True)
            self.automatic.setChecked(not enabled)
            self.automatic.blockSignals(False)
            QMessageBox.information(self, 'Update Preference', 'This preference could not be saved. Check the computer storage and try again.')
