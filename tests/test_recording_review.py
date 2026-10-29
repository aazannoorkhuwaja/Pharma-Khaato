"""Regression coverage for the fifteen pharmacy recording findings."""
import pytest
from PySide6.QtCore import QDate, QThreadPool, Qt
from PySide6.QtWidgets import QScrollArea, QFormLayout, QLabel
from PySide6.QtGui import QPalette


@pytest.fixture
def owner(qapp, seeded_shop, admin_emp_id, qtbot):
    from ui.app.state.session_state import SessionState
    state = SessionState.get_instance()
    state.set_user({'id': admin_emp_id, 'username': 'admin', 'occupation': 'Admin'})
    yield state
    qtbot.waitUntil(lambda: QThreadPool.globalInstance().activeThreadCount() == 0, timeout=10000)
    qapp.processEvents()
    state.clear_user()


def settle(qtbot, widget):
    runner = getattr(widget, '_tasks', getattr(widget, 'tasks', None))
    if runner:
        qtbot.waitUntil(lambda: not runner._active, timeout=10000)


@pytest.mark.parametrize("width", [1024, 1366])
def test_stock_form_labels_rows_calendar_and_receiving(qapp, owner, qtbot, width):
    from ui.screens.inventory_screen import InventoryScreen
    from ui.theme.theme_manager import ThemeManager
    from controllers.pos_controller import POSController
    screen = InventoryScreen(show_message_box=False)
    qtbot.addWidget(screen)
    screen.resize(width, 768)
    screen.show()
    screen.tabs.setCurrentWidget(screen.tab_intake)
    settle(qtbot, screen)
    for mode in ('dark', 'light'):
        ThemeManager.set_theme(mode, save=False)
        qapp.setStyleSheet(ThemeManager.build_qss(mode))
        qapp.processEvents()
        scroll = screen.cmb_intake_prod.parent().parent().parent()
        assert isinstance(scroll, QScrollArea)
        assert scroll.horizontalScrollBar().maximum() == 0
        if width == 1366:
            assert scroll.width() > 430
        label = screen.intake_form.labelForField(screen.spn_intake_qty)
        assert label.palette().color(QPalette.WindowText) != scroll.widget().palette().color(QPalette.Window)
        assert screen.intake_form.isRowVisible(screen.txt_expiry_month)
        assert not screen.intake_form.isRowVisible(screen.dt_expiry)
    screen.cmb_expiry_precision.setCurrentIndex(1)
    assert not screen.intake_form.isRowVisible(screen.txt_expiry_month)
    assert screen.intake_form.isRowVisible(screen.dt_expiry)
    calendar = screen.dt_expiry.calendarWidget()
    calendar.show()
    qapp.processEvents()
    assert calendar.yearShown() == QDate.currentDate().year()
    assert calendar.monthShown() == QDate.currentDate().month()
    assert screen.dt_expiry.date() == QDate(1900, 1, 1)  # Opening never invents an expiry.
    calendar.hide()
    screen.cmb_expiry_precision.setCurrentIndex(0)
    screen.cmb_intake_prod.setCurrentIndex(screen.cmb_intake_prod.findData(1))
    settle(qtbot, screen)
    screen.spn_intake_qty.setValue(12)
    screen.txt_lot.setText('REVIEW-RECEIVED')
    screen.txt_expiry_month.setText('12/2099')
    screen.on_submit_intake()
    settle(qtbot, screen)
    assert not screen.txt_lot.text()
    assert POSController().search_products('TestMed')[0][4] == 112
    qapp.setStyleSheet('')
    ThemeManager.set_theme('light', save=False)


def test_optional_product_details_are_collapsed_without_losing_values(owner, qtbot):
    from ui.screens.inventory_screen import AddProductDialog
    dialog = AddProductDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.txt_name.isVisible()
    assert not dialog.txt_company.isVisible()
    dialog.btn_optional.click()
    dialog.txt_company.setText('Example manufacturer')
    assert dialog.txt_company.isVisible()
    dialog.btn_optional.click()
    assert dialog.txt_company.text() == 'Example manufacturer'
    assert not dialog.txt_company.isVisible()


def test_total_and_change_stay_with_checkout_and_customer_id_stays_internal(owner, qtbot):
    from ui.screens.pos_screen import POSScreen
    screen = POSScreen()
    qtbot.addWidget(screen)
    screen.resize(1100, 650)
    screen.show()
    settle(qtbot, screen)
    scroll = screen.findChild(QScrollArea, 'paymentSummaryScroll')
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    assert not scroll.isAncestorOf(screen.lbl_total)
    assert screen.lbl_total.parent() == screen.btn_checkout.parent()
    assert screen.lbl_total.isVisible()
    screen.cust_search_data = [('CUST_internal_example', 'Ali', 'Khan', '', 'Town')]
    screen.on_cust_table_double_clicked(0)
    assert screen.txt_customer.text() == 'Ali Khan'
    assert screen.selected_customer_cnic == 'CUST_internal_example'
    settle(qtbot, screen)


def test_missing_medicine_and_unavailable_stock_are_distinct(owner, qtbot, seeded_shop):
    from ui.screens.pos_screen import POSScreen
    screen = POSScreen()
    qtbot.addWidget(screen)
    settle(qtbot, screen)
    screen.txt_search.setText('DoesNotExist')
    screen.search_timer.stop()
    screen.perform_live_search()
    settle(qtbot, screen)
    assert 'Medicine not found' in screen.lbl_search_feedback.text()
    with seeded_shop.get_db() as (_, cur):
        cur.execute('UPDATE Batch SET quantity=0 WHERE product_id=1')
    screen.txt_search.setText('TestMed')
    screen.search_timer.stop()
    screen.perform_live_search()
    settle(qtbot, screen)
    assert 'Medicine found, but no stock' in screen.lbl_search_feedback.text()


def test_close_count_difference_ack_and_persisted_summary(owner, qtbot, admin_emp_id):
    from controllers.cash_session_controller import CashSessionController
    from ui.screens.cash_session_screen import CloseSessionDialog, CashSessionScreen
    from ui.app.main_window import MainWindow
    controller = CashSessionController()
    ok, shift = controller.open_session(admin_emp_id, 5000)
    assert ok
    window = MainWindow()
    qtbot.addWidget(window)
    settle(qtbot, window)
    dialog = CloseSessionDialog(shift, 5000)
    qtbot.addWidget(dialog)
    assert not dialog.btn_close.isEnabled()
    dialog.spn_actual.setValue(500)
    dialog.confirm_count.setChecked(True)
    assert not dialog.btn_close.isEnabled()
    dialog.confirm_difference.setChecked(True)
    assert dialog.btn_close.isEnabled()
    dialog.spn_actual.setValue(501)
    assert not dialog.btn_close.isEnabled()
    dialog.spn_actual.setValue(500)
    dialog.confirm_count.setChecked(True)
    dialog.confirm_difference.setChecked(True)
    dialog.on_close()
    settle(qtbot, dialog)
    assert window.lbl_shift_status.text() == 'Shift Closed'
    saved = controller.last_closed_session(admin_emp_id)
    assert (saved['expected_cash'], saved['actual_cash'], saved['discrepancy']) == (5000, 500, -4500)
    screen = CashSessionScreen(show_message_box=False)
    qtbot.addWidget(screen)
    settle(qtbot, screen)
    assert '5,000.00' in screen.lbl_last_close.text()
    assert '500.00' in screen.lbl_last_close.text()
    assert '-4,500.00' in screen.lbl_last_close.text()


def test_shift_open_updates_footer_without_signing_in_again(owner, qtbot, admin_emp_id):
    from ui.app.main_window import MainWindow
    from ui.screens.cash_session_screen import OpenSessionDialog
    window = MainWindow()
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: not window._shift_tasks._active, timeout=5000)
    assert window.lbl_shift_status.text() == 'Shift Closed'
    dialog = OpenSessionDialog(admin_emp_id)
    qtbot.addWidget(dialog)
    dialog.on_open()
    settle(qtbot, dialog)
    assert window.lbl_shift_status.text() == 'Shift Open'


def test_empty_accounts_and_preparation_routes(owner, qtbot, seeded_shop):
    from ui.screens.supplier_accounts import SupplierAccountsDialog
    from ui.screens.khatoo_screen import KhatooScreen
    from ui.dialogs.getting_started import GettingStartedDialog
    from ui.app.main_window import MainWindow
    from ui.screens.inventory_screen import InventoryScreen
    with seeded_shop.get_db() as (_, cur):
        cur.execute('DELETE FROM Batch')
        cur.execute('DELETE FROM Supplier')
    suppliers = SupplierAccountsDialog()
    qtbot.addWidget(suppliers)
    settle(qtbot, suppliers)
    assert suppliers.btn_add_supplier.text() == 'Add First Supplier'
    credit = KhatooScreen(show_message_box=False)
    qtbot.addWidget(credit)
    settle(qtbot, credit)
    assert 'No customer credit accounts yet' in credit.lbl_empty.text()
    window = MainWindow()
    qtbot.addWidget(window)
    window.router.register_screen_factory('inventory', lambda: InventoryScreen(show_message_box=False))
    guide = GettingStartedDialog(window)
    qtbot.addWidget(guide)
    settle(qtbot, guide)
    assert 'Suppliers added' in guide.status.text()
    guide.receive_stock()
    stock = window.router.currentWidget()
    assert stock.tabs.currentWidget() == stock.tab_intake
    settle(qtbot, stock)
