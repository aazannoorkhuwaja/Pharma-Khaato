"""Pharmacy settings, receipt design, staff access, backups, recovery, and system status."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
    QDoubleSpinBox, QSpinBox, QMessageBox, QTabWidget, QTextEdit,
    QComboBox, QInputDialog, QDialog, QApplication, QAbstractItemView, QFileDialog,
)

from config import ApplicationSettings
from ui.theme.tokens import ThemeTokens
from ui.theme.theme_manager import ThemeManager
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import flexible_side_panel, configure_dialog
from ui.ux_copy import ROLE_OPTIONS, role_label
from ui.app.state.health_checker import SystemHealthChecker
from ui.app.state.session_state import SessionState
from ui.app.async_tasks import AsyncTaskRunner
from controllers.settings_controller import SettingsController

_SETTINGS_CONTROLLER = SettingsController()


class SettingsScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box
        self._tasks = AsyncTaskRunner(self)
        self._staff_loaded = False
        self._system_loaded = False
        self._staff_rows = []
        self._backup_rows = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Settings",
            "Manage pharmacy profile, business rules, receipts, staff access, backups, and recovery."
        )
        self.pill_system_status = BadgePill("Not Checked", BadgePill.TYPE_INFO)
        header_card.add_pill(self.pill_system_status)
        layout.addWidget(header_card)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self._setup_general_tab()
        self._setup_receipts_tab()
        self.setup_user_management_tab()
        self._setup_system_tab()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

        # One batched settings read only. Staff, health, backup listing and
        # integrity checks are lazy so opening Settings is immediate.
        self.load_settings()

    def _setup_general_tab(self):
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(14)

        profile_card = Card()
        profile_layout = profile_card.layout()
        profile_layout.setSpacing(12)
        profile_title = QLabel("Pharmacy Profile")
        profile_title.setObjectName("h2")
        profile_layout.addWidget(profile_title)
        profile_help = QLabel(
            "These details identify the pharmacy on receipts and operational records. Keep licence and tax details current."
        )
        profile_help.setWordWrap(True)
        profile_help.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        profile_layout.addWidget(profile_help)

        profile_form = QFormLayout()
        profile_form.setSpacing(10)
        self.txt_pharmacy_name = QLineEdit()
        self.txt_pharmacy_name.setPlaceholderText("Pharmacy trading name")
        self.txt_pharmacy_name.setAccessibleName("Pharmacy name")
        self.txt_slogan = QLineEdit()
        self.txt_slogan.setPlaceholderText("Optional receipt tagline")
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("Street / area / city")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Customer contact number")
        self.txt_license = QLineEdit()
        self.txt_license.setPlaceholderText("Drug sale / pharmacy licence number")
        self.txt_ntn = QLineEdit()
        self.txt_ntn.setPlaceholderText("NTN / tax registration, if applicable")
        profile_form.addRow("Pharmacy name:", self.txt_pharmacy_name)
        profile_form.addRow("Tagline:", self.txt_slogan)
        profile_form.addRow("Address:", self.txt_address)
        profile_form.addRow("Phone:", self.txt_phone)
        profile_form.addRow("Licence number:", self.txt_license)
        profile_form.addRow("NTN / tax ID:", self.txt_ntn)
        profile_layout.addLayout(profile_form)
        gen_layout.addWidget(profile_card)

        card = Card()
        card_layout = card.layout()
        card_layout.setSpacing(12)
        title = QLabel("Business & Display")
        title.setObjectName("h2")
        card_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0.0, 50.0)
        self.spn_tax.setSuffix(" %")
        self.spn_tax.setDecimals(2)
        self.spn_tax.setAccessibleName("Sales tax percentage")

        self.spn_credit_limit = QDoubleSpinBox()
        self.spn_credit_limit.setRange(1000.0, 1000000.0)
        self.spn_credit_limit.setPrefix("Rs. ")
        self.spn_credit_limit.setDecimals(2)
        self.spn_credit_limit.setAccessibleName("Customer credit limit")

        self.spn_expiry_threshold = QSpinBox()
        self.spn_expiry_threshold.setRange(7, 365)
        self.spn_expiry_threshold.setSuffix(" days")
        self.spn_expiry_threshold.setAccessibleName("Expiry warning days")

        self.cmb_theme_mode = QComboBox()
        self.cmb_theme_mode.addItem("Light", "light")
        self.cmb_theme_mode.addItem("Dark", "dark")

        self.cmb_font_scale = QComboBox()
        self.cmb_font_scale.addItem("Standard (100%)", "1.0")
        self.cmb_font_scale.addItem("Medium (125%)", "1.25")
        self.cmb_font_scale.addItem("Large (150%)", "1.5")

        form.addRow("Sales tax:", self.spn_tax)
        form.addRow("Customer credit limit:", self.spn_credit_limit)
        form.addRow("Warn about expiry:", self.spn_expiry_threshold)
        form.addRow("Theme:", self.cmb_theme_mode)
        form.addRow("Interface size:", self.cmb_font_scale)
        card_layout.addLayout(form)

        self.btn_save_settings = QPushButton("Save Pharmacy Settings")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.clicked.connect(self.save_settings)
        card_layout.addWidget(self.btn_save_settings)
        card_layout.addStretch()
        gen_layout.addWidget(card)
        gen_layout.addStretch()
        self.tabs.addTab(self.tab_general, "General")

    def _setup_receipts_tab(self):
        self.tab_receipts = QWidget()
        layout = QHBoxLayout(self.tab_receipts)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        settings_card = Card()
        flexible_side_panel(settings_card, minimum=330, maximum=470)
        settings_layout = settings_card.layout()
        settings_layout.setSpacing(12)

        title = QLabel("Receipt Design")
        title.setObjectName("h2")
        settings_layout.addWidget(title)
        help_text = QLabel(
            "Choose the format that matches your thermal printer and the amount of detail your pharmacy needs."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        settings_layout.addWidget(help_text)

        form = QFormLayout()
        form.setSpacing(10)
        self.cmb_receipt_template = QComboBox()
        for key, label, description in _SETTINGS_CONTROLLER.receipt_template_options():
            self.cmb_receipt_template.addItem(label, key)
            index = self.cmb_receipt_template.count() - 1
            self.cmb_receipt_template.setItemData(index, description, 3)
        self.cmb_receipt_template.setAccessibleName("Receipt format")
        self.cmb_receipt_template.currentIndexChanged.connect(self._update_receipt_template_help)

        self.txt_receipt_header = QLineEdit()
        self.txt_receipt_header.setReadOnly(True)
        self.txt_receipt_header.setToolTip("Receipt heading comes from the Pharmacy Profile on the General tab.")
        self.txt_receipt_footer = QLineEdit()
        self.txt_receipt_footer.setPlaceholderText("Short message at the bottom of receipts")
        form.addRow("Receipt format:", self.cmb_receipt_template)
        form.addRow("Receipt heading:", self.txt_receipt_header)
        form.addRow("Receipt footer:", self.txt_receipt_footer)
        settings_layout.addLayout(form)

        self.lbl_receipt_template_help = QLabel()
        self.lbl_receipt_template_help.setWordWrap(True)
        self.lbl_receipt_template_help.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        settings_layout.addWidget(self.lbl_receipt_template_help)

        button_row = QHBoxLayout()
        self.btn_preview_receipt = QPushButton("Preview Sample")
        self.btn_preview_receipt.clicked.connect(self.preview_receipt)
        self.btn_save_receipt = QPushButton("Save Receipt Settings")
        self.btn_save_receipt.setObjectName("primaryButton")
        self.btn_save_receipt.clicked.connect(self.save_settings)
        button_row.addWidget(self.btn_preview_receipt)
        button_row.addWidget(self.btn_save_receipt)
        settings_layout.addLayout(button_row)
        settings_layout.addStretch()
        layout.addWidget(settings_card, 4)

        info_card = Card()
        info_layout = info_card.layout()
        info_title = QLabel("Format Guide")
        info_title.setObjectName("h2")
        info_layout.addWidget(info_title)
        guide = QLabel(
            "Professional 80mm — best for a polished pharmacy counter receipt.\n\n"
            "Standard 80mm — simple and balanced for everyday use.\n\n"
            "Detailed 80mm — includes more transaction information for record-heavy pharmacies.\n\n"
            "Tax Invoice 80mm — emphasizes licence, NTN, tax and payable amount.\n\n"
            "Compact 58mm — fastest and shortest option for narrow printers."
        )
        guide.setWordWrap(True)
        guide.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        info_layout.addWidget(guide)
        info_layout.addStretch()
        layout.addWidget(info_card, 6)
        self.tabs.addTab(self.tab_receipts, "Receipts")

    def _update_receipt_template_help(self):
        index = self.cmb_receipt_template.currentIndex()
        options = _SETTINGS_CONTROLLER.receipt_template_options()
        if 0 <= index < len(options):
            self.lbl_receipt_template_help.setText(options[index][2])

    def preview_receipt(self):
        template = self.cmb_receipt_template.currentData() or "standard_80"
        receipt = _SETTINGS_CONTROLLER.receipt_preview(template)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Receipt Preview — {self.cmb_receipt_template.currentText()}")
        configure_dialog(dialog, 620, 700, minimum_width=430, minimum_height=450)
        preview_layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setPlainText(receipt)
        preview.setStyleSheet("font-family: monospace;")
        preview.setAccessibleName("Receipt sample preview")
        preview_layout.addWidget(preview, 1)
        close_button = QPushButton("Close Preview")
        close_button.clicked.connect(dialog.accept)
        preview_layout.addWidget(close_button)
        dialog.exec()

    def _setup_system_tab(self):
        self.tab_technical = QWidget()
        tech_layout = QVBoxLayout(self.tab_technical)
        tech_layout.setContentsMargins(16, 16, 16, 16)
        tech_layout.setSpacing(14)
        tech_grid = QHBoxLayout()
        tech_grid.setSpacing(14)

        status_card = Card()
        status_layout = status_card.layout()
        status_layout.setSpacing(10)
        title = QLabel("System & Support")
        title.setObjectName("h2")
        status_layout.addWidget(title)
        version = QLabel(f"{ApplicationSettings.DISPLAY_NAME} • Version {ApplicationSettings.APP_VERSION}")
        version.setObjectName("caption")
        status_layout.addWidget(version)
        self.lbl_health_info = QLabel("Open this tab to run the system check.")
        self.lbl_health_info.setWordWrap(True)
        self.lbl_health_info.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        status_layout.addWidget(self.lbl_health_info)
        self.btn_toggle_details = QPushButton("Show Diagnostics")
        self.btn_toggle_details.setToolTip("Show diagnostic information that technical support may ask for.")
        self.btn_toggle_details.clicked.connect(self.toggle_technical_details)
        status_layout.addWidget(self.btn_toggle_details)
        self.lbl_log_hdr = QLabel("Diagnostics (for support)")
        self.lbl_log_hdr.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; margin-top: 8px;")
        self.lbl_log_hdr.hide()
        status_layout.addWidget(self.lbl_log_hdr)
        self.txt_tech_log = QTextEdit()
        self.txt_tech_log.setReadOnly(True)
        self.txt_tech_log.setAccessibleName("System technical details")
        self.txt_tech_log.setStyleSheet(
            f"background-color: #0d1117; color: #9CDCFE; font-family: monospace; "
            f"border: 1px solid {ThemeTokens.BORDER_SUBTLE}; border-radius: 6px;"
        )
        self.txt_tech_log.hide()
        status_layout.addWidget(self.txt_tech_log, 1)
        system_buttons = QHBoxLayout()
        self.btn_refresh_system = QPushButton("Check System Again")
        self.btn_refresh_system.clicked.connect(self.refresh_db_health_and_backups)
        self.btn_support_bundle = QPushButton("Create Support Bundle")
        self.btn_support_bundle.setToolTip("Create a diagnostics ZIP without including the live database or receipts.")
        self.btn_support_bundle.clicked.connect(self.create_support_bundle)
        system_buttons.addWidget(self.btn_refresh_system)
        system_buttons.addWidget(self.btn_support_bundle)
        status_layout.addLayout(system_buttons)
        tech_grid.addWidget(status_card, 1)

        backup_card = Card()
        backup_layout = backup_card.layout()
        backup_layout.setSpacing(10)
        title = QLabel("Backup & Recovery")
        title.setObjectName("h2")
        backup_layout.addWidget(title)
        backup_help = QLabel(
            "Pharma Khaato checks backups every minute and saves an automatic snapshot at least hourly while open. "
            "Keep a second copy on a protected USB drive or another device. Recovery preserves the previous files and requires a restart."
        )
        backup_help.setWordWrap(True)
        backup_help.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        backup_layout.addWidget(backup_help)
        self.lbl_backup_destination = QLabel("Second backup copy: " + (_SETTINGS_CONTROLLER.backup_destination() or "Not configured"))
        self.lbl_backup_destination.setWordWrap(True)
        backup_layout.addWidget(self.lbl_backup_destination)
        self.btn_backup_destination = QPushButton("Choose Second Backup Location")
        self.btn_backup_destination.clicked.connect(self.choose_backup_destination)
        backup_layout.addWidget(self.btn_backup_destination)
        backup_actions = QHBoxLayout()
        self.btn_trigger_backup = QPushButton("Create Backup Now")
        self.btn_trigger_backup.setObjectName("successButton")
        self.btn_trigger_backup.clicked.connect(self.trigger_backup)
        self.btn_restore_backup = QPushButton("Restore Selected Backup")
        self.btn_restore_backup.setEnabled(False)
        self.btn_restore_backup.clicked.connect(self.restore_selected_backup)
        backup_actions.addWidget(self.btn_trigger_backup)
        backup_actions.addWidget(self.btn_restore_backup)
        backup_layout.addLayout(backup_actions)
        saved_label = QLabel("Saved Backups")
        saved_label.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY};")
        backup_layout.addWidget(saved_label)
        self.tbl_backups = QTableWidget(0, 3)
        self.tbl_backups.setHorizontalHeaderLabels(["Backup File", "Size", "Created"])
        self.tbl_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_backups.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_backups.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_backups.itemSelectionChanged.connect(self._update_restore_button)
        polish_table(self.tbl_backups)
        self.tbl_backups.verticalHeader().setVisible(False)
        self.tbl_backups.setEditTriggers(QTableWidget.NoEditTriggers)
        backup_layout.addWidget(self.tbl_backups, 1)
        tech_grid.addWidget(backup_card, 1)
        tech_layout.addLayout(tech_grid, 1)
        self.tabs.addTab(self.tab_technical, "System & Recovery")

    def _on_tab_changed(self, index: int):
        current = self.tabs.widget(index)
        if current is self.tab_users and not self._staff_loaded:
            self.refresh_employee_table()
        elif current is self.tab_technical and not self._system_loaded:
            self.refresh_db_health_and_backups()

    def toggle_technical_details(self):
        visible = not self.txt_tech_log.isVisible()
        self.txt_tech_log.setVisible(visible)
        self.lbl_log_hdr.setVisible(visible)
        self.btn_toggle_details.setText("Hide Diagnostics" if visible else "Show Diagnostics")

    def load_settings(self):
        keys = [
            "default_tax_rate",
            "max_customer_credit_limit",
            "near_expiry_days",
            "expiry_warning_threshold_days",
            "pharmacy_name",
            "slogan",
            "address",
            "phone",
            "license_number",
            "ntn_number",
            "receipt_header_text",
            "receipt_footer",
            "receipt_footer_text",
            "receipt_template",
        ]
        settings = _SETTINGS_CONTROLLER.get_many(
            keys,
            {
                "default_tax_rate": "0.10",
                "max_customer_credit_limit": "25000.00",
                "near_expiry_days": "30",
                "expiry_warning_threshold_days": "30",
                "pharmacy_name": "Pharma Khaato Pharmacy",
                "slogan": "",
                "address": "",
                "phone": "",
                "license_number": "",
                "ntn_number": "",
                "receipt_header_text": "Pharma Khaato Pharmacy",
                "receipt_footer": "Thank you for trusting Pharma Khaato.",
                "receipt_footer_text": "Thank you for trusting Pharma Khaato.",
                "receipt_template": "standard_80",
            },
        )
        tax_raw = settings.get("default_tax_rate", "0.00")
        limit_raw = settings.get("max_customer_credit_limit", "25000.00")
        expiry_raw = settings.get("near_expiry_days") or settings.get("expiry_warning_threshold_days", "30")
        receipt_title = settings.get("pharmacy_name") or settings.get("receipt_header_text", "Pharma Khaato Pharmacy")
        receipt_footer = settings.get("receipt_footer") or settings.get("receipt_footer_text", "Thank you for trusting Pharma Khaato.")
        receipt_template = settings.get("receipt_template", "standard_80")

        self.txt_pharmacy_name.setText(str(settings.get("pharmacy_name") or ""))
        self.txt_slogan.setText(str(settings.get("slogan") or ""))
        self.txt_address.setText(str(settings.get("address") or ""))
        self.txt_phone.setText(str(settings.get("phone") or ""))
        self.txt_license.setText(str(settings.get("license_number") or ""))
        self.txt_ntn.setText(str(settings.get("ntn_number") or ""))

        try:
            tax_value = float(tax_raw)
            self.spn_tax.setValue(tax_value)
        except Exception:
            self.spn_tax.setValue(0.0)
        try:
            self.spn_credit_limit.setValue(float(limit_raw))
        except Exception:
            self.spn_credit_limit.setValue(25000.0)
        try:
            self.spn_expiry_threshold.setValue(int(expiry_raw))
        except Exception:
            self.spn_expiry_threshold.setValue(30)

        self.txt_receipt_header.setText(receipt_title)
        self.txt_receipt_footer.setText(receipt_footer)
        template_index = self.cmb_receipt_template.findData(receipt_template)
        self.cmb_receipt_template.setCurrentIndex(template_index if template_index >= 0 else 0)
        self._update_receipt_template_help()

        mode_index = self.cmb_theme_mode.findData(ThemeManager.get_theme_mode())
        if mode_index >= 0:
            self.cmb_theme_mode.setCurrentIndex(mode_index)
        scale_index = self.cmb_font_scale.findData(str(ThemeManager.get_font_scale()))
        if scale_index >= 0:
            self.cmb_font_scale.setCurrentIndex(scale_index)

    def save_settings(self):
        pharmacy_name = self.txt_pharmacy_name.text().strip()
        receipt_footer = self.txt_receipt_footer.text().strip()
        if not pharmacy_name:
            show_toast(self, "Enter the pharmacy name before saving.", ToastType.WARNING)
            self.tabs.setCurrentWidget(self.tab_general)
            self.txt_pharmacy_name.setFocus()
            return
        values = {
            "default_tax_rate": str(self.spn_tax.value()),
            "max_customer_credit_limit": f"{self.spn_credit_limit.value():.2f}",
            "near_expiry_days": str(self.spn_expiry_threshold.value()),
            "expiry_warning_threshold_days": str(self.spn_expiry_threshold.value()),
            "pharmacy_name": pharmacy_name,
            "slogan": self.txt_slogan.text().strip(),
            "address": self.txt_address.text().strip(),
            "phone": self.txt_phone.text().strip(),
            "license_number": self.txt_license.text().strip(),
            "ntn_number": self.txt_ntn.text().strip(),
            "receipt_header_text": pharmacy_name,
            "receipt_footer": receipt_footer,
            "receipt_footer_text": receipt_footer,
            "receipt_template": str(self.cmb_receipt_template.currentData() or "standard_80"),
        }
        if not _SETTINGS_CONTROLLER.update(values):
            QMessageBox.critical(self, "Could Not Save Settings", "Some settings could not be saved. Your previous values were kept where possible.")
            return
        self.txt_receipt_header.setText(pharmacy_name)
        ThemeManager.set_theme(self.cmb_theme_mode.currentData(), save=True)
        ThemeManager.set_font_scale(float(self.cmb_font_scale.currentData()), save=True)
        if self.show_message_box:
            show_toast(self, "Pharmacy settings saved.", ToastType.SUCCESS)

    def refresh_db_health_and_backups(self):
        self._system_loaded = False
        self.pill_system_status.setText("Checking")
        self.pill_system_status.set_pill_type(BadgePill.TYPE_INFO)
        self.lbl_health_info.setText("Checking database, storage, and backups…")
        self.btn_refresh_system.setEnabled(False)

        def load_system_snapshot():
            return SystemHealthChecker.run_diagnostics(), _SETTINGS_CONTROLLER.backups()

        self._tasks.run_latest(
            "settings-system",
            load_system_snapshot,
            self._apply_system_snapshot,
            self._system_load_failed,
        )

    def _apply_system_snapshot(self, payload):
        health, backups = payload
        self._backup_rows = list(backups)
        issues = list(health.get("issues") or [])
        healthy = bool(
            health.get("db_connected")
            and health.get("wal_enabled")
            and health.get("db_integrity_ok")
            and health.get("writable_directories")
            and not issues
        )
        if healthy:
            free_space = health.get("free_space_mb", 0)
            free_text = f"\nFree storage: {free_space:,} MB" if free_space else ""
            self.lbl_health_info.setText("Database: Ready\nDatabase integrity: Passed\nData folders: Writable" + free_text)
            self.pill_system_status.setText("Ready")
            self.pill_system_status.set_pill_type(BadgePill.TYPE_SUCCESS)
        else:
            summary = "; ".join(issues) if issues else "A system check did not pass."
            self.lbl_health_info.setText(f"System needs attention.\n{summary}")
            self.pill_system_status.setText("Needs Attention")
            self.pill_system_status.set_pill_type(BadgePill.TYPE_DANGER)

        technical_lines = [
            f"[CHECK] Database connected: {bool(health.get('db_connected'))}",
            f"[CHECK] WAL write mode: {bool(health.get('wal_enabled'))}",
            f"[CHECK] Database integrity: {bool(health.get('db_integrity_ok'))}",
            f"[CHECK] Data folders writable: {bool(health.get('writable_directories'))}",
            f"[CHECK] Free storage MB: {health.get('free_space_mb', 0)}",
        ]
        technical_lines.extend(
            (f"[ISSUE] {issue}" for issue in issues)
            if issues
            else ["[RESULT] Basic system checks passed."]
        )
        self.txt_tech_log.setText("\n".join(technical_lines))

        self.tbl_backups.setUpdatesEnabled(False)
        try:
            self.tbl_backups.setRowCount(len(backups))
            for row, item in enumerate(backups):
                self.tbl_backups.setItem(row, 0, QTableWidgetItem(str(item["filename"])))
                self.tbl_backups.setItem(row, 1, QTableWidgetItem(f"{item['size_bytes'] / 1024:.1f} KB"))
                self.tbl_backups.setItem(row, 2, QTableWidgetItem(str(item["created_at"])))
        finally:
            self.tbl_backups.setUpdatesEnabled(True)
        self.tbl_backups.clearSelection()
        self._update_restore_button()

        self._system_loaded = True
        self.btn_refresh_system.setEnabled(True)

    def _system_load_failed(self, _details: str):
        self.btn_refresh_system.setEnabled(True)
        self.pill_system_status.setText("Could Not Check")
        self.pill_system_status.set_pill_type(BadgePill.TYPE_DANGER)
        self.lbl_health_info.setText("Could not complete the system check. Try again.")

    def trigger_backup(self):
        self.btn_trigger_backup.setEnabled(False)
        self.btn_trigger_backup.setText("Creating Backup…")

        def complete(result):
            self.btn_trigger_backup.setEnabled(True)
            self.btn_trigger_backup.setText("Create Backup Now")
            ok, value = result
            if ok:
                if self.show_message_box:
                    show_toast(self, f"Backup created: {Path(str(value)).name}", ToastType.SUCCESS)
                self._system_loaded = False
                self.refresh_db_health_and_backups()
            elif self.show_message_box:
                QMessageBox.critical(self, "Could Not Create Backup", str(value))

        def failed(_details):
            self.btn_trigger_backup.setEnabled(True)
            self.btn_trigger_backup.setText("Create Backup Now")
            if self.show_message_box:
                QMessageBox.critical(self, "Could Not Create Backup", "The backup operation failed. Try again.")

        self._tasks.run(_SETTINGS_CONTROLLER.create_backup, complete, failed)

    def choose_backup_destination(self):
        destination = QFileDialog.getExistingDirectory(self, "Choose Protected Backup Folder")
        if not destination:
            return
        ok, message = _SETTINGS_CONTROLLER.configure_backup_destination(destination)
        if ok:
            self.lbl_backup_destination.setText("Second backup copy: " + destination)
            self.trigger_backup()
        elif self.show_message_box:
            QMessageBox.warning(self, "Backup Location", str(message))

    def _update_restore_button(self):
        row = self.tbl_backups.currentRow() if hasattr(self, "tbl_backups") else -1
        self.btn_restore_backup.setEnabled(0 <= row < len(self._backup_rows))

    def restore_selected_backup(self):
        row = self.tbl_backups.currentRow()
        if row < 0 or row >= len(self._backup_rows):
            if self.show_message_box:
                show_toast(self, "Select a backup to restore.", ToastType.WARNING)
            return
        item = self._backup_rows[row]
        filename = str(item.get("filename", "selected backup"))
        filepath = str(item.get("filepath", ""))
        if not filepath:
            return

        reply = QMessageBox.question(
            self,
            "Restore Pharmacy Data",
            f"Restore data from {filename}?\n\n"
            "Pharma Khaato will first create a safety backup of the current database. "
            "After a successful restore the application will close and must be reopened.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        user = SessionState.get_instance().current_user or {}
        employee_id = int(user.get("id") or user.get("emp_id") or 0)
        self.btn_restore_backup.setEnabled(False)
        self.btn_trigger_backup.setEnabled(False)
        self.btn_restore_backup.setText("Restoring…")
        self.window().setEnabled(False)

        def complete(result):
            self.window().setEnabled(True)
            ok, message = result
            if not ok:
                self.btn_restore_backup.setText("Restore Selected Backup")
                self.btn_trigger_backup.setEnabled(True)
                self._update_restore_button()
                QMessageBox.critical(self, "Restore Failed", str(message))
                return
            QMessageBox.information(
                self,
                "Restore Complete",
                "The backup was restored successfully and a safety copy of the previous database was kept. "
                "Pharma Khaato will now close. Reopen it to continue with the restored data.",
            )
            QApplication.quit()

        def failed(_details):
            self.window().setEnabled(True)
            self.btn_restore_backup.setText("Restore Selected Backup")
            self.btn_trigger_backup.setEnabled(True)
            self._update_restore_button()
            QMessageBox.critical(self, "Restore Failed", "The restore operation could not be completed. Your current data was left protected.")

        self._tasks.run(
            lambda: _SETTINGS_CONTROLLER.restore_backup(filepath, employee_id),
            complete,
            failed,
        )

    def create_support_bundle(self):
        self.btn_support_bundle.setEnabled(False)
        self.btn_support_bundle.setText("Creating Bundle…")

        def complete(result):
            self.btn_support_bundle.setEnabled(True)
            self.btn_support_bundle.setText("Create Support Bundle")
            ok, value = result
            if ok:
                QMessageBox.information(
                    self,
                    "Support Bundle Created",
                    f"Diagnostics were saved as:\n{Path(str(value)).name}\n\n"
                    "The bundle does not include the live pharmacy database, receipts, exports, or backups. "
                    "It is stored in the application exports folder.",
                )
            else:
                QMessageBox.critical(self, "Could Not Create Support Bundle", str(value))

        def failed(_details):
            self.btn_support_bundle.setEnabled(True)
            self.btn_support_bundle.setText("Create Support Bundle")
            QMessageBox.critical(self, "Could Not Create Support Bundle", "Diagnostics could not be packaged. Try again after running the system check.")

        self._tasks.run(_SETTINGS_CONTROLLER.create_support_bundle, complete, failed)

    def setup_user_management_tab(self):
        self.tab_users = QWidget()
        layout = QHBoxLayout(self.tab_users)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        create_card = Card()
        flexible_side_panel(create_card, minimum=300, maximum=410)
        create_layout = create_card.layout()
        create_layout.setSpacing(12)
        title = QLabel("Add Staff Member")
        title.setObjectName("h2")
        title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 700;")
        create_layout.addWidget(title)
        helper = QLabel("Create a separate account for each person so activity and permissions stay traceable.")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        create_layout.addWidget(helper)

        form = QFormLayout()
        form.setSpacing(8)
        self.txt_new_user = QLineEdit()
        self.txt_new_user.setPlaceholderText("e.g. cashier1")
        self.txt_new_user.setAccessibleName("New staff username")
        self.txt_new_pass = QLineEdit()
        self.txt_new_pass.setEchoMode(QLineEdit.Password)
        self.txt_new_pass.setPlaceholderText("At least 8 characters")
        self.txt_new_pass.setAccessibleName("New staff password")
        self.txt_new_fname = QLineEdit()
        self.txt_new_fname.setPlaceholderText("First name")
        self.txt_new_lname = QLineEdit()
        self.txt_new_lname.setPlaceholderText("Last name")
        self.cmb_new_role = QComboBox()
        for display_label, backend_value in ROLE_OPTIONS:
            self.cmb_new_role.addItem(display_label, backend_value)
        self.cmb_new_role.setAccessibleName("Staff role")
        form.addRow("Username *:", self.txt_new_user)
        form.addRow("Password *:", self.txt_new_pass)
        form.addRow("First name *:", self.txt_new_fname)
        form.addRow("Last name:", self.txt_new_lname)
        form.addRow("Role:", self.cmb_new_role)
        create_layout.addLayout(form)
        self.btn_create_user = QPushButton("Add Staff")
        self.btn_create_user.setObjectName("primaryButton")
        self.btn_create_user.clicked.connect(self.on_create_user)
        create_layout.addWidget(self.btn_create_user)
        create_layout.addStretch()
        layout.addWidget(create_card, 3)

        list_card = Card()
        list_layout = list_card.layout()
        list_layout.setSpacing(10)
        title = QLabel("Staff Accounts")
        title.setObjectName("h2")
        list_layout.addWidget(title)
        staff_help = QLabel("Select a staff member to manage their account. Password reset is kept outside the table so rows stay readable at every interface size.")
        staff_help.setWordWrap(True)
        staff_help.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        list_layout.addWidget(staff_help)
        self.tbl_users = QTableWidget(0, 3)
        self.tbl_users.setHorizontalHeaderLabels(["Username", "Staff Member", "Role"])
        self.tbl_users.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_users.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_users.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_users.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_users.itemSelectionChanged.connect(self._update_staff_actions)
        polish_table(self.tbl_users, min_row_height=40)
        self.tbl_users.verticalHeader().setVisible(False)
        self.tbl_users.setEditTriggers(QTableWidget.NoEditTriggers)
        list_layout.addWidget(self.tbl_users, 1)
        staff_actions = QHBoxLayout()
        staff_actions.addStretch(1)
        self.btn_reset_selected = QPushButton("Reset Selected Password")
        self.btn_reset_selected.setEnabled(False)
        self.btn_reset_selected.clicked.connect(self.on_reset_selected_password)
        staff_actions.addWidget(self.btn_reset_selected)
        list_layout.addLayout(staff_actions)
        layout.addWidget(list_card, 7)
        layout.setStretch(0, 3)
        layout.setStretch(1, 7)
        self.tabs.addTab(self.tab_users, "Staff Access")

    def refresh_employee_table(self):
        self._staff_loaded = False
        self._tasks.run_latest(
            "settings-staff",
            _SETTINGS_CONTROLLER.employees,
            self._apply_employee_table,
            self._staff_load_failed,
        )

    def _apply_employee_table(self, employees):
        self._staff_rows = list(employees)
        self.tbl_users.setUpdatesEnabled(False)
        try:
            self.tbl_users.setRowCount(len(employees))
            for row, item in enumerate(employees):
                _employee_id, username, first_name, last_name, occupation = item
                self.tbl_users.setItem(row, 0, QTableWidgetItem(str(username)))
                self.tbl_users.setItem(row, 1, QTableWidgetItem(f"{first_name} {last_name}".strip()))
                self.tbl_users.setItem(row, 2, QTableWidgetItem(role_label(str(occupation))))
        finally:
            self.tbl_users.setUpdatesEnabled(True)
        self.tbl_users.clearSelection()
        self._update_staff_actions()
        self._staff_loaded = True

    def _update_staff_actions(self):
        row = self.tbl_users.currentRow() if hasattr(self, "tbl_users") else -1
        self.btn_reset_selected.setEnabled(0 <= row < len(self._staff_rows))

    def _staff_load_failed(self, _details: str):
        self._staff_loaded = False
        if self.show_message_box:
            show_toast(self, "Could not load staff accounts. Try again.", ToastType.WARNING)

    def on_create_user(self):
        username = self.txt_new_user.text().strip()
        password = self.txt_new_pass.text()
        first_name = self.txt_new_fname.text().strip()
        last_name = self.txt_new_lname.text().strip()
        role = self.cmb_new_role.currentData() or self.cmb_new_role.currentText()
        if not username or not password or not first_name:
            if self.show_message_box:
                show_toast(self, "Enter a username, password, and first name.", ToastType.WARNING)
            return
        ok, message = _SETTINGS_CONTROLLER.create_employee(username, password, first_name, last_name, occupation=role)
        if ok:
            if self.show_message_box:
                show_toast(self, message, ToastType.SUCCESS)
            self.txt_new_user.clear()
            self.txt_new_pass.clear()
            self.txt_new_fname.clear()
            self.txt_new_lname.clear()
            self._staff_loaded = False
            self.refresh_employee_table()
        elif self.show_message_box:
            QMessageBox.critical(self, "Could Not Add Staff", message)

    def on_reset_selected_password(self):
        row = self.tbl_users.currentRow()
        if row < 0 or row >= len(self._staff_rows):
            if self.show_message_box:
                show_toast(self, "Select a staff account first.", ToastType.WARNING)
            return
        employee_id, username, _first_name, _last_name, _occupation = self._staff_rows[row]
        self.on_reset_user_password(employee_id, username)

    def on_reset_user_password(self, employee_id: int, username: str):
        new_password, accepted = QInputDialog.getText(
            self,
            "Reset Password",
            f"Enter a new password for {username}. Use at least 8 characters:",
            QLineEdit.Password,
        )
        if not accepted or not new_password:
            return
        ok, message = _SETTINGS_CONTROLLER.reset_password(employee_id, new_password)
        if ok:
            if self.show_message_box:
                show_toast(self, message, ToastType.SUCCESS)
        elif self.show_message_box:
            QMessageBox.critical(self, "Could Not Reset Password", message)

    def on_screen_show(self):
        # One small batched read keeps visible general/receipt controls fresh.
        self.load_settings()
        current = self.tabs.currentWidget()
        if current is self.tab_users:
            self._staff_loaded = False
            self.refresh_employee_table()
        elif current is self.tab_technical:
            self._system_loaded = False
            self.refresh_db_health_and_backups()
