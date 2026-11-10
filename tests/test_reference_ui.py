"""Native behavior checks for the supplied reference layout (no pytest-qt needed)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QThreadPool, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def reference_ui(seeded_shop, admin_emp_id):
    from ui.app.state.session_state import SessionState
    from ui.theme.theme_manager import ThemeManager
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    ThemeManager._current_scale = 1.0
    ThemeManager._current_density = 'standard'
    app.setStyleSheet(ThemeManager.build_qss('light', 1.0))
    state = SessionState.get_instance()
    state.set_user({'id': admin_emp_id, 'username': 'admin', 'occupation': 'Admin'})
    windows = []
    yield app, state, windows
    QThreadPool.globalInstance().waitForDone(10000)
    app.processEvents()
    for window in windows:
        window.hide()
        window.deleteLater()
    app.processEvents()
    state.pending_checkout = None
    state.clear_cart()
    state.set_user(None)
    app.setStyleSheet('')


def settle(app):
    from time import monotonic
    from ui.app.async_tasks import AsyncTaskRunner
    deadline = monotonic() + 10
    while monotonic() < deadline:
        app.processEvents()
        QTest.qWait(15)
        runners = [runner for window in app.topLevelWidgets()
                   for runner in window.findChildren(AsyncTaskRunner)]
        if QThreadPool.globalInstance().activeThreadCount() == 0 and not any(runner._active for runner in runners):
            app.processEvents()
            return
    pytest.fail('UI workers did not finish within ten seconds')


def test_reference_checkout_reflows_and_tenders_remain_exclusive(reference_ui):
    from ui.screens.pos_screen import POSScreen
    app, state, windows = reference_ui
    screen = POSScreen(show_message_box=False)
    windows.append(screen)
    screen.resize(1150, 710)
    screen.show()
    settle(app)
    for index, button in enumerate(screen.payment_choice_buttons):
        button.click()
        assert screen.cmb_pay_method.currentIndex() == index
        assert sum(item.isChecked() for item in screen.payment_choice_buttons) == 1
    state.pending_checkout = {'request': {'checkout_token': 'pending'}}
    screen._set_checkout_locked(True)
    screen.payment_choice_buttons[0].click()
    assert screen.cmb_pay_method.currentIndex() == 4
    assert all(not b.isEnabled() for b in screen.payment_choice_buttons)
    state.pending_checkout = None
    screen._set_checkout_locked(False)
    screen.resize(730, 440)
    settle(app)
    screen.cust_table.setRowCount(3)
    screen.cust_table.show()
    screen.search_results_data = [("preview",)]
    screen.show_search_table()
    settle(app)
    assert screen.height() <= 440, [(w.objectName(), w.size(), w.minimumSizeHint()) for w in (screen, screen._reference_right_card, screen.shift_banner, screen.left_scroll, screen.txt_search)]
    for control in (screen.txt_search, screen.lbl_total, screen.btn_checkout):
        point = control.mapTo(screen, QPoint(0, 0))
        assert point.y() >= 0 and point.y()+control.height() <= screen.height()


def test_product_detail_uses_selected_record(reference_ui):
    from ui.screens.inventory_screen import InventoryScreen
    app, state, windows = reference_ui
    screen = InventoryScreen(show_message_box=False)
    windows.append(screen)
    screen.resize(1150, 710)
    screen.show()
    settle(app)
    screen.tbl_products.selectRow(0)
    settle(app)
    assert screen.lbl_product_name.text() == 'TestMed'
    assert '15.00' in screen.lbl_product_details.text()
    screen.tbl_products.clearSelection()
    settle(app)
    assert screen.lbl_product_name.text() == 'Select a medicine'
    assert not screen.btn_selected_stock.isEnabled()


def test_report_charts_reflect_service_totals(reference_ui):
    from ui.screens.reports_screen import ReportsScreen
    app, state, windows = reference_ui
    screen = ReportsScreen(show_message_box=False)
    windows.append(screen)
    screen.show()
    settle(app)
    assert len(screen.sales_trend.values) == 7
    assert all(value == 0 for _, value in screen.sales_trend.values)
    assert sum(value for _, value in screen.payment_mix.values) == 0
    assert 'Rs.' in screen.payment_mix.accessibleDescription()


def test_cashier_cannot_access_owner_utilities(reference_ui):
    from ui.app.main_window import MainWindow
    app, state, windows = reference_ui
    state.set_user({'id': 1, 'username': 'cashier', 'occupation': 'Salesman'})
    window = MainWindow()
    windows.append(window)
    window.show()
    settle(app)
    for button in (window.btn_printer_setup, window.btn_shop_computers, window.btn_getting_started):
        assert not window.utility_actions[button].isVisible()


def test_quantity_stepper_updates_cart_and_respects_pending_sale(reference_ui):
    from ui.screens.pos_screen import POSScreen, _POS_CONTROLLER
    from PySide6.QtWidgets import QPushButton
    app, state, windows = reference_ui
    screen = POSScreen(show_message_box=False)
    windows.append(screen)
    screen.resize(1150, 710)
    screen.show()
    settle(app)
    screen._add_result_tuple_to_cart(_POS_CONTROLLER.search_products("TestMed")[0])
    settle(app)
    assert state.active_cart[0]["qty"] == 1
    plus = next(button for button in screen.cart_table.cellWidget(0, 3).findChildren(QPushButton) if button.text() == "+")
    plus.click()
    assert state.active_cart[0]["qty"] == 2
    state.pending_checkout = {"request": {"checkout_token": "locked"}}
    screen._set_checkout_locked(True)
    plus = next(button for button in screen.cart_table.cellWidget(0, 3).findChildren(QPushButton) if button.text() == "+")
    plus.click()
    assert state.active_cart[0]["qty"] == 2


def test_supplier_receiving_summary_and_commit_use_real_invoice(reference_ui):
    from ui.screens.supplier_accounts import SupplierInvoiceDialog
    from core.db_engine import get_conn
    app, state, windows = reference_ui
    dialog = SupplierInvoiceDialog(1, 'Sup')
    windows.append(dialog)
    dialog.show()
    settle(app)
    dialog.reference.setText('UI-REFERENCE-001')
    dialog.quantity.setValue(2)
    dialog.cost.setValue(5)
    dialog.expiry.setText('12/2099')
    dialog.add.click()
    assert len(dialog.lines) == 1
    assert dialog.total.text() == 'Invoice: Rs. 10.00'
    dialog.paid.setValue(2)
    assert dialog.balance.text() == 'Balance Due: Rs. 8.00'
    dialog.resize(750, 440)
    settle(app)
    assert dialog.height() <= 440
    position = dialog.save.mapTo(dialog, QPoint(0, 0))
    assert position.y()+dialog.save.height() <= dialog.height()
    dialog.save.click()
    for _ in range(200):
        app.processEvents()
        QTest.qWait(25)
        if not dialog._busy:
            break
    assert not dialog._busy, 'Invoice write did not finish within five seconds'
    assert dialog.result() == 1, dialog.status.text()  # QDialog.DialogCode.Accepted
    cur = get_conn().cursor()
    cur.execute('SELECT SUM(quantity) FROM Batch')
    assert cur.fetchone()[0] == 102


def test_batch_browser_native_filters_and_details(reference_ui):
    from ui.screens.batches_screen import BatchesScreen
    app, state, windows = reference_ui
    screen = BatchesScreen()
    windows.append(screen)
    screen.resize(1150, 650)
    screen.show()
    screen.refresh()
    settle(app)
    assert screen.table.rowCount() == 1
    screen.table.selectRow(0)
    assert screen.selected_name.text() == 'TestMed'
    assert screen.adjust.isEnabled()
    screen.expiry_filter.setCurrentIndex(screen.expiry_filter.findData('expired'))
    screen.timer.stop()
    screen.refresh()
    settle(app)
    assert screen.table.rowCount() == 0
    assert not screen.adjust.isEnabled()


def test_returns_preview_tracks_quantity_and_clears_stale_sale(reference_ui):
    from core.pos_service import confirm_sale
    from ui.screens.returns_screen import ReturnsScreen
    app, state, windows = reference_ui
    ok, message = confirm_sale(None, state.current_user['id'],
        [{'prod_id':1,'name':'TestMed','price':15,'qty':4}],payment_method='Credit Card')
    assert ok, message
    purchase_id = int(message.split('Sale #')[1].split()[0])
    screen = ReturnsScreen(show_message_box=False)
    windows.append(screen)
    screen.show()
    screen.txt_sale_id.setText(str(purchase_id))
    screen.find_sale()
    settle(app)
    assert screen.current_sale is not None
    screen._qty_widgets[1].setValue(2)
    assert screen.lbl_refund_preview.text() == 'Estimated Refund: Rs. 30.00'
    assert 'Credit Card' in screen.lbl_return_tender.text()
    screen.clear_sale()
    assert screen.lbl_refund_preview.text() == 'Estimated Refund: Rs. 0.00'


def test_failed_cash_and_product_reads_leave_loading_state(reference_ui, monkeypatch):
    from ui.screens import cash_session_screen as cash, inventory_screen as inventory
    app, state, windows = reference_ui
    def unavailable(*_args, **_kwargs):
        raise OSError('test connection interrupted')
    monkeypatch.setattr(cash._CASH_CONTROLLER, 'active_session', unavailable)
    drawer = cash.CashSessionScreen(show_message_box=False)
    windows.append(drawer)
    drawer.refresh_all_data()
    settle(app)
    assert all(label.text() == 'Unavailable' for label in drawer.cash_metrics.values())
    screen = inventory.InventoryScreen(show_message_box=False)
    windows.append(screen)
    screen.show()
    settle(app)
    monkeypatch.setattr(inventory._INVENTORY_CONTROLLER, 'product_details', unavailable)
    screen.tbl_products.selectRow(0)
    settle(app)
    assert screen.lbl_product_name.text() == 'Medicine details unavailable'
    screen.tbl_products.clearSelection()
    assert screen.lbl_product_name.text() == 'Select a medicine'


def test_batch_correction_refreshes_catalog_and_invalidates_intake(reference_ui, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from ui.screens import inventory_screen as inventory
    from core.inventory_service import set_batch_count
    app, state, windows = reference_ui
    screen = inventory.InventoryScreen(show_message_box=False)
    windows.append(screen)
    screen.show()
    settle(app)
    assert screen.all_products_raw[0][3] == 100
    screen._intake_loaded = True
    screen.tabs.setCurrentWidget(screen.batch_browser)
    settle(app)
    screen.batch_browser.table.selectRow(0)
    def correction(dialog):
        ok, message = set_batch_count(1, 93, 'Physical recount', employee_id=state.current_user['id'], expected_quantity=100)
        assert ok, message
        return QDialog.Accepted
    monkeypatch.setattr(inventory.StockCorrectionDialog, 'exec', correction)
    screen.batch_browser._adjust_selected()
    settle(app)
    assert screen.batch_browser._rows[0]['quantity'] == 93
    assert screen.all_products_raw[0][3] == 93
    assert not screen._intake_loaded


@pytest.mark.parametrize('invalid', [None, 'not a number', float('nan'), float('inf')])
def test_invalid_chart_amounts_are_unavailable_not_zero(reference_ui, invalid):
    from ui.widgets.report_chart import ReportChart
    app, state, windows = reference_ui
    chart = ReportChart('trend')
    windows.append(chart)
    chart.set_values([('Good', 10), ('Unknown', invalid)])
    assert chart.values == []
    assert chart.accessibleDescription() == 'Report data unavailable'
    chart.set_values([('Good', 12.5)])
    assert chart.values == [('Good', 12.5)]


def test_failed_batch_page_keeps_back_navigation(reference_ui):
    from ui.screens.batches_screen import BatchesScreen
    app, state, windows = reference_ui
    screen = BatchesScreen()
    windows.append(screen)
    screen._page = 1
    screen.previous.setEnabled(False)
    screen._failed('unavailable')
    assert screen.previous.isEnabled()
    assert not screen.adjust.isEnabled()


def test_backup_destination_setup_serializes_manual_backups(reference_ui, monkeypatch, tmp_path):
    from ui.screens import settings_screen as settings
    app, state, windows = reference_ui
    screen = settings.SettingsScreen(show_message_box=False)
    windows.append(screen)
    settle(app)
    scheduled = []
    monkeypatch.setattr(screen._tasks, 'run', lambda fn, done, failed: scheduled.append((fn, done, failed)))
    monkeypatch.setattr(settings.QFileDialog, 'getExistingDirectory', lambda *_: str(tmp_path))
    screen.choose_backup_destination()
    assert not screen.btn_trigger_backup.isEnabled()
    assert not screen.btn_backup_destination.isEnabled()
    screen.trigger_backup()
    screen.choose_backup_destination()
    assert len(scheduled) == 1
    scheduled[0][2]('write failure')
    assert screen.btn_trigger_backup.isEnabled()
    screen.trigger_backup()
    screen.trigger_backup()
    assert len(scheduled) == 2
    assert not screen.btn_backup_destination.isEnabled()
    scheduled[1][2]('backup failure')
    assert screen.btn_trigger_backup.isEnabled() and screen.btn_backup_destination.isEnabled()


def test_account_preview_uses_selected_row_with_missing_contact_cells(reference_ui, monkeypatch):
    from PySide6.QtCore import Qt, QItemSelectionModel
    from PySide6.QtWidgets import QTableWidgetItem
    from ui.screens import khatoo_screen as credit
    app, state, windows = reference_ui
    monkeypatch.setattr(credit._KHATOO_CONTROLLER, 'statement', lambda *_: 'Practice statement')
    screen = credit.KhatooScreen(show_message_box=False)
    windows.append(screen)
    settle(app)
    table = screen.tbl_ledger
    table.blockSignals(True)
    table.setRowCount(2)
    for row in range(2):
        item = QTableWidgetItem('Customer '+str(row))
        item.setData(Qt.UserRole, 'practice-'+str(row))
        item.setData(Qt.UserRole+1, 10.0)
        table.setItem(row, 0, item)
    table.setItem(1, 1, QTableWidgetItem('Other phone'))
    table.setItem(1, 2, QTableWidgetItem('Other area'))
    table.selectRow(0)
    table.selectionModel().setCurrentIndex(table.model().index(1, 0), QItemSelectionModel.NoUpdate)
    table.blockSignals(False)
    screen._update_payment_action()
    settle(app)
    assert screen.account_name.text() == 'Customer 0'
    assert screen.account_contact.text() == 'Phone: —\nArea: —'
