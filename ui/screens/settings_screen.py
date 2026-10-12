"""Pharmacy settings, staff access, backups, and system status."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
    QDoubleSpinBox, QSpinBox, QMessageBox, QTabWidget, QTextEdit,
    QComboBox, QInputDialog,
)

from ui.theme.tokens import ThemeTokens
from ui.theme.theme_manager import ThemeManager
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import ToastType, show_toast
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import flexible_side_panel
from ui.ux_copy import ROLE_OPTIONS, role_label
from ui.app.state.health_checker import SystemHealthChecker
from controllers.settings_controller import SettingsController

_SETTINGS_CONTROLLER = SettingsController()


class SettingsScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Settings",
            "Manage pharmacy rules, receipts, display, staff access, backups, and system status."
        )
        self.pill_system_status = BadgePill("Checking", BadgePill.TYPE_INFO)
        header_card.add_pill(self.pill_system_status)
        layout.addWidget(header_card)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        self._setup_general_tab()
        self.setup_user_management_tab()
        self._setup_system_tab()

        layout.addWidget(self.tabs, 1)

        self.load_settings()
        self.refresh_db_health_and_backups()
        self.refresh_employee_table()

    def _setup_general_tab(self):
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(14)

        card = Card()
        card_layout = card.layout()
        card_layout.setSpacing(12)

        title = QLabel("General Settings")
        title.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
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

        self.txt_receipt_header = QLineEdit()
        self.txt_receipt_header.setPlaceholderText("Pharmacy name shown on receipts")
        self.txt_receipt_footer = QLineEdit()
        self.txt_receipt_footer.setPlaceholderText("Short message shown at the bottom of receipts")

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
        form.addRow("Receipt title:", self.txt_receipt_header)
        form.addRow("Receipt footer:", self.txt_receipt_footer)
        form.addRow("Theme:", self.cmb_theme_mode)
        form.addRow("Interface size:", self.cmb_font_scale)
        card_layout.addLayout(form)

        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.clicked.connect(self.save_settings)
        card_layout.addWidget(self.btn_save_settings)
        card_layout.addStretch()

        gen_layout.addWidget(card)
        self.tabs.addTab(self.tab_general, "General")

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

        title = QLabel("System Status")
        title.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        status_layout.addWidget(title)

        self.lbl_health_info = QLabel("Checking system...")
        self.lbl_health_info.setWordWrap(True)
        self.lbl_health_info.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY};")
        status_layout.addWidget(self.lbl_health_info)

        self.btn_toggle_details = QPushButton("Show Technical Details")
        self.btn_toggle_details.setToolTip(
            "Show diagnostic information that technical support may ask for."
        )
        self.btn_toggle_details.clicked.connect(self.toggle_technical_details)
        status_layout.addWidget(self.btn_toggle_details)

        self.lbl_log_hdr = QLabel("Technical details (for support)")
        self.lbl_log_hdr.setStyleSheet(
            f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; margin-top: 8px;"
        )
        self.lbl_log_hdr.hide()
        status_layout.addWidget(self.lbl_log_hdr)

        self.txt_tech_log = QTextEdit()
        self.txt_tech_log.setReadOnly(True)
        self.txt_tech_log.setAccessibleName("System technical details")
        self.txt_tech_log.setStyleSheet(f"""
            background-color: #0d1117;
            color: #9CDCFE;
            font-family: monospace;
            border: 1px solid {ThemeTokens.BORDER_SUBTLE};
            border-radius: 6px;
        """)
        self.txt_tech_log.hide()
        status_layout.addWidget(self.txt_tech_log, 1)

        btn_refresh = QPushButton("Check System Again")
        btn_refresh.clicked.connect(self.refresh_db_health_and_backups)
        status_layout.addWidget(btn_refresh)
        tech_grid.addWidget(status_card, 1)

        backup_card = Card()
        backup_layout = backup_card.layout()
        backup_layout.setSpacing(10)

        title = QLabel("Backups")
        title.setStyleSheet(f"font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        backup_layout.addWidget(title)

        backup_help = QLabel(
            "Create a backup before major data changes. Backups are checked for database integrity before they are kept."
        )
        backup_help.setWordWrap(True)
        backup_help.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED};")
        backup_layout.addWidget(backup_help)

        self.btn_trigger_backup = QPushButton("Create Backup Now")
        self.btn_trigger_backup.setObjectName("successButton")
        self.btn_trigger_backup.clicked.connect(self.trigger_backup)
        backup_layout.addWidget(self.btn_trigger_backup)

        saved_label = QLabel("Saved Backups")
        saved_label.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY};")
        backup_layout.addWidget(saved_label)

        self.tbl_backups = QTableWidget(0, 3)
        self.tbl_backups.setHorizontalHeaderLabels(["Backup File", "Size", "Created"])
        self.tbl_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        polish_table(self.tbl_backups)
        self.tbl_backups.verticalHeader().setVisible(False)
        self.tbl_backups.setEditTriggers(QTableWidget.NoEditTriggers)
        backup_layout.addWidget(self.tbl_backups, 1)

        tech_grid.addWidget(backup_card, 1)
        tech_layout.addLayout(tech_grid, 1)
        self.tabs.addTab(self.tab_technical, "System & Backup")

    def toggle_technical_details(self):
        visible = not self.txt_tech_log.isVisible()
        self.txt_tech_log.setVisible(visible)
        self.lbl_log_hdr.setVisible(visible)
        self.btn_toggle_details.setText(
            "Hide Technical Details" if visible else "Show Technical Details"
        )

    def load_settings(self):
        tax_raw = _SETTINGS_CONTROLLER.get("default_tax_rate", "0.10")
        limit_raw = _SETTINGS_CONTROLLER.get("max_customer_credit_limit", "25000.00")
        expiry_raw = (
            _SETTINGS_CONTROLLER.get("near_expiry_days")
            or _SETTINGS_CONTROLLER.get("expiry_warning_threshold_days", "30")
        )
        receipt_title = (
            _SETTINGS_CONTROLLER.get("pharmacy_name")
            or _SETTINGS_CONTROLLER.get("receipt_header_text", "Pharma-Khaato POS")
        )
        receipt_footer = (
            _SETTINGS_CONTROLLER.get("receipt_footer")
            or _SETTINGS_CONTROLLER.get(
                "receipt_footer_text", "Thank you for trusting Pharma-Khaato."
            )
        )

        try:
            tax_value = float(tax_raw)
            if tax_value <= 1.0:
                tax_value *= 100.0
            self.spn_tax.setValue(tax_value)
        except Exception:
            self.spn_tax.setValue(10.0)

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

        mode_index = self.cmb_theme_mode.findData(ThemeManager.get_theme_mode())
        if mode_index >= 0:
            self.cmb_theme_mode.setCurrentIndex(mode_index)

        scale_index = self.cmb_font_scale.findData(str(ThemeManager.get_font_scale()))
        if scale_index >= 0:
            self.cmb_font_scale.setCurrentIndex(scale_index)

    def save_settings(self):
        receipt_title = self.txt_receipt_header.text().strip()
        receipt_footer = self.txt_receipt_footer.text().strip()
        if not receipt_title:
            show_toast(self, "Enter a receipt title before saving.", ToastType.WARNING)
            return

        values = {
            "default_tax_rate": str(self.spn_tax.value()),
            "max_customer_credit_limit": f"{self.spn_credit_limit.value():.2f}",
            "near_expiry_days": str(self.spn_expiry_threshold.value()),
            "expiry_warning_threshold_days": str(self.spn_expiry_threshold.value()),
            "pharmacy_name": receipt_title,
            "receipt_header_text": receipt_title,
            "receipt_footer": receipt_footer,
            "receipt_footer_text": receipt_footer,
        }
        if not _SETTINGS_CONTROLLER.update(values):
            QMessageBox.critical(
                self,
                "Could Not Save Settings",
                "Some settings could not be saved. Your previous values were kept where possible.",
            )
            return

        ThemeManager.set_theme(self.cmb_theme_mode.currentData(), save=True)
        ThemeManager.set_font_scale(float(self.cmb_font_scale.currentData()), save=True)
        if self.show_message_box:
            show_toast(self, "Settings saved.", ToastType.SUCCESS)

    def refresh_db_health_and_backups(self):
        health = SystemHealthChecker.run_diagnostics()
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
            self.lbl_health_info.setText(
                "Database: Ready\n"
                "Database integrity: Passed\n"
                "Data folders: Writable"
                f"{free_text}"
            )
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
        if issues:
            technical_lines.extend(f"[ISSUE] {issue}" for issue in issues)
        else:
            technical_lines.append("[RESULT] Basic system checks passed.")
        self.txt_tech_log.setText("\n".join(technical_lines))

        backups = _SETTINGS_CONTROLLER.backups()
        self.tbl_backups.setRowCount(len(backups))
        for row, item in enumerate(backups):
            self.tbl_backups.setItem(row, 0, QTableWidgetItem(str(item["filename"])))
            self.tbl_backups.setItem(
                row, 1, QTableWidgetItem(f"{item['size_bytes'] / 1024:.1f} KB")
            )
            self.tbl_backups.setItem(row, 2, QTableWidgetItem(str(item["created_at"])))

    def trigger_backup(self):
        ok, result = _SETTINGS_CONTROLLER.create_backup()
        if ok:
            if self.show_message_box:
                show_toast(
                    self,
                    f"Backup created: {Path(str(result)).name}",
                    ToastType.SUCCESS,
                )
            self.refresh_db_health_and_backups()
        elif self.show_message_box:
            QMessageBox.critical(self, "Could Not Create Backup", str(result))

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

        helper = QLabel(
            "Create a separate account for each person so activity and permissions stay traceable."
        )
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

        self.tbl_users = QTableWidget(0, 4)
        self.tbl_users.setHorizontalHeaderLabels(
            ["Username", "Staff Member", "Role", "Action"]
        )
        self.tbl_users.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_users.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        polish_table(self.tbl_users, min_row_height=40)
        self.tbl_users.verticalHeader().setVisible(False)
        self.tbl_users.setEditTriggers(QTableWidget.NoEditTriggers)
        list_layout.addWidget(self.tbl_users, 1)

        layout.addWidget(list_card, 7)
        layout.setStretch(0, 3)
        layout.setStretch(1, 7)
        self.tabs.addTab(self.tab_users, "Staff & Access")

    def refresh_employee_table(self):
        employees = _SETTINGS_CONTROLLER.employees()
        self.tbl_users.setRowCount(len(employees))
        for row, item in enumerate(employees):
            employee_id, username, first_name, last_name, occupation = item
            self.tbl_users.setItem(row, 0, QTableWidgetItem(str(username)))
            self.tbl_users.setItem(
                row,
                1,
                QTableWidgetItem(f"{first_name} {last_name}".strip()),
            )
            self.tbl_users.setItem(row, 2, QTableWidgetItem(role_label(str(occupation))))

            button = QPushButton("Reset Password")
            button.setProperty("compact", True)
            button.setMinimumWidth(112)
            button.setAccessibleName(f"Reset password for {username}")
            button.clicked.connect(
                lambda checked=False, eid=employee_id, user=username:
                self.on_reset_user_password(eid, user)
            )
            self.tbl_users.setCellWidget(row, 3, button)

    def on_create_user(self):
        username = self.txt_new_user.text().strip()
        password = self.txt_new_pass.text()
        first_name = self.txt_new_fname.text().strip()
        last_name = self.txt_new_lname.text().strip()
        role = self.cmb_new_role.currentData() or self.cmb_new_role.currentText()

        if not username or not password or not first_name:
            if self.show_message_box:
                show_toast(
                    self,
                    "Enter a username, password, and first name.",
                    ToastType.WARNING,
                )
            return

        ok, message = _SETTINGS_CONTROLLER.create_employee(
            username,
            password,
            first_name,
            last_name,
            occupation=role,
        )
        if ok:
            if self.show_message_box:
                show_toast(self, message, ToastType.SUCCESS)
            self.txt_new_user.clear()
            self.txt_new_pass.clear()
            self.txt_new_fname.clear()
            self.txt_new_lname.clear()
            self.refresh_employee_table()
        elif self.show_message_box:
            QMessageBox.critical(self, "Could Not Add Staff", message)

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
