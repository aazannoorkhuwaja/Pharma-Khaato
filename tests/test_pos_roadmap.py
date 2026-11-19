"""Lot-specific POS selection, prescription state and settings/accessibility regressions."""
import json
from types import SimpleNamespace


def test_search_and_barcode_expose_lot_specific_prices_and_stock(seeded_shop):
    from core.product_search_service import search_sellable_products, get_product_by_barcode
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute("UPDATE Batch SET quantity=5,lot_number='EARLY',expiry_date='2099-01-01' WHERE id=1")
        cur.execute("INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id,sale_price,lot_number) VALUES(1,'LATE',7,'2099-12-31','2026-01-01',1,20,'LATE')")
    rows = search_sellable_products('TestMed')
    assert len(rows) == 2
    assert [(row[2], row[4], row[6]['lot_number']) for row in rows] == [(15,5,'EARLY'), (20,7,'LATE')]
    barcode = get_product_by_barcode('BC1')
    choices = barcode[6]['batch_choices']
    assert [row[2] for row in choices] == [15,20]
    assert len(search_sellable_products('BC1')) == 2
    json.dumps(barcode)  # LAN serialization must not contain recursive metadata.


def test_malformed_expiry_is_not_offered_in_search(seeded_shop):
    from core.product_search_service import search_sellable_products
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute("UPDATE Batch SET expiry_date='not-a-date' WHERE id=1")
    assert search_sellable_products('BC1') == []


def test_cart_keeps_different_lots_and_prices_separate():
    from ui.app.state.session_state import SessionState
    state = SessionState()
    base = {'prod_id':1,'name':'Medicine','price':15,'batch_id':1,'expiry_date':'2099-01-01',
            'stock':5,'lot_number':'A','unit_code':'base'}
    state.add_to_cart(base)
    state.add_to_cart({**base,'batch_id':2,'price':20,'lot_number':'B'})
    state.add_to_cart(base)
    state.add_to_cart({**base,'price':16})
    assert [(row['batch_id'],row['price'],row['qty']) for row in state.active_cart] == [(1,15,2),(2,20,1),(1,16,1)]
    assert state.active_cart[0]['expiry_date'] == '2099-01-01'
    assert state.active_cart[1]['lot_number'] == 'B'


def test_prescription_result_is_blocked_before_cart_mutation():
    from ui.screens.pos_screen import POSScreen
    notices = []
    screen = SimpleNamespace(session=SimpleNamespace(pending_checkout=None),
                             _set_search_feedback=lambda *args: notices.append(args))
    POSScreen._add_result_tuple_to_cart(screen, (1,'Restricted',5,1,4,'2099-01-01',{'requires_prescription':True}))
    assert 'cannot be sold' in notices[0][0]


def test_catalog_announces_lot_and_prescription(qapp):
    from PySide6.QtCore import Qt
    from ui.widgets.pos_models import ProductCatalogModel
    model = ProductCatalogModel()
    model.update_data([(1,'Medicine',15,1,5,'2099-01-01',{'lot_number':'A12','requires_prescription':True})])
    announcement = model.data(model.index(0,0), Qt.AccessibleTextRole)
    assert 'A12' in announcement and 'Prescription verification required' in announcement


def test_form_labels_have_names_and_buddies(qapp):
    from PySide6.QtWidgets import QWidget,QFormLayout,QLineEdit
    from ui.widgets.accessibility import label_form_controls
    panel = QWidget()
    form = QFormLayout(panel)
    control = QLineEdit()
    form.addRow('Licence number:', control)
    label_form_controls(panel)
    assert control.accessibleName() == 'Licence number'
    assert form.labelForField(control).buddy() is control


def test_settings_failed_save_and_navigation_keep_draft(qapp,qtbot,monkeypatch):
    import ui.screens.settings_screen as settings
    calls = []
    monkeypatch.setattr(settings._SETTINGS_CONTROLLER,'get_many',lambda *args: calls.append('read') or {'pharmacy_name':'Saved pharmacy'})
    monkeypatch.setattr(settings._SETTINGS_CONTROLLER,'update',lambda values:False)
    screen = settings.SettingsScreen(show_message_box=False)
    qtbot.addWidget(screen)
    qtbot.waitUntil(lambda: not screen._tasks._active, timeout=10000)
    assert screen._settings_loaded
    screen.txt_pharmacy_name.setText('Unsaved pharmacy')
    screen._mark_settings_dirty()
    screen.save_settings()
    qtbot.waitUntil(lambda: not screen._tasks._active, timeout=10000)
    screen.on_screen_show()
    assert screen.txt_pharmacy_name.text() == 'Unsaved pharmacy'
    assert calls == ['read'] and screen._settings_dirty


def test_mixed_price_lots_checkout_uses_chosen_lots(seeded_shop,admin_emp_id):
    from core.pos_service import CheckoutRequest,POSTransactionEngine
    with seeded_shop.get_db(immediate=True) as (_, cur):
        cur.execute("UPDATE Batch SET quantity=5,sale_price=15 WHERE id=1")
        cur.execute("INSERT INTO Batch(product_id,number_of_product,quantity,expiry_date,manufacture_Date,supplier_id,sale_price) VALUES(1,'LATE',7,'2099-12-31','2026-01-01',1,20)")
        second = cur.lastrowid
        cur.execute('UPDATE Products SET stock_quantity=12 WHERE id=1')
    sale = POSTransactionEngine.process_checkout(CheckoutRequest('WALKIN',admin_emp_id,
        [{'prod_id':1,'batch_id':1,'price':15,'qty':5}, {'prod_id':1,'batch_id':second,'price':20,'qty':2}],payment_method='Card'))
    assert sale.success, sale.message
    assert sale.total == 115
    with seeded_shop.get_db() as (_, cur):
        cur.execute('SELECT batch_id,Quantity FROM Sales_details WHERE purchase_id=%s ORDER BY batch_id',(sale.purchase_id,))
        assert cur.fetchall() == [(1,5),(second,2)]
