#!/usr/bin/env python3
"""Render the reference UI with isolated practice data, without resetting user/demo data.

Run normally for populated screenshots, or with --matrix for the strict size,
theme and text-scale checks. Every invocation uses a new artifacts/ data folder.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', action='store_true')
    args = parser.parse_args()
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    from scripts import demo_mode
    demo_mode.DEMO_DIR = Path(tempfile.mkdtemp(prefix='reference-data-', dir=artifacts)).resolve()
    os.environ['PHARMA_KHAATO_DATA_DIR'] = str(demo_mode.DEMO_DIR)
    if args.matrix:
        from scripts.ui_acceptance_matrix import collect
        sys.argv = [sys.argv[0], '--strict', '--output', 'artifacts/reference-review']
        return collect()

    summary = demo_mode.seed_demo_database()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThreadPool
    from PySide6.QtTest import QTest
    from ui.theme.theme_manager import ThemeManager
    from ui.app.state.session_state import SessionState
    from ui.app.main_window import MainWindow
    from ui.screens.pos_screen import POSScreen, _POS_CONTROLLER
    from ui.screens.inventory_screen import InventoryScreen
    from ui.screens.khatoo_screen import KhatooScreen
    from ui.screens.customer_screen import CustomerScreen
    from ui.screens.settings_screen import SettingsScreen
    from ui.screens.cash_session_screen import CashSessionScreen
    from ui.screens.reports_screen import ReportsScreen
    from ui.screens.returns_screen import ReturnsScreen
    from ui.screens.supplier_accounts import SupplierInvoiceDialog

    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(ThemeManager.build_qss('light', 1.0))
    state = SessionState.get_instance()
    state.set_user({'id': summary['admin_id'], 'username': 'admin', 'occupation': 'Admin'})
    window = MainWindow()
    window.resize(1440, 810)
    output = artifacts / 'reference-review' / 'populated'
    output.mkdir(parents=True, exist_ok=True)

    def settle():
        for _ in range(250):
            app.processEvents()
            QTest.qWait(20)
            if QThreadPool.globalInstance().activeThreadCount() == 0:
                app.processEvents()
                return
        raise RuntimeError('Screen refresh did not finish within five seconds')

    def capture(name, widget=window):
        settle()
        if not widget.grab().save(str(output / f'{name}.png')):
            raise RuntimeError(f'Could not save {name}')
        print(f'Captured {name}')

    try:
        screens = [('pos', POSScreen), ('inventory', InventoryScreen),
                   ('customers', CustomerScreen), ('khatoo', KhatooScreen),
                   ('cash_session', CashSessionScreen), ('reports', ReportsScreen),
                   ('returns', ReturnsScreen), ('settings', SettingsScreen)]
        for key, screen_type in screens:
            screen = screen_type(show_message_box=False)
            window.router.register_screen(key, screen)
            window.on_nav_clicked(key)
            window.show()
            settle()
            if key == 'pos':
                for term in ('Paracetamol', 'Amoxicillin', 'Cetirizine', 'ORS', 'Ibuprofen'):
                    matches = _POS_CONTROLLER.search_products(term)
                    if matches:
                        screen._add_result_tuple_to_cart(matches[0])
                screen.txt_search.setText('a')
                screen.perform_live_search()
            elif key == 'inventory':
                screen.tbl_products.selectRow(0)
                screen.tabs.setCurrentIndex(3)
                settle()
                screen.batch_browser.table.selectRow(0)
                capture('batches')
                window.resize(855, 440)
                capture('batches-compact')
                if window.width() > 855 or window.height() > 440:
                    raise AssertionError('Batch browser enlarged the compact desktop')
                window.resize(1440, 810)
                screen.tabs.setCurrentIndex(0)
                invoice = SupplierInvoiceDialog(1, 'Practice supplier', window)
                invoice.resize(1200, 760)
                invoice.show()
                settle()
                invoice.reference.setText('REFERENCE-PREVIEW')
                invoice.quantity.setValue(3)
                invoice.cost.setValue(25)
                invoice.expiry.setText('12/2099')
                invoice.lot.setText('DEMO-001')
                invoice.add.click()
                invoice.paid.setValue(20)
                capture('receiving', invoice)
                invoice.hide()
                invoice.deleteLater()
            elif key == 'khatoo':
                screen.tbl_ledger.selectRow(0)
            elif key == 'customers' and hasattr(screen, 'tbl_customers'):
                screen.tbl_customers.selectRow(0)
            elif key == 'returns':
                screen.txt_sale_id.setText(str(summary['sale_ids']['cash']))
                screen.find_sale()
                settle()
                for field in screen._qty_widgets.values():
                    field.setValue(min(1, field.maximum()))
            capture(key)
        print(f'Review screenshots: {output}')
        return 0
    finally:
        QThreadPool.globalInstance().waitForDone(10000)
        app.processEvents()
        window.hide()


if __name__ == '__main__':
    raise SystemExit(main())
