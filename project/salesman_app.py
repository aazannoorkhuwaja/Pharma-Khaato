# ============================================================
#  Pharma-Khaato  —  Salesman App
#  Cross-platform (Windows + Linux), layman-friendly startup
# ============================================================

import os
import sys
import platform
import subprocess
import time
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
import os
from datetime import date, datetime

# ── 1. Auto-install MySQL driver if missing ─────────────────
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print("MySQL driver not found. Installing automatically...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "mysql-connector-python"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        import mysql.connector
        from mysql.connector import Error as MySQLError
        print("Driver installed successfully.")
    except Exception as e:
        # Show a GUI error if tkinter is already available
        try:
            _r = tk.Tk(); _r.withdraw()
            messagebox.showerror(
                "Missing Dependency",
                "Could not auto-install the MySQL driver.\n\n"
                "Please open a terminal / command prompt and run:\n\n"
                "    pip install mysql-connector-python\n\n"
                "Then restart the app."
            )
            _r.destroy()
        except Exception:
            print(f"Auto-install failed: {e}")
            print("   Fix: pip install mysql-connector-python")
        sys.exit(1)


# ── 2. OS detection helpers ─────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"


# ── 3. MySQL auto-start  ────────────────────────────────────
def try_start_mysql():
    """
    Silently attempts to start MySQL/MariaDB before the app loads.
    Tries the most common service managers and XAMPP paths on both
    Windows and Linux so laymen don't have to open a terminal.
    """
    commands = []

    if IS_WINDOWS:
        commands = [
            # XAMPP default service name
            ["net", "start", "mysql"],
            ["net", "start", "MySQL"],
            ["net", "start", "MySQL80"],
            ["net", "start", "MySQL57"],
            # Standalone MySQL installer service names
            ["net", "start", "MySQL Server 8.0"],
            # XAMPP control panel helper
            [r"C:\xampp\mysql\bin\mysqld.exe", "--standalone"],
        ]
    elif IS_LINUX:
        commands = [
            ["systemctl", "start", "mysql"],
            ["systemctl", "start", "mariadb"],
            ["service",   "mysql",   "start"],
            ["service",   "mariadb", "start"],
            ["/opt/lampp/lampp", "startmysql"],   # XAMPP on Linux
        ]
    elif IS_MAC:
        commands = [
            ["/Applications/XAMPP/xamppfiles/bin/mysql.server", "start"],
            ["brew", "services", "start", "mysql"],
        ]

    # Only try to start if we actually need to
    for cmd in commands:
        try:
            # Use 'pkexec' or similar to avoid "disappearing" prompts, 
            # or just run silently if it doesn't need sudo.
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
        except Exception:
            continue
    
    if commands:
        time.sleep(1.0) # Short wait


# ── 4. Connection profiles ──────────────────────────────────
# Load from .env if available, otherwise use defaults
_DB_USER = os.getenv("DB_USER", "pharma")
_DB_PASS = os.getenv("DB_PASSWORD", "pharma123")
_DB_NAME = os.getenv("DB_NAME", "pharmacy_db")

_CREDENTIALS = [
    {"user": "root",   "password": ""},           # XAMPP default
    {"user": _DB_USER, "password": _DB_PASS},     # .env / project user
    {"user": "root",   "password": "root"},
    {"user": "root",   "password": "mysql"},
]

_TCP_HOSTS = ["127.0.0.1", "localhost"]

_UNIX_SOCKETS = [
    "/var/run/mysqld/mysqld.sock",   # Ubuntu / Debian
    "/tmp/mysql.sock",               # macOS / older Linux
    "/var/lib/mysql/mysql.sock",     # CentOS / RHEL
    "/opt/lampp/var/mysql/mysql.sock",  # XAMPP Linux
]

_DB_NAME = os.getenv("DB_NAME", "pharmacy_db")


def _try_connect(host=None, unix_socket=None, user="root", password=""):
    """Single low-level connection attempt with a short timeout."""
    kwargs = dict(user=user, password=password, database=_DB_NAME)
    if unix_socket:
        kwargs["unix_socket"] = unix_socket
    else:
        kwargs["host"]            = host
        kwargs["port"]            = int(os.getenv("DB_PORT", 3306))
        kwargs["connect_timeout"] = 1
    return mysql.connector.connect(**kwargs)


def get_conn():
    """
    Returns a live MySQL connection or None.
    Prioritizes Unix sockets (Linux/macOS) to avoid TCP port conflicts.
    """
    # 1. Try Unix socket attempts first (Linux / macOS) - Most reliable for XAMPP
    if not IS_WINDOWS:
        for sock in _UNIX_SOCKETS:
            if os.path.exists(sock):
                for creds in _CREDENTIALS:
                    try:
                        return _try_connect(unix_socket=sock, **creds)
                    except Exception:
                        continue

    # 2. Try TCP attempts (Windows default / Linux fallback)
    for host in _TCP_HOSTS:
        for creds in _CREDENTIALS:
            try:
                return _try_connect(host=host, **creds)
            except Exception:
                continue

    # 3. Nothing worked — attempt first-time DB setup
    return _setup_database()


def _initialize_db(conn):
    """Internal helper to create DB and run the SQL schema file."""
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{_DB_NAME}`")
    cur.execute(f"USE `{_DB_NAME}`")
    
    # Look for the SQL file
    sql_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "drawSQL-mysql-export-2026-04-26.sql"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "drawSQL-mysql-export-2026-04-26.sql"),
    ]
    sql_file = next((p for p in sql_candidates if os.path.exists(p)), None)
    
    if sql_file:
        _run_sql_file(cur, sql_file)
        conn.commit()
    print(f"Database '{_DB_NAME}' setup complete.")


def _setup_database():
    """
    Called when no pharmacy_db connection could be made.
    Tries to connect to MySQL *without* specifying a database,
    then creates pharmacy_db and runs the schema SQL.
    Returns a connection to pharmacy_db or None.
    """
    # 1. Try Unix Sockets first (Linux/macOS)
    if not IS_WINDOWS:
        for sock in _UNIX_SOCKETS:
            if os.path.exists(sock):
                for creds in _CREDENTIALS:
                    try:
                        conn = mysql.connector.connect(
                            unix_socket=sock,
                            user=creds["user"],
                            password=creds["password"],
                            connect_timeout=2
                        )
                        _initialize_db(conn)
                        return conn
                    except Exception:
                        continue

    # 2. Try TCP (Windows/Linux fallback)
    for host in _TCP_HOSTS:
        for creds in _CREDENTIALS:
            try:
                conn = mysql.connector.connect(
                    host=host,
                    port=int(os.getenv("DB_PORT", 3306)),
                    user=creds["user"],
                    password=creds["password"],
                    connect_timeout=2
                )
                _initialize_db(conn)
                return conn
            except Exception:
                continue

    # All setup attempts failed — show a helpful, OS-aware dialog
    _show_db_help()
    return None


def _run_sql_file(cursor, path):
    """Execute a SQL file, skipping statements that already exist."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    for stmt in raw.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception:
                pass   # Table/index already exists — safe to ignore


def _show_db_help():
    """Show an OS-appropriate, step-by-step help dialog."""
    if IS_WINDOWS:
        msg = (
            "Could not connect to MySQL.\n\n"
            "How to fix on Windows:\n\n"
            "  Option A — XAMPP users:\n"
            "    1. Open XAMPP Control Panel\n"
            "    2. Click  [Start]  next to MySQL\n"
            "    3. Wait for the green 'Running' label\n"
            "    4. Close this dialog and restart the app\n\n"
            "  Option B — Standalone MySQL:\n"
            "    1. Press  Win + R  and type  services.msc\n"
            "    2. Find 'MySQL80' (or MySQL57)\n"
            "    3. Right-click → Start\n"
            "    4. Restart the app\n\n"
            "  Option C — First time install:\n"
            "    Download XAMPP from https://www.apachefriends.org"
        )
    elif IS_LINUX:
        msg = (
            "Could not connect to MySQL.\n\n"
            "How to fix on Linux:\n\n"
            "  Option A — XAMPP users:\n"
            "    Open a terminal and run:\n"
            "    sudo /opt/lampp/lampp startmysql\n\n"
            "  Option B — System MySQL / MariaDB:\n"
            "    sudo service mysql start\n"
            "    (or: sudo systemctl start mysql)\n\n"
            "  Option C — Not installed?\n"
            "    sudo apt install mysql-server   (Ubuntu/Debian)\n"
            "    sudo dnf install mysql-server   (Fedora/CentOS)\n\n"
            "Then restart the app."
        )
    else:
        msg = (
            "Could not connect to MySQL.\n\n"
            "Please start MySQL and restart the app.\n"
            "XAMPP users: run  sudo /Applications/XAMPP/xamppfiles/bin/mysql.server start"
        )

    try:
        messagebox.showerror("MySQL Not Running", msg)
    except Exception:
        print(msg)


# ── 5. DB connection health check with retry UI ─────────────
def ensure_connection_or_warn(parent_window=None):
    """
    Call this before any DB operation.
    If the DB is down, shows a retry dialog so the user can start
    MySQL and try again without restarting the whole app.
    Returns True if connected, False if the user gave up.
    """
    conn = get_conn()
    if conn:
        conn.close()
        return True

    # Connection failed — ask user to start MySQL and retry
    while True:
        answer = messagebox.askretrycancel(
            "Database Offline",
            "MySQL is not running.\n\n"
            "Please start MySQL (XAMPP → click Start next to MySQL),\n"
            "then click  [Retry].\n\n"
            "Click  [Cancel]  to continue without the database\n"
            "(some features will not work)."
        )
        if not answer:   # user clicked Cancel
            return False
        # Retry
        try_start_mysql()
        conn = get_conn()
        if conn:
            conn.close()
            messagebox.showinfo("Connected", "Database connected successfully!")
            return True
        # Loop again — still not up


# ── 6. Security Helpers ─────────────────────────────────────
def hash_password(password):
    """Returns a SHA-256 hash of the password."""
    if not password: return ""
    return hashlib.sha256(password.encode()).hexdigest()

# ── 7. Database functions ───────────────────────────────────

def db_login(username, password):
    """
    Returns (employee_id, first_name, occupation) or None.
    Supports both plain-text (legacy) and SHA-256 hashed passwords.
    """
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        hashed = hash_password(password)
        
        cur.execute(
            "SELECT Employee_id, First_name, occupation FROM Employee "
            "WHERE username = %s AND (password = %s OR password = %s)",
            (username, password, hashed)
        )
        return cur.fetchone()
    except Exception as e:
        print(f"Login error: {e}")
        return None
    finally:
        conn.close()


def db_register_customer(cnic, fname, lname, email, city):
    if not email: email = "N/A"
    conn = get_conn()
    if not conn:
        messagebox.showerror("No Database", "Cannot save — MySQL is not connected.")
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Customers "
            "(id_card_number, first_name, last_name, Email_Address, city, registration_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (str(cnic), fname, lname, email, city, date.today())
        )
        conn.commit()
        return True
    except MySQLError as e:
        if e.errno == 1062:   # Duplicate entry
            messagebox.showerror(
                "Already Registered",
                f"A customer with CNIC  {cnic}  already exists."
            )
        else:
            messagebox.showerror("Database Error", f"Could not register customer:\n{e}")
        return False
    finally:
        conn.close()


def db_search_customer(kw):
    """
    Search for customer by CNIC (Exact or Partial) or Name.
    Prioritizes Exact CNIC first.
    """
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        # 1. Exact CNIC Match
        cur.execute("SELECT id_card_number, first_name, last_name FROM Customers WHERE id_card_number = %s", (kw,))
        exact = cur.fetchall()
        if exact: return exact
        
        # 2. Partial Search (CNIC or First Name)
        cur.execute(
            "SELECT id_card_number, first_name, last_name "
            "FROM Customers WHERE id_card_number = %s OR first_name LIKE %s",
            (kw, f"%{kw}%")
        )
        return cur.fetchall()
    except Exception as e:
        print(f"Search customer error: {e}")
        return []
    finally:
        conn.close()


def db_search_products(keyword):
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, p.product_name, p.price, b.id, b.quantity "
            "FROM Products p "
            "JOIN Batch b ON b.product_id = p.id "
            "WHERE p.product_name LIKE %s "
            "  AND b.quantity > 0 "
            "  AND b.expiry_date > CURDATE()",
            (f"%{keyword}%",)
        )
        return cur.fetchall()
    except Exception as e:
        print(f"Search products error: {e}")
        return []
    finally:
        conn.close()


def db_get_purchase_items(purchase_id):
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        query = """
            SELECT p.product_name, sd.batch_id, sd.Quantity, p.price, 
                   (sd.Quantity * p.price) as subtotal
            FROM Sales_details sd
            JOIN Batch b ON sd.batch_id = b.id
            JOIN Products p ON b.product_id = p.id
            WHERE sd.purchase_id = %s
        """
        cur.execute(query, (purchase_id,))
        return cur.fetchall()
    except Exception as e:
        print(f"Error fetching items: {e}")
        return []
    finally:
        conn.close()


def db_confirm_sale(customer_id, employee_id, cart, total, discount, payment_method):
    conn = get_conn()
    if not conn:
        messagebox.showerror("No Database", "Cannot save sale — MySQL is not connected.")
        return False
    try:
        cur = conn.cursor()
        
        # 0. EMPTY CART VALIDATION
        if not cart:
            messagebox.showwarning("Empty Cart", "Cannot process a sale with zero items.")
            return False
        
        # 1. STOCK & EXPIRY VALIDATION (Pharmacy Safety Layer)
        # Check all items BEFORE starting the sale - LOCKING rows for update
        today = date.today()
        for item in cart:
            cur.execute("SELECT quantity, expiry_date FROM Batch WHERE id = %s FOR UPDATE", (item["batch_id"],))
            res = cur.fetchone()
            if not res:
                messagebox.showerror("System Error", f"Batch for {item['name']} not found.")
                conn.rollback()
                return False
            
            current_qty, exp_date = res
            
            # Expiry Check (Strict Block)
            if exp_date < today:
                messagebox.showerror(
                    "Expired Medicine",
                    f"STOP! {item['name']} (Batch {item['batch_id']}) has just EXPIRED!\n"
                    f"Expiry Date: {exp_date}\n"
                    "Please remove this item from the cart."
                )
                conn.rollback()
                return False

            # Stock Check
            if current_qty < item["qty"]:
                messagebox.showwarning(
                    "Out of Stock",
                    f"Not enough stock for {item['name']}.\n"
                    f"Requested: {item['qty']}, Available: {current_qty}"
                )
                conn.rollback()
                return False

        # 2. CALCULATIONS & CONSOLIDATION
        # Merge items with the same batch_id to prevent Duplicate Entry errors in Sales_details
        consolidated_cart = {}
        for item in cart:
            bid = item["batch_id"]
            if bid in consolidated_cart:
                consolidated_cart[bid]["qty"] += item["qty"]
                consolidated_cart[bid]["subtotal"] += item["subtotal"]
            else:
                consolidated_cart[bid] = item.copy()
        
        final_items = list(consolidated_cart.values())
        subtotal  = sum(i["subtotal"] for i in final_items)
        total     = max(subtotal - discount, 0)
        tax_rate  = 0.10
        total_tax = round(total * (1 + tax_rate), 2)
        pay_label = "Cash" if payment_method == "Cash" else "Credit"

        # 3. RECORD SALE
        cur.execute(
            "INSERT INTO Purchase "
            "(number_of_products, total_price, price_with_tax, "
            " customer_id, employee_id, payment_method, discount_amount) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (len(final_items), total, total_tax, customer_id,
             employee_id, pay_label, discount)
        )
        purchase_id = cur.lastrowid

        # 4. UPDATE STOCK
        for item in final_items:
            # Sales details
            cur.execute(
                "INSERT INTO Sales_details (purchase_id, batch_id, Quantity) "
                "VALUES (%s, %s, %s)",
                (purchase_id, item["batch_id"], item["qty"])
            )
            # Batch stock
            cur.execute(
                "UPDATE Batch SET quantity = quantity - %s WHERE id = %s",
                (item["qty"], item["batch_id"])
            )
            # Global product stock
            cur.execute(
                "UPDATE Products SET stock_quantity = stock_quantity - %s WHERE id = %s",
                (item["qty"], item["prod_id"])
            )
            

        cur.execute(
            "INSERT INTO Receipt (printing_date, time, purchase_id, number_of_items) "
            "VALUES (%s, %s, %s, %s)",
            (date.today(), datetime.now().strftime("%H:%M:%S"),
             purchase_id, len(final_items))
        )

        if payment_method == "Credit (Khatoo)":
            cur.execute(
                "INSERT INTO Customer_Khatoo "
                "(amount_paid, amount_due, purchase_id, customer_id, payment_method) "
                "VALUES (%s, %s, %s, %s, %s)",
                (0, total_tax, purchase_id, customer_id, "Credit")
            )

        conn.commit()
        
        # 5. GENERATE INVOICE FILE
        try:
            _generate_invoice_file(purchase_id, customer_id, final_items, total, total_tax, discount)
        except Exception as inv_e:
            print(f"Invoice printing error: {inv_e}")
            
        return True
    except Exception as e:
        conn.rollback()
        messagebox2 | Abbot.showerror("Sale Error", f"Failed to record sale:\n{e}")
        return False
    finally:
        conn.close()


def _generate_invoice_file(p_id, c_id, items, total, tax, discount):
    """Creates a professional text-based receipt in the receipts/ folder."""
    try:
        if not os.path.exists("receipts"):
            os.makedirs("receipts")
        
        filename = f"receipts/invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{p_id}.txt"
        with open(filename, "w") as f:
            f.write("==========================================\n")
            f.write("         PHARMA-KHATOO SURGICAL          \n")
            f.write("      Emergency & Specialized Care       \n")
            f.write("==========================================\n")
            f.write(f"Invoice ID:  {p_id}\n")
            f.write(f"Date/Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Customer ID: {c_id}\n")
            f.write("------------------------------------------\n")
            f.write(f"{'Product':<18} {'Qty':<4} {'Price':>8} {'Sub':>8}\n")
            f.write("------------------------------------------\n")
            
            subtotal = 0
            for item in items:
                name = item["name"][:17]
                qty  = item["qty"]
                prc  = item["price"]
                sub  = item["subtotal"]
                subtotal += sub
                f.write(f"{name:<18} {qty:<4} {prc:>8.1f} {sub:>8.1f}\n")
            
            f.write("------------------------------------------\n")
            f.write(f"{'Subtotal:':<32} Rs.{subtotal:>8.1f}\n")
            f.write(f"{'Discount:':<32} Rs.{discount:>8.1f}\n")
            f.write(f"{'Tax (10%):':<32} Rs.{tax-total+discount:>8.1f}\n")
            f.write("------------------------------------------\n")
            f.write(f"{'GRAND TOTAL:':<32} Rs.{tax:>8.1f}\n")
            f.write("==========================================\n")
            f.write("       Thank you for your purchase!       \n")
            f.write("   System generated - No signature req.  \n")
            f.write("==========================================\n")
        return filename
    except Exception as e:
        print(f"Error creating invoice file: {e}")
        return None

def db_load_khatoo(keyword=""):
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        
        if keyword != "":
            print("show one")
            # Search by exact CNIC or partial customer name
            cur.execute(
                "SELECT k.id, c.first_name, k.purchase_id, k.amount_due, k.amount_paid "
                "FROM Customer_Khatoo k "
                "JOIN Customers c ON k.customer_id = c.id_card_number "
                "WHERE c.id_card_number = %s "
                "   OR c.first_name   LIKE %s",
                (keyword, f"%{keyword}%")
            )
        else:
            print("show all")
            cur.execute(
                "SELECT k.id, c.first_name, k.purchase_id, k.amount_due, k.amount_paid "
                "FROM Customer_Khatoo k "
                "JOIN Customers c ON k.customer_id = c.id_card_number"
            )
        return cur.fetchall()
    except Exception as e:
        print(f"Load khatoo error: {e}")
        return []
    finally:
        conn.close()


def db_record_payment(khatoo_id, amount):
    conn = get_conn()
    if not conn:
        messagebox.showerror("No Database", "Cannot save payment — MySQL is not connected.")
        return False
    try:
        cur = conn.cursor()
        # 1. LOCK the row and check balance
        cur.execute("SELECT amount_due FROM Customer_Khatoo WHERE id = %s FOR UPDATE", (khatoo_id,))
        res = cur.fetchone()
        if not res:
            messagebox.showerror("Payment Error", "Khatoo record not found.")
            return False
        
        due = res[0]
        if amount > due:
            messagebox.showwarning(
                "Overpayment Blocked",
                f"Amount exceeds balance!\nDue: Rs.{due:.2f}, Paying: Rs.{amount:.2f}\n"
                "Please enter exactly the due amount or less."
            )
            return False

        # 2. Update
        cur.execute(
            "UPDATE Customer_Khatoo "
            "SET amount_paid = amount_paid + %s, "
            "    amount_due  = amount_due - %s "
            "WHERE id = %s",
            (amount, amount, khatoo_id)
        )
        conn.commit()
        return True
    except Exception as e:
        messagebox.showerror("Payment Error", f"Failed to record payment:\n{e}")
        return False
    finally:
        conn.close()


def db_get_sales_history():
    """Fetches full history of purchases with customer and receipt details."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.id, r.printing_date, r.time, c.first_name, p.total_price, p.payment_method "
            "FROM Purchase p "
            "JOIN Receipt r ON p.id = r.purchase_id "
            "LEFT JOIN Customers c ON p.customer_id = c.id_card_number "
            "ORDER BY r.printing_date DESC, r.time DESC"
        )
        return cur.fetchall()
    except Exception as e:
        print(f"Sales history error: {e}")
        return []
    finally:
        conn.close()

def db_get_stocks_by_supplier(supplier_id):
    """Returns all available batches filtered by a specific supplier."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.product_name, b.id, b.quantity, b.expiry_date "
            "FROM Batch b "
            "JOIN Products p ON b.product_id = p.id "
            "WHERE b.supplier_id = %s AND b.quantity > 0 "
            "ORDER BY b.expiry_date ASC",
            (supplier_id,)
        )
        return cur.fetchall()
    finally:
        conn.close()

def db_get_near_expiry(days=30):
    """Returns batches expiring soon."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.product_name, b.id, b.expiry_date, b.quantity "
            "FROM Batch b "
            "JOIN Products p ON b.product_id = p.id "
            "WHERE b.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY) "
            "AND b.quantity > 0",
            (days,)
        )
        return cur.fetchall()
    finally:
        conn.close()

def db_get_expired():
    """Returns already expired batches."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT p.product_name, b.id, b.expiry_date, b.quantity "
            "FROM Batch b "
            "JOIN Products p ON b.product_id = p.id "
            "WHERE b.expiry_date < CURDATE() AND b.quantity > 0"
        )
        return cur.fetchall()
    finally:
        conn.close()

def db_get_low_stock():
    """Returns list of products below min_stock."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT product_name, stock_quantity, min_stock "
            "FROM Products WHERE stock_quantity <= min_stock"
        )
        return cur.fetchall()
    finally:
        conn.close()

def db_get_khatoo_summary():
    """Returns total pending amount due."""
    conn = get_conn()
    if not conn: return 0.0
    try:
        cur = conn.cursor()
        cur.execute("SELECT SUM(amount_due) FROM Customer_Khatoo")
        res = cur.fetchone()
        return float(res[0]) if res and res[0] else 0.0
    finally:
        conn.close()

def db_add_batch(prod_id, supp_id, qty, expiry, mfg_date):
    """Adds a new batch and updates product total stock."""
    conn = get_conn()
    if not conn: return False
    try:
        cur = conn.cursor()
        # 1. Insert Batch
        cur.execute(
            "INSERT INTO Batch (product_id, supplier_id, quantity, expiry_date, manufacture_Date, number_of_product) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (prod_id, supp_id, qty, expiry, mfg_date, qty)
        )
        # 2. Update Product Total
        cur.execute(
            "UPDATE Products SET stock_quantity = stock_quantity + %s WHERE id = %s",
            (qty, prod_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Add batch error: {e}")
        return False
    finally:
        conn.close()

def db_get_suppliers():
    """Returns list of suppliers (id, name)."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, supplier_name FROM Supplier")
        return cur.fetchall()
    finally:
        conn.close()

def db_get_all_products():
    """Returns list of products (id, name)."""
    conn = get_conn()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, product_name FROM Products")
        return cur.fetchall()
    finally:
        conn.close()

def db_register_product(name, price, min_stock, category="Surgical"):
    """Adds a new product to the master list with duplication check."""
    conn = get_conn()
    if not conn: return False
    try:
        cur = conn.cursor()
        # Duplication Guard
        cur.execute("SELECT id FROM Products WHERE product_name = %s", (name,))
        if cur.fetchone():
            return "EXISTS"
        
        cur.execute(
            "INSERT INTO Products (product_name, company_name, category, price, stock_quantity, min_stock, formula) "
            "VALUES (%(name)s, %(company)s, %(cat)s, %(price)s, 0, %(min)s, %(form)s)",
            {
                "name": name,
                "company": "General",
                "cat": category,
                "price": price,
                "min": min_stock,
                "form": "N/A"
            }
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Product registration error: {e}")
        return False
    finally:
        conn.close()

def db_register_supplier(name, contact):
    """Adds a new supplier to the master list with duplication check."""
    conn = get_conn()
    if not conn: return False
    try:
        cur = conn.cursor()
        # Duplication Guard
        cur.execute("SELECT id FROM Supplier WHERE supplier_name = %s", (name,))
        if cur.fetchone():
            return "EXISTS"

        cur.execute(
            "INSERT INTO Supplier (supplier_name, supplier_company_name, Email_address, phone_number) "
            "VALUES (%(name)s, %(comp)s, %(email)s, %(phone)s)",
            {
                "name": name,
                "comp": name,
                "email": "info@supplier.com",
                "phone": contact
            }
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Supplier registration error: {e}")
        return False
    finally:
        conn.close()


# ── 7. GUI Application ──────────────────────────────────────

class SalesmanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pharma-Khatoo - Access Portal")
        self.root.geometry("400x450")
        self.root.configure(bg="#f8f9fa")
        self.cart = []
        self.current_user = None   # Will be (id, name)
        
        self._startup_db()
        self._show_login()

    def _show_login(self):
        """Builds the security gateway."""
        self.login_frame = tk.Frame(self.root, bg="#f8f9fa")
        self.login_frame.pack(expand=True, fill="both", padx=40, pady=40)
        
        tk.Label(self.login_frame, text="🔒 Restricted Access", font=("Arial", 14, "bold"), 
                 bg="#f8f9fa", fg="#2c3e50").pack(pady=(0, 25))
        
        # Username
        tk.Label(self.login_frame, text="Username", bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w")
        self.user_var = tk.StringVar()
        self._entry(self.login_frame, var=self.user_var, width=30).pack(pady=(5, 15))
        
        # Password
        tk.Label(self.login_frame, text="Password", bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w")
        self.pass_var = tk.StringVar()
        e = self._entry(self.login_frame, var=self.pass_var, width=30, show="*")
        e.pack(pady=(5, 25))
        e.bind("<Return>", lambda e: self._do_login())
        
        self._btn(self.login_frame, "Login Securely", self._do_login, bg="#27ae60").pack(fill="x")
        
        self.login_msg = tk.Label(self.login_frame, text="", font=("Arial", 9), bg="#f8f9fa")
        self.login_msg.pack(pady=10)

    def _do_login(self):
        u = self.user_var.get().strip()
        p = self.pass_var.get().strip()
        
        if not u or not p:
            self.login_msg.config(text="Please enter credentials.", fg="#e67e22")
            return
            
        res = db_login(u, p)
        if res:
            self.current_user = res
            self.login_frame.destroy()
            self._init_main_app()
        else:
            self.login_msg.config(text="Invalid username or password.", fg="#c0392b")

    def _init_main_app(self):
        """Transitions from login to the full management layout."""
        self.root.geometry("1100x680")
        name = self.current_user[1]
        role = self.current_user[2]
        self.root.title(f"Pharma-Khatoo - {role}: {name}")
        self._build_layout()
        self.show_frame(self.home_frame)

    # ── DB startup ───────────────────────────────────────────
    def _startup_db(self):
        """
        Run once at startup: check connection first. Only try to start
        MySQL if it's actually down.
        """
        conn = get_conn()
        if not conn:
            try_start_mysql()
            conn = get_conn()
            
        if conn:
            conn.close()
        else:
            ensure_connection_or_warn(self.root)

    # ── Layout ───────────────────────────────────────────────
    def _build_layout(self):
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Pharma-Khatoo", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=20)

        role = self.current_user[2]
        nav = [
            ("Home",              lambda: self.show_frame(self.home_frame)),
            ("Register Customer", lambda: self.show_frame(self.reg_frame)),
            ("Make a Bill",       lambda: self.show_frame(self.bill_frame)),
            ("Khatoo",            lambda: self.show_frame(self.khatoo_frame)),
            ("Alerts",            lambda: self.show_frame(self.alerts_frame)),
        ]

        # Role-based restriction: Only Admin or Pharmacist can manage stock/reports
        if role in ["Admin", "Pharmacist", "admin"]:
            nav.extend([
                ("Manage Stock",      lambda: self.show_frame(self.stock_frame)),
                ("Supplier Stocks",   lambda: self.show_frame(self.supp_stock_frame)),
                ("Sales Reports",     lambda: self.show_frame(self.reports_frame)),
            ])

        for label, cmd in nav:
            tk.Button(
                sidebar, text=label, font=("Arial", 10),
                bg="#2c3e50", fg="white", relief="flat",
                activebackground="#34495e", anchor="w",
                padx=16, pady=10, cursor="hand2",
                command=cmd
            ).pack(fill="x")

        # DB status indicator at the bottom of sidebar
        self.db_status_lbl = tk.Label(
            sidebar, text="⬤ DB: checking…",
            font=("Arial", 8), bg="#2c3e50", fg="#f39c12"
        )
        self.db_status_lbl.pack(side="bottom", pady=10)
        self._refresh_db_status()

        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(side="right", fill="both", expand=True)

        self.home_frame   = self._build_home()
        self.reg_frame    = self._build_register()
        self.bill_frame   = self._build_bill()
        self.khatoo_frame = self._build_khatoo()
        self.stock_frame  = self._build_inventory()
        self.supp_stock_frame = self._build_supp_report()
        self.alerts_frame     = self._build_alerts()
        self.reports_frame    = self._build_reports()

        for f in [self.home_frame, self.reg_frame, self.bill_frame, 
                  self.khatoo_frame, self.stock_frame, self.supp_stock_frame, self.alerts_frame, self.reports_frame]:
            f.place(relwidth=1, relheight=1)

    def _refresh_db_status(self):
        """Ping DB every 10 seconds and update the sidebar indicator."""
        try:
            c = get_conn()
            if c:
                c.close()
                self.db_status_lbl.config(text="⬤ DB: Connected", fg="#2ecc71")
            else:
                self.db_status_lbl.config(text="⬤ DB: Offline", fg="#e74c3c")
        except Exception:
            self.db_status_lbl.config(text="⬤ DB: Offline", fg="#e74c3c")
        self.root.after(10_000, self._refresh_db_status)

    def show_frame(self, frame):
        frame.tkraise()

    # ── Helpers ──────────────────────────────────────────────
    def _title(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 16, "bold"),
                 bg="white", fg="#2c3e50").pack(anchor="w", padx=20, pady=(20, 4))
        tk.Frame(parent, bg="#bdc3c7", height=1).pack(fill="x", padx=20, pady=(0, 14))

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, font=("Arial", 9), bg="white", fg="#555")

    def _entry(self, parent, var=None, width=30, **kwargs):
        return tk.Entry(parent, textvariable=var, width=width,
                        font=("Arial", 10), relief="solid", bd=1, **kwargs)

    def _btn(self, parent, text, cmd, bg="#2980b9", fg="white"):
        return tk.Button(parent, text=text, command=cmd,
                         font=("Arial", 9, "bold"), bg=bg, fg=fg,
                         relief="flat", padx=10, pady=5, cursor="hand2")

    # ── HOME ─────────────────────────────────────────────────
    def _build_home(self):
        f = tk.Frame(self.content, bg="white")
        tk.Label(f, text="Welcome to Pharma-Khaato",
                 font=("Arial", 20, "bold"),
                 bg="white", fg="#2c3e50").pack(pady=(40, 8))
        tk.Label(f, text="Select an option from the sidebar or see alerts below",
                 font=("Arial", 11), bg="white", fg="#7f8c8d").pack()

        cards = tk.Frame(f, bg="white")
        cards.pack(pady=20)
        for label, cmd in [
            ("Register Customer", lambda: self.show_frame(self.reg_frame)),
            ("Make Bill",       lambda: self.show_frame(self.bill_frame)),
            ("Inventory",      lambda: self.show_frame(self.stock_frame)),
            ("Khatoo",         lambda: self.show_frame(self.khatoo_frame)),
        ]:
            tk.Button(cards, text=label, command=cmd,
                      font=("Arial", 10), width=14, height=2,
                      bg="#ecf0f1", fg="#2c3e50", relief="solid",
                      bd=1, cursor="hand2").pack(side="left", padx=8)

        # Dashboard Stats
        header = tk.Frame(f, bg="white")
        header.pack(fill="x", padx=40)
        tk.Label(header, text="Operational Dashboard", font=("Arial", 12, "bold"), bg="white", fg="#2c3e50").pack(side="left")
        self._btn(header, "↻ Refresh Stats", self._refresh_dashboard, bg="#34495e").pack(side="right")

        stats = tk.Frame(f, bg="white")
        stats.pack(pady=10)

        # 1. Low Stock Card
        self.low_stock_box = tk.LabelFrame(stats, text="Low Stock Alerts", 
                                            bg="white", font=("Arial", 9, "bold"), fg="#e67e22")
        self.low_stock_box.pack(side="left", padx=10, fill="y")
        self.low_stock_list = tk.Label(self.low_stock_box, text="Checking...", bg="white", font=("Arial", 8))
        self.low_stock_list.pack(padx=10, pady=5)

        # 2. Total Debt Card
        self.debt_box = tk.LabelFrame(stats, text="Khatoo Debt", 
                                       bg="white", font=("Arial", 9, "bold"), fg="#2980b9")
        self.debt_box.pack(side="left", padx=10, fill="y")
        self.debt_val = tk.Label(self.debt_box, text="Checking...", bg="white", font=("Arial", 12, "bold"))
        self.debt_val.pack(padx=20, pady=10)

        # 3. Near Expiry Card
        self.expiry_box = tk.LabelFrame(stats, text="Near Expiry (30d)", 
                                         bg="white", font=("Arial", 9, "bold"), fg="#8e44ad")
        self.expiry_box.pack(side="left", padx=10, fill="y")
        self.expiry_count = tk.Label(self.expiry_box, text="0", bg="white", font=("Arial", 14, "bold"))
        self.expiry_count.pack(padx=20, pady=10)

        # 4. Expired Card
        self.exp_box = tk.LabelFrame(stats, text="Expired (DANGER)", 
                                      bg="white", font=("Arial", 9, "bold"), fg="#c0392b")
        self.exp_box.pack(side="left", padx=10, fill="y")
        self.exp_count = tk.Label(self.exp_box, text="0", bg="white", font=("Arial", 14, "bold"), fg="#c0392b")
        self.exp_count.pack(padx=20, pady=10)

        self._refresh_dashboard()
        return f

    def _refresh_dashboard(self):
        # Update Low Stock
        low_items = db_get_low_stock()
        if not low_items:
            self.low_stock_list.config(text="All levels healthy.", fg="green")
        else:
            txt = "\n".join([f"• {i[0]}: {i[1]} left" for i in low_items[:3]])
            self.low_stock_list.config(text=txt, fg="#c0392b")

        # Update Debt
        total_debt = db_get_khatoo_summary()
        self.debt_val.config(text=f"Rs. {total_debt:,.0f}", fg="#2980b9")

        # Update Expiry Alerts
        near = db_get_near_expiry(30)
        expired = db_get_expired()
        self.expiry_count.config(text=str(len(near)), fg="#8e44ad" if near else "green")
        self.exp_count.config(text=str(len(expired)), fg="#c0392b" if expired else "green")
        
        self.root.after(30_000, self._refresh_dashboard)

    def _manual_reconnect(self):
        try_start_mysql()
        conn = get_conn()
        if conn:
            conn.close()
            messagebox.showinfo("Connected", "Database connected successfully!")
            self._refresh_db_status()
        else:
            ensure_connection_or_warn(self.root)

    # ── REGISTER CUSTOMER ────────────────────────────────────
    def _build_register(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Register Customer")

        form = tk.Frame(f, bg="white")
        form.pack(padx=30, anchor="w")

        self.reg_vars = {}
        fields = [
            ("Customer ID *", "cnic"),
            ("First Name *",        "fname"),
            ("Last Name *",         "lname"),
            ("Email",               "email"),
            ("City",                "city"),
        ]
        for i, (label, key) in enumerate(fields):
            self._lbl(form, label).grid(row=i, column=0, sticky="w",
                                        pady=5, padx=(0, 12))
            var = tk.StringVar()
            self.reg_vars[key] = var
            self._entry(form, var=var).grid(row=i, column=1, sticky="w", pady=5)

        btn_row = tk.Frame(f, bg="white")
        btn_row.pack(anchor="w", padx=30, pady=14)
        self._btn(btn_row, "Register", self._do_register).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "Clear", self._clear_reg, bg="#95a5a6").pack(side="left")

        self.reg_msg = tk.Label(f, text="", font=("Arial", 9),
                                bg="white", fg="green")
        self.reg_msg.pack(anchor="w", padx=30)
        return f

    def _do_register(self):
        v = self.reg_vars
        cnic  = v["cnic"].get().strip()
        fname = v["fname"].get().strip()
        lname = v["lname"].get().strip()
        if not cnic or not fname or not lname:
            self.reg_msg.config(
                text="Customer ID (CNIC), First Name and Last Name are required.", fg="red"
            )
            return
        
        # CNIC Validation (Must be exactly 13 digits)
        if not (cnic.isdigit() and len(cnic) == 13):
            self.reg_msg.config(
                text="Invalid ID: CNIC must be exactly 13 digits (numeric).", fg="red"
            )
            return
        
        # Guard removed for fast-paced real-world checkouts
        ok = db_register_customer(
            cnic, fname, lname,
            v["email"].get().strip(),
            v["city"].get().strip()
        )
        if ok:
            self.reg_msg.config(
                text=f"Customer '{fname} {lname}' registered successfully.", fg="green"
            )
            self._clear_reg()
        # If not ok, db_register_customer already showed an error dialog

    def _clear_reg(self):
        for var in self.reg_vars.values():
            var.set("")

    # ── MAKE A BILL ──────────────────────────────────────────
    def _build_bill(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Make a Bill")

        top = tk.Frame(f, bg="white")
        top.pack(fill="x", padx=20, pady=(0, 8))

        # Customer search
        cust_box = tk.LabelFrame(top, text="Customer (Enter ID)", bg="white",
                                  font=("Arial", 9), padx=8, pady=6)
        cust_box.pack(side="left", padx=(0, 12))
        self.cust_var = tk.StringVar()
        r = tk.Frame(cust_box, bg="white")
        r.pack()
        self._entry(r, var=self.cust_var, width=22).pack(side="left", padx=(0, 6))
        self._btn(r, "Search", self._search_cust).pack(side="left")
        self.cust_info = tk.Label(cust_box, text="No customer selected",
                                   font=("Arial", 8), bg="white", fg="#7f8c8d")
        self.cust_info.pack(anchor="w", pady=(4, 0))
        self.selected_cust = None

        # Product search
        prod_box = tk.LabelFrame(top, text="Add Product (Search/Type)", bg="white",
                                  font=("Arial", 9), padx=8, pady=6)
        prod_box.pack(side="left")
        self.prod_var = tk.StringVar()
        # LIVE FILTER: Run filtering whenever text changes
        self.prod_var.trace_add("write", lambda *a: self._live_filter_prod())
        
        r2 = tk.Frame(prod_box, bg="white")
        r2.pack()
        self._entry(r2, var=self.prod_var, width=20).pack(side="left", padx=(0, 6))
        self._btn(r2, "Refresh All", self._load_all_prods_to_pos).pack(side="left")
        
        self.prod_combo = ttk.Combobox(prod_box, state="readonly", width=42)
        self.prod_combo.pack(pady=4, anchor="w")
        self.prod_results = []
        
        r3 = tk.Frame(prod_box, bg="white")
        r3.pack(anchor="w")
        tk.Label(r3, text="Qty:", font=("Arial", 9), bg="white").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        self._entry(r3, var=self.qty_var, width=5).pack(side="left", padx=6)
        self._btn(r3, "Add to Cart", self._add_cart, bg="#27ae60").pack(side="left")
        
        # Initial Load: Pre-fill dropdown with everything
        self._load_all_prods_to_pos()

        # Cart treeview
        cart_frame = tk.Frame(f, bg="white")
        cart_frame.pack(fill="both", expand=True, padx=20)
        cols = ("Product", "Batch", "Price", "Qty", "Subtotal")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cols,
                                       show="headings", height=7)
        for col, w in zip(cols, [220, 80, 90, 60, 90]):
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=w, anchor="center")
        self.cart_tree.pack(fill="both", expand=True)

        # Bottom row
        bot = tk.Frame(f, bg="white")
        bot.pack(fill="x", padx=20, pady=8)

        # Totals
        tot = tk.LabelFrame(bot, text="Totals", bg="white",
                             font=("Arial", 9), padx=10, pady=6)
        tot.pack(side="left", padx=(0, 12))
        for lbl_text, attr, color in [
            ("Subtotal:", "lbl_sub",   "#2c3e50"),
            ("Discount:", "lbl_disc",  "#e67e22"),
            ("Total:",    "lbl_total", "#27ae60"),
        ]:
            row = tk.Frame(tot, bg="white")
            row.pack(anchor="w")
            tk.Label(row, text=lbl_text, width=10, anchor="w",
                     font=("Arial", 9), bg="white").pack(side="left")
            lw = tk.Label(row, text="Rs. 0.00",
                          font=("Arial", 10, "bold"), bg="white", fg=color)
            lw.pack(side="left")
            setattr(self, attr, lw)

        dr = tk.Frame(tot, bg="white")
        dr.pack(anchor="w", pady=(4, 0))
        tk.Label(dr, text="Discount (Rs):", font=("Arial", 8),
                 bg="white").pack(side="left")
        self.disc_var = tk.StringVar(value="0")
        disc_e = self._entry(dr, var=self.disc_var, width=8)
        disc_e.pack(side="left", padx=6)
        disc_e.bind("<KeyRelease>", lambda e: self._update_totals())

        # Payment
        pay = tk.LabelFrame(bot, text="Payment", bg="white",
                             font=("Arial", 9), padx=10, pady=6)
        pay.pack(side="left", padx=(0, 12))
        self.pay_var = tk.StringVar(value="Cash")
        for method in ["Cash", "Credit (Khatoo)"]:
            tk.Radiobutton(pay, text=method, variable=self.pay_var,
                           value=method, font=("Arial", 9),
                           bg="white").pack(anchor="w")

        # Actions
        act = tk.Frame(bot, bg="white")
        act.pack(side="left")
        self._btn(act, "Confirm Sale", self._confirm_sale,
                  bg="#27ae60").pack(pady=4)
        self._btn(act, "Clear Cart",   self._clear_cart,
                  bg="#e74c3c").pack(pady=4)
        return f

    def _search_cust(self):
        kw = self.cust_var.get().strip()
        if not kw:
            self.cust_info.config(text="Please enter an ID to search.", fg="#e67e22")
            return
        results = db_search_customer(kw)
        if results:
            cnic, fn, ln = results[0]
            self.selected_cust = cnic
            self.cust_info.config(text=f"{fn} {ln}  (ID: {cnic})", fg="green")
        else:
            self.selected_cust = None
            self.cust_info.config(
                text="Customer not found. Register them first.", fg="red"
            )

    def _load_all_prods_to_pos(self):
        """Loads every single product into the dropdown by default."""
        self.prod_results = db_search_products("")
        self._update_prod_combo_results()

    def _live_filter_prod(self):
        """Filters the product list in real-time as the user types."""
        query = self.prod_var.get().strip()
        self.prod_results = db_search_products(query)
        self._update_prod_combo_results()

    def _update_prod_combo_results(self):
        """Helper to refresh the dropdown UI with current search results."""
        if not self.prod_results:
            self.prod_combo["values"] = ["No matching products"]
            return
        
        # Format display: Name | Price | Stock
        display = [f"{r[1]}  |  Rs.{r[2]}  |  Stock:{r[4]}"
                   for r in self.prod_results]
        self.prod_combo["values"] = display
        if display:
            self.prod_combo.current(0) # Select first match automatically

    def _search_prod(self):
        # Triggered by manual button if needed, but _live_filter handles typing
        self._live_filter_prod()

    def _add_cart(self):
        idx = self.prod_combo.current()
        if idx < 0 or not self.prod_results:
            messagebox.showwarning("No Product", "Search and select a product first.")
            return
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Qty", "Please enter a whole number greater than 0.")
            return
        prod_id, name, price, batch_id, stock = self.prod_results[idx]
        if qty > stock:
            messagebox.showerror("Not Enough Stock",
                                 f"Only {stock} units of '{name}' are available.")
            return
        subtotal = float(price) * qty
        
        # CART MERGER: Check if batch_id already exists in cart
        for item in self.cart:
            if item["batch_id"] == batch_id:
                new_qty = item["qty"] + qty
                if new_qty > stock:
                    messagebox.showerror("Not Enough Stock", 
                                         f"Total qty ({new_qty}) exceeds available stock ({stock}).")
                    return
                item["qty"] = new_qty
                item["subtotal"] = item["price"] * new_qty
                self._refresh_cart_tree()
                self._update_totals()
                return

        # New item entry
        self.cart.append(dict(prod_id=prod_id, name=name, price=float(price),
                               batch_id=batch_id, qty=qty, subtotal=subtotal))
        self._refresh_cart_tree()
        self._update_totals()

    def _refresh_cart_tree(self):
        """Helper to redraw the cart UI from the self.cart list."""
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        for i in self.cart:
            self.cart_tree.insert("", tk.END,
                values=(i["name"], i["batch_id"], f"Rs.{i['price']}", i["qty"], f"Rs.{i['subtotal']:.2f}"))

    def _update_totals(self):
        sub = sum(i["subtotal"] for i in self.cart)
        try:
            disc = float(self.disc_var.get())
            if disc < 0:
                disc = 0
        except ValueError:
            disc = 0
        total = max(sub - disc, 0)
        self.lbl_sub.config(text=f"Rs. {sub:.2f}")
        self.lbl_disc.config(text=f"Rs. {disc:.2f}")
        self.lbl_total.config(text=f"Rs. {total:.2f}")

    def _clear_cart(self):
        self.cart = []
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.disc_var.set("0")
        self._update_totals()

    def _confirm_sale(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add at least one product before confirming.")
            return
        if not self.selected_cust:
            messagebox.showwarning("No Customer",
                                   "Please search and select a customer first.")
            return
        try:
            disc = float(self.disc_var.get())
            if disc < 0: disc = 0
        except ValueError:
            disc = 0
        
        subtotal = sum(i["subtotal"] for i in self.cart)
        if disc > subtotal:
            messagebox.showerror("Discount Error", 
                                 f"Discount (Rs.{disc}) cannot be greater than "
                                 f"Subtotal (Rs.{subtotal}).")
            return

        total = max(subtotal - disc, 0)
        if not messagebox.askyesno(
            "Confirm Sale",
            f"Total:    Rs. {total:.2f}\n"
            f"Payment:  {self.pay_var.get()}\n\n"
            "Confirm and record this sale?"
        ):
            return
        ok = db_confirm_sale(
            self.selected_cust, self.current_user[0], self.cart,
            total, disc, self.pay_var.get()
        )
        if ok:
            messagebox.showinfo("Sale Recorded", "Sale confirmed and saved!\n\nInvoice generated in 'receipts' folder.")
            self._clear_cart()
            self.selected_cust = None
            self.cust_info.config(text="No customer selected", fg="#7f8c8d")
            # Instant UI/Backend Sync: Update Dashboard AND Reports after sale
            self._refresh_dashboard()
            self._load_reports()

    # ── KHATOO ───────────────────────────────────────────────
    def _build_khatoo(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Khatoo (Credit Ledger)")

        # Search row
        sr = tk.Frame(f, bg="white")
        sr.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(sr, text="Search by CNIC or Name:",
                 font=("Arial", 9), bg="white").pack(side="left", padx=(0, 6))
        self.khatoo_search = tk.StringVar()
        self._entry(sr, var=self.khatoo_search, width=28).pack(side="left", padx=(0, 8))
        self._btn(sr, "Search", self._load_khatoo).pack(side="left", padx=(0, 6))
        self._btn(sr, "Show All",
                  lambda: (self.khatoo_search.set(""), self._load_khatoo()),
                  bg="#7f8c8d").pack(side="left")

        # Treeview
        cols = ("ID", "Customer", "Purchase #", "Amount Due", "Amount Paid", "Status")
        self.khatoo_tree = ttk.Treeview(f, columns=cols,
                                         show="headings", height=12)
        for col, w in zip(cols, [50, 160, 100, 120, 120, 90]):
            self.khatoo_tree.heading(col, text=col)
            self.khatoo_tree.column(col, width=w, anchor="center")

        # Colour rows: green for settled, red for pending
        self.khatoo_tree.tag_configure("settled", foreground="#27ae60")
        self.khatoo_tree.tag_configure("pending", foreground="#e74c3c")

        self.khatoo_tree.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        # Payment row
        pr = tk.Frame(f, bg="white")
        pr.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(pr, text="Payment Amount (Rs):",
                 font=("Arial", 9), bg="white").pack(side="left")
        self.pay_amt = tk.StringVar()
        self._entry(pr, var=self.pay_amt, width=12).pack(side="left", padx=8)
        self._btn(pr, "Record Payment", self._record_payment,
                  bg="#27ae60").pack(side="left")
        self.khatoo_msg = tk.Label(pr, text="", font=("Arial", 9),
                                    bg="white", fg="green")
        self.khatoo_msg.pack(side="left", padx=10)
        return f

    def _load_khatoo(self):
        for row in self.khatoo_tree.get_children():
            self.khatoo_tree.delete(row)
        rows = db_load_khatoo(self.khatoo_search.get().strip())
        if not rows:
            self.khatoo_msg.config(text="No records found.", fg="#7f8c8d")
            return
        self.khatoo_msg.config(text="")
        for r in rows:
            amount_due  = float(r[3])
            amount_paid = float(r[4])
            settled     = amount_due <= 0
            status      = "Settled" if settled else "⏳ Pending"
            tag         = "settled"   if settled else "pending"
            self.khatoo_tree.insert("", tk.END,
                values=(r[0], r[1], r[2],
                        f"Rs. {amount_due:.2f}",
                        f"Rs. {amount_paid:.2f}",
                        status),
                tags=(tag,))

    def _record_payment(self):
        selected = self.khatoo_tree.focus()
        if not selected:
            self.khatoo_msg.config(
                text="⚠ Select a row from the table first.", fg="red"
            )
            return
        try:
            amount = float(self.pay_amt.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.khatoo_msg.config(
                text="⚠ Enter a valid payment amount (e.g. 500).", fg="red"
            )
            return
        vals = self.khatoo_tree.item(selected, "values")
        try:
            # Safely parse the 'Amount Due' column which might have currency symbols
            due_str = str(vals[3]).replace("Rs.", "").replace(",", "").strip()
            due = float(due_str)
        except (ValueError, IndexError):
            due = 0.0

        if amount > due:
            messagebox.showwarning("Overpayment", 
                                 f"Transaction Blocked!\n\n"
                                 f"You are trying to pay Rs. {amount:,.2f} but "
                                 f"the amount due is only Rs. {due:,.2f}.\n\n"
                                 f"Overpayments are not allowed for security.")
            return

        # FINANCIAL HARDENING: Add Confirmation
        customer_name = vals[1]
        if not messagebox.askyesno("Confirm Payment", 
                                   f"Receive Payment for {customer_name}?\n\n"
                                   f"Amount: Rs. {amount:,.2f}\n\n"
                                   "This will update the ledger. Proceed?"):
            return

        khatoo_id = vals[0]
        ok = db_record_payment(khatoo_id, amount)
        if ok:
            self.khatoo_msg.config(text="Payment recorded.", fg="green")
            self.pay_amt.set("")
            self._load_khatoo()
            # Instant Dashboard Sync
            self._refresh_dashboard()


        self.root.after(30_000, self._refresh_dashboard)

    # ── INVENTORY MANAGEMENT ─────────────────────────────────
    def _build_inventory(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Inventory — Management")

        # Top row: Register New Master Data
        top_row = tk.Frame(f, bg="white")
        top_row.pack(fill="x", padx=20, pady=5)

        # 1. New Product Box
        p_box = tk.LabelFrame(top_row, text="Add New Product Type", bg="white", font=("Arial", 9, "bold"), fg="#2980b9")
        p_box.pack(side="left", padx=(0, 10), fill="both", expand=True)
        self.new_p_name = tk.StringVar()
        self.new_p_price = tk.StringVar()
        self.new_p_min = tk.StringVar(value="10")
        
        self._lbl(p_box, "Name:").grid(row=0, column=0, sticky="w", padx=5)
        self._entry(p_box, var=self.new_p_name, width=15).grid(row=0, column=1, pady=2)
        self._lbl(p_box, "Price:").grid(row=1, column=0, sticky="w", padx=5)
        self._entry(p_box, var=self.new_p_price, width=15).grid(row=1, column=1, pady=2)
        self._lbl(p_box, "Min Stock:").grid(row=2, column=0, sticky="w", padx=5)
        self._entry(p_box, var=self.new_p_min, width=15).grid(row=2, column=1, pady=2)
        self._btn(p_box, "Create Product", self._do_add_product, bg="#3498db").grid(row=3, column=0, columnspan=2, pady=10)

        # 2. New Supplier Box
        s_box = tk.LabelFrame(top_row, text="Add New Supplier", bg="white", font=("Arial", 9, "bold"), fg="#2980b9")
        s_box.pack(side="left", fill="both", expand=True)
        self.new_s_name = tk.StringVar()
        self.new_s_cont = tk.StringVar()
        
        self._lbl(s_box, "Company Name:").grid(row=0, column=0, sticky="w", padx=5)
        self._entry(s_box, var=self.new_s_name, width=15).grid(row=0, column=1, pady=2)
        self._lbl(s_box, "Contact Details:").grid(row=1, column=0, sticky="w", padx=5)
        self._entry(s_box, var=self.new_s_cont, width=15).grid(row=1, column=1, pady=2)
        self._btn(s_box, "Create Supplier", self._do_add_supplier, bg="#3498db").grid(row=3, column=0, columnspan=2, pady=10)

        # 3. Add Batch (Below)
        b_box = tk.LabelFrame(f, text="Add Shipment (Existing Product & Supplier)", bg="white", font=("Arial", 9, "bold"), fg="#27ae60")
        b_box.pack(fill="x", padx=20, pady=10)
        
        form = tk.Frame(b_box, bg="white")
        form.pack(padx=20, pady=10, anchor="w")

        # Product selection
        tk.Label(form, text="Select Product:", font=("Arial", 9), bg="white").grid(row=0, column=0, sticky="w")
        self.stock_prod = ttk.Combobox(form, state="readonly", width=30)
        self.stock_prod.grid(row=0, column=1, pady=5, padx=10)

        # Supplier selection
        tk.Label(form, text="Select Supplier:", font=("Arial", 9), bg="white").grid(row=1, column=0, sticky="w")
        self.stock_supp = ttk.Combobox(form, state="readonly", width=30)
        self.stock_supp.grid(row=1, column=1, pady=5, padx=10)

        # Qty
        tk.Label(form, text="Quantity:", font=("Arial", 9), bg="white").grid(row=2, column=0, sticky="w")
        self.stock_qty = tk.StringVar(value="100")
        self._entry(form, var=self.stock_qty, width=10).grid(row=2, column=1, sticky="w", padx=10)

        # Expiry
        tk.Label(form, text="Expiry (YYYY-MM-DD):", font=("Arial", 9), bg="white").grid(row=3, column=0, sticky="w")
        self.stock_exp = tk.StringVar(value="2027-01-01")
        self._entry(form, var=self.stock_exp, width=15).grid(row=3, column=1, sticky="w", padx=10)

        # MFG
        tk.Label(form, text="MFG Date (YYYY-MM-DD):", font=("Arial", 9), bg="white").grid(row=4, column=0, sticky="w")
        self.stock_mfg = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._entry(form, var=self.stock_mfg, width=15).grid(row=4, column=1, sticky="w", padx=10)

        self._btn(b_box, "Save Shipment to Inventory", self._do_add_stock, bg="#27ae60").pack(padx=20, pady=10, anchor="w")
        
        self.stock_msg = tk.Label(f, text="", font=("Arial", 9), bg="white")
        self.stock_msg.pack(padx=20, anchor="w")

        self._load_inventory_options()
        return f

    def _do_add_product(self):
        name = self.new_p_name.get().strip()
        try:
            price = float(self.new_p_price.get())
            min_s = int(self.new_p_min.get())
            if not name: raise ValueError
        except:
            messagebox.showerror("Input Error", "Enter valid Name, Price and Min Stock")
            return
        
        status = db_register_product(name, price, min_s)
        if status == True:
            messagebox.showinfo("Success", f"Product '{name}' registered!")
            self.new_p_name.set(""); self.new_p_price.set(""); self.new_p_min.set("10")
            self._load_inventory_options()
        elif status == "EXISTS":
            messagebox.showwarning("Duplicate", f"Product '{name}' already exists in the system.")
        else:
            messagebox.showerror("Error", "Failed to register product.")

    def _do_add_supplier(self):
        name = self.new_s_name.get().strip()
        cont = self.new_s_cont.get().strip()
        if not name or not cont:
            messagebox.showerror("Input Error", "Enter valid Supplier Name and Contact")
            return
        
        status = db_register_supplier(name, cont)
        if status == True:
            messagebox.showinfo("Success", f"Supplier '{name}' registered!")
            self.new_s_name.set(""); self.new_s_cont.set("")
            self._load_inventory_options()
        elif status == "EXISTS":
            messagebox.showwarning("Duplicate", f"Supplier '{name}' already exists.")
        else:
            messagebox.showerror("Error", "Failed to register supplier.")

    def _load_inventory_options(self):
        # Products
        prods = db_get_all_products()
        self.stock_prod["values"] = [f"{p[0]} | {p[1]}" for p in prods]
        # Suppliers
        supps = db_get_suppliers()
        self.stock_supp["values"] = [f"{s[0]} | {s[1]}" for s in supps]

    def _do_add_stock(self):
        try:
            p_sel = self.stock_prod.get()
            s_sel = self.stock_supp.get()
            if not p_sel or not s_sel: raise ValueError("Select product and supplier")
            
            p_id = p_sel.split("|")[0].strip()
            s_id = s_sel.split("|")[0].strip()
            qty  = int(self.stock_qty.get())
            exp  = self.stock_exp.get().strip()
            mfg  = self.stock_mfg.get().strip()
            
            if not mfg:
                mfg = date.today().strftime("%Y-%m-%d")

            # Date Format Validation
            for d in [exp, mfg]:
                try:
                    datetime.strptime(d, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Date Error", f"Invalid date: {d}\nPlease use YYYY-MM-DD format.")
                    return

            if qty <= 0:
                messagebox.showerror("Quantity Error", "Batch quantity must be a positive number.")
                return

            exp_dt = datetime.strptime(exp, "%Y-%m-%d").date()
            if exp_dt <= date.today():
                messagebox.showerror("Safety Warning", 
                                     f"STOP!\n\nYou are trying to add a batch that has ALREADY EXPIRED (Expiry: {exp}).\n\n"
                                     "Pharmacy safety rules prevent adding expired stock.")
                return

            ok = db_add_batch(p_id, s_id, qty, exp, mfg)
            if ok:
                messagebox.showinfo("Success", "New batch added successfully!")
                self._refresh_dashboard()
            else:
                messagebox.showerror("Error", "Failed to add batch.")
        except Exception as e:
            messagebox.showerror("Input Error", f"Check your entries:\n{e}")

    # ── SUPPLIER REPORT ──────────────────────────────────────
    def _build_supp_report(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Supplier Inventory Report")

        ctrl = tk.Frame(f, bg="white")
        ctrl.pack(fill="x", padx=20, pady=10)
        
        tk.Label(ctrl, text="Select Supplier:", font=("Arial", 9), bg="white").pack(side="left")
        self.rep_supp_combo = ttk.Combobox(ctrl, state="readonly", width=30)
        self.rep_supp_combo.pack(side="left", padx=10)
        self._btn(ctrl, "Load Report", self._load_supp_report, bg="#3498db").pack(side="left")

        self.rep_tree = ttk.Treeview(f, columns=("Product", "Batch", "Qty", "Expiry"), show="headings", height=15)
        for col, w in [("Product", 250), ("Batch", 120), ("Qty", 80), ("Expiry", 120)]:
            self.rep_tree.heading(col, text=col)
            self.rep_tree.column(col, width=w, anchor="center")
        self.rep_tree.pack(fill="both", expand=True, padx=20, pady=10)

        # Pre-load suppliers
        supps = db_get_suppliers()
        self.rep_supp_combo["values"] = [f"{s[0]} | {s[1]}" for s in supps]
        return f

    def _load_supp_report(self):
        sel = self.rep_supp_combo.get()
        if not sel: 
            messagebox.showwarning("Selection Required", "Please select a supplier first.")
            return
        s_id = sel.split("|")[0].strip()
        for row in self.rep_tree.get_children(): self.rep_tree.delete(row)
        rows = db_get_stocks_by_supplier(s_id)
        for r in rows:
            self.rep_tree.insert("", tk.END, values=r)

    # ── ALERT NOTIFICATION HUB ───────────────────────────────
    def _build_alerts(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Notification Center (Alerts)")

        nb = ttk.Notebook(f)
        nb.pack(fill="both", expand=True, padx=20, pady=10)

        # Tab 1: Near Expiry
        t1 = tk.Frame(nb, bg="white")
        nb.add(t1, text=" Near Expiry (30 Days) ")
        self.tree_near = self._create_alert_tree(t1)

        # Tab 2: Expired
        t2 = tk.Frame(nb, bg="white")
        nb.add(t2, text=" EXPIRED (Remove Stock) ")
        self.tree_expired = self._create_alert_tree(t2)

        self._btn(f, "Refresh All Alerts", self._refresh_alert_tabs, bg="#e67e22").pack(pady=10)
        self._refresh_alert_tabs()
        return f

    def _create_alert_tree(self, parent):
        tree = ttk.Treeview(parent, columns=("Product", "Batch", "Expiry", "Qty"), show="headings")
        for col, w in [("Product", 250), ("Batch", 120), ("Expiry", 120), ("Qty", 80)]:
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        return tree

    def _refresh_alert_tabs(self):
        # Near Expiry
        for r in self.tree_near.get_children(): self.tree_near.delete(r)
        for r in db_get_near_expiry(30): self.tree_near.insert("", tk.END, values=r)
        
        # Expired
        for r in self.tree_expired.get_children(): self.tree_expired.delete(r)
        for r in db_get_expired(): self.tree_expired.insert("", tk.END, values=r)

    # ── SALES REPORTS HUB ────────────────────────────────────
    def _build_reports(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Sales History & Revenue Reports")

        # Top summary bar
        summary = tk.Frame(f, bg="#f9f9f9", height=60)
        summary.pack(fill="x", padx=20, pady=10)
        summary.pack_propagate(False)

        tk.Label(summary, text="TOTAL REVENUE:", font=("Arial", 11, "bold"), bg="#f9f9f9", fg="#2c3e50").pack(side="left", padx=20)
        self.rev_lbl = tk.Label(summary, text="Rs. 0.00", font=("Arial", 14, "bold"), bg="#f9f9f9", fg="#27ae60")
        self.rev_lbl.pack(side="left")

        self._btn(summary, "↻ Refresh History", self._load_reports, bg="#34495e").pack(side="right", padx=20)

        # Main data table
        self.sales_tree = ttk.Treeview(f, columns=("ID", "Date", "Time", "Customer", "Amount", "Method"), show="headings")
        for col, w in [("ID", 60), ("Date", 110), ("Time", 100), ("Customer", 180), ("Amount", 120), ("Method", 100)]:
            self.sales_tree.heading(col, text=col)
            self.sales_tree.column(col, width=w, anchor="center")
        self.sales_tree.pack(fill="both", expand=True, padx=20, pady=10)

        # Action Bar
        act = tk.Frame(f, bg="white")
        act.pack(fill="x", padx=20, pady=(0, 20))
        self._btn(act, "View Detailed Receipt", self._view_receipt_detail, bg="#2980b9").pack(side="left")

        self._load_reports()
        return f

    def _view_receipt_detail(self):
        sel = self.sales_tree.selection()
        if not sel:
            messagebox.showwarning("Select Sale", "Please select a sale from the list first.")
            return
        
        row = self.sales_tree.item(sel[0], "values")
        purchase_id = row[0]
        
        # Create Popup
        pop = tk.Toplevel(self.root)
        pop.title(f"Receipt Details - Purchase #{purchase_id}")
        pop.geometry("500x400")
        pop.configure(bg="white")
        
        tk.Label(pop, text=f"Receipt for Purchase #{purchase_id}", 
                 font=("Arial", 12, "bold"), bg="white", fg="#2c3e50").pack(pady=10)
        
        cols = ("Product", "Batch", "Qty", "Price", "Subtotal")
        tree = ttk.Treeview(pop, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [150, 80, 60, 80, 100]):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Load Details from DB
        items = db_get_purchase_items(purchase_id)
        for i in items:
            tree.insert("", tk.END, values=i)
        
        self._btn(pop, "Close", pop.destroy, bg="#7f8c8d").pack(pady=10)

    def _load_reports(self):
        # Safety Check: Does the tree exist? (Prevent crash during init)
        if not hasattr(self, 'sales_tree'): return

        # Clear
        for r in self.sales_tree.get_children(): self.sales_tree.delete(r)
        
        # Load
        rows = db_get_sales_history()
        total_rev = 0
        for r in rows:
            self.sales_tree.insert("", tk.END, values=r)
            try:
                # DEEP CLEAN: Remove commas, spaces, and Rs. symbol before converting to float
                val = str(r[4]).replace("Rs.", "").replace(",", "").strip()
                price = float(val) if val else 0.0
                total_rev += price
            except (ValueError, TypeError):
                continue
        
        self.rev_lbl.config(text=f"Rs. {total_rev:,.2f}")

# ── Entry point (when run directly) ────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = SalesmanApp(root)
    root.mainloop()
