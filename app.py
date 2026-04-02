from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pymysql
from functools import wraps
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'arasan_ev_crm_secret_2026'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Welcome@123',
    'db': 'arasan',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') not in ['admin', 'manager']:
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM vehicles")
    total_vehicles = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM customers")
    total_customers = cur.fetchone()['cnt']
    cur.execute("SELECT COALESCE(SUM(total_price),0) as total FROM sales_order WHERE status='completed'")
    total_sales = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as cnt FROM bookings WHERE status='pending'")
    pending_bookings = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM invoices WHERE status='overdue'")
    overdue_invoices = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM purchase_order WHERE status='ordered'")
    pending_purchases = cur.fetchone()['cnt']
    cur.execute("""
        SELECT so.order_no, c.name as customer, v.make, v.model, so.total_price, so.status, so.sold_at
        FROM sales_order so
        LEFT JOIN customers c ON c.id=so.customer_id
        LEFT JOIN vehicles v ON v.id=so.vehicle_id
        ORDER BY so.sold_at DESC LIMIT 5
    """)
    recent_orders = cur.fetchall()
    cur.execute("""
        SELECT v.make, v.model, v.category, v.stock, v.price, v.status, v.range_km
        FROM vehicles v WHERE v.stock <= 3
        ORDER BY v.stock ASC LIMIT 5
    """)
    low_stock = cur.fetchall()
    cur.execute("""
        SELECT MIN(DATE_FORMAT(sold_at,'%b')) as month, SUM(total_price) as revenue
        FROM sales_order WHERE status='completed' AND sold_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(sold_at,'%Y-%m') ORDER BY DATE_FORMAT(sold_at,'%Y-%m') ASC
    """)
    chart_data = cur.fetchall()
    cur.execute("""
        SELECT category, COUNT(*) as cnt FROM vehicles GROUP BY category
    """)
    category_data = cur.fetchall()
    db.close()
    return render_template('dashboard.html',
        total_vehicles=total_vehicles, total_customers=total_customers,
        total_sales=total_sales, pending_bookings=pending_bookings,
        overdue_invoices=overdue_invoices, pending_purchases=pending_purchases,
        recent_orders=recent_orders, low_stock=low_stock,
        chart_data=chart_data, category_data=category_data)

# ─────────────────────────────────────────────
# VEHICLES
# ─────────────────────────────────────────────
@app.route('/vehicles')
@login_required
def vehicles():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '')
    cat = request.args.get('category', '')
    status = request.args.get('status', '')
    sql = "SELECT * FROM vehicles WHERE 1=1"
    params = []
    if q:
        sql += " AND (make LIKE %s OR model LIKE %s)"
        params += [f'%{q}%', f'%{q}%']
    if cat:
        sql += " AND category=%s"
        params.append(cat)
    if status:
        sql += " AND status=%s"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    cur.execute(sql, params)
    vehicles_list = cur.fetchall()
    db.close()
    return render_template('vehicles.html', vehicles=vehicles_list, q=q, cat=cat, status=status)

@app.route('/vehicles/add', methods=['GET', 'POST'])
@admin_required
def add_vehicle():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO vehicles (make, model, year, category, range_km, price, stock, status, image_url, color, battery_capacity_kwh, charging_time_hrs, top_speed_kmh, warranty_years)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['make'], request.form['model'], request.form['year'],
            request.form['category'], request.form['range_km'], request.form['price'],
            request.form['stock'], request.form['status'], request.form.get('image_url',''),
            request.form.get('color',''), request.form.get('battery_capacity_kwh', 0),
            request.form.get('charging_time_hrs', 0), request.form.get('top_speed_kmh', 0),
            request.form.get('warranty_years', 3)
        ))
        db.close()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('vehicles'))
    return render_template('vehicle_form.html', vehicle=None, action='Add')

@app.route('/vehicles/edit/<int:vid>', methods=['GET', 'POST'])
@admin_required
def edit_vehicle(vid):
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE vehicles SET make=%s, model=%s, year=%s, category=%s, range_km=%s,
            price=%s, stock=%s, status=%s, image_url=%s, color=%s,
            battery_capacity_kwh=%s, charging_time_hrs=%s, top_speed_kmh=%s, warranty_years=%s
            WHERE id=%s
        """, (
            request.form['make'], request.form['model'], request.form['year'],
            request.form['category'], request.form['range_km'], request.form['price'],
            request.form['stock'], request.form['status'], request.form.get('image_url',''),
            request.form.get('color',''), request.form.get('battery_capacity_kwh', 0),
            request.form.get('charging_time_hrs', 0), request.form.get('top_speed_kmh', 0),
            request.form.get('warranty_years', 3), vid
        ))
        db.close()
        flash('Vehicle updated!', 'success')
        return redirect(url_for('vehicles'))
    cur.execute("SELECT * FROM vehicles WHERE id=%s", (vid,))
    vehicle = cur.fetchone()
    db.close()
    return render_template('vehicle_form.html', vehicle=vehicle, action='Edit')

@app.route('/vehicles/delete/<int:vid>', methods=['POST'])
@admin_required
def delete_vehicle(vid):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM vehicles WHERE id=%s", (vid,))
    db.close()
    flash('Vehicle deleted.', 'info')
    return redirect(url_for('vehicles'))

# ─────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────
@app.route('/customers')
@login_required
def customers():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '')
    sql = """SELECT c.*, u.username, u.role,
             (SELECT COUNT(*) FROM sales_order so WHERE so.customer_id=c.id) as total_orders
             FROM customers c LEFT JOIN users u ON u.id=c.user_id WHERE 1=1"""
    params = []
    if q:
        sql += " AND (c.name LIKE %s OR c.email LIKE %s OR c.phone LIKE %s)"
        params += [f'%{q}%', f'%{q}%', f'%{q}%']
    sql += " ORDER BY c.created_at DESC"
    cur.execute(sql, params)
    customers_list = cur.fetchall()
    db.close()
    return render_template('customers.html', customers=customers_list, q=q)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        # Create user account if username provided
        user_id = None
        if request.form.get('username'):
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,'customer')",
                        (request.form['username'], request.form.get('password','password123')))
            user_id = cur.lastrowid
        cur.execute("""
            INSERT INTO customers (user_id, name, email, phone, address, city, state, pincode, dob, gender, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, request.form['name'], request.form['email'], request.form['phone'],
              request.form.get('address',''), request.form.get('city',''), request.form.get('state',''),
              request.form.get('pincode',''), request.form.get('dob') or None,
              request.form.get('gender',''), request.form.get('notes','')))
        db.close()
        flash('Customer added!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', customer=None, action='Add')

@app.route('/customers/edit/<int:cid>', methods=['GET', 'POST'])
@login_required
def edit_customer(cid):
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE customers SET name=%s, email=%s, phone=%s, address=%s,
            city=%s, state=%s, pincode=%s, dob=%s, gender=%s, notes=%s WHERE id=%s
        """, (request.form['name'], request.form['email'], request.form['phone'],
              request.form.get('address',''), request.form.get('city',''), request.form.get('state',''),
              request.form.get('pincode',''), request.form.get('dob') or None,
              request.form.get('gender',''), request.form.get('notes',''), cid))
        db.close()
        flash('Customer updated!', 'success')
        return redirect(url_for('customers'))
    cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
    customer = cur.fetchone()
    db.close()
    return render_template('customer_form.html', customer=customer, action='Edit')

@app.route('/customers/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_customer(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
    db.close()
    flash('Customer deleted.', 'info')
    return redirect(url_for('customers'))

@app.route('/customers/<int:cid>')
@login_required
def customer_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
    customer = cur.fetchone()
    cur.execute("""
        SELECT so.*, v.make, v.model FROM sales_order so
        LEFT JOIN vehicles v ON v.id=so.vehicle_id
        WHERE so.customer_id=%s ORDER BY so.sold_at DESC
    """, (cid,))
    orders = cur.fetchall()
    cur.execute("""
        SELECT b.*, v.make, v.model FROM bookings b
        LEFT JOIN vehicles v ON v.id=b.vehicle_id
        WHERE b.user_id=(SELECT user_id FROM customers WHERE id=%s)
        ORDER BY b.requested_at DESC
    """, (cid,))
    bookings = cur.fetchall()
    db.close()
    return render_template('customer_detail.html', customer=customer, orders=orders, bookings=bookings)

# ─────────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────────
@app.route('/bookings')
@login_required
def bookings():
    db = get_db()
    cur = db.cursor()
    status = request.args.get('status', '')
    sql = """SELECT b.*, u.username, v.make, v.model, v.category
             FROM bookings b LEFT JOIN users u ON u.id=b.user_id
             LEFT JOIN vehicles v ON v.id=b.vehicle_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND b.status=%s"
        params.append(status)
    sql += " ORDER BY b.requested_at DESC"
    cur.execute(sql, params)
    bookings_list = cur.fetchall()
    db.close()
    return render_template('bookings.html', bookings=bookings_list, status=status)

@app.route('/bookings/add', methods=['GET', 'POST'])
@login_required
def add_booking():
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        cur.execute("""
            INSERT INTO bookings (user_id, vehicle_id, scheduled_for, status, note, test_drive_location, preferred_contact)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (request.form['user_id'], request.form['vehicle_id'],
              request.form.get('scheduled_for') or None, request.form.get('status','pending'),
              request.form.get('note',''), request.form.get('test_drive_location',''),
              request.form.get('preferred_contact','')))
        db.close()
        flash('Booking created!', 'success')
        return redirect(url_for('bookings'))
    cur.execute("SELECT id, username FROM users ORDER BY username")
    users = cur.fetchall()
    cur.execute("SELECT id, make, model, year FROM vehicles WHERE status='available' ORDER BY make")
    vehicles_list = cur.fetchall()
    db.close()
    return render_template('booking_form.html', users=users, vehicles=vehicles_list, booking=None)

@app.route('/bookings/update/<int:bid>', methods=['POST'])
@login_required
def update_booking(bid):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (request.form['status'], bid))
    db.close()
    flash('Booking status updated!', 'success')
    return redirect(url_for('bookings'))

# ─────────────────────────────────────────────
# SALES ORDERS
# ─────────────────────────────────────────────
@app.route('/sales-orders')
@login_required
def sales_orders():
    db = get_db()
    cur = db.cursor()
    status = request.args.get('status', '')
    sql = """SELECT so.*, c.name as customer_name, v.make, v.model
             FROM sales_order so LEFT JOIN customers c ON c.id=so.customer_id
             LEFT JOIN vehicles v ON v.id=so.vehicle_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND so.status=%s"
        params.append(status)
    sql += " ORDER BY so.sold_at DESC"
    cur.execute(sql, params)
    orders = cur.fetchall()
    db.close()
    return render_template('sales_orders.html', orders=orders, status=status)

@app.route('/sales-orders/add', methods=['GET', 'POST'])
@login_required
def add_sales_order():
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        qty = int(request.form['qty'])
        unit_price = float(request.form['unit_price'])
        discount = float(request.form.get('discount', 0))
        total_price = (unit_price * qty) - discount
        import random, string
        order_no = 'ORD-' + ''.join(random.choices(string.digits, k=6))
        cur.execute("""
            INSERT INTO sales_order (order_no, customer_id, vehicle_id, qty, unit_price, total_price, status, discount, payment_method, sales_person, emi_months)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (order_no, request.form['customer_id'], request.form['vehicle_id'],
              qty, unit_price, total_price, request.form.get('status','pending'),
              discount, request.form.get('payment_method','cash'),
              request.form.get('sales_person',''), request.form.get('emi_months',0)))
        order_id = cur.lastrowid
        # Auto-create invoice
        invoice_no = 'INV-' + order_no[4:]
        tax = total_price * 0.18
        cur.execute("""
            INSERT INTO invoices (invoice_no, order_id, customer_id, sub_total, tax, total, status)
            VALUES (%s,%s,%s,%s,%s,%s,'draft')
        """, (invoice_no, order_id, request.form['customer_id'],
              total_price, round(tax,2), round(total_price + tax, 2)))
        # Reduce stock
        cur.execute("UPDATE vehicles SET stock=stock-%s WHERE id=%s", (qty, request.form['vehicle_id']))
        db.close()
        flash(f'Sales order {order_no} created with invoice {invoice_no}!', 'success')
        return redirect(url_for('sales_orders'))
    cur.execute("SELECT id, name FROM customers ORDER BY name")
    customers_list = cur.fetchall()
    cur.execute("SELECT id, make, model, year, price, stock FROM vehicles WHERE stock>0 ORDER BY make")
    vehicles_list = cur.fetchall()
    cur.execute("SELECT id, username FROM users ORDER BY username")
    users = cur.fetchall()
    db.close()
    return render_template('sales_order_form.html', customers=customers_list, vehicles=vehicles_list, users=users)

# ─────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────
@app.route('/invoices')
@login_required
def invoices():
    db = get_db()
    cur = db.cursor()
    status = request.args.get('status', '')
    sql = """SELECT i.*, c.name as customer_name, so.order_no
             FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id
             LEFT JOIN sales_order so ON so.id=i.order_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND i.status=%s"
        params.append(status)
    sql += " ORDER BY i.issued_at DESC"
    cur.execute(sql, params)
    invoices_list = cur.fetchall()
    db.close()
    return render_template('invoices.html', invoices=invoices_list, status=status)

@app.route('/invoices/update/<int:iid>', methods=['POST'])
@login_required
def update_invoice(iid):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE invoices SET status=%s WHERE id=%s", (request.form['status'], iid))
    db.close()
    flash('Invoice updated!', 'success')
    return redirect(url_for('invoices'))

@app.route('/invoices/view/<int:iid>')
@login_required
def view_invoice(iid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT i.*, c.name as customer_name, c.email, c.phone, c.address,
               so.order_no, v.make, v.model, v.year, so.qty, so.payment_method
        FROM invoices i
        LEFT JOIN customers c ON c.id=i.customer_id
        LEFT JOIN sales_order so ON so.id=i.order_id
        LEFT JOIN vehicles v ON v.id=so.vehicle_id
        WHERE i.id=%s
    """, (iid,))
    invoice = cur.fetchone()
    due_date = None
    if invoice and invoice.get('issued_at'):
        due_date = invoice['issued_at'] + timedelta(days=30)
    db.close()
    return render_template('invoice_view.html', invoice=invoice, due_date=due_date)

# ─────────────────────────────────────────────
# SUPPLIERS
# ─────────────────────────────────────────────
@app.route('/suppliers')
@login_required
def suppliers():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '')
    sql = """SELECT s.*,
             (SELECT COUNT(*) FROM purchase_order po WHERE po.supplier_id=s.id) as total_orders
             FROM suppliers s WHERE 1=1"""
    params = []
    if q:
        sql += " AND (s.name LIKE %s OR s.email LIKE %s)"
        params += [f'%{q}%', f'%{q}%']
    sql += " ORDER BY s.created_at DESC"
    cur.execute(sql, params)
    suppliers_list = cur.fetchall()
    db.close()
    return render_template('suppliers.html', suppliers=suppliers_list, q=q)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@admin_required
def add_supplier():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO suppliers (name, contact_name, email, phone, address, city, state, gstin, payment_terms, rating)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (request.form['name'], request.form.get('contact_name',''),
              request.form['email'], request.form['phone'],
              request.form.get('address',''), request.form.get('city',''),
              request.form.get('state',''), request.form.get('gstin',''),
              request.form.get('payment_terms','30 days'), request.form.get('rating',5)))
        db.close()
        flash('Supplier added!', 'success')
        return redirect(url_for('suppliers'))
    return render_template('supplier_form.html', supplier=None, action='Add')

@app.route('/suppliers/edit/<int:sid>', methods=['GET', 'POST'])
@admin_required
def edit_supplier(sid):
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE suppliers SET name=%s, contact_name=%s, email=%s, phone=%s, address=%s,
            city=%s, state=%s, gstin=%s, payment_terms=%s, rating=%s WHERE id=%s
        """, (request.form['name'], request.form.get('contact_name',''),
              request.form['email'], request.form['phone'],
              request.form.get('address',''), request.form.get('city',''),
              request.form.get('state',''), request.form.get('gstin',''),
              request.form.get('payment_terms','30 days'), request.form.get('rating',5), sid))
        db.close()
        flash('Supplier updated!', 'success')
        return redirect(url_for('suppliers'))
    cur.execute("SELECT * FROM suppliers WHERE id=%s", (sid,))
    supplier = cur.fetchone()
    db.close()
    return render_template('supplier_form.html', supplier=supplier, action='Edit')

@app.route('/suppliers/delete/<int:sid>', methods=['POST'])
@admin_required
def delete_supplier(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM suppliers WHERE id=%s", (sid,))
    db.close()
    flash('Supplier deleted.', 'info')
    return redirect(url_for('suppliers'))

# ─────────────────────────────────────────────
# PURCHASE ORDERS
# ─────────────────────────────────────────────
@app.route('/purchase-orders')
@login_required
def purchase_orders():
    db = get_db()
    cur = db.cursor()
    status = request.args.get('status', '')
    sql = """SELECT po.*, s.name as supplier_name, v.make, v.model
             FROM purchase_order po LEFT JOIN suppliers s ON s.id=po.supplier_id
             LEFT JOIN vehicles v ON v.id=po.vehicle_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND po.status=%s"
        params.append(status)
    sql += " ORDER BY po.ordered_at DESC"
    cur.execute(sql, params)
    orders = cur.fetchall()
    db.close()
    return render_template('purchase_orders.html', orders=orders, status=status)

@app.route('/purchase-orders/add', methods=['GET', 'POST'])
@admin_required
def add_purchase_order():
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        import random, string
        po_no = 'PO-' + ''.join(random.choices(string.digits, k=6))
        qty = int(request.form['qty'])
        unit_cost = float(request.form['unit_cost'])
        total_cost = qty * unit_cost
        cur.execute("""
            INSERT INTO purchase_order (purchase_no, supplier_id, vehicle_id, qty, unit_cost, total_cost, status, expected_delivery, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (po_no, request.form['supplier_id'], request.form['vehicle_id'],
              qty, unit_cost, total_cost, request.form.get('status','ordered'),
              request.form.get('expected_delivery') or None, request.form.get('notes','')))
        po_id = cur.lastrowid
        # Auto-create bill
        bill_no = 'BILL-' + po_no[3:]
        cur.execute("""
            INSERT INTO bills (bill_no, supplier_id, purchase_id, amount, status)
            VALUES (%s,%s,%s,%s,'unpaid')
        """, (bill_no, request.form['supplier_id'], po_id, total_cost))
        db.close()
        flash(f'Purchase order {po_no} created with bill {bill_no}!', 'success')
        return redirect(url_for('purchase_orders'))
    cur.execute("SELECT id, name FROM suppliers ORDER BY name")
    suppliers_list = cur.fetchall()
    cur.execute("SELECT id, make, model, year FROM vehicles ORDER BY make")
    vehicles_list = cur.fetchall()
    db.close()
    return render_template('purchase_order_form.html', suppliers=suppliers_list, vehicles=vehicles_list)

@app.route('/purchase-orders/receive/<int:pid>', methods=['POST'])
@admin_required
def receive_purchase_order(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM purchase_order WHERE id=%s", (pid,))
    po = cur.fetchone()
    cur.execute("UPDATE purchase_order SET status='received', received_at=NOW() WHERE id=%s", (pid,))
    cur.execute("UPDATE vehicles SET stock=stock+%s WHERE id=%s", (po['qty'], po['vehicle_id']))
    db.close()
    flash('Purchase order marked as received, stock updated!', 'success')
    return redirect(url_for('purchase_orders'))

# ─────────────────────────────────────────────
# BILLS
# ─────────────────────────────────────────────
@app.route('/bills')
@login_required
def bills():
    db = get_db()
    cur = db.cursor()
    status = request.args.get('status', '')
    sql = """SELECT b.*, s.name as supplier_name, po.purchase_no
             FROM bills b LEFT JOIN suppliers s ON s.id=b.supplier_id
             LEFT JOIN purchase_order po ON po.id=b.purchase_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND b.status=%s"
        params.append(status)
    sql += " ORDER BY b.issued_at DESC"
    cur.execute(sql, params)
    bills_list = cur.fetchall()
    db.close()
    return render_template('bills.html', bills=bills_list, status=status)

@app.route('/bills/pay/<int:bid>', methods=['POST'])
@admin_required
def pay_bill(bid):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE bills SET status='paid' WHERE id=%s", (bid,))
    db.close()
    flash('Bill marked as paid!', 'success')
    return redirect(url_for('bills'))

# ─────────────────────────────────────────────
# INVENTORY
# ─────────────────────────────────────────────
@app.route('/inventory')
@login_required
def inventory():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT i.*, v.id as vid, v.make, v.model, v.year, v.category, v.stock as vehicle_stock, v.price
        FROM inventory i RIGHT JOIN vehicles v ON v.id=i.vehicle_id
        ORDER BY v.make
    """)
    inventory_list = cur.fetchall()
    db.close()
    return render_template('inventory.html', inventory=inventory_list)

@app.route('/inventory/update/<int:vid>', methods=['POST'])
@admin_required
def update_inventory(vid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM inventory WHERE vehicle_id=%s", (vid,))
    existing = cur.fetchone()
    if existing:
        cur.execute("""UPDATE inventory SET warehouse_location=%s, stock=%s, min_stock=%s WHERE vehicle_id=%s""",
                    (request.form.get('warehouse_location',''), request.form['stock'],
                     request.form.get('min_stock',1), vid))
    else:
        cur.execute("""INSERT INTO inventory (vehicle_id, warehouse_location, stock, min_stock) VALUES (%s,%s,%s,%s)""",
                    (vid, request.form.get('warehouse_location',''), request.form['stock'], request.form.get('min_stock',1)))
    cur.execute("UPDATE vehicles SET stock=%s WHERE id=%s", (request.form['stock'], vid))
    db.close()
    flash('Inventory updated!', 'success')
    return redirect(url_for('inventory'))

# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports():
    db = get_db()
    cur = db.cursor()
    # Sales summary
    cur.execute("""
        SELECT DATE_FORMAT(sold_at,'%Y-%m') as month,
               COUNT(*) as orders, SUM(total_price) as revenue
        FROM sales_order WHERE status='completed'
        GROUP BY DATE_FORMAT(sold_at,'%Y-%m')
        ORDER BY month DESC LIMIT 12
    """)
    monthly_sales = cur.fetchall()
    # Top vehicles
    cur.execute("""
        SELECT v.make, v.model, COUNT(so.id) as sold_count, SUM(so.total_price) as total_revenue
        FROM sales_order so LEFT JOIN vehicles v ON v.id=so.vehicle_id
        WHERE so.status='completed'
        GROUP BY so.vehicle_id ORDER BY sold_count DESC LIMIT 5
    """)
    top_vehicles = cur.fetchall()
    # Top customers
    cur.execute("""
        SELECT c.name, c.email, COUNT(so.id) as orders, SUM(so.total_price) as spent
        FROM sales_order so LEFT JOIN customers c ON c.id=so.customer_id
        WHERE so.status='completed'
        GROUP BY so.customer_id ORDER BY spent DESC LIMIT 5
    """)
    top_customers = cur.fetchall()
    # Payment method breakdown
    cur.execute("""
        SELECT payment_method, COUNT(*) as cnt, SUM(total_price) as total
        FROM sales_order WHERE status='completed'
        GROUP BY payment_method
    """)
    payment_breakdown = cur.fetchall()
    # Category breakdown
    cur.execute("""
        SELECT v.category, COUNT(so.id) as sales
        FROM sales_order so LEFT JOIN vehicles v ON v.id=so.vehicle_id
        WHERE so.status='completed' GROUP BY v.category
    """)
    category_sales = cur.fetchall()
    # Log this report
    cur.execute("INSERT INTO reports (report_type, generated_by) VALUES ('full_report',%s)", (session['user_id'],))
    db.close()
    return render_template('reports.html',
        monthly_sales=monthly_sales, top_vehicles=top_vehicles,
        top_customers=top_customers, payment_breakdown=payment_breakdown,
        category_sales=category_sales)

# ─────────────────────────────────────────────
# USERS / SETTINGS
# ─────────────────────────────────────────────
@app.route('/users')
@admin_required
def users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users_list = cur.fetchall()
    db.close()
    return render_template('users.html', users=users_list)

@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)",
                    (request.form['username'], request.form['password'], request.form['role']))
        db.close()
        flash('User created!', 'success')
        return redirect(url_for('users'))
    return render_template('user_form.html', user=None, action='Add')

@app.route('/users/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    if uid == session['user_id']:
        flash("Can't delete yourself!", 'error')
        return redirect(url_for('users'))
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    db.close()
    flash('User deleted.', 'info')
    return redirect(url_for('users'))

# ─────────────────────────────────────────────
# API endpoints for AJAX
# ─────────────────────────────────────────────
@app.route('/api/vehicle-price/<int:vid>')
@login_required
def api_vehicle_price(vid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT price, stock, make, model FROM vehicles WHERE id=%s", (vid,))
    v = cur.fetchone()
    db.close()
    return jsonify(v or {})

if __name__ == '__main__':
    app.run(debug=True, port=5000)