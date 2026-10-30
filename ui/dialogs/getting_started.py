"""A short preparation checklist for a new pharmacy owner."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from controllers.inventory_controller import InventoryController
from controllers.cash_session_controller import CashSessionController
from ui.app.state.session_state import SessionState
from ui.app.async_tasks import AsyncTaskRunner
from ui.widgets.responsive import configure_dialog


class GettingStartedDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Prepare Your Shop')
        configure_dialog(self, 600, 480, minimum_width=420, minimum_height=350)
        self.tasks = AsyncTaskRunner(self)
        layout = QVBoxLayout(self)
        intro = QLabel('Before the first sale, add your suppliers and medicines, receive the stock you have counted, then enter the cash in your drawer.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.status = QLabel('Checking shop preparation…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        for text, action in [('1. Add Supplier', self.add_supplier), ('2. Add Medicine', self.add_product),
                             ('3. Receive Opening Stock', self.receive_stock), ('4. Count Opening Cash', self.open_cash)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            layout.addWidget(button)
        done = QPushButton('Continue to App')
        done.clicked.connect(self.accept)
        layout.addWidget(done)
        self.refresh()

    def refresh(self):
        employee = (SessionState.get_instance().current_user or {}).get('id')
        inventory = InventoryController()
        def load():
            return inventory.suppliers(), inventory.products(), CashSessionController().active_session(employee)
        def loaded(result):
            suppliers, products, shift = result
            stocked = any(int(row[3] or 0) > 0 for row in products)
            self.status.setText('\n'.join([
                ('✓' if suppliers else '○') + ' Suppliers added',
                ('✓' if products else '○') + ' Medicines added',
                ('✓' if stocked else '○') + ' Saleable stock received',
                ('✓' if shift else '○') + ' Opening cash recorded',
            ]) + '\n\nReopen this checklist from Prepare Your Shop in the sidebar.')
        self.tasks.run_latest('readiness', load, loaded,
                              lambda _e: self.status.setText('Could not check preparation. Check the shop connection and reopen this checklist.'))

    def add_supplier(self):
        from ui.screens.inventory_screen import AddSupplierDialog
        if AddSupplierDialog(self).exec() == QDialog.Accepted:
            self.refresh()

    def add_product(self):
        from ui.screens.inventory_screen import AddProductDialog
        if AddProductDialog(self).exec() == QDialog.Accepted:
            self.refresh()

    def receive_stock(self):
        self.parent().on_nav_clicked('inventory')
        screen = self.parent().router.currentWidget()
        screen.tabs.setCurrentWidget(screen.tab_intake)
        self.accept()

    def open_cash(self):
        self.parent().on_nav_clicked('cash_session')
        self.accept()
