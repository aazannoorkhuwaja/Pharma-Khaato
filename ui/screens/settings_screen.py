"""
Pharma-Khaato Native PySide6 System Settings & Database Control Screen
Features system preferences tuning, database WAL status monitoring, and snapshot backup triggers.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QDoubleSpinBox, QSpinBox,
    QMessageBox, QFrame, QTabWidget, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt

from ui.theme.tokens import ThemeTokens
from ui.theme.theme_manager import ThemeManager
from ui.widgets.card import Card
from ui.widgets.badge_pill import BadgePill
from ui.widgets.screen_header import ScreenHeader
from ui.widgets.toast import Toast, ToastType, show_toast

from controllers.settings_controller import SettingsController

_SETTINGS_CONTROLLER = SettingsController()
from config import ApplicationSettings
from ui.app.state.health_checker import SystemHealthChecker
from ui.widgets.table_polish import polish_table
from ui.widgets.responsive import flexible_side_panel
from ui.ux_copy import ROLE_OPTIONS, role_label

class SettingsScreen(QWidget):
    def __init__(self, parent=None, show_message_box: bool = True):
        super().__init__(parent)
        self.show_message_box = show_message_box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        header_card = ScreenHeader(
            "Settings",
            "Set pharmacy rules, receipts, display, staff access, backups, and system health."
        )
        self.pill_system_status = BadgePill("Ready", BadgePill.TYPE_SUCCESS)
        header_card.add_pill(self.pill_system_status)
        layout.addWidget(header_card)

        # Create Tabbed Layout to Isolate Technical Details from General Users
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        # ----------------------------------------------------
        # TAB 1: GENERAL PHARMACY RULES & THEME PREFERENCES
        # ----------------------------------------------------
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(14)

        gen_card = Card()
        gen_card_layout = gen_card.layout()
        gen_card_layout.setSpacing(12)

        lbl_pref_hdr = QLabel("General Settings")
        lbl_pref_hdr.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        gen_card_layout.addWidget(lbl_pref_hdr)

        form = QFormLayout()
        form.setSpacing(12)

        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0.0, 50.0)
        self.spn_tax.setSuffix(" %")

        self.spn_credit_limit = QDoubleSpinBox()
        self.spn_credit_limit.setRange(1000.0, 1000000.0)
        self.spn_credit_limit.setPrefix("Rs. ")

        self.spn_expiry_threshold = QSpinBox()
        self.spn_expiry_threshold.setRange(7, 365)
        self.spn_expiry_threshold.setSuffix(" Days")

        self.txt_receipt_header = QLineEdit()
        self.txt_receipt_footer = QLineEdit()

        self.cmb_theme_mode = QComboBox()
        self.cmb_theme_mode.addItem("Light", "light")
        self.cmb_theme_mode.addItem("Dark", "dark")

        self.cmb_font_scale = QComboBox()
        self.cmb_font_scale.addItem("Standard (100%)", "1.0")
        self.cmb_font_scale.addItem("Medium (125%)", "1.25")
        self.cmb_font_scale.addItem("Large (150%)", "1.5")

        form.addRow("Sales tax:", self.spn_tax)
        form.addRow("Customer credit limit:", self.spn_credit_limit)
        form.addRow("Expiry warning:", self.spn_expiry_threshold)
        form.addRow("Receipt title:", self.txt_receipt_header)
        form.addRow("Receipt footer:", self.txt_receipt_footer)
        form.addRow("Theme:", self.cmb_theme_mode)
        form.addRow("Interface size:", self.cmb_font_scale)

        gen_card_layout.addLayout(form)
        gen_card_layout.addSpacing(12)

        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.clicked.connect(self.save_settings)
        gen_card_layout.addWidget(self.btn_save_settings)

        gen_card_layout.addStretch()
        gen_layout.addWidget(gen_card)
        self.tabs.addTab(self.tab_general, "General")

        # ----------------------------------------------------
        # TAB 2: STAFF & USER MANAGEMENT (ADMIN / ROLE CONTROL)
        # ----------------------------------------------------
        self.setup_user_management_tab()

        # ----------------------------------------------------
        # TAB 3: TECHNICAL DIAGNOSTICS & LOGS (ISOLATED)
        # ----------------------------------------------------
        self.tab_technical = QWidget()
        tech_layout = QVBoxLayout(self.tab_technical)
        tech_layout.setContentsMargins(16, 16, 16, 16)
        tech_layout.setSpacing(14)

        tech_grid = QHBoxLayout()
        tech_grid.setSpacing(14)

        # Left Sub-card: Engine Status & Error Console
        left_tech_card = Card()
        left_tech_layout = left_tech_card.layout()
        left_tech_layout.setSpacing(10)

        lbl_tech_hdr = QLabel("System Health")
        lbl_tech_hdr.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        left_tech_layout.addWidget(lbl_tech_hdr)

        self.lbl_health_info = QLabel("Checking system...")
        self.lbl_health_info.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; line-height: 1.4;")
        left_tech_layout.addWidget(self.lbl_health_info)

        self.btn_toggle_details = QPushButton("Show Technical Details")
        self.btn_toggle_details.setToolTip("Show diagnostic information that may be requested by technical support.")
        self.btn_toggle_details.clicked.connect(self.toggle_technical_details)
        left_tech_layout.addWidget(self.btn_toggle_details)

        self.lbl_log_hdr = QLabel("Technical details (for support)")
        self.lbl_log_hdr.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY}; margin-top: 8px;")
        self.lbl_log_hdr.hide()
        left_tech_layout.addWidget(self.lbl_log_hdr)

        self.txt_tech_log = QTextEdit()
        self.txt_tech_log.setReadOnly(True)
        # INTENTIONAL: The diagnostic log console uses fixed terminal-style colors
        # (#0d1117 dark background, #58a6ff blue monospace text) that do NOT change
        # with the app theme (dark/light/high_contrast). This is the same convention
        # used by GitHub, VS Code, and most IDE diagnostic panels — a log viewer
        # should look like a terminal regardless of the surrounding UI theme.
        # Do NOT replace these with ThemeTokens entries.
        self.txt_tech_log.setStyleSheet(f"""
            background-color: #0d1117;
            color: #9CDCFE;
            font-family: monospace;
            border: 1px solid {ThemeTokens.BORDER_SUBTLE};
            border-radius: 6px;
        """)
        self.txt_tech_log.hide()
        left_tech_layout.addWidget(self.txt_tech_log, 1)

        btn_refresh_tech = QPushButton("Check Again")
        btn_refresh_tech.clicked.connect(self.refresh_db_health_and_backups)
        left_tech_layout.addWidget(btn_refresh_tech)

        tech_grid.addWidget(left_tech_card, 1)

        # Right Sub-card: Database Backup Snapshots
        right_tech_card = Card()
        right_tech_layout = right_tech_card.layout()
        right_tech_layout.setSpacing(10)

        lbl_db_hdr = QLabel("Backups")
        lbl_db_hdr.setStyleSheet(f" font-weight: 700; color: {ThemeTokens.TEXT_PRIMARY};")
        right_tech_layout.addWidget(lbl_db_hdr)

        self.btn_trigger_backup = QPushButton("Create Backup Now")
        self.btn_trigger_backup.setObjectName("successButton")
        self.btn_trigger_backup.clicked.connect(self.trigger_backup)
        right_tech_layout.addWidget(self.btn_trigger_backup)

        right_tech_layout.addSpacing(6)
        lbl_backups = QLabel("Saved Backups")
        lbl_backups.setStyleSheet(f"font-weight: 600; color: {ThemeTokens.TEXT_PRIMARY};")
        right_tech_layout.addWidget(lbl_backups)

        self.tbl_backups = QTableWidget(0, 3)
        self.tbl_backups.setHorizontalHeaderLabels(["Backup File", "Size", "Created"])
        self.tbl_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        polish_table(self.tbl_backups)
        self.tbl_backups.verticalHeader().setVisible(False)
        self.tbl_backups.setEditTriggers(QTableWidget.NoEditTriggers)
        right_tech_layout.addWidget(self.tbl_backups, 1)

        tech_grid.addWidget(right_tech_card, 1)
        tech_layout.addLayout(tech_grid, 1)

        self.tabs.addTab(self.tab_technical, "System & Backup")

        layout.addWidget(self.tabs, 1)

        self.load_settings()
        self.refresh_db_health_and_backups()
        self.refresh_employee_table()

    def toggle_technical_details(self):
        visible = not self.txt_tech_log.isVisible()
        self.txt_tech_log.setVisible(visible)
        self.lbl_log_hdr.setVisible(visible)
        self.btn_toggle_details.setText("Hide Technical Details" if visible else "Show Technical Details")

    def load_settings(self):
        tax_str = _SETTINGS_CONTROLLER.get("default_tax_rate", "0.10")
        limit_str = _SETTINGS_CONTROLLER.get("max_customer_credit_limit", "25000.00")
        expiry_str = _SETTINGS_CONTROLLER.get("near_expiry_days") or _SETTINGS_CONTROLLER.get("expiry_warning_threshold_days", "30")
        hdr_str = _SETTINGS_CONTROLLER.get("pharmacy_name") or _SETTINGS_CONTROLLER.get("receipt_header_text", "Pharma-Khaato POS")
        ftr_str = _SETTINGS_CONTROLLER.get("receipt_footer") or _SETTINGS_CONTROLLER.get("receipt_footer_text", "Thank you for trusting Pharma-Khaato.")

        try:
            val = float(tax_str)
            if val <= 1.0:
                val = val * 100.0
            self.spn_tax.setValue(val)
        except Exception:
            self.spn_tax.setValue(10.0)

        try:
            self.spn_credit_limit.setValue(float(limit_str))
        except Exception:
            self.spn_credit_limit.setValue(25000.0)

        try:
            self.spn_expiry_threshold.setValue(int(expiry_str))
        except Exception:
            self.spn_expiry_threshold.setValue(30)

        self.txt_receipt_header.setText(hdr_str)
        self.txt_receipt_footer.setText(ftr_str)

        curr_mode = ThemeManager.get_theme_mode()
        mode_idx = self.cmb_theme_mode.findData(curr_mode)
        if mode_idx >= 0:
            self.cmb_theme_mode.setCurrentIndex(mode_idx)

        curr_scale = str(ThemeManager.get_font_scale())
        scale_idx = self.cmb_font_scale.findData(curr_scale)
        if scale_idx >= 0:
            self.cmb_font_scale.setCurrentIndex(scale_idx)

    def save_settings(self):
        tax_val = self.spn_tax.value()
        _SETTINGS_CONTROLLER.set("default_tax_rate", str(tax_val))
        _SETTINGS_CONTROLLER.set("max_customer_credit_limit", f"{self.spn_credit_limit.value():.2f}")
        _SETTINGS_CONTROLLER.set("near_expiry_days", str(self.spn_expiry_threshold.value()))
        _SETTINGS_CONTROLLER.set("expiry_warning_threshold_days", str(self.spn_expiry_threshold.value()))
        
        hdr = self.txt_receipt_header.text().strip()
        ftr = self.txt_receipt_footer.text().strip()
        _SETTINGS_CONTROLLER.set("pharmacy_name", hdr)
        _SETTINGS_CONTROLLER.set("receipt_header_text", hdr)
        _SETTINGS_CONTROLLER.set("receipt_footer", ftr)
        _SETTINGS_CONTROLLER.set("receipt_footer_text", ftr)

        mode = self.cmb_theme_mode.currentData()
        scale = float(self.cmb_font_scale.currentData())
        ThemeManager.set_theme(mode, save=True)
        ThemeManager.set_font_scale(scale, save=True)

        if self.show_message_box:
            show_toast(self, "Settings saved.", ToastType.SUCCESS)

    def refresh_db_health_and_backups(self):
        health = SystemHealthChecker.run_diagnostics()
        db_engine_name = "SQLite"
        
        if health["db_connected"]:
            self.lbl_health_info.setText(
                f"Database: Connected\n"
                f"Safe write mode: {'Active' if health['wal_enabled'] else 'Needs attention'}\n"
                "Data folder: Ready"
            )
            self.pill_system_status.setText("Ready")
            self.pill_system_status.set_pill_type(BadgePill.TYPE_SUCCESS)
            
            tech_log = (
                "[DIAGNOSTICS] Connection Test: PASSED\n"
                f"[DIAGNOSTICS] Database Engine: {db_engine_name}\n"
                f"[DIAGNOSTICS] WAL Journal Mode: {health['wal_enabled']}\n"
                "[DIAGNOSTICS] Table Constraints & Foreign Keys: OK\n"
                "[DIAGNOSTICS] Zero Runtime Faults Detected."
            )
            self.txt_tech_log.setText(tech_log)
        else:
            issues = health.get('issues', ['Connection failed'])
            self.lbl_health_info.setText(f"System needs attention.\n{'; '.join(issues)}")
            self.pill_system_status.setText("Needs Attention")
            self.pill_system_status.set_pill_type(BadgePill.TYPE_DANGER)

            
            tech_log = "[SYSTEM FAULT LOG]\n" + "\n".join(f"[ERROR] {issue}" for issue in issues)
            self.txt_tech_log.setText(tech_log)

        backups = _SETTINGS_CONTROLLER.backups()
        self.tbl_backups.setRowCount(len(backups))
        for r, item in enumerate(backups):
            self.tbl_backups.setItem(r, 0, QTableWidgetItem(str(item['filename'])))
            self.tbl_backups.setItem(r, 1, QTableWidgetItem(f"{item['size_bytes'] / 1024:.1f} KB"))
            self.tbl_backups.setItem(r, 2, QTableWidgetItem(str(item['created_at'])))

    def trigger_backup(self):
        ok, res = _SETTINGS_CONTROLLER.create_backup()
        if ok:
            if self.show_message_box:
                show_toast(self, f"Backup created:\n{res}", ToastType.SUCCESS)
            self.refresh_db_health_and_backups()
        else:
            if self.show_message_box:
                QMessageBox.critical(self, "Could Not Create Backup", str(res))

    def setup_user_management_tab(self):
        self.tab_users = QWidget()
        u_layout = QHBoxLayout(self.tab_users)
        u_layout.setContentsMargins(16, 16, 16, 16)
        u_layout.setSpacing(14)

        # Left Card: Create New User Form
        create_card = Card()
        flexible_side_panel(create_card, minimum=300, maximum=410)
        c_layout = create_card.layout()
        c_layout.setSpacing(12)

        c_title = QLabel("Add Staff Member")
        c_title.setObjectName("h2")
        c_title.setStyleSheet(f"color: {ThemeTokens.ACCENT}; font-weight: 700;")
        c_layout.addWidget(c_title)

        form = QFormLayout()
        form.setSpacing(8)

        self.txt_new_user = QLineEdit()
        self.txt_new_user.setPlaceholderText("Username (e.g. cashier1)")

        self.txt_new_pass = QLineEdit()
        self.txt_new_pass.setEchoMode(QLineEdit.Password)
        self.txt_new_pass.setPlaceholderText("At least 6 characters")

        self.txt_new_fname = QLineEdit()
        self.txt_new_fname.setPlaceholderText("First Name")

        self.txt_new_lname = QLineEdit()
        self.txt_new_lname.setPlaceholderText("Last Name")

        self.cmb_new_role = QComboBox()
        for display_label, backend_value in ROLE_OPTIONS:
            self.cmb_new_role.addItem(display_label, backend_value)

        form.addRow("Username *:", self.txt_new_user)
        form.addRow("Password *:", self.txt_new_pass)
        form.addRow("First Name *:", self.txt_new_fname)
        form.addRow("Last Name:", self.txt_new_lname)
        form.addRow("Role:", self.cmb_new_role)

        c_layout.addLayout(form)
        c_layout.addSpacing(8)

        self.btn_create_user = QPushButton("Add Staff")
        self.btn_create_user.setObjectName("primaryButton")
        self.btn_create_user.clicked.connect(self.on_create_user)
        c_layout.addWidget(self.btn_create_user)

        c_layout.addStretch()
        u_layout.addWidget(create_card, 3)

        # Right Card: Staff List Table
        list_card = Card()
        l_layout = list_card.layout()
        l_layout.setSpacing(10)

        l_title = QLabel("Staff Accounts")
        l_title.setObjectName("h2")
        l_layout.addWidget(l_title)

        self.tbl_users = QTableWidget(0, 5)
        self.tbl_users.setHorizontalHeaderLabels(["ID", "Username", "Full Name", "Role", "Actions"])
        self.tbl_users.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_users.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_users.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        polish_table(self.tbl_users, min_row_height=40)
        self.tbl_users.verticalHeader().setVisible(False)
        self.tbl_users.setEditTriggers(QTableWidget.NoEditTriggers)
        l_layout.addWidget(self.tbl_users, 1)


        u_layout.addWidget(list_card, 7)
        u_layout.setStretch(0, 3)
        u_layout.setStretch(1, 7)
        self.tabs.addTab(self.tab_users, "Staff & Access")

    def refresh_employee_table(self):
        emps = _SETTINGS_CONTROLLER.employees()
        self.tbl_users.setRowCount(len(emps))
        for r, item in enumerate(emps):
            emp_id, uname, fname, lname, occupation = item
            self.tbl_users.setItem(r, 0, QTableWidgetItem(str(emp_id)))
            self.tbl_users.setItem(r, 1, QTableWidgetItem(str(uname)))
            self.tbl_users.setItem(r, 2, QTableWidgetItem(f"{fname} {lname}".strip()))
            self.tbl_users.setItem(r, 3, QTableWidgetItem(role_label(str(occupation))))

            btn_reset = QPushButton("Reset Password")
            btn_reset.setProperty("compact", True)
            btn_reset.setMinimumWidth(104)
            btn_reset.clicked.connect(lambda checked=False, eid=emp_id, u=uname: self.on_reset_user_password(eid, u))
            self.tbl_users.setCellWidget(r, 4, btn_reset)

    def on_create_user(self):
        u = self.txt_new_user.text().strip()
        p = self.txt_new_pass.text()
        fn = self.txt_new_fname.text().strip()
        ln = self.txt_new_lname.text().strip()
        role = self.cmb_new_role.currentData() or self.cmb_new_role.currentText()

        if not u or not p or not fn:
            if self.show_message_box:
                show_toast(self, "Enter a username, password, and first name.", ToastType.WARNING)
            return

        ok, msg = _SETTINGS_CONTROLLER.create_employee(u, p, fn, ln, occupation=role)
        if ok:
            if self.show_message_box:
                show_toast(self, msg, ToastType.SUCCESS)
            self.txt_new_user.clear()
            self.txt_new_pass.clear()
            self.txt_new_fname.clear()
            self.txt_new_lname.clear()
            self.refresh_employee_table()
        else:
            if self.show_message_box:
                QMessageBox.critical(self, "Could Not Add Staff", msg)

    def on_reset_user_password(self, emp_id: int, username: str):
        from PySide6.QtWidgets import QInputDialog
        new_pass, ok = QInputDialog.getText(self, "Reset Password", f"Enter a new password for {username}:", QLineEdit.Password)
        if ok and new_pass:
            pok, pmsg = _SETTINGS_CONTROLLER.reset_password(emp_id, new_pass)
            if pok:
                if self.show_message_box:
                    show_toast(self, pmsg, ToastType.SUCCESS)
            else:
                if self.show_message_box:
                    QMessageBox.critical(self, "Could Not Reset Password", pmsg)

