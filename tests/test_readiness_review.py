"""Real-stylesheet regressions for the second owner recording."""
import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QLabel
from tests.test_recording_review import owner, settle


@pytest.fixture
def styled(qapp):
    from ui.theme.theme_manager import ThemeManager
    yield ThemeManager
    ThemeManager.set_font_scale(1, save=False)
    ThemeManager.set_theme('light', save=False)
    qapp.setStyleSheet('')


@pytest.mark.parametrize('scale', [1.0, 1.25, 1.5])
@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_settings_rows_do_not_overlap_and_reach_save(owner, qtbot, qapp, styled, scale, mode):
    from ui.screens.settings_screen import SettingsScreen
    styled.set_font_scale(scale, save=False)
    styled.set_theme(mode, save=False)
    qapp.setStyleSheet(styled.build_qss(mode, scale))
    screen = SettingsScreen(show_message_box=False)
    qtbot.addWidget(screen)
    screen.resize(1000, 650)
    screen.show()
    qapp.processEvents()
    controls = [screen.txt_pharmacy_name, screen.txt_slogan, screen.txt_address,
                screen.txt_phone, screen.txt_license, screen.txt_ntn]
    for first, second in zip(controls, controls[1:]):
        assert first.geometry().bottom() < second.geometry().top()
    for first, second in zip([screen.spn_tax, screen.spn_credit_limit, screen.spn_expiry_threshold, screen.cmb_theme_mode],
                             [screen.spn_credit_limit, screen.spn_expiry_threshold, screen.cmb_theme_mode, screen.cmb_font_scale]):
        assert first.geometry().bottom() < second.geometry().top()
    assert screen.cmb_font_scale.geometry().bottom() < screen.btn_save_settings.geometry().top()
    screen.general_scroll.ensureWidgetVisible(screen.btn_save_settings)
    qapp.processEvents()
    assert screen.general_scroll.horizontalScrollBar().maximum() == 0
    screen.grab().save(f'/tmp/pharma-settings-{mode}-{scale}.png')
    styled.set_theme('dark' if mode == 'light' else 'light', save=False)
    assert screen.cmb_theme_mode.currentData() == styled.get_theme_mode()
    for label in screen.findChildren(QLabel):
        if label.property('uiTone') in ('secondary', 'muted'):
            assert not label.styleSheet()


def test_supplier_amount_and_invoice_layout(owner, qtbot, qapp, styled):
    from ui.screens.supplier_accounts import SupplierAccountsDialog, SupplierInvoiceDialog
    qapp.setStyleSheet(styled.build_qss('light', 1.0))
    accounts = SupplierAccountsDialog()
    qtbot.addWidget(accounts); accounts.show(); settle(qtbot, accounts)
    accounts.suppliers.item(0, 1).setText('Due Rs. 123,456,789.99')
    qapp.processEvents()
    item = accounts.suppliers.item(0, 1)
    assert accounts.suppliers.columnWidth(1) > accounts.suppliers.fontMetrics().horizontalAdvance(item.text())
    invoice = SupplierInvoiceDialog(1, 'Supplier')
    qtbot.addWidget(invoice); invoice.resize(1100, 900); invoice.show(); settle(qtbot, invoice)
    qapp.processEvents()
    assert invoice.entry_scroll.height() > invoice.rows.height()
    assert invoice.entry_scroll.horizontalScrollBar().maximum() == 0
    invoice.grab().save('/tmp/pharma-invoice-242.png')


def test_sidebar_controls_never_overlap(owner, qtbot, qapp, styled):
    from ui.app.main_window import MainWindow
    styled.set_font_scale(1.5, save=False)
    qapp.setStyleSheet(styled.build_qss('dark', 1.5))
    window = MainWindow(); qtbot.addWidget(window); window.resize(1100, 650); window.show()
    qapp.processEvents()
    assert window.nav_buttons['returns'].geometry().bottom() < window.user_badge.geometry().top()
    assert window.sidebar_scroll.verticalScrollBar().maximum() > 0
    window.hide()
    qtbot.waitUntil(lambda: QThreadPool.globalInstance().activeThreadCount() == 0, timeout=10000)


def test_search_keeps_customers_with_missing_legacy_contact_fields():
    import sqlite3
    from core.customer_directory_service import customer_filter
    # Migration 001 allowed a NULL city; current fresh schema does not.
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE Customers (id_card_number TEXT, cnic TEXT, display_name TEXT, first_name TEXT, last_name TEXT, city TEXT, phone TEXT)')
    conn.execute("INSERT INTO Customers VALUES ('CUST_1', '', 'Ayesha Khan', 'Ayesha', 'Khan', NULL, '')")
    for term, expected in [('Ayesha', 1), ('unrelated', 0)]:
        where, params = customer_filter(term)
        assert conn.execute('SELECT COUNT(*) FROM Customers c WHERE ' + where.replace('%s', '?'), params).fetchone()[0] == expected
    conn.close()


def test_invoice_cannot_add_previous_products_units_while_loading(owner, qtbot):
    from ui.screens.supplier_accounts import SupplierInvoiceDialog
    dialog = SupplierInvoiceDialog(1, 'Supplier'); qtbot.addWidget(dialog)
    settle(qtbot, dialog)
    assert dialog.units.count() > 0
    dialog.product.blockSignals(True)
    dialog.product.addItem('Another medicine', 999)
    dialog.product.setCurrentIndex(dialog.product.count() - 1)
    dialog.product.blockSignals(False)
    dialog.load_units()
    assert dialog.units.count() == 0
    assert not dialog.add.isEnabled()
    settle(qtbot, dialog)


def test_expiry_report_distinguishes_expired_stock(owner, qtbot):
    from ui.screens.reports_screen import ReportsScreen
    screen = ReportsScreen(); qtbot.addWidget(screen)
    screen._populate_expiry([{'product_name':'TestMed', 'quantity':2, 'expiry_date':'2020-01-01', 'days_left':-1, 'category':'Medicine'}])
    assert screen.tbl_expiry.item(0, 3).text() == 'Expired'
    settle(qtbot, screen)
