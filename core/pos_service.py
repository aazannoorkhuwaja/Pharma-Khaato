from core.business_time import business_date, business_now
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from core.db_engine import get_conn, get_db
from core.receipt_service import generate_invoice_file
from core.inventory_service import clear_inventory_cache
from core.logger import get_logger

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
    methods = {"cash": "Cash", "": "Cash", "card": "Credit Card",
               "credit card": "Credit Card", "easypaisa": "Easypaisa", "jazzcash": "JazzCash"}
    if key not in methods:
        raise ValueError("Choose Cash, Card, Easypaisa, JazzCash, or Customer Credit.")
    return methods[key], "Cash"


@dataclass
class CheckoutRequest:
    customer_id: str
    employee_id: int
    cart: list
    discount: float = 0.0
    payment_method: str = "Cash"
    total: float = 0.0
    checkout_token: str | None = None
    held_sale_id: int | None = None
    cash_received: float | None = None
    manager_approval_token: str | None = None
    terminal_id: str | None = None
    expected_total: float | None = None


@dataclass
class CheckoutResult:
    success: bool
    message: str
    purchase_id: int | None = None
    net_total: float = 0.0
    total_tax: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    payment_method: str = ""
    cash_received: float | None = None
    change_due: float = 0.0
    outcome: str = "rejected"
    duplicate: bool = False
    receipt_status: str = 'SAVED'


class POSTransactionEngine:
    """
    Unified high-locality seam for POS sales transactions,
    FEFO multi-batch allocation, financial precision, and invoice generation.
    """

    @staticmethod
    def process_checkout(req: CheckoutRequest) -> CheckoutResult:
        return _execute_checkout(req)


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
        today = business_date().strftime("%Y-%m-%d")
        cur.execute(
            "SELECT id, quantity, expiry_date FROM Batch "
            "WHERE product_id = %s AND expiry_date >= %s AND quantity > 0 AND stock_status = 'SELLABLE' "
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
    from core.permission_service import require_permission
    from core.unit_service import whole_quantity, resolve_unit
    allowed, reason = require_permission(employee_id, "pos.sell")
    if not allowed:
        raise ValueError(reason)
    if pay_label == "Credit" and customer_id == "WALKIN":
        raise ValueError("Select a registered customer before using customer credit.")
    cur.execute("SELECT id_card_number FROM Customers WHERE id_card_number=%s", (customer_id,))
    if not cur.fetchone():
        raise ValueError("The selected customer no longer exists. Select the customer again.")
    if not isinstance(cart, list) or not cart:
        raise ValueError("Cart is empty.")
    if len(cart) > 1000:
        raise ValueError("This sale contains too many lines.")
    today = business_date().isoformat()
    expanded = []
    reserved = {}
    for item in cart:
        qty_selected = whole_quantity(item.get("qty", 0))
        prod_id = whole_quantity(item.get("prod_id", item.get("id")))
        cur.execute("SELECT product_name,price,is_active,base_unit,strength,dosage_form FROM Products WHERE id=%s", (prod_id,))
        product = cur.fetchone()
        if not product or not product[2]:
            raise ValueError("A product in this cart is no longer available. Remove it and search again.")
        unit = resolve_unit(prod_id, item.get("unit_code", "base"), cur=cur)
        multiplier = int(unit["multiplier"])
        if "unit_multiplier" in item and whole_quantity(item["unit_multiplier"]) != multiplier:
            raise ValueError("This pack size changed. Remove the item and select it again.")
        qty_base = whole_quantity(qty_selected * multiplier)
        supplied = _finite_money(item.get("price", 0), "Selling price")
        specific = item.get("batch_id")
        if specific:
            specific = whole_quantity(specific)
            cur.execute("SELECT product_id,expiry_date,stock_status FROM Batch WHERE id=%s", (specific,))
            batch = cur.fetchone()
            if not batch or int(batch[0]) != prod_id:
                raise ValueError("This medicine does not match its batch. Remove the item and search again.")
            if str(batch[1]) < today or batch[2] != "SELLABLE":
                raise ValueError(f"{product[0]} is expired, recalled, or quarantined and cannot be sold.")
        cur.execute("SELECT id,quantity,expiry_date,COALESCE(sale_price,%s) FROM Batch "
                    "WHERE product_id=%s AND expiry_date>=%s AND quantity>0 AND stock_status='SELLABLE' "
                    "ORDER BY CASE WHEN id=%s THEN 0 ELSE 1 END,expiry_date,id",
                    (product[1], prod_id, today, specific or -1))
        batches = cur.fetchall()
        remaining = qty_base
        allocations = []
        expected_price = None
        for bid, stock, expiry, base_price in batches:
            available = int(stock) - reserved.get(int(bid), 0)
            if available <= 0:
                continue
            selected_price = (Decimal(str(base_price)) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if not selected_price.is_finite() or selected_price <= 0:
                raise ValueError("The selling price needs an owner review before this medicine can be sold.")
            if expected_price is None:
                expected_price = selected_price
                if supplied != selected_price:
                    raise ValueError(f"The price of {product[0]} changed to Rs. {selected_price:.2f}. Remove the item and select it again.")
            # A single cart line cannot silently combine differently priced lots.
            if selected_price != expected_price:
                continue
            take = min(remaining, available)
            allocations.append((int(bid), take))
            reserved[int(bid)] = reserved.get(int(bid), 0) + take
            remaining -= take
            if not remaining:
                break
        if remaining:
            raise ValueError(f"Insufficient sellable stock at this price for {product[0]}. Refresh the item or choose another batch.")
        selected_total = expected_price * qty_selected
        allocated_total = Decimal("0.00")
        for index, (bid, take) in enumerate(allocations):
            line_total = (selected_total * take / qty_base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if index == len(allocations) - 1:
                line_total = selected_total - allocated_total
            allocated_total += line_total
            expanded.append({"prod_id": prod_id, "name": product[0],
                             "price": float(expected_price / multiplier), "batch_id": bid,
                             "qty": take, "subtotal": float(line_total), "unit_label": product[3] or "unit",
                             "unit_code": unit["code"], "unit_multiplier": multiplier,
                             "display_quantity": float(Decimal(take) / multiplier),
                             "strength": product[4], "dosage_form": product[5]})
    consolidated = {}
    for item in expanded:
        bid = item["batch_id"]
        if bid in consolidated:
            previous = consolidated[bid]
            if Decimal(str(previous["price"])) != Decimal(str(item["price"])):
                raise ValueError("The same batch has conflicting prices or pack sizes. Use one selling unit for this medicine.")
            previous["qty"] += item["qty"]
            previous["subtotal"] = float(Decimal(str(previous["subtotal"])) + Decimal(str(item["subtotal"])))
            if previous["unit_code"] == item["unit_code"]:
                previous["display_quantity"] += item["display_quantity"]
            else:
                previous.update(unit_code="base", unit_multiplier=1, display_quantity=previous["qty"])
        else:
            consolidated[bid] = item.copy()
    return list(consolidated.values())


def _finite_money(value, label="Amount"):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > Decimal("1000000000"):
            raise ValueError()
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a valid finite amount.") from exc


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
        (Decimal(str(i.get("subtotal", Decimal(str(i["price"])) * i["qty"]))) for i in final_items),
        Decimal("0.00"),
    )
    if disc_dec < 0 or disc_dec > subtotal_dec:
        raise ValueError("Discount must be between zero and the sale subtotal.")
    net_total_dec = subtotal_dec - disc_dec
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
def _write_sale_to_db(cur, customer_id, employee_id, pay_label, final_items, financials: SaleFinancials, payment_method: str = "Cash", *, request=None, session_id=None, tax_rate=None, received=None, change=0):
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
    today = business_date().strftime("%Y-%m-%d")
    now_time = business_now().strftime("%H:%M:%S")

    # INSERT Purchase header
    cur.execute(
        "INSERT INTO Purchase "
        "(number_of_products,total_price,price_with_tax,customer_id,employee_id,payment_method,discount_amount,checkout_token,held_sale_id,session_id,tax_rate,total_tax,cash_received,change_due,terminal_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            len(final_items),
            financials.net_total,
            financials.price_with_tax,
            customer_id,
            employee_id,
            payment_method,
            financials.discount, request.checkout_token, request.held_sale_id, session_id,
            float(tax_rate), financials.tax_amount, received, float(change), request.terminal_id,
        ),
    )
    purchase_id = cur.lastrowid

    # INSERT Sales_details + deduct Batch and Products stock
    for item in final_items:
        cur.execute(
            "INSERT INTO Sales_details (purchase_id,batch_id,Quantity,unit_price,line_subtotal,unit_code,unit_multiplier,display_quantity) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (purchase_id,item["batch_id"],item["qty"],item["price"],item["subtotal"],item["unit_code"],item["unit_multiplier"],item["display_quantity"]),
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

        cur.execute("INSERT INTO Stock_Movement(product_id,batch_id,quantity_delta,movement_type,reason,employee_id,operation_key,created_at) VALUES(%s,%s,%s,'SALE',%s,%s,%s,%s)",
                    (item["prod_id"],item["batch_id"],-item["qty"],f"Sale #{purchase_id}",employee_id,request.checkout_token,business_now().isoformat(timespec="seconds")))

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
def confirm_sale(customer_id, employee_id, cart, *, total=0.0, discount=0.0, payment_method="Cash", **kwargs):
    """Compatibility API; a caller retry must reuse an explicit checkout_token."""
    result = _execute_checkout(CheckoutRequest(customer_id, employee_id, cart, discount,
                                               payment_method, total, **kwargs))
    return result.success, result.message


def _execute_checkout(request):
    from core.checkout_idempotency_service import claim_checkout, _result_from_purchase
    from core.settings_service import SettingsService
    from core.permission_service import require_permission
    request.checkout_token = request.checkout_token or uuid.uuid4().hex
    try:
        request.employee_id = int(request.employee_id)
        from core.customer_service import resolve_customer_ref
        customer_id = resolve_customer_ref(request.customer_id) if request.customer_id and request.customer_id != "WALKIN" else "WALKIN"
        if not customer_id:
            raise ValueError("Select a valid registered customer.")
        request.customer_id = customer_id
        payment_method, pay_label = _normalize_payment_method(request.payment_method)
        request.payment_method = payment_method
        with get_db(immediate=True) as (conn, cur):
            allowed, reason = require_permission(request.employee_id, "pos.sell")
            if not allowed:
                raise ValueError(reason)
            duplicate = claim_checkout(cur, request)
            if duplicate is not None:
                return duplicate
            final_items = _validate_and_allocate_cart(cur,request.cart,customer_id,request.employee_id,request.total,pay_label,conn)
            tax_rate = SettingsService.get_tax_rate()
            discount = _finite_money(request.discount, "Discount")
            financials = calculate_sale_totals(final_items, discount, tax_rate)
            if request.expected_total is not None and _finite_money(request.expected_total, "Expected total") != Decimal(str(financials.price_with_tax)):
                raise ValueError("The bill changed. Refresh the total and try again.")
            subtotal = sum((Decimal(str(i["subtotal"])) for i in final_items),Decimal("0.00"))
            from core.manager_auth_service import discount_requires_authorization, validate_discount_approval
            if discount_requires_authorization(float(discount),float(subtotal)):
                allowed, reason = validate_discount_approval(cur,request.manager_approval_token,request.employee_id,float(discount),float(subtotal))
                if not allowed:
                    raise ValueError(reason)
            if pay_label == "Credit":
                from core.customer_service import check_customer_credit_limit
                allowed, reason = check_customer_credit_limit(customer_id,financials.price_with_tax,conn=conn)
                if not allowed:
                    raise ValueError(reason)
            session_id = None
            received = None
            change = Decimal("0.00")
            if payment_method == "Cash":
                from core.cash_session_service import _terminal
                terminal_id = _terminal(request.terminal_id)
                cur.execute("SELECT id FROM Cash_Register_Session WHERE employee_id=%s AND terminal_id=%s AND status='OPEN' ORDER BY id DESC LIMIT 1", (request.employee_id, terminal_id))
                session = cur.fetchone()
                if not session:
                    raise ValueError("Start a cash shift before accepting cash payments.")
                session_id = int(session[0])
                received_dec = Decimal(str(financials.price_with_tax)) if request.cash_received is None else _finite_money(request.cash_received,"Cash received")
                if received_dec < Decimal(str(financials.price_with_tax)):
                    raise ValueError("Cash received is less than the payable amount. Choose customer credit or enter the full cash amount.")
                received = float(received_dec)
                change = received_dec - Decimal(str(financials.price_with_tax))
            if request.held_sale_id is not None:
                request.held_sale_id = int(request.held_sale_id)
                cur.execute("SELECT employee_id,status,purchase_id FROM Hold_Sales WHERE id=%s",(request.held_sale_id,))
                held=cur.fetchone()
                if not held or int(held[0]) != request.employee_id or held[1] != "RESUMED" or held[2] is not None:
                    raise ValueError("This held sale is no longer available. Review its completed sale before trying again.")
            purchase_id = _write_sale_to_db(cur,customer_id,request.employee_id,pay_label,final_items,financials,payment_method,
                                            request=request,session_id=session_id,tax_rate=tax_rate,received=received,change=change)
            if request.held_sale_id is not None:
                cur.execute("UPDATE Hold_Sales SET status='COMPLETED',purchase_id=%s,completed_at=%s,updated_at=%s WHERE id=%s AND status='RESUMED' AND purchase_id IS NULL",
                            (purchase_id,business_now().isoformat(),business_now().isoformat(),request.held_sale_id))
                if cur.rowcount != 1:
                    raise ValueError("This held sale changed before completion. No sale was saved.")
            cur.execute("UPDATE Checkout_Request SET status='COMPLETED',purchase_id=%s,updated_at=%s WHERE token=%s AND status='PENDING'",
                        (purchase_id,business_now().isoformat(),request.checkout_token))
            if cur.rowcount != 1:
                raise ValueError("The checkout safety record changed. No sale was saved.")
            cur.execute("INSERT INTO Audit_Log(timestamp,user_id,action,details) VALUES(%s,%s,'POS_CHECKOUT_SUCCESS',%s)",
                        (business_now().isoformat(),str(request.employee_id),f"Sale #{purchase_id}; {payment_method}; Rs.{financials.price_with_tax:.2f}"))
            from core.receipt_service import create_receipt_snapshot
            create_receipt_snapshot(cur,purchase_id,customer_id,final_items,financials.price_with_tax,
                                    financials.tax_amount,financials.discount,payment_method,request.employee_id,
                                    amount_received=received,change=float(change))
            result = _result_from_purchase(cur,purchase_id)
        clear_inventory_cache()
        try:
            generate_invoice_file(purchase_id,customer_id,final_items,financials.price_with_tax,
                                  financials.tax_amount,financials.discount,payment_method)
        except Exception as exc:
            logger.warning("Sale #%s saved; receipt export/printing needs retry: %s",purchase_id,exc)
            result.message = f"Sale #{purchase_id} completed. Receipt printing needs retry; do not repeat the sale."
        return result
    except (ValueError, TypeError, InvalidOperation, KeyError) as exc:
        return CheckoutResult(False,str(exc),outcome="rejected")
    except Exception as exc:
        logger.exception("Checkout outcome could not be confirmed for token %s",request.checkout_token)
        return CheckoutResult(False,"The sale result could not be confirmed. Check this saved request before trying again.",outcome="unknown")


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
            "SELECT p.product_name, sd.batch_id, sd.Quantity, sd.unit_price, sd.line_subtotal as subtotal "
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


def process_sale_return(purchase_id, return_items, reason="Customer Return", employee_id=1, restock_sellable=True, **kwargs):
    """Compatibility entry point delegates to the authoritative return service."""
    from core.return_service import process_return
    return process_return(purchase_id,return_items,employee_id,reason,
                          "SELLABLE" if restock_sellable else "DAMAGED",**kwargs)
