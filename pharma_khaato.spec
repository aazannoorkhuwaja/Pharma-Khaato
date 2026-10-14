# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

BASE_DIR = os.path.dirname(os.path.abspath('__file__'))

datas = [
    ('schema_sqlite.sql', '.'),
    ('migrations/*.sql', 'migrations'),
    ('.env.example', '.'),
    ('receipts/.gitkeep', 'receipts'),
]

binaries = []

# Several product modules are imported lazily so normal startup stays fast.
# Keep the packaged build explicit: a release must contain every major screen
# and every service reached through MVC facades/background tasks.
hiddenimports = [
    'sqlite3',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    'core.audit_service',
    'core.auth_service',
    'core.backup_service',
    'core.cash_query_service',
    'core.cash_session_service',
    'core.checkout_idempotency_service',
    'core.credit_payment_service',
    'core.credit_query_service',
    'core.customer_directory_service',
    'core.customer_service',
    'core.data_revision',
    'core.db_engine',
    'core.error_handler',
    'core.health_service',
    'core.hold_sale_service',
    'core.inventory_query_service',
    'core.inventory_service',
    'core.logger',
    'core.manager_auth_service',
    'core.migration_manager',
    'core.path_manager',
    'core.permission_service',
    'core.pos_service',
    'core.product_search_service',
    'core.readiness_service',
    'core.receipt_service',
    'core.reports_service',
    'core.return_service',
    'core.settings_service',
    'core.support_service',
    'core.version_service',
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
    'ui.app.async_tasks',
    'ui.app.main_window',
    'ui.app.router',
    'ui.app.state.session_state',
    'ui.app.state.health_checker',
    'ui.theme.tokens',
    'ui.theme.typography',
    'ui.theme.theme_manager',
    'ui.theme.layout',
    'ui.widgets.hotkey_badge',
    'ui.widgets.table_polish',
    'ui.widgets.screen_header',
    'ui.widgets.responsive',
    'ui.widgets.badge_pill',
    'ui.widgets.card',
    'ui.widgets.glass_card',
    'ui.widgets.pos_models',
    'ui.widgets.pos_widgets',
    'ui.widgets.toast',
    'ui.screens.first_run_wizard',
    'ui.screens.login_screen',
    'ui.screens.pos_screen',
    'ui.screens.inventory_screen',
    'ui.screens.customer_screen',
    'ui.screens.khatoo_screen',
    'ui.screens.cash_session_screen',
    'ui.screens.reports_screen',
    'ui.screens.returns_screen',
    'ui.screens.settings_screen',
]

excluded_modules = [
    'pytest',
    'pytest_qt',
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
