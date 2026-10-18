"""Installed-build verification in a disposable shop, never the operator's data."""

def run():
    import os
    import tempfile
    import importlib
    from pathlib import Path
    from core.path_manager import PathManager
    from core import db_engine

    previous = os.environ.get('PHARMA_KHAATO_DATA_DIR')
    previous_server = os.environ.get('PHARMA_KHAATO_SHOP_SERVER')
    with tempfile.TemporaryDirectory(prefix='pharma-installed-check-') as directory:
        db_engine.reset_thread_connections()
        os.environ['PHARMA_KHAATO_DATA_DIR'] = directory
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        # Explicit environment-based counter routing must not reach a real shop.
        os.environ['PHARMA_KHAATO_SHOP_SERVER'] = '1'
        PathManager._BASE_DATA_DIR = None
        try:
            from core.auth_service import register_initial_admin, login_user
            from core.inventory_service import register_supplier, register_product, add_batch, search_products
            from core.cash_session_service import open_session
            from core.pos_service import CheckoutRequest, POSTransactionEngine
            from core.settings_service import SettingsService
            from core.receipt_service import receipt_for_sale
            from core.lan_service import ensure_shop_certificate
            from PySide6.QtWidgets import QApplication
            from PySide6.QtTest import QTest
            from ui.app.state.session_state import SessionState

            def require(result):
                if not result[0]:
                    raise RuntimeError(str(result[1]))
                return result[1]

            require(register_initial_admin('installed-check', 'CheckOnly-8472', 'Installed', 'Check'))
            result = login_user('installed-check', 'CheckOnly-8472')
            if not result:
                raise RuntimeError('Installed sign-in failed')
            employee, first, last, role = result
            user = {'id': employee, 'username': 'installed-check', 'first_name': first, 'last_name': last, 'occupation': role}
            assert SettingsService.update_settings({'default_tax_rate': '0', 'receipt_auto_print': '0'}, actor_id=employee)
            require(register_supplier('Check Supplier', '03000000000'))
            require(register_product('Check Medicine 500mg', 15, barcode='CHECK-001'))
            require(add_batch(1, 1, 20, '2099-12-31', employee_id=employee, sale_price=15))
            require(open_session(employee, 100))
            product = search_products('CHECK-001')[0]
            request = CheckoutRequest('WALKIN', employee, [{'prod_id':product[0], 'name':product[1], 'price':15, 'qty':2, 'batch_id':product[3], 'subtotal':30}], total=30, cash_received=50, checkout_token='installed-check-once')
            sale = POSTransactionEngine.process_checkout(request)
            if not sale.success or sale.change_due != 20:
                raise RuntimeError(sale.message)
            repeated = POSTransactionEngine.process_checkout(request)
            assert repeated.purchase_id == sale.purchase_id and repeated.duplicate
            assert receipt_for_sale(sale.purchase_id)['receipt_text']
            ensure_shop_certificate(Path(directory) / 'tls', ['localhost'])
            app = QApplication.instance() or QApplication([])
            SessionState.get_instance().set_user(user)
            screens = [
                ('pos_screen', 'POSScreen'), ('inventory_screen', 'InventoryScreen'),
                ('customer_screen', 'CustomerScreen'), ('khatoo_screen', 'KhatooScreen'),
                ('cash_session_screen', 'CashSessionScreen'), ('reports_screen', 'ReportsScreen'),
                ('returns_screen', 'ReturnsScreen'), ('settings_screen', 'SettingsScreen'),
            ]
            widgets = []
            for module, name in screens:
                widget = getattr(importlib.import_module('ui.screens.' + module), name)(show_message_box=False)
                widget.resize(1024, 768)
                widget.show()
                widgets.append(widget)
                QTest.qWait(100)
                app.processEvents()
            from types import SimpleNamespace
            from config import ApplicationSettings
            from ui.dialogs.about_dialog import AboutDialog
            from ui.dialogs.update_dialog import UpdateDialog
            about = AboutDialog(SimpleNamespace(poll=lambda **kwargs: None))
            notice = UpdateDialog({'latest_version': '99.0.0', 'current_version': ApplicationSettings.APP_VERSION,
                                  'release_notes': 'Installed dialog verification only.',
                                  'download_url': 'https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases'})
            for dialog in (about, notice):
                dialog.show()
                app.processEvents()
                dialog.close()
            from PySide6.QtCore import QThreadPool
            QThreadPool.globalInstance().waitForDone(15000)
            app.processEvents()
            for widget in widgets:
                widget.close()
            SessionState.get_instance().clear_user()
            print('PASS: installed migrations, login, stock, cash, checkout/retry, receipt, TLS certificate, eight screens, credits and update dialogs')
            return 0
        finally:
            db_engine.reset_thread_connections()
            PathManager._BASE_DATA_DIR = None
            if previous_server is None:
                os.environ.pop('PHARMA_KHAATO_SHOP_SERVER', None)
            else:
                os.environ['PHARMA_KHAATO_SHOP_SERVER'] = previous_server
            if previous is None:
                os.environ.pop('PHARMA_KHAATO_DATA_DIR', None)
            else:
                os.environ['PHARMA_KHAATO_DATA_DIR'] = previous
