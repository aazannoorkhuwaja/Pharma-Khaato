import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from core.db_engine import get_conn, get_db
from core.receipt_service import generate_invoice_file
from core.inventory_service import clear_inventory_cache
from core.logger import get_logger
from core.permission_service import require_permission

logger = get_logger("PharmaKhaatoPOS")
_CHECKOUT_LOCK = threading.Lock()


def _normalize_payment_method(payment_method: str) -> tuple[str, str]:
    """Return (canonical tender label, accounting class).

    Historical callers used both ``Khatoo Credit`` and ``Credit (Khatoo)``.
    Normalizing at the service boundary keeps the database/reporting value
    consistent and prevents credit sales from being misclassified as cash.
    """
    raw = str(payment_method or "Cash").strip()
    key = " ".join(raw.lower().replace("_", " ").split())
    if key in {"khatoo credit", "credit (khatoo)", "khatoo"}:
        return "Khatoo Credit", "Credit"
    if key in {"cash", ""}:
        return "Cash", "Cash"
    return raw, "Cash"


@dataclass
class CheckoutRequest:
    customer_id: str
    employee_id: int
    cart: list
    discount: float = 0.0
    payment_method: str = "Cash"
    total: float = 0.0


@dataclass
class CheckoutResult:
    success: bool
    message: str
    purchase_id: int | None = None
    net_total: float = 0.0
    total_tax: float = 0.0
    discount: float = 0.0


class POSTransactionEngine:
    """
    Unified high-locality seam for POS sales transactions,
    FEFO multi-batch allocation, financial precision, and invoice generation.
    """

    @staticmethod
    def process_checkout(req: CheckoutRequest) -> CheckoutResult:
        success, msg = confirm_sale(
            customer_id=req.customer_id,
            employee_id=req.employee_id,
            cart=req.cart,
            total=req.total,
            discount=req.discount,
            payment_method=req.payment_method
        )
        purchase_id = None
        if success and "Sale #" in msg:
            try:
                purchase_id = int(msg.split("Sale #")[1].split(" ")[0])
            except (ValueError, IndexError, AttributeError) as parse_err:
                logger.warning(f"Handled sale ID parse notice: {parse_err}")
        return CheckoutResult(success=success, message=msg, purchase_id=purchase_id)


def allocate_sellable_batches(product_id, qty_needed, conn=None):
    """
    FEFO (First-Expired-First-Out) multi-batch allocation engine.
    Allocates requested quantity across active, non-expired batches ordered by expiry date.
    Returns list of dicts: [{"batch_id": int, "quantity": int, "expiry_date": str}]
    or empty list if total available stock < qty_needed.
    """
    own_conn = False
    if conn is None:
        conn = get_conn()
        own_conn = True

    if not conn:
        return []
    try:
        cur = conn.cursor()
        today = date.today().strftime("%Y-%m-%d")
        cur.execute(
            "SELECT id, quantity, expiry_date FROM Batch "
            "WHERE product_id = %s AND expiry_date > %s AND quantity > 0 "
            "ORDER BY expiry_date ASC, id ASC",
            (product_id, today)
        )
        batches = cur.fetchall()
        if not batches:
            return []

        allocations = []
        remaining = qty_needed
        for b_id, b_qty, b_exp in batches:
            if remaining <= 0:
                break
            take = min(remaining, b_qty)
            allocations.append({
                "batch_id": b_id,
                "quantity": take,
                "expiry_date": str(b_exp)
            })
            remaining -= take

        if remaining > 0:
            return []

        return allocations
    except Exception as e:
        logger.error(f"FEFO allocation error for product {product_id}: {e}")
        return []
    finally:
        if own_conn and conn:
            conn.close()


def get_sellable_batch(product_id, qty_needed=1, conn=None):
    """
    Returns primary FEFO batch for product_id.
    Delegates to allocate_sellable_batches.
    """
    allocs = allocate_sellable_batches(product_id, qty_needed, conn=conn)
    return allocs[0] if allocs else None


# ---------------------------------------------------------------------------
# Internal seam 1 — CartValidator
# Validates quantities, enforces credit rules, runs FEFO allocation.
# Returns a consolidated list of resolved cart items ready for writing,
# or raises ValueError with a human-readable message on any failure.
# Takes an open cursor so it participates in the caller's transaction.
# ---------------------------------------------------------------------------
def _validate_and_allocate_cart(cur, cart, customer_id, employee_id, total, pay_label, conn):
    """
    Pure validation + FEFO allocation pass over a raw cart.

    Inputs:
        cur         — active db cursor (participates in caller's transaction)
        cart        — list of cart item dicts from the UI
        customer_id — CNIC string
        employee_id — int
        total       — declared cart total (used for credit limit check)
        pay_label   — "Cash" or "Credit"
        conn        — connection reference (needed for allocate_sellable_batches)

    Returns:
        final_items — list of consolidated, batch-resolved cart item dicts:
                      [{"prod_id", "name", "price", "batch_id", "qty", "subtotal"}, ...]

    Raises:
        ValueError  — with a user-facing message on any validation failure.
    """
    today = date.today().strftime("%Y-%m-%d")

    # Employee existence guard
    try:
        emp_id_int = int(employee_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid employee ID '{employee_id}'. Cannot process checkout.")
    cur.execute("SELECT Employee_id FROM Employee WHERE Employee_id = %s", (emp_id_int,))
    if not cur.fetchone():
        raise ValueError(f"Employee ID #{emp_id_int} not found. Please log in again before checkout.")

    # Customer existence guard
    cur.execute("SELECT id_card_number FROM Customers WHERE id_card_number = %s", (customer_id,))
    if not cur.fetchone():
        if customer_id == "WALKIN":
            cur.execute(
                "INSERT OR IGNORE INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date) "
                "VALUES ('WALKIN', 'Walk-in', 'Customer', 'N/A', 'N/A', '2026-01-01')"
            )
        elif pay_label == "Credit":
            raise ValueError(
                f"Customer CNIC '{customer_id}' is not registered. "
                "Credit (Khatoo) checkout requires a registered customer."
            )

    # Per-item quantity validation + FEFO batch resolution
    expanded_cart = []
    for item in cart:
        try:
            qty = int(item.get("qty", 0))
            if qty <= 0:
                raise ValueError(f"Invalid quantity ({qty}) specified for item '{item.get('name', 'Unknown')}'.")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Non-numeric quantity for item '{item.get('name', 'Unknown')}'.") from exc

        prod_id = item["prod_id"]
        price_dec = Decimal(str(item.get("price", 0.0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # If the UI supplied a specific batch, validate it first
        batch_id = item.get("batch_id")
        if batch_id:
            cur.execute("SELECT quantity, expiry_date FROM Batch WHERE id = %s", (batch_id,))
            res = cur.fetchone()
            if res:
                current_qty, exp_date = res
                exp_date_str = str(exp_date)
                if exp_date_str <= today:
                    raise ValueError(
                        f"STOP! Medicine '{item.get('name')}' (Batch #{batch_id}) is EXPIRED ({exp_date_str})."
                    )
                if current_qty >= qty:
                    expanded_cart.append({
                        "prod_id": prod_id,
                        "name": item.get("name"),
                        "price": float(price_dec),
                        "batch_id": batch_id,
                        "qty": qty,
                        "subtotal": float(price_dec * qty),
                    })
                    continue

        # Fall back to FEFO multi-batch allocation
        allocations = allocate_sellable_batches(prod_id, qty, conn=conn)
        if not allocations:
            raise ValueError(
                f"Insufficient valid non-expired stock for product '{item.get('name')}'. Requested: {qty}."
            )
        for alloc in allocations:
            expanded_cart.append({
                "prod_id": prod_id,
                "name": item.get("name"),
                "price": float(price_dec),
                "batch_id": alloc["batch_id"],
                "qty": alloc["quantity"],
                "subtotal": float(price_dec * alloc["quantity"]),
            })

    # Consolidate split-batch rows for the same batch_id
    consolidated: dict = {}
    for item in expanded_cart:
        bid = item["batch_id"]
        if bid in consolidated:
            consolidated[bid]["qty"] += item["qty"]
            consolidated[bid]["subtotal"] += item["subtotal"]
        else:
            consolidated[bid] = item.copy()

    return list(consolidated.values())


# ---------------------------------------------------------------------------
# Internal seam 2 — SaleTotals
# Pure financial calculation — zero I/O, zero DB, unit-testable stand-alone.
# ---------------------------------------------------------------------------
@dataclass
class SaleFinancials:
    net_total: float
    tax_amount: float
    price_with_tax: float
    discount: float


def calculate_sale_totals(final_items: list, discount: float, tax_rate_dec: Decimal) -> SaleFinancials:
    """
    Pure function: derives all monetary values for a resolved cart.

    Inputs:
        final_items  — consolidated list of cart item dicts (from _validate_and_allocate_cart)
        discount     — discount amount as float
        tax_rate_dec — tax rate as a properly scaled Decimal (e.g. Decimal("0.10") for 10%)

    Returns:
        SaleFinancials dataclass with net_total, tax_amount, price_with_tax, discount (all floats).

    No I/O. No database. No side effects.
    """
    disc_dec = Decimal(str(discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    subtotal_dec = sum(
        (Decimal(str(i["price"])) * i["qty"] for i in final_items),
        Decimal("0.00"),
    )
    net_total_dec = max(subtotal_dec - disc_dec, Decimal("0.00"))
    tax_amount_dec = (net_total_dec * tax_rate_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    price_with_tax_dec = (net_total_dec + tax_amount_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return SaleFinancials(
        net_total=float(net_total_dec),
        tax_amount=float(tax_amount_dec),
        price_with_tax=float(price_with_tax_dec),
        discount=float(disc_dec),
    )


# ---------------------------------------------------------------------------
# Internal seam 3 — SaleWriter
# Pure SQL writer — accepts resolved data, executes all INSERTs/UPDATEs,
# returns the new purchase_id. No business logic, no financial maths.
# ---------------------------------------------------------------------------
def _write_sale_to_db(cur, customer_id, employee_id, pay_label, final_items, financials: SaleFinancials, payment_method: str = "Cash"):
    """
    Writes a fully resolved sale to the database inside an existing transaction.
    pay_label drives Cash-vs-Credit behaviour (Khatoo ledger); payment_method
    preserves the actual tender type (Cash/Credit Card/Easypaisa/JazzCash/
    Khatoo Credit) on the Purchase row for reporting.

    Inputs:
        cur         — active db cursor
        customer_id — CNIC string
        employee_id — int
        pay_label   — "Cash" or "Credit"
        final_items — consolidated cart item list from _validate_and_allocate_cart
        financials  — SaleFinancials from calculate_sale_totals

    Returns:
        purchase_id — integer PK of the inserted Purchase row.

    No validation. No financial logic. Only SQL.
    """
    today = date.today().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")

    # INSERT Purchase header
    cur.execute(
        "INSERT INTO Purchase "
        "(number_of_products, total_price, price_with_tax, customer_id, employee_id, payment_method, discount_amount) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            len(final_items),
            financials.net_total,
            financials.price_with_tax,
            customer_id,
            employee_id,
            payment_method,
            financials.discount,
        ),
    )
    purchase_id = cur.lastrowid

    # INSERT Sales_details + deduct Batch and Products stock
    for item in final_items:
        cur.execute(
            "INSERT INTO Sales_details (purchase_id, batch_id, Quantity) VALUES (%s, %s, %s)",
            (purchase_id, item["batch_id"], item["qty"]),
        )
        cur.execute(
            "UPDATE Batch SET quantity = quantity - %s WHERE id = %s AND quantity >= %s",
            (item["qty"], item["batch_id"], item["qty"]),
        )
        if cur.rowcount == 0:
            raise ValueError(
                f"Stock conflict: Batch #{item['batch_id']} does not have sufficient stock ({item['qty']} requested)."
            )
        cur.execute(
            "UPDATE Products SET stock_quantity = stock_quantity - %s WHERE id = %s AND stock_quantity >= %s",
            (item["qty"], item["prod_id"], item["qty"]),
        )
        if cur.rowcount == 0:
            # Batch and product-level totals have diverged — abort rather
            # than silently desync inventory.
            raise ValueError(
                f"Stock conflict: Product #{item['prod_id']} does not have "
                f"sufficient aggregate stock ({item['qty']} requested)."
            )

    # INSERT Receipt
    cur.execute(
        "INSERT INTO Receipt (printing_date, time, purchase_id, number_of_items) VALUES (%s, %s, %s, %s)",
        (today, now_time, purchase_id, len(final_items)),
    )

    # INSERT Khatoo ledger entry for credit sales
    if pay_label == "Credit":
        cur.execute(
            "INSERT INTO Customer_Khatoo "
            "(amount_paid, amount_due, purchase_id, customer_id, payment_method) "
            "VALUES (%s, %s, %s, %s, %s)",
            (0.0, financials.price_with_tax, purchase_id, customer_id, "Credit"),
        )

    return purchase_id


# ---------------------------------------------------------------------------
# Public API — confirm_sale
# Thin orchestrator: acquires lock, delegates to the three internal seams,
# commits, then fires decoupled side-effects (audit + receipt).
# Interface is unchanged — all existing callers continue to work.
# ---------------------------------------------------------------------------
def confirm_sale(customer_id, employee_id, cart, *, total=0.0, discount=0.0, payment_method="Cash"):
    """
    Executes an atomic checkout transaction for a shopping cart.
    Protected by _CHECKOUT_LOCK against concurrent double-checkout submissions.

    Delegates to three internal seams:
      1. _validate_and_allocate_cart  — input validation + FEFO batch resolution
      2. calculate_sale_totals        — pure financial calculation
      3. _write_sale_to_db            — SQL INSERT/UPDATE, no logic

    Side-effects (audit log, receipt file) run after commit and do not
    trigger a rollback on failure.
    """
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Your staff account could not be verified. Sign in again."

    allowed, permission_reason = require_permission(employee_id, "pos.sell")
    if not allowed:
        return False, permission_reason

    if not _CHECKOUT_LOCK.acquire(blocking=False):
        return False, "Checkout request already in progress. Duplicate submission prevented."

    try:
        return _confirm_sale_locked(customer_id, employee_id, cart, total=total, discount=discount, payment_method=payment_method)
    finally:
        _CHECKOUT_LOCK.release()


def _confirm_sale_locked(customer_id, employee_id, cart, *, total=0.0, discount=0.0, payment_method="Cash"):
    """Body of confirm_sale — caller owns the _CHECKOUT_LOCK lifecycle."""

    # CRITICAL: normalize customer identity ONCE at the boundary. All debt
    # lookups (get_customer_total_debt etc.) use validate_cnic()'s 13-digit
    # normalized form — storing a dashed/raw string here makes debt silently
    # unreadable and defeats credit-limit enforcement.
    if customer_id:
        from core.customer_service import validate_cnic
        normalized = validate_cnic(customer_id)
        if not normalized and str(customer_id).strip().upper() != "WALKIN":
            return False, f"Invalid Customer ID/CNIC format: '{customer_id}'."
        customer_id = normalized or "WALKIN"
    else:
        customer_id = "WALKIN"

    conn = None
    try:
        conn = get_conn()
        if not conn:
            return False, "Database connection offline."

        if not cart:
            return False, "Cart is empty."

        cur = conn.cursor()
        payment_method, pay_label = _normalize_payment_method(payment_method)
        # Validate discount sign before passing to pure function
        disc_dec = Decimal(str(discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if disc_dec < Decimal("0.00"):
            return False, "Discount cannot be a negative amount."

        # Seam 1 — validate cart and resolve FEFO batches
        final_items = _validate_and_allocate_cart(cur, cart, customer_id, employee_id, total, pay_label, conn)

        # Resolve tax rate — normalisation lives in SettingsService.get_tax_rate()
        from core.settings_service import SettingsService
        tax_rate_dec = SettingsService.get_tax_rate()

        # Seam 2 — pure financial calculation
        financials = calculate_sale_totals(final_items, float(disc_dec), tax_rate_dec)

        # Post-tax credit limit validation for Khatoo Credit payment mode
        if pay_label == "Credit":
            from core.customer_service import check_customer_credit_limit
            ok_limit, limit_msg = check_customer_credit_limit(customer_id, float(financials.price_with_tax), conn=conn)
            if not ok_limit:
                raise ValueError(limit_msg)

        # Seam 3 — write to DB
        purchase_id = _write_sale_to_db(cur, customer_id, employee_id, pay_label, final_items, financials, payment_method)

        conn.commit()
        clear_inventory_cache()

        # Decoupled side-effects — failures here do NOT rollback the committed sale
        try:
            from core.audit_service import log_audit_event
            log_audit_event(
                employee_id,
                "POS_CHECKOUT_SUCCESS",
                f"Sale #{purchase_id} committed ({pay_label}). Net: Rs.{financials.net_total:.2f}",
            )
        except (sqlite3.Error, ValueError, OSError) as audit_err:
            logger.warning(f"Handled checkout audit logging notice: {audit_err}")

        try:
            generate_invoice_file(
                purchase_id, customer_id, final_items,
                financials.price_with_tax, financials.tax_amount,
                financials.discount, pay_label,
            )
        except Exception as pe:
            logger.warning(f"Receipt generation issue for sale #{purchase_id}: {pe}")

        return True, f"Sale #{purchase_id} recorded successfully! Invoice generated."

    except ValueError as ve:
        if conn:
            conn.rollback()
        return False, str(ve)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Checkout transaction failed: {e}")
        return False, f"Checkout failed: {e}"
    finally:
        try:
            if conn:
                conn.close()
        except (sqlite3.Error, OSError) as close_err:
            logger.warning(f"Handled checkout connection close notice: {close_err}")


def get_sales_history():
    """Returns complete list of purchase sales transactions."""
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, r.printing_date, r.time, c.first_name || ' ' || c.last_name, p.price_with_tax, p.payment_method "
            "FROM Purchase p "
            "JOIN Receipt r ON p.id = r.purchase_id "
            "LEFT JOIN Customers c ON p.customer_id = c.id_card_number "
            "ORDER BY p.id DESC"
        )
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Sales history fetch error: {e}")
        return []
    finally:
        conn.close()


def get_purchase_items(purchase_id):
    """Returns itemized breakdown for a specific purchase ID."""
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.product_name, sd.batch_id, sd.Quantity, p.price, (sd.Quantity * p.price) as subtotal "
            "FROM Sales_details sd "
            "JOIN Batch b ON sd.batch_id = b.id "
            "JOIN Products p ON b.product_id = p.id "
            "WHERE sd.purchase_id = %s",
            (purchase_id,)
        )
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Fetch purchase items error: {e}")
        return []
    finally:
        conn.close()


def process_sale_return(purchase_id: int, return_items: list, reason: str = "Customer Return", employee_id: int = 1, restock_sellable: bool = True):
    """
    Processes formal sales item returns and refunds.
    Persists formal audit records in Customer_Returns and Return_Items tables.
    Inputs:
        purchase_id      - Original purchase ID
        return_items     - List of dicts: [{"batch_id": int, "qty": int, "prod_id": int, "price": float}]
        reason           - Reason string for audit log
        employee_id      - Authorizing employee ID
        restock_sellable - If True, returns stock to sellable Batch; if False, flags as damaged/quarantine
    Returns:
        (success: bool, message: str)
    """
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return False, "Your staff account could not be verified. Sign in again."
    allowed, permission_reason = require_permission(employee_id, "returns.process")
    if not allowed:
        return False, permission_reason

    if not return_items:
        return False, "No return items specified."

    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT customer_id, payment_method FROM Purchase WHERE id = %s", (purchase_id,))
            row = cur.fetchone()
            if not row:
                return False, f"Purchase #{purchase_id} not found."
            customer_id = row[0] if row and row[0] else "WALKIN"
            payment_method = str(row[1]) if len(row) > 1 and row[1] else "Cash"

            today_str = date.today().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")

            total_refund = Decimal("0.00")
            valid_items = []
            for item in return_items:
                qty = int(item.get("qty", 0))
                if qty <= 0:
                    continue
                batch_id = item.get("batch_id")
                prod_id = item.get("prod_id")

                # Guard: cannot return more than was sold on this purchase line.
                cur.execute(
                    "SELECT COALESCE(SUM(Quantity), 0) FROM Sales_details "
                    "WHERE purchase_id = %s AND batch_id = %s",
                    (purchase_id, batch_id),
                )
                sold_qty = int(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(ri.quantity), 0) FROM Return_Items ri "
                    "JOIN Customer_Returns cr ON ri.return_id = cr.id "
                    "WHERE cr.purchase_id = %s AND ri.batch_id = %s",
                    (purchase_id, batch_id),
                )
                already_returned = int(cur.fetchone()[0] or 0)
                if qty > sold_qty - already_returned:
                    return False, (
                        f"Cannot return {qty} of batch #{batch_id}: only "
                        f"{max(sold_qty - already_returned, 0)} remain returnable on this sale."
                    )

                unit_price = Decimal(str(item.get("price", 0.0)))
                subtotal = (unit_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_refund += subtotal
                valid_items.append((item, qty, unit_price, subtotal))

            if not valid_items:
                return False, "No valid item quantities to return."

            cur.execute(
                "INSERT INTO Customer_Returns (purchase_id, customer_id, employee_id, refund_amount, reason, return_date, return_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (purchase_id, customer_id, employee_id, float(total_refund), reason, today_str, time_str)
            )
            return_id = cur.lastrowid

            restock_label = "RESTOCKED" if restock_sellable else "DAMAGED_QUARANTINE"
            for item, qty, unit_price, subtotal in valid_items:
                batch_id = item["batch_id"]
                prod_id = item["prod_id"]

                cur.execute(
                    "INSERT INTO Return_Items (return_id, product_id, batch_id, quantity, unit_price, subtotal, restock_status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (return_id, prod_id, batch_id, qty, float(unit_price), float(subtotal), restock_label)
                )

                if restock_sellable:
                    cur.execute(
                        "UPDATE Batch SET quantity = quantity + %s WHERE id = %s",
                        (qty, batch_id)
                    )
                    cur.execute(
                        "UPDATE Products SET stock_quantity = stock_quantity + %s WHERE id = %s",
                        (qty, prod_id)
                    )

            # Credit-sale returns reduce the Khatoo ledger debt, not cash.
            if payment_method == "Khatoo Credit" and customer_id and customer_id != "WALKIN":
                cur.execute(
                    "SELECT id, amount_due FROM Customer_Khatoo "
                    "WHERE purchase_id = %s AND customer_id = %s ORDER BY id DESC LIMIT 1",
                    (purchase_id, customer_id),
                )
                khatoo_row = cur.fetchone()
                if khatoo_row:
                    ledger_id, amount_due = khatoo_row[0], Decimal(str(khatoo_row[1]))
                    reduction = min(total_refund, max(amount_due, Decimal("0.00")))
                    cur.execute(
                        "UPDATE Customer_Khatoo SET amount_due = amount_due - %s, "
                        "amount_paid = amount_paid + %s WHERE id = %s",
                        (float(reduction), float(reduction), ledger_id),
                    )

            # Record audit log event for sale return
            try:
                from core.audit_service import log_audit_event
                log_audit_event(
                    employee_id,
                    "SALE_RETURN",
                    f"Returned {len(valid_items)} items for Purchase #{purchase_id}. Refund: Rs.{total_refund:.2f}. Reason: {reason}"
                )
            except (sqlite3.Error, ValueError, OSError) as audit_err:
                logger.warning(f"Handled return audit logging notice: {audit_err}")

        logger.info(f"Sale return #{return_id} processed for Purchase #{purchase_id}. Refund Amount: Rs.{total_refund:.2f}")
        return True, f"Return #{return_id} processed successfully. Refund Due: Rs. {total_refund:.2f}"
    except Exception as e:
        logger.error(f"Sale return failed for Purchase #{purchase_id}: {e}")
        return False, f"Return failed: {e}"