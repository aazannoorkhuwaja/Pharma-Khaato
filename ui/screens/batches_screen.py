"""Reference batch/expiry browser using bounded authoritative inventory reads."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QScrollArea, QLayout, QSizePolicy)
from controllers.inventory_controller import InventoryController
from ui.app.async_tasks import AsyncTaskRunner
from ui.widgets.card import Card
from ui.widgets.table_polish import polish_table
from ui.widgets.semantic_style import set_tone
from ui.widgets.responsive import flexible_side_panel
from ui.widgets.reference_icons import icon


class BatchesScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = InventoryController()
        self._tasks = AsyncTaskRunner(self)
        self._page = 0
        self._rows = []
        self._today = self._cutoff = ''
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        layout.setContentsMargins(12, 12, 12, 12)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        toolbar = Card()
        filters = QGridLayout()
        toolbar.addLayout(filters)
        self.expiry_filter = QComboBox()
        for label, value in [('All Batches','all'),('Near Expiry · 30 Days','near'),('Expired','expired'),('Later Expiry','later')]:
            self.expiry_filter.addItem(label, value)
        self.condition_filter = QComboBox()
        for label, value in [('All Stock Conditions','all'),('Sellable Condition','SELLABLE'),('Quarantined','QUARANTINED'),('Recalled','RECALLED')]:
            self.condition_filter.addItem(label, value)
        self.supplier_filter = QComboBox()
        self.supplier_filter.addItem('All Suppliers', None)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search medicine, printed lot or supplier')
        self.search.setAccessibleName('Search batches')
        self.search.addAction(icon('search'), QLineEdit.LeadingPosition)
        self._filter_controls = (self.expiry_filter, self.condition_filter, self.supplier_filter, self.search)
        self._filter_labels = []
        self._filter_columns = 4
        for column, (label, widget) in enumerate(zip(('Expiry Range','Stock Condition','Supplier','Search'), self._filter_controls)):
            caption = QLabel(label)
            self._filter_labels.append(caption)
            filters.addWidget(caption, 0, column)
            widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            if isinstance(widget,QComboBox):
                widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
                widget.setMinimumContentsLength(6)
            filters.addWidget(widget, 1, column)
            filters.setColumnStretch(column, 1 if column<3 else 2)
        self.filter_grid = filters
        layout.addWidget(toolbar)
        body = QHBoxLayout()
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(['Medicine','Lot','Supplier','Mfg Date','Expiry','Stock','Cost','Sale Price','Status'])
        self.table.setMinimumHeight(180)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().hide()
        polish_table(self.table)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1,9):
            self.table.horizontalHeader().setSectionResizeMode(column,QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        body.addWidget(self.table, 7)
        self.details = Card()
        flexible_side_panel(self.details, minimum=220, maximum=310)
        title = QLabel('Batch Details'); title.setObjectName('h2'); self.details.addWidget(title)
        self.selected_name = QLabel('Select a batch'); self.selected_name.setWordWrap(True)
        self.selected_name.setObjectName('h2'); self.selected_name.setTextFormat(Qt.PlainText)
        self.selected_info = QLabel('Review stock and expiry before changing its condition.')
        self.selected_info.setWordWrap(True); self.selected_info.setTextFormat(Qt.PlainText)
        self.details.addWidget(self.selected_name)
        detail_scroll=QScrollArea();detail_scroll.setWidgetResizable(True)
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.selected_info.setAlignment(Qt.AlignTop)
        detail_scroll.setWidget(self.selected_info)
        self.details.addWidget(detail_scroll,1)
        self.adjust = QPushButton('Count / Block Batch')
        self.adjust.setEnabled(False)
        self.adjust.clicked.connect(self._adjust_selected)
        self.details.addWidget(self.adjust)
        body.addWidget(self.details, 3); layout.addLayout(body, 1)
        footer = QHBoxLayout()
        self.metrics = {}
        for key,title in [('near','Near Expiry'),('expired','Expired'),('blocked','Blocked / Recalled')]:
            card=Card(); card.addWidget(QLabel(title))
            value=QLabel('…');value.setObjectName('metric')
            set_tone(value,'warning' if key=='near' else 'danger')
            card.addWidget(value);self.metrics[key]=value;footer.addWidget(card,1)
        layout.addLayout(footer)
        pager=QHBoxLayout()
        self.adjust_compact=QPushButton("Count / Block Batch")
        self.adjust_compact.setEnabled(False)
        self.adjust_compact.clicked.connect(self._adjust_selected)
        self.adjust_compact.hide()
        self.previous=QPushButton('Previous');self.next=QPushButton('Next');self.status=QLabel('Open this tab to load batches.')
        self.status.setWordWrap(True)
        self.previous.clicked.connect(lambda:self._change_page(-1))
        self.next.clicked.connect(lambda:self._change_page(1))
        pager.addWidget(self.previous);pager.addWidget(self.status,1);pager.addWidget(self.adjust_compact);pager.addWidget(self.next)
        layout.addLayout(pager)
        warning=QLabel('Expired, quarantined and recalled batches cannot be sold. Their physical stock remains recorded.')
        warning.setWordWrap(True);set_tone(warning,'danger');layout.addWidget(warning)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        for control in self._filter_controls[:3]:control.currentIndexChanged.connect(self._filter_changed)
        self.search.textChanged.connect(self._filter_changed)

    def _filter_changed(self, *_):
        self._page=0
        self._tasks.invalidate('batches')
        self.timer.start()

    def _change_page(self, delta):
        self._page=max(0,self._page+delta);self.refresh()

    def refresh(self):
        args=(self.search.text(),self.expiry_filter.currentData(),self.condition_filter.currentData(),
              self.supplier_filter.currentData(),100,self._page*100)
        self.status.setText('Loading batches…')
        self.adjust.setEnabled(False)
        self.adjust_compact.setEnabled(False)
        self.previous.setEnabled(False);self.next.setEnabled(False)
        self._tasks.run_latest('batches',lambda:self.controller.batch_browser(*args),self._loaded,self._failed)

    def _loaded(self, payload):
        self._today,self._cutoff=payload['today'],payload['cutoff']
        self._rows=payload['rows']
        supplier=self.supplier_filter.currentData()
        self.supplier_filter.blockSignals(True);self.supplier_filter.clear()
        self.supplier_filter.addItem('All Suppliers',None)
        for key,name in payload['suppliers']:self.supplier_filter.addItem(str(name),key)
        self.supplier_filter.setCurrentIndex(max(0,self.supplier_filter.findData(supplier)))
        self.supplier_filter.blockSignals(False)
        self.table.blockSignals(True);self.table.setRowCount(len(self._rows))
        for row,batch in enumerate(self._rows):
            values=(batch['medicine'],batch['lot'] or '—',batch['supplier'] or '—',
                    batch['manufactured'] or '—',batch['expiry'],str(batch['quantity'])+' '+batch['unit'],
                    '—' if batch['cost'] is None else f"Rs. {float(batch['cost']):,.2f}",
                    f"Rs. {float(batch['price']):,.2f}",self._status(batch))
            for column,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(row,column,item)
        self.table.clearSelection();self.table.blockSignals(False);self._selection_changed()
        count=payload['count'];offset=payload['offset']
        self.status.setText(f"{offset+1 if self._rows else 0}–{offset+len(self._rows)} of {count} batches · stock in smallest units")
        self.previous.setEnabled(offset>0);self.next.setEnabled(offset+len(self._rows)<count)
        for key,label in self.metrics.items():label.setText(str(payload['counts'][key])+' batches')

    def _status(self,batch):
        if str(batch['expiry']) < self._today:return 'Expired · blocked'
        if batch['condition']!='SELLABLE':return str(batch['condition']).title()
        if batch['quantity']<=0:return 'No stock'
        return 'Near expiry' if str(batch['expiry'])<=self._cutoff else 'Normal'

    def _selection_changed(self):
        selected=self.table.selectionModel().selectedRows()
        batch=self._rows[selected[0].row()] if selected and selected[0].row()<len(self._rows) else None
        self.adjust.setEnabled(batch is not None)
        self.adjust_compact.setEnabled(batch is not None)
        self.selected_name.setText(str(batch['medicine']) if batch else 'Select a batch')
        self.selected_info.setText('\n'.join([
            'Printed lot: '+str(batch['lot'] or 'Not recorded'),'Supplier: '+str(batch['supplier'] or '—'),
            'Stock: '+str(batch['quantity'])+' '+str(batch['unit']),
            'Expiry: '+str(batch['expiry']),'Manufactured: '+str(batch['manufactured'] or '—'),
            'Cost: '+('Not recorded' if batch['cost'] is None else f"Rs. {float(batch['cost']):,.2f}"),
            f"Sale price: Rs. {float(batch['price']):,.2f}",'Condition: '+self._status(batch)]) if batch else '')

    def _adjust_selected(self):
        selected=self.table.selectionModel().selectedRows()
        if not selected:return
        batch=self._rows[selected[0].row()]
        from ui.screens.inventory_screen import StockCorrectionDialog
        row=(batch['id'],batch['medicine'],batch['lot'],batch['quantity'],batch['expiry'],
             batch['condition'],batch['unit'],batch['price'],batch['expiry_precision'])
        if StockCorrectionDialog([row],self).exec()==QDialog.Accepted:self.refresh()

    def _failed(self, _details):
        self._rows=[];self.table.setRowCount(0);self._selection_changed()
        for label in self.metrics.values():label.setText('Unavailable')
        self.status.setText('Could not load batches. Change a filter or reopen the tab to retry.')

    def resizeEvent(self,event):
        self.details.setVisible(event.size().width()>=950)
        self.adjust_compact.setVisible(event.size().width()<950)
        self.table.setColumnHidden(3,event.size().width()<1200)
        self.table.setColumnHidden(6,event.size().width()<1200)
        columns=4 if event.size().width()>=1000 else 2
        if columns!=self._filter_columns:
            self._filter_columns=columns
            for index,(label,control) in enumerate(zip(self._filter_labels,self._filter_controls)):
                self.filter_grid.removeWidget(label);self.filter_grid.removeWidget(control)
                row,column=divmod(index,columns)
                self.filter_grid.addWidget(label,row*2,column)
                self.filter_grid.addWidget(control,row*2+1,column)
            for column in range(4):self.filter_grid.setColumnStretch(column,1 if column<columns else 0)
        super().resizeEvent(event)
