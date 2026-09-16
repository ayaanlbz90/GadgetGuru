"""
GadgetGuru - Full E-commerce Website
=====================================
A complete Flask-based e-commerce site with customer shopping, cart,
checkout, UPI/QR payments, receipts, and a full admin panel.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

import os
import io
import base64
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

# QR code generation for UPI payments
import qrcode

# ------------------------------------------------------------------
# CONFIGURATION    ----  EDIT THIS SECTION FOR YOUR OWN BUSINESS
# ------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gadgetguru-secret-key-change-this-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ---- DATABASE CONFIGURATION (Supports SQLite & PostgreSQL) ----
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Fix Render's 'postgres://' prefix for SQLAlchemy compatibility
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gadgetguru.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---- ADMIN LOGIN (hardcoded as requested) ----
ADMIN_EMAIL = "ayaan@gadgetguru.com"
ADMIN_PASSWORD = "password2007"

# ---- PAYMENT SETTINGS -------------------------------------------------
UPI_ID = "shaikh.imroz2@ibl"          # <-- CHANGE THIS to your real UPI ID
PAYEE_NAME = "GadgetGuru"                 # <-- CHANGE THIS to your business/registered name
USE_CUSTOM_QR_IMAGE = False
CUSTOM_QR_IMAGE_PATH = "QRIM.png"

# WhatsApp floating chat button number (with country code, no + or spaces)
WHATSAPP_NUMBER = "919558533117"           # <-- CHANGE THIS
WHATSAPP_DEFAULT_MSG = "Hi GadgetGuru! I have a question about a product."
# ---- BUSINESS / CONTACT INFO (shown on the About page) ---------------
BUSINESS_ADDRESS = "FoneBook, Near TownHall, Kapadvanj, Gujarat, India"
CONTACT_EMAIL = "ayanshai414@gmail.com"
CONTACT_PHONE_DISPLAY = "+91 9558533117"
BUSINESS_HOURS = "Mon - San, 10:00 AM - 8:00 PM"


# ------------------------------------------------------------------
# DATABASE MODELS
# ------------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    phone = db.Column(db.String)
    address = db.Column(db.Text)
    created_at = db.Column(db.String, nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String)
    stock = db.Column(db.Integer, default=0)
    image_filename = db.Column(db.String)
    created_at = db.Column(db.String, nullable=False)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String, unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String, nullable=False)
    payment_status = db.Column(db.String, default='Pending')
    order_status = db.Column(db.String, default='Processing')
    shipping_name = db.Column(db.String)
    shipping_phone = db.Column(db.String)
    shipping_address = db.Column(db.Text)
    order_date = db.Column(db.String, nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


def init_db():
    with app.app_context():
        db.create_all()
        # Seed demo products if products table is empty
        if Product.query.count() == 0:
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
                prod = Product(
                    name=p[0],
                    description=p[1],
                    price=p[2],
                    category=p[3],
                    stock=p[4],
                    image_filename=None,
                    created_at=datetime.now().isoformat()
                )
                db.session.add(prod)
            db.session.commit()


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
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = sorted(set(p.category for p in products if p.category))
    return render_template('index.html', products=products, categories=categories)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('index'))
    related = Product.query.filter(Product.category == product.category, Product.id != product_id).limit(4).all()
    return render_template('product_detail.html', product=product, related=related)


@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if query:
        search_filter = f"%{query}%"
        products = Product.query.filter(
            (Product.name.ilike(search_filter)) | (Product.description.ilike(search_filter))
        ).order_by(Product.created_at.desc()).all()
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
    cart_session = session.get('cart', {})
    items = []
    total = 0
    for pid, entry in cart_session.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * entry['quantity']
            total += subtotal
            items.append({'product': product, 'quantity': entry['quantity'], 'subtotal': subtotal})
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get(product_id)
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
    flash(f"Added \"{product.name}\" to your cart.", "success")
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

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with this email already exists.", "error")
            return redirect(url_for('signup'))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            address=address,
            created_at=datetime.now().isoformat()
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['user_name'] = new_user.name
        flash(f"Welcome to GadgetGuru, {name}!", "success")
        return redirect(url_for('index'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if email == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_email'] = email
            flash("Welcome back, Admin.", "success")
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f"Welcome back, {user.name}!", "success")
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
    cart_session = session.get('cart', {})
    if not cart_session:
        flash("Your cart is empty.", "error")
        return redirect(url_for('index'))

    items = []
    total = 0
    for pid, entry in cart_session.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * entry['quantity']
            total += subtotal
            items.append({'product': product, 'quantity': entry['quantity'], 'subtotal': subtotal})

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        name = request.form.get('shipping_name', user.name)
        phone = request.form.get('shipping_phone', user.phone)
        address = request.form.get('shipping_address', user.address)
        payment_method = 'UPI'

        receipt_no = "GG" + datetime.now().strftime("%Y%m%d%H%M%S")
        new_order = Order(
            receipt_no=receipt_no,
            user_id=user.id,
            total_amount=total,
            payment_method=payment_method,
            payment_status='Pending',
            order_status='Processing',
            shipping_name=name,
            shipping_phone=phone,
            shipping_address=address,
            order_date=datetime.now().isoformat()
        )
        db.session.add(new_order)
        db.session.commit()

        for item in items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                product_name=item['product'].name,
                price=item['product'].price,
                quantity=item['quantity']
            )
            db.session.add(order_item)
        db.session.commit()

        session['cart'] = {}
        session.modified = True
        session['last_order_id'] = new_order.id
        return redirect(url_for('payment', order_id=new_order.id))

    return render_template('checkout.html', items=items, total=total, user=user)


@app.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))
    return render_template('payment.html', order=order, upi_id=UPI_ID, payee_name=PAYEE_NAME,
                           use_custom_qr=USE_CUSTOM_QR_IMAGE, custom_qr_path=CUSTOM_QR_IMAGE_PATH)


@app.route('/payment/<int:order_id>/qr.png')
def payment_qr(order_id):
    """Dynamically generate a scannable UPI QR code for this order's amount."""
    order = Order.query.get(order_id)
    amount = order.total_amount if order else 0
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
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))
    order.payment_status = 'Awaiting Verification'
    db.session.commit()
    flash("Thanks! We'll verify your payment shortly.", "success")
    return redirect(url_for('receipt', order_id=order_id))


@app.route('/receipt/<int:order_id>')
@login_required
def receipt(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first()
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))

    if order.payment_status == 'Pending':
        flash("Please complete your payment first.", "error")
        return redirect(url_for('payment', order_id=order_id))

    items = OrderItem.query.filter_by(order_id=order_id).all()
    return render_template('receipt.html', order=order, items=items)


@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.order_date.desc()).all()
    return render_template('my_orders.html', orders=orders)


# ------------------------------------------------------------------
# ADMIN DASHBOARD
# ------------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    
    revenue_result = db.session.query(db.func.coalesce(db.func.sum(Order.total_amount), 0)).filter(Order.payment_status != 'Pending').scalar()
    total_revenue = revenue_result if revenue_result else 0.0

    recent_orders = db.session.query(Order, User).join(User, Order.user_id == User.id).order_by(Order.order_date.desc()).limit(6).all()
    
    # Flatten recent orders structure for the template
    formatted_recent_orders = []
    for ord_obj, usr_obj in recent_orders:
        ord_obj.customer_name = usr_obj.name
        ord_obj.customer_email = usr_obj.email
        formatted_recent_orders.append(ord_obj)

    low_stock = Product.query.filter(Product.stock <= 5).order_by(Product.stock.asc()).all()
    return render_template('admin_dashboard.html', total_products=total_products,
                           total_orders=total_orders, total_users=total_users,
                           total_revenue=total_revenue, recent_orders=formatted_recent_orders,
                           low_stock=low_stock)


@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
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

        new_product = Product(
            name=name,
            description=description,
            price=float(price),
            category=category,
            stock=int(stock or 0),
            image_filename=image_filename,
            created_at=datetime.now().isoformat()
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Product \"{name}\" added successfully.", "success")
        return redirect(url_for('admin_products'))

    return render_template('admin_add_product.html')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.description = request.form.get('description', '').strip()
        product.price = float(request.form.get('price', '0'))
        product.category = request.form.get('category', '').strip()
        product.stock = int(request.form.get('stock', '0') or 0)

        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_filename = filename

        db.session.commit()
        flash(f"Product \"{product.name}\" updated.", "success")
        return redirect(url_for('admin_products'))

    return render_template('admin_edit_product.html', product=product)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        # Clear linked order items manually if needed, or rely on cascade
        OrderItem.query.filter_by(product_id=product_id).delete()
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully.", "success")
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = db.session.query(Order, User).join(User, Order.user_id == User.id).order_by(Order.order_date.desc()).all()
    formatted_orders = []
    for ord_obj, usr_obj in orders:
        ord_obj.customer_name = usr_obj.name
        ord_obj.customer_email = usr_obj.email
        ord_obj.customer_phone = usr_obj.phone
        formatted_orders.append(ord_obj)
    return render_template('admin_orders.html', orders=formatted_orders)


@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    result = db.session.query(Order, User).join(User, Order.user_id == User.id).filter(Order.id == order_id).first()
    if not result:
        flash("Order not found.", "error")
        return redirect(url_for('admin_orders'))
    
    order, user = result
    order.customer_name = user.name
    order.customer_email = user.email
    order.customer_phone = user.phone
    order.customer_address = user.address

    items = OrderItem.query.filter_by(order_id=order_id).all()
    return render_template('admin_order_detail.html', order=order, items=items)


@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    order = Order.query.get(order_id)
    if order:
        order.payment_status = request.form.get('payment_status')
        order.order_status = request.form.get('order_status')
        db.session.commit()
        flash("Order updated.", "success")
    return redirect(url_for('admin_order_detail', order_id=order_id))


@app.route('/admin/customers')
@admin_required
def admin_customers():
    customers = User.query.order_by(User.created_at.desc()).all()
    customers_with_stats = []
    for c in customers:
        stats = db.session.query(
            db.func.count(Order.id),
            db.func.coalesce(db.func.sum(Order.total_amount), 0)
        ).filter(Order.user_id == c.id).first()
        customers_with_stats.append({'user': c, 'order_count': stats[0], 'total_spent': stats[1]})
    return render_template('admin_customers.html', customers=customers_with_stats)


@app.route('/admin/settings')
@admin_required
def admin_settings():
    return render_template('admin_settings.html', upi_id=UPI_ID, payee_name=PAYEE_NAME,
                           whatsapp_number=WHATSAPP_NUMBER)


@app.route('/admin/customers/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_customer(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user) # Cascade will handle orders and order_items
        db.session.commit()
        flash("Customer and all related records deleted successfully.", "success")
    return redirect(url_for('admin_customers'))


@app.route('/admin/orders/delete/<int:order_id>', methods=['POST'])
@admin_required
def delete_order(order_id):
    order = Order.query.get(order_id)
    if order:
        db.session.delete(order) # Cascade will handle order_items
        db.session.commit()
        flash("Order deleted successfully.", "success")
    return redirect(url_for('admin_orders'))


# ------------------------------------------------------------------
# STATIC FILE HELPERS
# ------------------------------------------------------------------
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Initialize the database on import
init_db()


# ------------------------------------------------------------------
# MAIN (used only for local development with "python app.py")
# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)