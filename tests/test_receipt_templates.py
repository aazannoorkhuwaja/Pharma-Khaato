from core import receipt_service


def _mock_settings(monkeypatch, selected="standard_80"):
    values = {
        "receipt_template": selected,
        "pharmacy_name": "Demo Pharmacy",
        "slogan": "Care Close to Home",
        "address": "Main Road",
        "phone": "03001234567",
        "license_number": "LIC-123",
        "ntn_number": "NTN-456",
        "receipt_footer": "Get well soon",
    }

    def fake_get_many(keys, defaults=None):
        defaults = defaults or {}
        return {key: values.get(key, defaults.get(key, "")) for key in keys}

    monkeypatch.setattr(
        receipt_service.SettingsService,
        "get_many",
        staticmethod(fake_get_many),
    )


def _render(monkeypatch, template):
    _mock_settings(monkeypatch, template)
    return receipt_service.generate_invoice_text(
        77,
        "Walk-in Customer",
        [{"name": "Panadol 500mg", "qty": 2, "price": 50.0}],
        total=100.0,
        tax=0.0,
        discount=0.0,
        payment_method="Cash",
        cashier_name="Admin",
        amount_received=200.0,
        change=100.0,
    )


def test_all_receipt_templates_render(monkeypatch):
    keys = [row[0] for row in receipt_service.get_receipt_template_options()]
    assert len(keys) == 5
    for key in keys:
        output = _render(monkeypatch, key)
        assert "Demo Pharmacy" in output
        assert "100.00" in output
        assert "Panadol" in output


def test_compact_receipt_uses_narrow_width(monkeypatch):
    output = _render(monkeypatch, "compact_58")
    assert max(len(line) for line in output.splitlines()) <= 32


def test_professional_receipt_has_structured_heading(monkeypatch):
    output = _render(monkeypatch, "professional_80")
    assert "SALES RECEIPT" in output
    assert "Amount received" in output
    assert "Change" in output


def test_tax_invoice_receipt_exposes_regulatory_fields(monkeypatch):
    output = _render(monkeypatch, "tax_invoice_80")
    assert "TAX INVOICE" in output
    assert "Licence: LIC-123" in output
    assert "NTN: NTN-456" in output


def test_unknown_saved_template_falls_back_safely(monkeypatch):
    output = _render(monkeypatch, "not-a-template")
    assert "Invoice ID:" in output


def test_receipt_renderer_uses_one_batched_settings_read(monkeypatch):
    calls = []

    def fake_get_many(keys, defaults=None):
        calls.append(tuple(keys))
        defaults = defaults or {}
        return {key: defaults.get(key, "") for key in keys}

    monkeypatch.setattr(receipt_service.SettingsService, "get_many", staticmethod(fake_get_many))
    receipt_service.generate_invoice_text(
        1,
        "Walk-in Customer",
        [{"name": "Test", "qty": 1, "price": 10}],
        total=10,
        tax=0,
        discount=0,
    )
    assert len(calls) == 1
