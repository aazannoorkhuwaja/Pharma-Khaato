"""A print-engine failure must not mark a saved receipt as printed."""
import re
import pytest


@pytest.fixture(scope='module')
def receipt_app():
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    yield app


def configure_pdf(monkeypatch, output, template='standard_80'):
    from PySide6 import QtPrintSupport
    from core import receipt_service, lan_config
    original=QtPrintSupport.QPrinter
    class PDFPrinter(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.setOutputFormat(original.PdfFormat)
            self.setOutputFileName(str(output))
    monkeypatch.setattr(QtPrintSupport,'QPrinter',PDFPrinter)
    monkeypatch.setattr(lan_config,'load_counter_config',lambda:None)
    monkeypatch.setattr(receipt_service.SettingsService,'get_setting',lambda key,default=None:default)
    monkeypatch.setattr(receipt_service,'_receipt_settings',lambda:{'receipt_template':template})
    return receipt_service


def test_begin_failure_returns_false_without_success_log(receipt_app, tmp_path, monkeypatch, caplog):
    service=configure_pdf(monkeypatch,tmp_path/'nonexistent-parent'/'receipt.pdf')
    assert not service.print_receipt_spooler('Receipt fixture\nTotal Rs.15.00')
    assert 'Receipt sent to OS print spooler' not in caplog.text


@pytest.mark.parametrize('template',['standard_80','compact_58'])
def test_long_receipt_produces_complete_multipage_pdf(receipt_app,tmp_path,monkeypatch,template):
    target=tmp_path/'receipt.pdf'
    service=configure_pdf(monkeypatch,target,template)
    assert service.print_receipt_spooler('\n'.join(f'Fixture item {i}: Rs.15.00' for i in range(200)))
    content=target.read_bytes()
    assert content.startswith(b'%PDF-') and content.rstrip().endswith(b'%%EOF')
    assert any(int(value)>1 for value in re.findall(rb'/Count\s+(\d+)',content))
