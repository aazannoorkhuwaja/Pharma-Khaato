"""Owner receiving and supplier dues, separate from the cashier counter."""
import copy
from decimal import Decimal, ROUND_HALF_UP
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTableWidget,QTableWidgetItem,QHeaderView,
    QMessageBox,QInputDialog,QScrollArea,QWidget)
from controllers.inventory_controller import InventoryController
from ui.app.async_tasks import AsyncTaskRunner
from ui.widgets.responsive import configure_dialog
from ui.widgets.table_polish import polish_table

_INVENTORY=InventoryController()


def table(headers):
    view=QTableWidget(0,len(headers))
    view.setHorizontalHeaderLabels(headers)
    view.setSelectionBehavior(QTableWidget.SelectRows)
    view.setEditTriggers(QTableWidget.NoEditTriggers)
    view.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
    polish_table(view)
    return view


class SupplierInvoiceDialog(QDialog):
    def __init__(self,supplier_id,supplier_name,parent=None):
        super().__init__(parent)
        configure_dialog(self,1000,760,minimum_width=680,minimum_height=500)
        self.setWindowTitle('Receive Supplier Invoice — '+supplier_name)
        self.supplier_id=supplier_id
        self.lines=[]
        self._busy=False
        self.tasks=AsyncTaskRunner(self)
        layout=QVBoxLayout(self)
        self.reference=QLineEdit()
        self.reference.setPlaceholderText('Invoice number printed by the supplier')
        layout.addWidget(QLabel('Receive all lines from one invoice once. Stock and the supplier balance save together.'))
        layout.addWidget(self.reference)
        body=QWidget()
        forms=QHBoxLayout(body)
        left=QFormLayout()
        right=QFormLayout()
        forms.addLayout(left,1)
        forms.addLayout(right,1)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Find product by name or barcode')
        self.product=QComboBox()
        self.units=QComboBox()
        self.quantity=QSpinBox();self.quantity.setRange(1,1000000)
        self.bonus=QSpinBox();self.bonus.setRange(0,1000000)
        self.cost=QDoubleSpinBox();self.cost.setRange(0,100000000);self.cost.setDecimals(4);self.cost.setPrefix('Rs. ')
        self.sell=QDoubleSpinBox();self.sell.setRange(.0001,1000000);self.sell.setDecimals(4);self.sell.setPrefix('Rs. ')
        self.expiry=QLineEdit();self.expiry.setPlaceholderText('MM/YYYY from the pack')
        self.lot=QLineEdit();self.lot.setPlaceholderText('Manufacturer lot, if printed')
        for label,field in [('Search',self.search),('Product',self.product),('Receive in',self.units),('Quantity',self.quantity),('Free smallest units',self.bonus)]:
            left.addRow(label,field)
        for label,field in [('Cost per selected pack/unit',self.cost),('Sell per smallest unit',self.sell),('Printed expiry month',self.expiry),('Lot / batch',self.lot)]:
            right.addRow(label,field)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body)
        layout.addWidget(scroll,1)
        self.add=QPushButton('Add Invoice Line');self.add.clicked.connect(self.add_line)
        layout.addWidget(self.add)
        self.rows=table(['Product','Quantity','Unit','Cost','Expiry','Lot'])
        layout.addWidget(self.rows,1)
        remove=QPushButton('Remove Selected Line');remove.clicked.connect(self.remove_line);layout.addWidget(remove)
        footer=QHBoxLayout()
        self.paid=QDoubleSpinBox();self.paid.setRange(0,100000000);self.paid.setDecimals(2);self.paid.setPrefix('Paid now: Rs. ')
        self.method=QComboBox();self.method.addItems(['Bank transfer','Outside drawer','Cash from drawer'])
        self.total=QLabel('Invoice: Rs. 0.00')
        footer.addWidget(self.total);footer.addWidget(self.paid);footer.addWidget(self.method)
        layout.addLayout(footer)
        self.status=QLabel('');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.save=QPushButton('Save Invoice & Stock');self.save.setObjectName('primaryButton');self.save.clicked.connect(self.save_invoice)
        layout.addWidget(self.save)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180)
        self.search.textChanged.connect(lambda:self.timer.start())
        self.timer.timeout.connect(self.search_products)
        self.product.currentIndexChanged.connect(self.load_units)
        self.search_products()

    def search_products(self):
        term=self.search.text().strip()
        def complete(rows):
            if self.search.text().strip()!=term:return
            self.product.blockSignals(True);self.product.clear()
            for row in rows:self.product.addItem(str(row[1]),int(row[0]))
            self.product.blockSignals(False);self.load_units()
        self.tasks.run_latest('invoice-products',lambda:(_INVENTORY.catalog_search(term,100) if term else _INVENTORY.catalog_snapshot(100,25)['products']),complete,
                              lambda _e:self.status.setText('Product list unavailable. Check the connection.'))

    def load_units(self):
        product=self.product.currentData()
        if product is None:return
        def complete(units):
            if self.product.currentData()!=product:return
            self.units.clear()
            for unit in units:self.units.addItem(unit['label'],unit)
            if units:self.sell.setValue(float(units[0]['price']))
        self.tasks.run_latest('invoice-units',lambda:_INVENTORY.sell_units(product),complete,
                              lambda _e:self.status.setText('Unit sizes unavailable. Choose the product again.'))

    def add_line(self):
        unit=self.units.currentData()
        if self.product.currentData() is None or not unit or not self.expiry.text().strip():
            self.status.setText('Choose the product and enter its printed expiry month.');return
        self.lines.append({'product_id':self.product.currentData(),'name':self.product.currentText(),
            'quantity':self.quantity.value(),'unit_code':unit['code'],'unit_label':unit['label'],
            'bonus_base_units':self.bonus.value(),'cost_per_unit':self.cost.value(),'sale_price':self.sell.value(),
            'expiry':self.expiry.text().strip(),'expiry_precision':'MONTH','lot':self.lot.text().strip()})
        self.refresh_lines()
        self.lot.clear();self.expiry.clear();self.quantity.setValue(1);self.bonus.setValue(0)

    def remove_line(self):
        index=self.rows.currentRow()
        if index>=0 and not self._busy:self.lines.pop(index);self.refresh_lines()

    def refresh_lines(self):
        self.rows.setRowCount(len(self.lines))
        total=Decimal('0')
        for index,line in enumerate(self.lines):
            cost=(Decimal(line['quantity'])*Decimal(str(line['cost_per_unit']))).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP);total+=cost
            for col,value in enumerate([line['name'],line['quantity'],line['unit_label'],f'Rs. {cost:,.2f}',line['expiry'],line['lot']]):
                self.rows.setItem(index,col,QTableWidgetItem(str(value)))
        self.total.setText(f'Invoice: Rs. {total:,.2f}')

    def save_invoice(self):
        if self._busy:return
        if not self.reference.text().strip() or not self.lines:
            self.status.setText('Enter the supplier invoice number and add its lines.');return
        self._busy=True;self.save.setEnabled(False);self.add.setEnabled(False)
        payload={'supplier_id':self.supplier_id,'reference':self.reference.text().strip(),'lines':copy.deepcopy(self.lines),
                 'paid_amount':self.paid.value(),'payment_method':self.method.currentText()}
        self.tasks.run(lambda:_INVENTORY.receive_invoice(**payload),self.finished_invoice,
                       lambda _e:self.unknown())

    def finished_invoice(self,result):
        self._busy=False;self.save.setEnabled(True);self.add.setEnabled(True)
        if result[0]:self.accept()
        else:self.status.setText(str(result[1]))

    def unknown(self):
        self._busy=False
        self.status.setText('Invoice result unconfirmed. Close this window and use Confirm Pending Entry before receiving anything again.')

    def reject(self):
        if not self._busy:super().reject()


class SupplierAccountsDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        configure_dialog(self,950,700,minimum_width=650,minimum_height=450)
        self.setWindowTitle('Supplier Invoices & Payments')
        self.tasks=AsyncTaskRunner(self)
        self.accounts=[]
        self._busy=False
        layout=QVBoxLayout(self)
        self.status=QLabel('Choose a supplier. Positive balance is due; negative balance is credit with that supplier.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.suppliers=table(['Supplier','Amount Due / Credit'])
        layout.addWidget(self.suppliers,1)
        buttons=QHBoxLayout()
        for label,method in [('Receive Invoice',self.receive),('Pay Supplier',self.pay),('Return Stock',self.return_stock),('History',self.history),('Confirm Pending Entry',self.recover)]:
            button=QPushButton(label);button.clicked.connect(method);buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        def complete(rows):
            self.accounts=rows;self.suppliers.setRowCount(len(rows))
            for index,row in enumerate(rows):
                self.suppliers.setItem(index,0,QTableWidgetItem(row['name']))
                value=row['balance'];text=f'Due Rs. {value:,.2f}' if value>=0 else f'Credit Rs. {-value:,.2f}'
                self.suppliers.setItem(index,1,QTableWidgetItem(text))
        self.tasks.run_latest('suppliers',_INVENTORY.supplier_accounts,complete,
                              lambda _e:self.status.setText('Supplier accounts unavailable. Check the connection and reopen this window.'))

    def selected(self):
        index=self.suppliers.currentRow()
        if index<0:
            self.status.setText('Select a supplier first. Add missing suppliers in Add Stock.');return None
        return self.accounts[index]

    def receive(self):
        if self._busy:return
        row=self.selected()
        if row and SupplierInvoiceDialog(row['supplier_id'],row['name'],self).exec()==QDialog.Accepted:self.refresh()

    def _write(self,fn):
        if self._busy:return
        self._busy=True
        self.tasks.run(fn,self._saved,lambda _e:self._unknown())

    def _saved(self,result):
        self._busy=False;self.status.setText(str(result[1]));self.refresh()

    def _unknown(self):
        self._busy=False
        self.status.setText('Result unconfirmed. Use Confirm Pending Entry; do not enter the same money or stock again.')

    def pay(self):
        if self._busy:return
        row=self.selected()
        if not row:return
        if row['balance']<=0:self.status.setText('This supplier has no unpaid balance.');return
        amount,ok=QInputDialog.getDouble(self,'Pay Supplier',f"{row['name']} — amount actually paid",0,.01,row['balance'],2)
        if not ok:return
        method,ok=QInputDialog.getItem(self,'Payment Source','Choose where the payment came from',
            ['Bank transfer','Outside drawer','Cash from drawer'],0,False)
        if ok:self._write(lambda:_INVENTORY.pay_supplier(supplier_id=row['supplier_id'],amount=amount,payment_method=method))

    def recover(self):
        self._write(_INVENTORY.recover_supplier_entry)

    def history(self):
        row=self.selected()
        if not row:return
        self.tasks.run(lambda:_INVENTORY.supplier_history(row['supplier_id']),self.show_history,
                       lambda _e:self.status.setText('History unavailable. Retry when the shop connection returns.'))

    def show_history(self,rows):
        dialog=QDialog(self);dialog.setWindowTitle('Supplier History — recent 500 entries')
        configure_dialog(dialog,800,500,minimum_width=550,minimum_height=350)
        layout=QVBoxLayout(dialog);view=table(['Date','Reference / Note','Amount','Entry'])
        view.setRowCount(len(rows))
        for index,row in enumerate(rows):
            for col,value in enumerate(row):view.setItem(index,col,QTableWidgetItem(str(value)))
        layout.addWidget(view);dialog.exec()

    def return_stock(self):
        if self._busy:return
        row=self.selected()
        if not row:return
        def choose(lines):
            available=[line for line in lines if min(line[4]-line[5],line[6])>0]
            if not available:self.status.setText('No invoice stock is available to return.');return
            choices=[f'{line[1]} — {line[2]} — lot {line[3] or "not entered"} — available {min(line[4]-line[5],line[6])}' for line in available]
            chosen,ok=QInputDialog.getItem(self,'Return to Supplier','Choose the received invoice line',choices,0,False)
            if not ok:return
            line=available[choices.index(chosen)]
            qty,ok=QInputDialog.getInt(self,'Return Quantity','Smallest units physically returned',1,1,min(line[4]-line[5],line[6]))
            if not ok:return
            reason,ok=QInputDialog.getText(self,'Supplier Return Reason','Reason for this return')
            if ok:self._write(lambda:_INVENTORY.return_to_supplier(line_id=line[0],quantity=qty,reason=reason))
        self.tasks.run(lambda:_INVENTORY.supplier_invoice_lines(row['supplier_id']),choose,
                       lambda _e:self.status.setText('Received invoice lines unavailable. Retry later.'))
