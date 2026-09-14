"""
GadgetGuru - Full E-commerce Website
=====================================
A complete Flask-based e-commerce site with customer shopping, cart,
checkout, UPI/QR payments, receipts, and a full admin panel.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

import os
import sqlite3
import io
import base64
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, send_from_directory, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# QR code generation for UPI payments
import qrcode

# ------------------------------------------------------------------
# CONFIGURATION  ----  EDIT THIS SECTION FOR YOUR OWN BUSINESS
# ------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gadgetguru-secret-key-change-this-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

DATABASE = 'gadgetguru.db'

# ---- ADMIN LOGIN (hardcoded as requested) ----
ADMIN_EMAIL = "ayaan@gadgetguru.com"
ADMIN_PASSWORD = "password2007"

# ---- PAYMENT SETTINGS -------------------------------------------------
# >>> PUT YOUR OWN UPI ID AND DETAILS HERE <
UPI_ID = "shaikh.imroz2@ibl"          # <-- CHANGE THIS to your real UPI ID
PAYEE_NAME = "GadgetGuru"                  # <-- CHANGE THIS to your business/registered name
USE_CUSTOM_QR_IMAGE = False
CUSTOM_QR_IMAGE_PATH = "QRIM.png"

# WhatsApp floating chat button number (with country code, no + or spaces)
WHATSAPP_NUMBER = "919558533117"           # <-- CHANGE THIS
WHATSAPP_DEFAULT_MSG = "Hi GadgetGuru! I have a question about a product."
# ---- BUSINESS / CONTACT INFO (shown on the About page) ---------------
# >>> EDIT THESE WITH YOUR REAL DETAILS <
BUSINESS_ADDRESS = "FoneBook, Near TownHall, Kapadvanj, Gujarat, India"
CONTACT_EMAIL = "ayanshai414@gmail.com"
CONTACT_PHONE_DISPLAY = "+91 9558533117"
BUSINESS_HOURS = "Mon - San, 10:00 AM - 8:00 PM"


# ------------------------------------------------------------------
# DATABASE HELPERS
# ------------------------------------------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    first_run = not os.path.exists(DATABASE)
    db = sqlite3.connect(DATABASE)
    cur = db.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT,
        stock INTEGER DEFAULT 0,
        image_filename TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_no TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        payment_method TEXT NOT NULL,
        payment_status TEXT DEFAULT 'Pending',
        order_status TEXT DEFAULT 'Processing',
        shipping_name TEXT,
        shipping_phone TEXT,
        shipping_address TEXT,
        order_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id)
    );
    """)
    db.commit()

    if first_run:
        demo_products = [
            ("Nova X1 Wireless Earbuds",
             "Crisp active-noise-cancelling earbuds with 30-hour battery life, "
             "touch controls and deep bass tuning. Perfect for daily commutes.",
             2499.0, "Audio", 25),
            ("PulseFit Smartwatch",
             "AMOLED smartwatch with heart-rate & SpO2 tracking, 7-day battery, "
             "100+ sport modes, and full call/notification support.",
             3799.0, "Wearables", 18),
            ("ThunderBolt 65W GaN Charger",
             "Compact 65W GaN fast charger with 3 ports, charges laptop, phone "
             "and tablet simultaneously. Travel-friendly and heat-efficient.",
             1299.0, "Accessories", 40),
            ("AeroCam 4K Action Camera",
             "Waterproof 4K60 action camera with gimbal-grade stabilization, "
             "voice control and a rugged mounting kit included.",
             6499.0, "Cameras", 12),
            ("EchoBeam Bluetooth Speaker",
             "360-degree party speaker with RGB light show, 20W output and "
             "IPX6 splash resistance for indoor or outdoor use.",
             1999.0, "Audio", 30),
            ("GigaPower 20000mAh Power Bank",
             "Slim 20000mAh power bank with 22.5W fast charge, dual USB-A and "
             "USB-C output, digital charge display.",
             1599.0, "Accessories", 50),
        ]
        for p in demo_products:
            cur.execute(
                "INSERT INTO products (name, description, price, category, stock, "
                "image_filename, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*p, None, datetime.now().isoformat())
            )
        db.commit()
    db.close()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------------
# AUTH DECORATORS
# ------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Please log in as admin to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------
# CONTEXT PROCESSOR (available in every template)
# ------------------------------------------------------------------
@app.context_processor
def inject_globals():
    cart = session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    return dict(
        cart_count=cart_count,
        is_logged_in='user_id' in session,
        current_user_name=session.get('user_name'),
        is_admin=session.get('is_admin', False),
        whatsapp_number=WHATSAPP_NUMBER,
        whatsapp_msg=WHATSAPP_DEFAULT_MSG,
    )


# ------------------------------------------------------------------
# PUBLIC STORE ROUTES
# ------------------------------------------------------------------
@app.route('/')
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
    categories = sorted(set(p['category'] for p in products if p['category']))
    return render_template('index.html', products=products, categories=categories)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('index'))
    related = db.execute(
        "SELECT * FROM products WHERE category = ? AND id != ? LIMIT 4",
        (product['category'], product_id)
    ).fetchall()
    return render_template('product_detail.html', product=product, related=related)


@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    db = get_db()
    if query:
        products = db.execute(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY created_at DESC",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        products = []
    return render_template('index.html', products=products, categories=[], search_query=query)

@app.route('/about')
def about():
    return render_template(
        'about.html',
        business_address=BUSINESS_ADDRESS,
        contact_email=CONTACT_EMAIL,
        contact_phone_display=CONTACT_PHONE_DISPLAY,
        business_hours=BUSINESS_HOURS,
    )


# ------------------------------------------------------------------
# CART (session based)
# ------------------------------------------------------------------
@app.route('/cart')
def cart():
    db = get_db()
    cart_session = session.get('cart', {})
    items = []
    total = 0
    for pid, entry in cart_session.items():
        product = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if product:
            subtotal = product['price'] * entry['quantity']
            total += subtotal
            items.append({'product': product, 'quantity': entry['quantity'], 'subtotal': subtotal})
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('index'))

    cart_session = session.get('cart', {})
    key = str(product_id)
    qty = int(request.form.get('quantity', 1))
    if key in cart_session:
        cart_session[key]['quantity'] += qty
    else:
        cart_session[key] = {'quantity': qty}
    session['cart'] = cart_session
    session.modified = True
    flash(f"Added \"{product['name']}\" to your cart.", "success")
    return redirect(request.referrer or url_for('index'))


@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart_session = session.get('cart', {})
    key = str(product_id)
    qty = int(request.form.get('quantity', 1))
    if key in cart_session:
        if qty <= 0:
            del cart_session[key]
        else:
            cart_session[key]['quantity'] = qty
    session['cart'] = cart_session
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:product_id>')
def remove_from_cart(product_id):
    cart_session = session.get('cart', {})
    cart_session.pop(str(product_id), None)
    session['cart'] = cart_session
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for('cart'))


# ------------------------------------------------------------------
# CUSTOMER AUTH
# ------------------------------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('signup'))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email already exists.", "error")
            return redirect(url_for('signup'))

        db.execute(
            "INSERT INTO users (name, email, password, phone, address, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, generate_password_hash(password), phone, address, datetime.now().isoformat())
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        flash(f"Welcome to GadgetGuru, {name}!", "success")
        return redirect(url_for('index'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # If the credentials match the admin account, log in as admin and
        # send them straight to the admin panel. Everyone else logs in as
        # a normal customer. There is no separate admin login page anymore.
        if email == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_email'] = email
            flash("Welcome back, Admin.", "success")
            return redirect(url_for('admin_dashboard'))

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        flash("Invalid email or password.", "error")
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('is_admin', None)
    session.pop('admin_email', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('is_admin', None)
    session.pop('admin_email', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))
# ------------------------------------------------------------------
# CHECKOUT / PAYMENT / RECEIPT
# ------------------------------------------------------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    db = get_db()
    cart_session = session.get('cart', {})
    if not cart_session:
        flash("Your cart is empty.", "error")
        return redirect(url_for('index'))

    items = []
    total = 0
    for pid, entry in cart_session.items():
        product = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if product:
            subtotal = product['price'] * entry['quantity']
            total += subtotal
            items.append({'product': product, 'quantity': entry['quantity'], 'subtotal': subtotal})

    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    if request.method == 'POST':
        name = request.form.get('shipping_name', user['name'])
        phone = request.form.get('shipping_phone', user['phone'])
        address = request.form.get('shipping_address', user['address'])

        # NOTE: Cash on Delivery is temporarily disabled. Only UPI is accepted
        # for now, regardless of what's submitted. To re-enable COD, remove
        # this override and re-enable the radio button in checkout.html.
        payment_method = 'UPI'

        receipt_no = "GG" + datetime.now().strftime("%Y%m%d%H%M%S")
        db.execute(
            "INSERT INTO orders (receipt_no, user_id, total_amount, payment_method, "
            "payment_status, order_status, shipping_name, shipping_phone, shipping_address, order_date) "
            "VALUES (?, ?, ?, ?, 'Pending', 'Processing', ?, ?, ?, ?)",
            (receipt_no, user['id'], total, payment_method, name, phone, address, datetime.now().isoformat())
        )
        order_id = db.execute("SELECT id FROM orders WHERE receipt_no = ?", (receipt_no,)).fetchone()['id']

        for item in items:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, product_name, price, quantity) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_id, item['product']['id'], item['product']['name'], item['product']['price'], item['quantity'])
            )
        db.commit()

        session['cart'] = {}
        session.modified = True
        session['last_order_id'] = order_id
        return redirect(url_for('payment', order_id=order_id))

    return render_template('checkout.html', items=items, total=total, user=user)


@app.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?",
                        (order_id, session['user_id'])).fetchone()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))
    return render_template('payment.html', order=order, upi_id=UPI_ID, payee_name=PAYEE_NAME,
                            use_custom_qr=USE_CUSTOM_QR_IMAGE, custom_qr_path=CUSTOM_QR_IMAGE_PATH)


@app.route('/payment/<int:order_id>/qr.png')
def payment_qr(order_id):
    """Dynamically generate a scannable UPI QR code for this order's amount."""
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    amount = order['total_amount'] if order else 0
    upi_link = (
        f"upi://pay?pa={UPI_ID}&pn={PAYEE_NAME.replace(' ', '%20')}"
        f"&am={amount:.2f}&cu=INR&tn=GadgetGuruOrder{order_id}"
    )
    qr_img = qrcode.make(upi_link, box_size=8, border=2)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return app.response_class(buf.read(), mimetype='image/png')


@app.route('/payment/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_payment(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?",
                        (order_id, session['user_id'])).fetchone()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))
    # Customer confirms they've paid; admin will verify & mark as Paid in the admin panel.
    db.execute("UPDATE orders SET payment_status = 'Awaiting Verification' WHERE id = ?", (order_id,))
    db.commit()
    flash("Thanks! We'll verify your payment shortly.", "success")
    return redirect(url_for('receipt', order_id=order_id))


@app.route('/receipt/<int:order_id>')
@login_required
def receipt(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?",
                        (order_id, session['user_id'])).fetchone()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))

    # The receipt only unlocks once the customer has scanned the QR, paid,
    # and confirmed it on the payment page (payment_status moves away from
    # "Pending" at that point). Anyone trying to jump straight to the
    # receipt URL without paying gets sent back to the payment page instead.
    if order['payment_status'] == 'Pending':
        flash("Please complete your payment first.", "error")
        return redirect(url_for('payment', order_id=order_id))

    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return render_template('receipt.html', order=order, items=items)


@app.route('/my-orders')
@login_required
def my_orders():
    db = get_db()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC", (session['user_id'],)
    ).fetchall()
    return render_template('my_orders.html', orders=orders)


# ------------------------------------------------------------------
# ADMIN DASHBOARD
# ------------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    total_products = db.execute("SELECT COUNT(*) c FROM products").fetchone()['c']
    total_orders = db.execute("SELECT COUNT(*) c FROM orders").fetchone()['c']
    total_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()['c']
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(total_amount), 0) s FROM orders WHERE payment_status != 'Pending'"
    ).fetchone()['s']
    recent_orders = db.execute(
        "SELECT o.*, u.name AS customer_name, u.email AS customer_email "
        "FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC LIMIT 6"
    ).fetchall()
    low_stock = db.execute("SELECT * FROM products WHERE stock <= 5 ORDER BY stock ASC").fetchall()
    return render_template('admin_dashboard.html', total_products=total_products,
                            total_orders=total_orders, total_users=total_users,
                            total_revenue=total_revenue, recent_orders=recent_orders,
                            low_stock=low_stock)


@app.route('/admin/products')
@admin_required
def admin_products():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        category = request.form.get('category', '').strip()
        stock = request.form.get('stock', '0')

        if not name or not price:
            flash("Product name and price are required.", "error")
            return redirect(url_for('admin_add_product'))

        image_filename = None
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        db = get_db()
        db.execute(
            "INSERT INTO products (name, description, price, category, stock, image_filename, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, description, float(price), category, int(stock or 0), image_filename, datetime.now().isoformat())
        )
        db.commit()
        flash(f"Product \"{name}\" added successfully.", "success")
        return redirect(url_for('admin_products'))

    return render_template('admin_add_product.html')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        category = request.form.get('category', '').strip()
        stock = request.form.get('stock', '0')

        image_filename = product['image_filename']
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        db.execute(
            "UPDATE products SET name=?, description=?, price=?, category=?, stock=?, image_filename=? WHERE id=?",
            (name, description, float(price), category, int(stock or 0), image_filename, product_id)
        )
        db.commit()
        flash(f"Product \"{name}\" updated.", "success")
        return redirect(url_for('admin_products'))

    return render_template('admin_edit_product.html', product=product)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    flash("Product deleted.", "success")
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    db = get_db()
    orders = db.execute(
        "SELECT o.*, u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone "
        "FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC"
    ).fetchall()
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    db = get_db()
    order = db.execute(
        "SELECT o.*, u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone, "
        "u.address AS customer_address FROM orders o JOIN users u ON o.user_id = u.id WHERE o.id = ?",
        (order_id,)
    ).fetchone()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('admin_orders'))
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return render_template('admin_order_detail.html', order=order, items=items)


@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    payment_status = request.form.get('payment_status')
    order_status = request.form.get('order_status')
    db = get_db()
    db.execute(
        "UPDATE orders SET payment_status = ?, order_status = ? WHERE id = ?",
        (payment_status, order_status, order_id)
    )
    db.commit()
    flash("Order updated.", "success")
    return redirect(url_for('admin_order_detail', order_id=order_id))


@app.route('/admin/customers')
@admin_required
def admin_customers():
    db = get_db()
    customers = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    customers_with_stats = []
    for c in customers:
        stats = db.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(total_amount),0) s FROM orders WHERE user_id = ?",
            (c['id'],)
        ).fetchone()
        customers_with_stats.append({'user': c, 'order_count': stats['c'], 'total_spent': stats['s']})
    return render_template('admin_customers.html', customers=customers_with_stats)


@app.route('/admin/settings')
@admin_required
def admin_settings():
    return render_template('admin_settings.html', upi_id=UPI_ID, payee_name=PAYEE_NAME,
                            whatsapp_number=WHATSAPP_NUMBER)

# ------------------------------------------------------------------
# STATIC FILE HELPERS
# ------------------------------------------------------------------
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Initialize the database on import — this runs whether the app is started
# with "python app.py" locally, or with Gunicorn in production (Render,
# etc.), since Gunicorn imports this file as a module rather than running
# the __main__ block below.
init_db()


# ------------------------------------------------------------------
# MAIN (used only for local development with "python app.py")
# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)