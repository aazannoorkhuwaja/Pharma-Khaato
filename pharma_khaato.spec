# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

BASE_DIR = os.path.dirname(os.path.abspath('__file__'))

datas = [
    ('schema_sqlite.sql', '.'),
    ('migrations/*.sql', 'migrations'),
    ('.env.example', '.'),
    ('receipts/.gitkeep', 'receipts'),
]

binaries = []

hiddenimports = [
    'sqlite3',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'core.audit_service',
    'core.auth_service',
    'core.backup_service',
    'core.cash_session_service',
    'core.customer_service',
    'core.db_engine',
    'core.hold_sale_service',
    'core.inventory_service',
    'core.logger',
    'core.migration_manager',
    'core.path_manager',
    'core.pos_service',
    'core.receipt_service',
    'core.reports_service',
    'core.settings_service',
    'core.health_service',
    'models.services',
    'controllers.application_controller',
    'controllers.auth_controller',
    'controllers.cash_session_controller',
    'controllers.customer_controller',
    'controllers.inventory_controller',
    'controllers.khatoo_controller',
    'controllers.manager_auth_controller',
    'controllers.pos_controller',
    'controllers.reports_controller',
    'controllers.settings_controller',
    'ui.app.application',
    'ui.app.main_window',
    'ui.app.router',
    'ui.app.state.session_state',
    'ui.app.state.health_checker',
    'ui.theme.tokens',
    'ui.theme.typography',
    'ui.theme.theme_manager',
    'ui.widgets.hotkey_badge',
    'ui.widgets.table_polish',
    'ui.widgets.screen_header',
    'ui.widgets.responsive',
    'ui.theme.layout',
    'ui.widgets.badge_pill',
    'ui.widgets.glass_card',
    'ui.screens.first_run_wizard',
    'ui.screens.login_screen',
    'ui.screens.pos_screen',
    'ui.screens.inventory_screen',
    'ui.screens.customer_screen',
    'ui.screens.khatoo_screen',
    'ui.screens.cash_session_screen',
    'ui.screens.reports_screen',
    'ui.screens.settings_screen',
]

excluded_modules = [
    'pytest',
    'unittest',
    'pyinstaller',
]

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pharma_khaato',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pharma_khaato',
)
