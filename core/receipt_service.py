import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.path_manager import PathManager
from core.settings_service import SettingsService
from core.logger import get_logger

logger = get_logger("PharmaKhaatoReceipt")

RECEIPT_TEMPLATES = (
    ("standard_80", "Standard 80mm", "Balanced everyday receipt with clear totals."),
    ("professional_80", "Professional 80mm", "Structured pharmacy receipt with stronger visual sections."),
    ("detailed_80", "Detailed 80mm", "Extra customer, payment and pharmacy information."),
    ("tax_invoice_80", "Tax Invoice 80mm", "Tax/regulatory focused format with licence and NTN details."),
    ("compact_58", "Compact 58mm", "Short receipt for narrow 58mm thermal printers."),
)
_TEMPLATE_KEYS = {item[0] for item in RECEIPT_TEMPLATES}
_RECEIPT_SETTING_KEYS = (
    "receipt_template",
    "pharmacy_name",
    "slogan",
    "address",
    "phone",
    "license_number",
    "ntn_number",
    "receipt_footer",
)


def get_receipt_template_options():
    return RECEIPT_TEMPLATES


def available_printers() -> list[str]:
    """Return printer names exposed by the operating system, sorted for UI use."""
    try:
        from PySide6.QtPrintSupport import QPrinterInfo

        names = {str(name).strip() for name in QPrinterInfo.availablePrinterNames() if str(name).strip()}
        return sorted(names, key=str.casefold)
    except Exception as exc:
        logger.warning("Could not enumerate printers: %s", exc)
        return []


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_valid_setting(val):
    if not val:
        return False
    clean = str(val).strip()
    return bool(clean and clean.upper() not in ("NOT_CONFIGURED", "N/A", "NONE", "NULL"))


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value):
    return f"{value:.2f}" if value == value.quantize(Decimal(".01")) else f"{value:.4f}"


def _item_total(item):
    value = item.get("subtotal")
    if value is None:
        value = Decimal(str(item.get("price", 0))) * int(item.get("qty", 1))
    return _money(value)


def _receipt_settings():
    return SettingsService.get_many(
        _RECEIPT_SETTING_KEYS,
        {
            "receipt_template": "standard_80",
            "pharmacy_name": "Pharma Khaato Pharmacy",
            "slogan": "NOT_CONFIGURED",
            "address": "NOT_CONFIGURED",
            "phone": "NOT_CONFIGURED",
            "license_number": "NOT_CONFIGURED",
            "ntn_number": "NOT_CONFIGURED",
            "receipt_footer": "NOT_CONFIGURED",
        },
    )


def _template_key(explicit=None, settings=None):
    settings = settings or {}
    key = str(explicit or settings.get("receipt_template", "standard_80")).strip()
    return key if key in _TEMPLATE_KEYS else "standard_80"


def _template_width(key: str) -> int:
    return 32 if key == "compact_58" else 42


def _center(text: str, width: int) -> str:
    return str(text or "")[:width].center(width)


def _pair(left: str, right: str, width: int) -> str:
    left = str(left)
    right = str(right)
    gap = max(1, width - len(left) - len(right))
    return (left + (" " * gap) + right)[:width]


def _pharmacy_header(width: int, settings: dict, *, tax_focused: bool = False):
    p_name = settings.get("pharmacy_name", "Pharma Khaato Pharmacy")
    p_slogan = settings.get("slogan", "NOT_CONFIGURED")
    p_address = settings.get("address", "NOT_CONFIGURED")
    p_phone = settings.get("phone", "NOT_CONFIGURED")
    p_lic = settings.get("license_number", "NOT_CONFIGURED")
    p_ntn = settings.get("ntn_number", "NOT_CONFIGURED")

    lines = [_center(p_name, width)]
    if _is_valid_setting(p_slogan) and not tax_focused:
        lines.append(_center(p_slogan, width))
    if _is_valid_setting(p_address):
        lines.append(_center(p_address, width))
    if _is_valid_setting(p_phone):
        lines.append(_center(f"Phone: {p_phone}", width))
    if _is_valid_setting(p_lic):
        lines.append(_center(f"Licence: {p_lic}", width))
    if _is_valid_setting(p_ntn):
        lines.append(_center(f"NTN: {p_ntn}", width))
    return lines


def _purchase_receipt_context(purchase_id, fallback_payment="Cash", fallback_cashier="Cashier"):
    """Resolve immutable sale context after commit for receipt accuracy.

    Older checkout callers only distinguished Cash-vs-Credit when invoking the
    receipt side effect. The Purchase row is the source of truth for the actual
    tender (Card/Easypaisa/JazzCash/etc.), so receipts resolve it by sale ID.
    """
    try:
        from core.db_engine import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT p.payment_method, e.first_name, e.last_name "
            "FROM Purchase p LEFT JOIN Employee e ON e.Employee_id = p.employee_id "
            "WHERE p.id = %s LIMIT 1",
            (purchase_id,),
        )
        row = cur.fetchone()
        if not row:
            return str(fallback_payment or "Cash"), str(fallback_cashier or "Cashier")
        payment = str(row[0] or fallback_payment or "Cash")
        cashier = " ".join(part for part in (str(row[1] or "").strip(), str(row[2] or "").strip()) if part)
        return payment, cashier or str(fallback_cashier or "Cashier")
    except Exception as exc:
        logger.warning("Could not resolve committed sale context for receipt #%s: %s", purchase_id, exc)
        return str(fallback_payment or "Cash"), str(fallback_cashier or "Cashier")


def generate_invoice_text(
    purchase_id,
    customer_id,
    items,
    total,
    tax,
    discount,
    payment_method="Cash",
    cashier_name="Cashier",
    amount_received=None,
    change=None,
    template=None,
    *,
    sale_datetime=None,
):
    """Render the selected fast thermal-receipt template."""
    settings = _receipt_settings()
    key = _template_key(template, settings)
    width = _template_width(key)
    sep = "-" * width
    strong = "=" * width
    now = sale_datetime or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # A database reference is not useful customer-facing receipt information.
    identity = str(customer_id or "Walk-in Customer").strip()
    if identity.upper() in {"WALKIN", "GUEST_WALKIN"} or identity.startswith("CUST_"):
        customer_id = "Walk-in Customer" if identity.upper() in {"WALKIN", "GUEST_WALKIN"} else "Customer"
    elif identity.replace("-", "").isdigit() and len(identity.replace("-", "")) == 13:
        customer_id = "Customer • " + identity.replace("-", "")[-4:]
    footer = settings.get("receipt_footer", "NOT_CONFIGURED")

    dec_discount = _money(discount)
    dec_tax = _money(tax)
    grand_total = _money(total)
    subtotal = sum((_item_total(item) for item in items), Decimal("0.00"))
    items = [dict(item, name=str(item.get("name", "Item")) + (" [" + str(item["unit_label"]) + "]" if item.get("unit_label") else "")) for item in items]
    lines = []

    if key == "compact_58":
        lines.extend(_pharmacy_header(width, settings))
        lines.append(sep)
        lines.append(f"Sale #{purchase_id}  {now[:10]}")
        lines.append(f"Pay: {payment_method}")
        lines.append(sep)
        for item in items:
            name = str(item.get("name", "Item"))[:20]
            qty = int(item.get("qty", 1))
            price = Decimal(str(item.get("price", 0)))
            line_total = _item_total(item)
            lines.append(name)
            lines.append(_pair(f" {qty} x {_rate(price)}", f"{line_total:.2f}", width))
        lines.append(sep)
        lines.append(_pair("TOTAL", f"Rs.{grand_total:.2f}", width))
        if amount_received is not None:
            lines.append(_pair("Received", f"Rs.{_money(amount_received):.2f}", width))
        if change is not None:
            lines.append(_pair("Change", f"Rs.{_money(change):.2f}", width))

    elif key == "professional_80":
        lines.append(strong)
        lines.extend(_pharmacy_header(width, settings))
        lines.append(strong)
        lines.append(_center("SALES RECEIPT", width))
        lines.append(sep)
        lines.append(_pair(f"Receipt: #{purchase_id}", now[:10], width))
        lines.append(_pair(f"Cashier: {cashier_name}", now[11:16], width))
        lines.append(f"Customer: {customer_id}")
        lines.append(f"Payment:  {payment_method}")
        lines.append(sep)
        lines.append(f"{'ITEM':<20}{'QTY':>4}{'PRICE':>8}{'AMT':>10}"[:width])
        lines.append(sep)
        for item in items:
            name = str(item.get("name", "Item"))[:19]
            qty = int(item.get("qty", 1))
            price = Decimal(str(item.get("price", 0)))
            line_total = _item_total(item)
            lines.append(f"{name:<20}{qty:>4}{_rate(price):>8}{line_total:>10.2f}"[:width])
        lines.append(sep)
        lines.append(_pair("Subtotal", f"Rs. {subtotal:.2f}", width))
        if dec_discount:
            lines.append(_pair("Discount", f"- Rs. {dec_discount:.2f}", width))
        if dec_tax:
            lines.append(_pair("Tax", f"Rs. {dec_tax:.2f}", width))
        lines.append(strong)
        lines.append(_pair("TOTAL", f"Rs. {grand_total:.2f}", width))
        if amount_received is not None:
            lines.append(_pair("Amount received", f"Rs. {_money(amount_received):.2f}", width))
        if change is not None:
            lines.append(_pair("Change", f"Rs. {_money(change):.2f}", width))
        lines.append(strong)

    elif key == "detailed_80":
        lines.append(strong)
        lines.extend(_pharmacy_header(width, settings))
        lines.append(strong)
        lines.append(f"Invoice: #{purchase_id}")
        lines.append(f"Date: {now}")
        lines.append(f"Cashier: {cashier_name}")
        lines.append(f"Customer: {customer_id}")
        lines.append(f"Payment method: {payment_method}")
        lines.append(sep)
        lines.append(f"{'Product':<18} {'Qty':<4} {'Price':>8} {'Sub':>8}")
        lines.append(sep)
        for item in items:
            name = str(item.get("name", "Item"))[:17]
            qty = int(item.get("qty", 1))
            price = Decimal(str(item.get("price", 0)))
            line_total = _item_total(item)
            lines.append(f"{name:<18} {qty:<4} {_rate(price):>8} {line_total:>8.2f}")
        lines.append(sep)
        lines.append(_pair("Subtotal", f"Rs.{subtotal:.2f}", width))
        lines.append(_pair("Discount", f"Rs.{dec_discount:.2f}", width))
        lines.append(_pair("Tax", f"Rs.{dec_tax:.2f}", width))
        lines.append(strong)
        lines.append(_pair("GRAND TOTAL", f"Rs.{grand_total:.2f}", width))
        if amount_received is not None:
            lines.append(_pair("Amount received", f"Rs.{_money(amount_received):.2f}", width))
        if change is not None:
            lines.append(_pair("Change given", f"Rs.{_money(change):.2f}", width))

    elif key == "tax_invoice_80":
        lines.append(strong)
        lines.extend(_pharmacy_header(width, settings, tax_focused=True))
        lines.append(strong)
        lines.append(_center("TAX INVOICE", width))
        lines.append(sep)
        lines.append(f"Invoice No: {purchase_id}")
        lines.append(f"Date/Time: {now}")
        lines.append(f"Customer: {customer_id}")
        lines.append(f"Cashier: {cashier_name}")
        lines.append(sep)
        lines.append(f"{'Description':<19}{'Qty':>4}{'Rate':>8}{'Amount':>11}"[:width])
        lines.append(sep)
        for item in items:
            name = str(item.get("name", "Item"))[:18]
            qty = int(item.get("qty", 1))
            price = Decimal(str(item.get("price", 0)))
            line_total = _item_total(item)
            lines.append(f"{name:<19}{qty:>4}{_rate(price):>8}{line_total:>11.2f}"[:width])
        lines.append(sep)
        lines.append(_pair("Gross amount", f"Rs.{subtotal:.2f}", width))
        if dec_discount:
            lines.append(_pair("Discount", f"Rs.{dec_discount:.2f}", width))
        lines.append(_pair("Tax", f"Rs.{dec_tax:.2f}", width))
        lines.append(strong)
        lines.append(_pair("NET PAYABLE", f"Rs.{grand_total:.2f}", width))
        lines.append(f"Tender: {payment_method}")

    else:
        lines.append(strong)
        lines.extend(_pharmacy_header(width, settings))
        lines.append(strong)
        lines.append(f"Invoice ID:  #{purchase_id}")
        lines.append(f"Date/Time:   {now}")
        lines.append(f"Cashier:     {cashier_name}")
        lines.append(f"Customer:    {customer_id}")
        lines.append(f"Payment:     {payment_method}")
        lines.append(sep)
        lines.append(f"{'Product':<18} {'Qty':<4} {'Price':>8} {'Sub':>8}")
        lines.append(sep)
        for item in items:
            name = str(item.get("name", "Item"))[:17]
            qty = int(item.get("qty", 1))
            price = Decimal(str(item.get("price", 0)))
            line_total = _item_total(item)
            lines.append(f"{name:<18} {qty:<4} {_rate(price):>8} {line_total:>8.2f}")
        lines.append(sep)
        lines.append(_pair("Subtotal:", f"Rs.{subtotal:.2f}", width))
        if dec_discount:
            lines.append(_pair("Discount:", f"Rs.{dec_discount:.2f}", width))
        if dec_tax:
            lines.append(_pair("Tax:", f"Rs.{dec_tax:.2f}", width))
        lines.append(sep)
        lines.append(_pair("GRAND TOTAL:", f"Rs.{grand_total:.2f}", width))
        if amount_received is not None:
            lines.append(_pair("Amount Received:", f"Rs.{_money(amount_received):.2f}", width))
        if change is not None:
            lines.append(_pair("Change Given:", f"Rs.{_money(change):.2f}", width))
        lines.append(strong)

    if _is_valid_setting(footer):
        lines.append(_center(footer, width))
    lines.append(_center("Thank You for Your Visit!", width))
    lines.append(strong)
    return "\n".join(lines)


def print_receipt_spooler(receipt_text: str, printer_name: str | None = None) -> bool:
    """Send receipt text to a configured OS printer without affecting sale state."""
    try:
        from PySide6.QtGui import QTextDocument, QFont, QPageSize, QPageLayout
        from PySide6.QtCore import QSizeF, QMarginsF
        from PySide6.QtPrintSupport import QPrinter

        from core.lan_config import load_counter_config
        from core.counter_preferences import read as local_preferences
        remote_counter = load_counter_config() is not None
        preferences = local_preferences() if remote_counter else {}
        chosen = str(printer_name or "").strip()
        if not chosen:
            chosen = str(preferences.get("preferred_printer", "") if remote_counter else SettingsService.get_setting("preferred_printer", "") or "").strip()

        if chosen and chosen not in available_printers():
            logger.warning("Configured receipt printer is not currently available: %s", chosen)
            return False

        printer = QPrinter(QPrinter.HighResolution)
        if chosen:
            printer.setPrinterName(chosen)
        if not printer.isValid():
            logger.warning("No valid OS printer is configured for receipt printing.")
            return False

        document = QTextDocument()
        document.setDefaultFont(QFont("Courier New", 9))
        document.setPlainText(receipt_text)
        template = preferences.get('printer_template','standard_80') if remote_counter else _template_key(settings=_receipt_settings())
        width_mm = 58.0 if template == "compact_58" else 80.0
        printer.setPageSize(QPageSize(QSizeF(width_mm, 297.0), QPageSize.Millimeter, "Receipt"))
        printer.setPageMargins(QMarginsF(2, 2, 2, 2), QPageLayout.Millimeter)
        document.print_(printer)
        logger.info("Receipt sent to OS print spooler%s.", f" ({chosen})" if chosen else "")
        return True
    except Exception as exc:
        logger.warning("Print spooler unavailable or printer not configured: %s", exc)
        return False


def create_receipt_snapshot(
    cur, purchase_id, customer_id, items, total, tax, discount,
    payment_method, employee_id, amount_received=None, change=None,
):
    """Capture the exact receipt inside the caller's sale transaction."""
    cur.execute("SELECT receipt_text FROM Receipt_Snapshot WHERE purchase_id = %s", (purchase_id,))
    existing = cur.fetchone()
    if existing:
        return existing[0]
    cur.execute("SELECT First_name, Last_name FROM Employee WHERE Employee_id = %s", (employee_id,))
    employee = cur.fetchone()
    cashier = " ".join(str(part or "").strip() for part in (employee or ())) or "Cashier"
    cur.execute("SELECT first_name, last_name FROM Customers WHERE id_card_number = %s", (customer_id,))
    customer = cur.fetchone()
    customer_label = " ".join(str(part or "").strip() for part in (customer or ())).strip()
    customer_label = customer_label or "Walk-in Customer"
    cur.execute("SELECT printing_date, time FROM Receipt WHERE purchase_id = %s", (purchase_id,))
    receipt = cur.fetchone()
    stamp = " ".join(str(part) for part in receipt) if receipt else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = _template_key(settings=_receipt_settings())
    text = generate_invoice_text(
        purchase_id, customer_label, items, total, tax, discount,
        payment_method, cashier, amount_received, change, template,
        sale_datetime=stamp,
    )
    cur.execute(
        "INSERT INTO Receipt_Snapshot (purchase_id, receipt_text, template, created_at) VALUES (%s,%s,%s,%s)",
        (purchase_id, text, template, stamp),
    )
    return text


def receipt_for_sale(purchase_id):
    """Read immutable content; legacy receipts are rebuilt from saved sale facts."""
    from core.db_engine import get_db
    purchase_id = int(purchase_id)
    with get_db() as (_conn, cur):
        cur.execute(
            "SELECT receipt_text, print_status FROM Receipt_Snapshot WHERE purchase_id = %s", (purchase_id,),
        )
        snapshot = cur.fetchone()
        if not snapshot:
            cur.execute(
                "SELECT p.customer_id,p.price_with_tax,COALESCE(p.total_tax,p.price_with_tax-p.total_price),p.discount_amount,p.payment_method,p.employee_id "
                "FROM Purchase p WHERE p.id=%s", (purchase_id,),
            )
            sale = cur.fetchone()
            if not sale:
                raise ValueError("That saved sale could not be found.")
            cur.execute(
                "SELECT p.product_name,sd.Quantity,sd.unit_price,sd.line_subtotal "
                "FROM Sales_details sd JOIN Batch b ON b.id=sd.batch_id "
                "JOIN Products p ON p.id=b.product_id WHERE sd.purchase_id=%s", (purchase_id,),
            )
            items = [{"name": name, "qty": qty, "price": price, "subtotal": subtotal}
                     for name, qty, price, subtotal in cur.fetchall()]
            if any(item["price"] is None for item in items):
                raise ValueError("This older receipt has incomplete price history. Ask the owner for help.")
            text = create_receipt_snapshot(cur, purchase_id, sale[0], items, sale[1], sale[2], sale[3], sale[4], sale[5])
            snapshot = (text, "SAVED")
    return {"purchase_id": purchase_id, "receipt_text": snapshot[0],
            "filepath": os.path.join(PathManager.get_receipts_dir(), f"sale_{purchase_id}.txt"),
            "print_status": snapshot[1]}


def _update_print_status(purchase_id, printed):
    from core.db_engine import get_db
    with get_db() as (_conn, cur):
        cur.execute(
            "UPDATE Receipt_Snapshot SET print_status=%s,print_attempts=print_attempts+1, "
            "last_printed_at=CASE WHEN %s THEN %s ELSE last_printed_at END WHERE purchase_id=%s",
            ("SENT_TO_PRINTER" if printed else "PRINT_PENDING", bool(printed), datetime.now().isoformat(), int(purchase_id)),
        )


def reprint_sale_receipt(purchase_id):
    """Print a saved sale without creating or changing any business transaction."""
    try:
        saved = receipt_for_sale(purchase_id)
        # A repeated physical copy is visibly distinguished from the original.
        printed = print_receipt_spooler("REPRINT — Sale #" + str(purchase_id) + "\n" + saved["receipt_text"])
        _update_print_status(purchase_id, printed)
        return (True, "Receipt sent to the printer.") if printed else (False, "Sale is saved. Check the printer and retry printing.")
    except Exception as exc:
        logger.error("Saved receipt printing failed for sale %s: %s", purchase_id, exc)
        return False, "Sale is saved. The receipt could not be printed. Ask the owner for help."


def generate_invoice_file(
    purchase_id,
    customer_id,
    items,
    total,
    tax,
    discount,
    payment_method="Cash",
    cashier_name="Cashier",
    amount_received=None,
    change=None,
    template=None,
):
    """Persist a receipt snapshot and optionally queue it for printing.

    File creation/printing happen after checkout commit in the transaction
    service. A printer failure therefore never reverses or duplicates a sale.
    """
    try:
        receipts_dir = PathManager.get_receipts_dir()
        os.makedirs(receipts_dir, exist_ok=True)
        filepath = os.path.join(receipts_dir, f"sale_{purchase_id}.txt")
        actual_payment, actual_cashier = _purchase_receipt_context(
            purchase_id,
            payment_method,
            cashier_name,
        )
        content = generate_invoice_text(
            purchase_id,
            customer_id,
            items,
            total,
            tax,
            discount,
            actual_payment,
            actual_cashier,
            amount_received,
            change,
            template,
        )
        # The sale transaction already committed its snapshot. Never regenerate
        # historical content from changed settings/catalog data during export.
        try:
            saved = receipt_for_sale(purchase_id)
            content = saved["receipt_text"]
        except ValueError:
            # Rendering helpers may also be used without a real sale (preview).
            pass
        with open(filepath + ".partial", "w", encoding="utf-8") as file_handle:
            file_handle.write(content)
        os.replace(filepath + ".partial", filepath)

        print_settings = SettingsService.get_many(
            ("receipt_auto_print", "preferred_printer"),
            {"receipt_auto_print": "0", "preferred_printer": ""},
        )
        from core.runtime_context import remote_request
        if _truthy(print_settings.get("receipt_auto_print")) and not remote_request.get():
            printed = print_receipt_spooler(content, print_settings.get("preferred_printer"))
            _update_print_status(purchase_id, printed)
            if not printed:
                logger.warning(
                    "Sale #%s receipt was saved but automatic printing did not complete.",
                    purchase_id,
                )
        return filepath
    except Exception as exc:
        logger.error("Receipt generation error: %s", exc)
        return None


def print_test_receipt(printer_name: str | None = None, template: str | None = None) -> bool:
    sample = generate_invoice_text(
        "TEST",
        "Walk-in Customer",
        [
            {"name": "Sample Medicine", "qty": 1, "price": 125.00},
            {"name": "Sample Item", "qty": 2, "price": 50.00},
        ],
        total=225.00,
        tax=0.00,
        discount=0.00,
        payment_method="Cash",
        cashier_name="Printer Test",
        amount_received=500.00,
        change=275.00,
        template=template,
    )
    return print_receipt_spooler(sample, printer_name)
