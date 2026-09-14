# GadgetGuru — Full E-Commerce Website

A complete e-commerce website for **GadgetGuru** built with **Python (Flask)**,
**HTML**, **CSS**, and **JavaScript**. Red & white theme, admin panel, UPI/QR
payments, receipts, and a WhatsApp chat button.

---

## 1. What's included

- Customer storefront: browse products, search, category filters, product
  detail pages, cart, checkout, UPI/QR or Cash-on-Delivery payment, and a
  printable receipt.
- Customer accounts: sign up / log in, order history.
- Admin panel (separate login) to:
  - See a dashboard with revenue, orders, products, and customer stats
  - Upload new products with an image, price, description, category & stock
  - Edit or delete products
  - View and update every order (payment status & delivery status)
  - See every registered customer's details (name, email, phone, address)
  - See payment settings (UPI ID / WhatsApp number)
- G-inside-G logo mark (red & white), matching favicon
- Distinct mobile menu — a full-screen red slide-in panel, different from the
  desktop nav bar
- Floating WhatsApp "chat with us" button (bottom-right)

---

## 2. Setup

You need **Python 3.9+** installed.

```bash
# 1. Unzip the project, then move into the folder
cd GadgetGuru

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The database (`gadgetguru.db`) and demo products are created automatically the
first time you run the app.

---

## 3. Admin Login

Go to **http://127.0.0.1:5000/admin/login** (also linked in the footer and the
mobile menu) and log in with:

- **Email:** `ayaan@gadgetguru.com`
- **Password:** `password2007`

These credentials are set near the top of `app.py`:

```python
ADMIN_EMAIL = "ayaan@gadgetguru.com"
ADMIN_PASSWORD = "password2007"
```

Change them there any time.

---

## 4. ⚠️ IMPORTANT — Add your own UPI ID / QR code

Open `app.py` and find the **PAYMENT SETTINGS** section near the top:

```python
UPI_ID = "gadgetguru@okhdfcbank"          # <-- CHANGE THIS to your real UPI ID
PAYEE_NAME = "GadgetGuru"                  # <-- CHANGE THIS to your business name
```

Replace `UPI_ID` with your real UPI ID (the one from Google Pay / PhonePe /
Paytm / your bank app — looks like `yourname@oksbi`, `yourname@ybl`, etc.).

The checkout page **automatically generates a scannable QR code** from this
UPI ID + the exact order amount, using the standard `upi://pay` link format
that every UPI app understands — so you don't have to design or upload a QR
image yourself.

If you'd rather use your **own bank-provided QR image** instead of the
auto-generated one:

1. Save your QR image as `static/images/my_upi_qr.png`
2. In `app.py`, set:
   ```python
   USE_CUSTOM_QR_IMAGE = True
   ```

Customers select "Pay via UPI" or "Cash on Delivery" at checkout. For UPI
orders, once the customer taps "I've completed the payment," the order is
marked **"Awaiting Verification"** — go to **Admin Panel → Orders** to confirm
you've received the money and mark it **"Paid."**

---

## 5. WhatsApp chat button

Also near the top of `app.py`:

```python
WHATSAPP_NUMBER = "919999999999"           # <-- CHANGE THIS
WHATSAPP_DEFAULT_MSG = "Hi GadgetGuru! I have a question about a product."
```

Replace `WHATSAPP_NUMBER` with your real WhatsApp Business number, **with
country code, digits only** (no `+`, no spaces, no dashes). This powers the
floating green WhatsApp button on every page and the "Chat with us" links.

---

## 6. Uploading products

Log into the admin panel → **Products → Upload New Product**. Fill in the
name, description, price, category, stock, and upload an image (JPG, PNG,
WEBP, GIF). The product appears on the storefront immediately.

---

## 7. Project structure

```
GadgetGuru/
├── app.py                  # Flask backend — all routes & logic
├── requirements.txt
├── gadgetguru.db            # created automatically on first run
├── static/
│   ├── css/style.css        # red & white theme, all styling
│   ├── js/main.js           # mobile menu, cart qty, payment UI, etc.
│   ├── images/logo.svg      # G-inside-G logo mark
│   └── uploads/             # product images uploaded via admin panel
└── templates/               # all HTML pages (Jinja2)
    ├── base.html             # header, mobile menu, footer, WhatsApp button
    ├── admin_base.html        # admin sidebar layout
    ├── index.html, product_detail.html, cart.html, checkout.html,
    │   payment.html, receipt.html, my_orders.html, login.html, signup.html
    └── admin_*.html           # dashboard, products, orders, customers, settings
```

---

## 8. Notes

- This uses Flask's built-in development server, which is fine for local use
  and testing. For a real public launch, deploy behind a production WSGI
  server (e.g. Gunicorn) and use a stronger `SECRET_KEY` in `app.py`.
- Passwords are hashed with Werkzeug's secure password hashing — never stored
  in plain text.
- The cart is stored in the browser session, so it clears if the customer
  clears cookies or switches browsers before checking out.
