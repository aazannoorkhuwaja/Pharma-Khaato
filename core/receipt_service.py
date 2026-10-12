import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from core.path_manager import PathManager
from core.settings_service import SettingsService
from core.logger import get_logger

logger = get_logger("PharmaKhaatoReceipt")

def _is_valid_setting(val):
    if not val:
        return False
    clean = str(val).strip()
    return clean and clean.upper() not in ("NOT_CONFIGURED", "N/A", "NONE", "NULL")

def generate_invoice_text(purchase_id, customer_id, items, total, tax, discount, payment_method="Cash", cashier_name="Cashier", amount_received=None, change=None):
    """
    Generates formatted 80mm ESC/POS thermal text receipt content using dynamic SettingsService values.
    Omits unconfigured regulatory fields and consumes authoritative transaction financial values.
    """
    p_name = SettingsService.get_setting("pharmacy_name", "Pharma-Khaato POS")
    p_slogan = SettingsService.get_setting("slogan", "NOT_CONFIGURED")
    p_address = SettingsService.get_setting("address", "NOT_CONFIGURED")
    p_phone = SettingsService.get_setting("phone", "NOT_CONFIGURED")
    p_lic = SettingsService.get_setting("license_number", "NOT_CONFIGURED")
    p_ntn = SettingsService.get_setting("ntn_number", "NOT_CONFIGURED")
    p_footer = SettingsService.get_setting("receipt_footer", "NOT_CONFIGURED")

    dec_discount = Decimal(str(discount or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    dec_tax_amount = Decimal(str(tax or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    lines = []
    lines.append("==========================================")
    lines.append(f"{p_name[:42].center(42)}")
    if _is_valid_setting(p_slogan):
        lines.append(f"{p_slogan[:42].center(42)}")
    if _is_valid_setting(p_address):
        lines.append(f"{p_address[:42].center(42)}")
    if _is_valid_setting(p_phone):
        lines.append(f"Phone: {p_phone}".center(42))
    
    lic_parts = []
    if _is_valid_setting(p_lic):
        lic_parts.append(f"Lic: {p_lic}")
    if _is_valid_setting(p_ntn):
        lic_parts.append(f"NTN: {p_ntn}")
    if lic_parts:
        lic_line = " | ".join(lic_parts)
        lines.append(f"{lic_line[:42].center(42)}")

    lines.append("==========================================")
    lines.append(f"Invoice ID:  #{purchase_id}")
    lines.append(f"Date/Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Cashier:     {cashier_name}")
    lines.append(f"Customer:    {customer_id}")
    lines.append(f"Payment:     {payment_method}")
    lines.append("------------------------------------------")
    lines.append(f"{'Product':<18} {'Qty':<4} {'Price':>8} {'Sub':>8}")
    lines.append("------------------------------------------")

    subtotal_dec = Decimal("0.00")
    for item in items:
        name = str(item.get("name", "Item"))[:17]
        qty = int(item.get("qty", 1))
        prc = Decimal(str(item.get("price", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sub = (prc * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal_dec += sub
        lines.append(f"{name:<18} {qty:<4} {prc:>8.2f} {sub:>8.2f}")

    grand_total_dec = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    lines.append("------------------------------------------")
    lines.append(f"{'Subtotal:':<28} Rs.{subtotal_dec:>9.2f}")
    if dec_discount > Decimal("0.00"):
        lines.append(f"{'Discount:':<28} Rs.{dec_discount:>9.2f}")
    if dec_tax_amount > Decimal("0.00"):
        lines.append(f"{'Tax:':<28} Rs.{dec_tax_amount:>9.2f}")
    lines.append("------------------------------------------")
    lines.append(f"{'GRAND TOTAL:':<28} Rs.{grand_total_dec:>9.2f}")

    if amount_received is not None:
        rec_dec = Decimal(str(amount_received)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines.append(f"{'Amount Received:':<28} Rs.{rec_dec:>9.2f}")
    if change is not None:
        chg_dec = Decimal(str(change)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines.append(f"{'Change Given:':<28} Rs.{chg_dec:>9.2f}")

    lines.append("==========================================")
    if _is_valid_setting(p_footer):
        lines.append(f"{p_footer[:42].center(42)}")
    lines.append("    Thank You for Your Visit!    ".center(42))
    lines.append("==========================================")

    return "\n".join(lines)

def generate_invoice_file(purchase_id, customer_id, items, total, tax, discount, payment_method="Cash", cashier_name="Cashier", amount_received=None, change=None):
    """
    Generates thermal text receipt and writes to local receipts/ directory.
    Returns file path.
    """
    try:
        receipts_dir = PathManager.get_receipts_dir()
        os.makedirs(receipts_dir, exist_ok=True)

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"invoice_{now_str}_{purchase_id}.txt"
        filepath = os.path.join(receipts_dir, filename)

        content = generate_invoice_text(
            purchase_id, customer_id, items, total, tax, discount, payment_method, cashier_name, amount_received, change
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath
    except Exception as e:
        logger.error(f"Receipt generation error: {e}")
        return None


def print_receipt_spooler(receipt_text: str) -> bool:
    """
    Sends thermal receipt text to the OS print spooler using Qt QPrinter when printer hardware is present.
    Returns True if print job was successfully queued.
    """
    try:
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        doc = QTextDocument()
        doc.setPlainText(receipt_text)
        doc.print_(printer)
        logger.info("Receipt sent to OS print spooler successfully.")
        return True
    except Exception as e:
        logger.warning(f"Print spooler unavailable or hardware printer not configured: {e}")
        return False
