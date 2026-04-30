import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

import mysql.connector

def get_conn():
    return mysql.connector.connect(
        host='localhost',
        user='pharma',
        password='pharma123',
        database='pharmacy_db'
    )
# ── Stub functions — fill these in ──────────────────────
def db_register_customer(cnic, fname, lname, email, city):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Customers (id_card_number, first_name, last_name, Email_Address, city, registration_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (cnic,fname,lname,email,city,date.today()))
    conn.commit()
    conn.close()

def db_search_customer(id_no):
    # return list of (cnic, first_name, last_name)
    customers = []
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
		SELECT id_card_number,first_name,last_name
		FROM Customers WHERE id_card_number LIKE %s""",(f"%{id_no}%",)
    )
    customers = cur.fetchall()
    conn.close()
    return customers

def db_search_products(keyword):
    # return list of (prod_id, name, price, batch_id, stock)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.product_name, p.price, b.id, b.quantity
        FROM Products p
        JOIN Batch b ON b.product_id = p.id
        WHERE p.product_name LIKE %s
          AND b.quantity > 0
          AND b.expiry_date > CURDATE()
    """, (f"%{keyword}%",))
    rows = cur.fetchall()
    conn.close()
    return rows
    
def db_confirm_sale(customer_id, cart, discount, payment_method):
    # cart = list of dicts: {prod_id, name, price, batch_id, qty, subtotal}
    pass

def db_confirm_sale(customer_id, cart, discount, payment_method):
    # cart = list of dicts: {prod_id, name, price, batch_id, qty, subtotal}
    conn = get_conn()
    cur = conn.cursor()
    
    total = max(sum(i["subtotal"] for i in cart)-discount,0)
    
    cur.execute("""
		Insert INTO Purchase(number_of_products,total_price,price_with_tax,customer_id,employee_id,payment_method,discount_amount)
		VALUES(%s,%s,%s,%s,%s,%s,%s)
    """,
		(len(cart), total, total, customer_id, 1,
          "Cash" if payment_method == "Cash" else "Credit", discount))
    
    
    purchase_id = cur.lastrowid
    
    for item in cart:
        cur.execute("""
            INSERT INTO Sales_details(purchase_id,batch_id,Quantity)
            VALUES (%s,%s,%s)
        """,(purchase_id, item["batch_id"], item["qty"]))

        cur.execute("""
            UPDATE Batch SET quantity = quantity -%s WHERE id = %s
        """,(item["qty"], item["batch_id"]))

        cur.execute("""
            UPDATE Products SET stock_quantity = stock_quantity - %s WHERE id=%s
        """,(item["qty"],item["prod_id"]))
		
		
    cur.execute("""
        INSERT INTO Receipt(printing_date,time,purchase_id,number_of_items)
        VALUES (%s,%s,%s,%s)
    """,(date.today(),datetime.now().strftime("%H:%M:%S"),purchase_id,len(cart)))
	
    if payment_method == "Credit (Khatoo)":
        cur.execute("""
            INSERT INTO Customer_Khatoo(amount_paid,amount_due,purchase_id,customer_id,payment_method)
            VALUES (%s,%s,%s,%s,%s)
        """,(0,total,purchase_id,customer_id,"Credit"))

    conn.commit()
    conn.close()


def db_load_khatoo(keyword=""):
    conn=get_conn()
    cur=conn.cursor()
    print(keyword)
    
    if keyword:

	    cur.execute(f"""
            SELECT k.id,c.first_name,k.purchase_id,k.amount_due,k.amount_paid
            FROM Customer_Khatoo k,Customers c
            WHERE k.customer_id =c.id_card_number AND c.id_card_number ={keyword}
            
        """,(f"%{keyword}%",))
         
    else:
        cur.execute("""
            SELECT k.id,c.first_name,k.purchase_id,k.amount_due,k.amount_paid
            FROM Customer_Khatoo k,Customers c
            WHERE k.customer_id =c.id_card_number
        """)
    
    data = cur.fetchall()
    print(data)
    conn.close()
    return data


def db_record_payment(khatoo_id, amount):
    
    conn=get_conn()
    cur = conn.cursor()
    
    cur.execute("""
		
    """)
    data = cur.fetchall()
    conn.close()
# ────────────────────────────────────────────────────────


class SalesmanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pharmacy - Salesman Panel")
        self.root.geometry("1100x680")
        self.cart = []
        self._build_layout()
        self.show_frame(self.home_frame)

    # ── Layout ───────────────────────────────────────────
    def _build_layout(self):
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Pharmacy System", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=20)

        nav = [
            ("Home",              lambda: self.show_frame(self.home_frame)),
            ("Register Customer", lambda: self.show_frame(self.reg_frame)),
            ("Make a Bill",       lambda: self.show_frame(self.bill_frame)),
            ("Khatoo",            lambda: self.show_frame(self.khatoo_frame)),
        ]
        for label, cmd in nav:
            tk.Button(sidebar, text=label, font=("Arial", 10),
                      bg="#2c3e50", fg="white", relief="flat",
                      activebackground="#34495e", anchor="w",
                      padx=16, pady=10, cursor="hand2",
                      command=cmd).pack(fill="x")

        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(side="right", fill="both", expand=True)

        self.home_frame   = self._build_home()
        self.reg_frame    = self._build_register()
        self.bill_frame   = self._build_bill()
        self.khatoo_frame = self._build_khatoo()

        for f in [self.home_frame, self.reg_frame,
                  self.bill_frame, self.khatoo_frame]:
            f.place(relwidth=1, relheight=1)

    def show_frame(self, frame):
        frame.tkraise()

    # ── Helpers ──────────────────────────────────────────
    def _title(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 16, "bold"),
                 bg="white", fg="#2c3e50").pack(anchor="w", padx=20, pady=(20, 4))
        tk.Frame(parent, bg="#bdc3c7", height=1).pack(fill="x", padx=20, pady=(0, 14))

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, font=("Arial", 9),
                        bg="white", fg="#555")

    def _entry(self, parent, var=None, width=30):
        return tk.Entry(parent, textvariable=var, width=width,
                        font=("Arial", 10), relief="solid", bd=1)

    def _btn(self, parent, text, cmd, bg="#2980b9", fg="white"):
        return tk.Button(parent, text=text, command=cmd,
                         font=("Arial", 9, "bold"), bg=bg, fg=fg,
                         relief="flat", padx=10, pady=5, cursor="hand2")

    # ══════════════════════════════════════════════════════
    # HOME
    # ══════════════════════════════════════════════════════
    def _build_home(self):
        f = tk.Frame(self.content, bg="white")
        tk.Label(f, text="Welcome", font=("Arial", 22, "bold"),
                 bg="white", fg="#2c3e50").pack(pady=(60, 8))
        tk.Label(f, text="Select an option from the sidebar",
                 font=("Arial", 11), bg="white", fg="#7f8c8d").pack()

        cards = tk.Frame(f, bg="white")
        cards.pack(pady=40)
        for (label, cmd) in [
            ("Register Customer", lambda: self.show_frame(self.reg_frame)),
            ("Make a Bill",       lambda: self.show_frame(self.bill_frame)),
            ("Khatoo",            lambda: self.show_frame(self.khatoo_frame)),
        ]:
            btn = tk.Button(cards, text=label, command=cmd,
                            font=("Arial", 11), width=18, height=3,
                            bg="#ecf0f1", fg="#2c3e50", relief="solid",
                            bd=1, cursor="hand2")
            btn.pack(side="left", padx=12)
        return f

    # ══════════════════════════════════════════════════════
    # REGISTER CUSTOMER
    # ══════════════════════════════════════════════════════
    def _build_register(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Register Customer")

        form = tk.Frame(f, bg="white")
        form.pack(padx=30, anchor="w")

        self.reg_vars = {}
        fields = [
            ("CNIC / ID Number *", "cnic"),
            ("First Name *",        "fname"),
            ("Last Name *",         "lname"),
            ("Email",               "email"),
            ("City",                "city"),
        ]
        for i, (label, key) in enumerate(fields):
            self._lbl(form, label).grid(row=i, column=0, sticky="w", pady=5, padx=(0, 12))
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
            self.reg_msg.config(text="CNIC, First Name and Last Name are required.", fg="red")
            return
        db_register_customer(cnic, fname, lname,
                              v["email"].get().strip(),
                              v["city"].get().strip())
        self.reg_msg.config(text=f"Customer '{fname} {lname}' registered.", fg="green")
        self._clear_reg()

    def _clear_reg(self):
        for var in self.reg_vars.values():
            var.set("")

    # ══════════════════════════════════════════════════════
    # MAKE A BILL
    # ══════════════════════════════════════════════════════
    def _build_bill(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Make a Bill")

        top = tk.Frame(f, bg="white")
        top.pack(fill="x", padx=20, pady=(0, 8))

        # Customer search
        cust_box = tk.LabelFrame(top, text="Customer(Enter cnic)", bg="white",
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
        prod_box = tk.LabelFrame(top, text="Add Product", bg="white",
                                  font=("Arial", 9), padx=8, pady=6)
        prod_box.pack(side="left")
        self.prod_var = tk.StringVar()
        r2 = tk.Frame(prod_box, bg="white")
        r2.pack()
        self._entry(r2, var=self.prod_var, width=20).pack(side="left", padx=(0, 6))
        self._btn(r2, "Search", self._search_prod).pack(side="left")
        self.prod_combo = ttk.Combobox(prod_box, state="readonly", width=36)
        self.prod_combo.pack(pady=4, anchor="w")
        self.prod_results = []
        r3 = tk.Frame(prod_box, bg="white")
        r3.pack(anchor="w")
        tk.Label(r3, text="Qty:", font=("Arial", 9), bg="white").pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        self._entry(r3, var=self.qty_var, width=5).pack(side="left", padx=6)
        self._btn(r3, "Add to Cart", self._add_cart, bg="#27ae60").pack(side="left")

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

        # Bottom
        bot = tk.Frame(f, bg="white")
        bot.pack(fill="x", padx=20, pady=8)

        # Totals
        tot = tk.LabelFrame(bot, text="Totals", bg="white",
                             font=("Arial", 9), padx=10, pady=6)
        tot.pack(side="left", padx=(0, 12))
        for (lbl, attr, color) in [
            ("Subtotal:", "lbl_sub",   "#2c3e50"),
            ("Discount:", "lbl_disc",  "#e67e22"),
            ("Total:",    "lbl_total", "#27ae60"),
        ]:
            row = tk.Frame(tot, bg="white")
            row.pack(anchor="w")
            tk.Label(row, text=lbl, width=10, anchor="w",
                     font=("Arial", 9), bg="white").pack(side="left")
            lw = tk.Label(row, text="Rs. 0.00", font=("Arial", 10, "bold"),
                          bg="white", fg=color)
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
            return
        results = db_search_customer(kw)
        if results:
            cnic, fn, ln = results[0]
            self.selected_cust = cnic
            self.cust_info.config(text=f"{fn} {ln}  (CNIC: {cnic})", fg="green")
        else:
            self.selected_cust = None
            self.cust_info.config(text="Customer not found.", fg="red")

    def _search_prod(self):
        kw = self.prod_var.get().strip()
        if not kw:
            return
        self.prod_results = db_search_products(kw)
        display = [f"{r[1]}  |  Rs.{r[2]}  |  Stock:{r[4]}"
                   for r in self.prod_results]
        self.prod_combo["values"] = display
        if display:
            self.prod_combo.current(0)

    def _add_cart(self):
        idx = self.prod_combo.current()
        if idx < 0 or not self.prod_results:
            messagebox.showwarning("No Product", "Search and select a product first.")
            return
        try:
            qty = int(self.qty_var.get())
            assert qty > 0
        except:
            messagebox.showerror("Invalid Qty", "Enter a valid quantity.")
            return
        prod_id, name, price, batch_id, stock = self.prod_results[idx]
        if qty > stock:
            messagebox.showerror("Stock Error", f"Only {stock} units available.")
            return
        subtotal = float(price) * qty
        self.cart.append(dict(prod_id=prod_id, name=name, price=float(price),
                               batch_id=batch_id, qty=qty, subtotal=subtotal))
        self.cart_tree.insert("", tk.END,
            values=(name, batch_id, f"Rs.{price}", qty, f"Rs.{subtotal:.2f}"))
        self._update_totals()

    def _update_totals(self):
        sub = sum(i["subtotal"] for i in self.cart)
        try:
            disc = float(self.disc_var.get())
        except:
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
            messagebox.showwarning("Empty Cart", "Add products first.")
            return
        if not self.selected_cust:
            messagebox.showwarning("No Customer", "Select a customer first.")
            return
        try:
            disc = float(self.disc_var.get())
        except:
            disc = 0
        total = max(sum(i["subtotal"] for i in self.cart) - disc, 0)
        if not messagebox.askyesno("Confirm",
                f"Total: Rs. {total:.2f}\nPayment: {self.pay_var.get()}\n\nConfirm?"):
            return
        db_confirm_sale(self.selected_cust, self.cart, disc, self.pay_var.get())
        messagebox.showinfo("Done", "Sale confirmed!")
        self._clear_cart()

    # ══════════════════════════════════════════════════════
    # KHATOO
    # ══════════════════════════════════════════════════════
    def _build_khatoo(self):
        f = tk.Frame(self.content, bg="white")
        self._title(f, "Khatoo — Credit Ledger")

        sr = tk.Frame(f, bg="white")
        sr.pack(fill="x", padx=20, pady=(0, 8))
        self.khatoo_search = tk.StringVar()
        self._entry(sr, var=self.khatoo_search, width=28).pack(side="left", padx=(0, 8))
        self._btn(sr, "Search", self._load_khatoo).pack(side="left", padx=(0, 6))
        self._btn(sr, "Show All", lambda: (self.khatoo_search.set(""),
                                            self._load_khatoo()),
                  bg="#7f8c8d").pack(side="left")

        cols = ("ID", "Customer", "Purchase", "Amount Due",
                "Amount Paid")
        self.khatoo_tree = ttk.Treeview(f, columns=cols,
                                         show="headings", height=12)
        for col, w in zip(cols, [50, 160, 90, 110, 110, 90, 90]):
            self.khatoo_tree.heading(col, text=col)
            self.khatoo_tree.column(col, width=w, anchor="center")
        self.khatoo_tree.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        pr = tk.Frame(f, bg="white")
        pr.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(pr, text="Payment Amount (Rs):", font=("Arial", 9),
                 bg="white").pack(side="left")
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
        for r in rows:
            status = "Settled" if float(r[3]) == 0 else "Pending"
            self.khatoo_tree.insert("", tk.END,
                values=(r[0], r[1], r[2],
                        f"Rs. {float(r[3]):.2f}",
                        f"Rs. {float(r[4]):.2f}",
                        ))

    def _record_payment(self):
        selected = self.khatoo_tree.focus()
        if not selected:
            self.khatoo_msg.config(text="Select a record first.", fg="red")
            return
        try:
            amount = float(self.pay_amt.get())
            assert amount > 0
        except:
            self.khatoo_msg.config(text="Enter a valid amount.", fg="red")
            return
        khatoo_id = self.khatoo_tree.item(selected, "values")[0]
        db_record_payment(khatoo_id, amount)
        self.khatoo_msg.config(text="Payment recorded.", fg="green")
        self.pay_amt.set("")
        self._load_khatoo()


# ── Run ──────────────────────────────────────────────────
root = tk.Tk()
app  = SalesmanApp(root)
root.mainloop()
