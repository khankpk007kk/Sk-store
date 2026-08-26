import streamlit as st
from supabase import create_client, Client
import pandas as pd
import requests
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
st.set_page_config(page_title="SK Store", page_icon="🛍️", layout="wide")

# --- STORE INFO ---
try:
    STORE_NAME = st.secrets["store"]["name"]
    STORE_ADDRESS = st.secrets["store"]["address"]
    STORE_PHONE = st.secrets["store"]["phone"]
    STORE_EMAIL = st.secrets["store"]["email"]
    STORE_WHATSAPP = st.secrets["store"]["whatsapp"]
except KeyError:
    STORE_NAME, STORE_ADDRESS = "SK Store", "Pakistan"
    STORE_PHONE, STORE_EMAIL, STORE_WHATSAPP = "N/A", "support@skstore.pk", ""

DELIVERY_CHARGE = 200.0
CATEGORY_EMOJI = {"Electronics": "🔌", "Fashion": "👗", "Accessories": "👜", "Home": "🏠"}
CATEGORIES = list(CATEGORY_EMOJI.keys())

# --- CUSTOM CSS ---
st.markdown(f"""
<style>
    .main {{ background-color: #f8f9fa; }}
    h1, h2, h3 {{ font-family: 'Inter', sans-serif; color: #1a1a1a; }}
    header[data-testid="stHeader"] {{
        background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        position: sticky; top: 0; z-index: 100;
    }}
    .sk-topbar {{
        background: linear-gradient(90deg,#ffe0ec,#e0f7f0); border-radius: 999px;
        padding: 10px 20px; margin-bottom: 14px; text-align: center;
        font-weight: 700; font-size: 0.85rem; color:#111;
    }}
    .sk-hero {{
        background: linear-gradient(135deg,#111 0%,#333 100%); border-radius: 16px;
        padding: 34px 30px; margin-bottom: 22px; color: white; text-align: center;
    }}
    .sk-hero h1 {{ color: white; margin-bottom: 4px; font-size: 2.1rem; }}
    .sk-hero p {{ color: #ddd; margin: 0; font-size: 0.95rem; }}
    .sk-cat-label {{ text-align:center; font-weight:600; font-size:0.85rem; color:#333; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: white; border-radius: 14px; padding: 14px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); transition: transform 0.15s, box-shadow 0.15s;
        border: none !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
        transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }}
    .sk-badge {{
        display: inline-block; background: #e11d48; color: white; font-size: 0.7rem;
        font-weight: 700; padding: 2px 9px; border-radius: 999px; margin: 0 4px 6px 0;
        letter-spacing: 0.3px;
    }}
    .sk-badge-new {{ background: #16a34a; }}
    .sk-price-row {{ display: flex; align-items: baseline; gap: 8px; margin: 2px 0 6px 0; }}
    .sk-price-now {{ font-size: 1.15rem; font-weight: 700; color: #111; }}
    .sk-price-old {{ font-size: 0.85rem; color: #999; text-decoration: line-through; }}
    .sk-stock {{ color: #6b7280; font-size: 0.78rem; margin-bottom: 4px; }}
    button[kind="primary"] {{
        background-color: #000 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600; border: none !important;
    }}
    button[kind="primary"]:hover {{ background-color: #222 !important; }}
    button[kind="secondary"] {{
        background-color: transparent !important; color: #333 !important;
        border: 1px solid #ddd !important; border-radius: 8px !important;
    }}
    .sk-flash {{
        background:#e6f9ee; border:1px solid #16a34a; border-radius:12px; padding:14px 18px;
        margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;
    }}
    .sk-footer {{
        margin-top: 40px; padding: 30px 20px 10px 20px; text-align: center;
        color: #555; font-size: 0.85rem; border-top: 1px solid #eee; background:#fafafa;
        border-radius: 16px;
    }}
    .sk-footer h4 {{ color:#111; margin-bottom: 10px; }}
    .sk-whatsapp-btn {{
        display:inline-block; background:#25D366; color:white !important; font-weight:700;
        padding:10px 24px; border-radius:999px; text-decoration:none; margin:14px 0;
    }}
    .sk-pay-badge {{
        display:inline-block; background:white; border:1px solid #ddd; border-radius:6px;
        padding:5px 12px; margin:3px; font-size:0.75rem; font-weight:700; color:#333;
    }}
    .sk-float-whatsapp {{
        position: fixed; bottom: 22px; right: 22px; z-index: 999;
        background:#25D366; color:white !important; border-radius:50%;
        width:56px; height:56px; display:flex; align-items:center; justify-content:center;
        font-size:26px; text-decoration:none; box-shadow:0 4px 14px rgba(0,0,0,0.25);
    }}
    .sk-summary-row {{ display:flex; justify-content:space-between; padding:6px 0; font-size:0.95rem; }}
    .sk-summary-total {{ display:flex; justify-content:space-between; padding:10px 0; font-size:1.2rem; font-weight:800; border-top:2px solid #111; margin-top:6px; }}
    #MainMenu, footer, .viewerBadge_container__1QSob {{ display: none !important; }}
</style>
""", unsafe_allow_html=True)

try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    SUPABASE_ADMIN_KEY = st.secrets["supabase"]["admin_key"]
except KeyError:
    st.error("⚠️ Supabase secrets missing! Configure in Streamlit Cloud Settings > Secrets.")
    st.stop()

supabase_public = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_ADMIN_KEY)

for key, default in [('cart', []), ('page', 'home'), ('cat_filter', 'All'), ('is_admin', False),
                      ('flash_add', None), ('detected_city', ''), ('detected_street', '')]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# HELPERS
# ============================================================
def get_youtube_embed(url):
    if not url or ('youtube.com' not in url and 'youtu.be' not in url): return None
    video_id = ""
    if 'youtu.be/' in url: video_id = url.split('youtu.be/')[1].split('?')[0]
    elif 'v=' in url: video_id = url.split('v=')[1].split('&')[0]
    return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&rel=0" if video_id else None

def is_new_product(p):
    try:
        created = p.get('created_at')
        if not created: return False
        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - created_dt) <= timedelta(days=7)
    except Exception:
        return False

def price_block(p):
    old_price = p.get('original_price')
    now = p['price']
    badges = ""
    if is_new_product(p):
        badges += '<span class="sk-badge sk-badge-new">NEW</span>'
    if old_price and old_price > now:
        badges += '<span class="sk-badge">SALE</span>'
    if badges:
        st.markdown(badges, unsafe_allow_html=True)
    if old_price and old_price > now:
        st.markdown(f"""<div class="sk-price-row"><span class="sk-price-now">Rs. {now:,.0f}</span>
                    <span class="sk-price-old">Rs. {old_price:,.0f}</span></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="sk-price-row"><span class="sk-price-now">Rs. {now:,.0f}</span></div>""",
                    unsafe_allow_html=True)

def add_to_cart(p):
    st.session_state.cart.append(p)
    st.session_state.flash_add = p['name']
    st.toast(f"Added {p['name']}!", icon="🛒")

def cart_subtotal():
    return sum(i['price'] for i in st.session_state.cart)

# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================
def send_order_emails(order_id, customer_name, customer_email, phone, alt_phone, whatsapp,
                       full_address, items, subtotal, delivery_charge, grand_total, payment_method):
    try:
        gmail_sender = st.secrets["gmail"]["sender_email"]
        gmail_password = st.secrets["gmail"]["app_password"]
        admin_email = st.secrets["gmail"]["admin_email"]
    except KeyError:
        return False, "Gmail secrets not configured — skipped sending emails."

    items_rows = "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{it['name']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #eee;text-align:right;'>Rs. {it['price']:,.2f}</td></tr>"
        for it in items
    )
    totals_html = f"""
        <tr><td style='padding:6px;'>Subtotal</td><td style='padding:6px;text-align:right;'>Rs. {subtotal:,.2f}</td></tr>
        <tr><td style='padding:6px;'>Delivery Charge</td><td style='padding:6px;text-align:right;'>Rs. {delivery_charge:,.2f}</td></tr>
        <tr><td style='padding:6px;font-weight:700;'>Grand Total</td><td style='padding:6px;text-align:right;font-weight:700;'>Rs. {grand_total:,.2f}</td></tr>
    """

    customer_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #eee;border-radius:12px;overflow:hidden;">
      <div style="background:#111;color:white;padding:20px;text-align:center;"><h2 style="margin:0;">🛍️ {STORE_NAME}</h2></div>
      <div style="padding:24px;">
        <h3 style="color:#111;">Thank you, {customer_name}! 🎉</h3>
        <p>Your order <b>#{order_id}</b> has been received ({payment_method}).</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#f4f4f4;"><th style="text-align:left;padding:8px;">Item</th><th style="text-align:right;padding:8px;">Price</th></tr>
          {items_rows}
        </table>
        <table style="width:100%;">{totals_html}</table>
        <p>📦 <b>Delivery Address:</b> {full_address}<br>📞 <b>Contact:</b> {phone}
           {f'<br>📱 Alt: {alt_phone}' if alt_phone else ''} {f'<br>💬 WhatsApp: {whatsapp}' if whatsapp else ''}</p>
        <p style="color:#666;">We'll notify you once your order ships. Thank you for shopping with us!</p>
      </div>
    </div>
    """
    admin_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #eee;border-radius:12px;overflow:hidden;">
      <div style="background:#e11d48;color:white;padding:20px;text-align:center;"><h2 style="margin:0;">📦 New Order — Packing Required</h2></div>
      <div style="padding:24px;">
        <p><b>Order ID:</b> {order_id} &nbsp;|&nbsp; <b>Payment:</b> {payment_method}</p>
        <p><b>Customer:</b> {customer_name}<br><b>Phone:</b> {phone}
           {f'<br><b>Alt Phone:</b> {alt_phone}' if alt_phone else ''}
           {f'<br><b>WhatsApp:</b> {whatsapp}' if whatsapp else ''}<br>
           <b>Email:</b> {customer_email or 'Not provided'}<br><b>Address:</b> {full_address}</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#f4f4f4;"><th style="text-align:left;padding:8px;">Item</th><th style="text-align:right;padding:8px;">Price</th></tr>
          {items_rows}
        </table>
        <table style="width:100%;">{totals_html}</table>
        <p style="color:#e11d48;"><b>👉 Please prepare this order for packing & dispatch.</b></p>
      </div>
    </div>
    """
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_sender, gmail_password)
        if customer_email:
            msg1 = MIMEMultipart("alternative")
            msg1["Subject"] = f"✅ Order Confirmed — {STORE_NAME} (Order #{order_id})"
            msg1["From"] = gmail_sender; msg1["To"] = customer_email
            msg1.attach(MIMEText(customer_body, "html"))
            server.sendmail(gmail_sender, customer_email, msg1.as_string())
        msg2 = MIMEMultipart("alternative")
        msg2["Subject"] = f"📦 New Order #{order_id} — Packing Required"
        msg2["From"] = gmail_sender; msg2["To"] = admin_email
        msg2.attach(MIMEText(admin_body, "html"))
        server.sendmail(gmail_sender, admin_email, msg2.as_string())
        server.quit()
        return True, "Emails sent successfully."
    except Exception as e:
        return False, str(e)

# ============================================================
# SAFEPAY ONLINE PAYMENT (hosted checkout — card data never touches our server)
# ⚠️ IMPORTANT: This is a starting structure. The exact endpoint/field names
# below must be verified against Safepay's CURRENT official docs (docs.safepay.pk)
# before going live — payment gateway APIs change and get it wrong = broken checkout.
# Test thoroughly in SANDBOX mode first.
# ============================================================
def safepay_configured():
    try:
        return bool(st.secrets["safepay"]["api_key"])
    except Exception:
        return False

def create_safepay_checkout(order_id, amount, customer_name, customer_email, return_base_url):
    """Creates a hosted checkout session and returns the redirect URL, or None on failure."""
    try:
        api_key = st.secrets["safepay"]["api_key"]
        mode = st.secrets["safepay"].get("mode", "sandbox")
    except Exception:
        return None, "Safepay not configured."

    base = "https://sandbox.api.getsafepay.com" if mode == "sandbox" else "https://api.getsafepay.com"
    try:
        resp = requests.post(
            f"{base}/checkout/v2/session",  # ⚠️ verify exact path in current Safepay docs
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "amount": int(amount * 100),  # smallest currency unit — confirm with docs
                "currency": "PKR",
                "order_id": str(order_id),
                "customer": {"name": customer_name, "email": customer_email or ""},
                "success_url": f"{return_base_url}?payment=success&order_id={order_id}",
                "cancel_url": f"{return_base_url}?payment=cancelled&order_id={order_id}",
            },
            timeout=15,
        )
        data = resp.json()
        checkout_url = data.get("checkout_url") or data.get("data", {}).get("checkout_url")
        if checkout_url:
            return checkout_url, None
        return None, f"Unexpected response from Safepay: {data}"
    except Exception as e:
        return None, str(e)

def verify_safepay_payment(order_id):
    """
    Server-side confirmation — NEVER trust the ?payment=success URL alone,
    since anyone could type that URL manually without paying.
    ⚠️ Replace this with a real call to Safepay's payment-status API per their docs.
    """
    try:
        api_key = st.secrets["safepay"]["api_key"]
        mode = st.secrets["safepay"].get("mode", "sandbox")
    except Exception:
        return False
    base = "https://sandbox.api.getsafepay.com" if mode == "sandbox" else "https://api.getsafepay.com"
    try:
        resp = requests.get(
            f"{base}/order/v1/{order_id}",  # ⚠️ verify exact path in current Safepay docs
            headers={"Authorization": f"Bearer {api_key}"}, timeout=15,
        )
        data = resp.json()
        status = (data.get("state") or data.get("status") or "").lower()
        return status in ("paid", "completed", "success", "tracked")
    except Exception:
        return False

# ============================================================
# ADMIN
# ============================================================
def admin_login_gate():
    st.title("🔐 Admin Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login", type="primary"):
        try:
            correct = st.secrets["admin"]["password"]
        except KeyError:
            st.error("⚠️ No admin password set in secrets."); return
        if pwd and pwd == correct:
            st.session_state.is_admin = True; st.rerun()
        else:
            st.error("❌ Incorrect password.")

def admin_panel():
    st.sidebar.success("✅ Logged in as Admin")
    if st.sidebar.button("Logout"):
        st.session_state.is_admin = False; st.rerun()

    st.title("🔐 Admin Dashboard")
    tab1, tab2 = st.tabs(["➕ Add Product", " Orders"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Product Name *")
            price = st.number_input("Price (PKR) *", min_value=0.0)
            original_price = st.number_input("Original Price (optional, for sale badge)", min_value=0.0, value=0.0)
            categories = st.multiselect("Categories * (select one or more)", CATEGORIES)
            stock = st.number_input("Stock", min_value=0, value=10)
        with col2:
            desc = st.text_area("Description")
            yt_url = st.text_input("YouTube Link")
            active = st.checkbox("Active", value=True)

        st.markdown("---")
        files = st.file_uploader("Upload Images (Max 5)", type=['png', 'jpg'], accept_multiple_files=True)

        if st.button("💾 Save Product", type="primary"):
            if name and price > 0 and categories:
                prod = {"name": name, "description": desc, "price": float(price),
                        "categories": categories, "stock": int(stock), "youtube_url": yt_url,
                        "is_active": active, "images": []}
                if original_price > 0:
                    prod["original_price"] = float(original_price)

                pid = None
                try:
                    with st.spinner("Saving..."):
                        try:
                            res = supabase_admin.table("products").insert(prod).execute()
                        except Exception:
                            if "original_price" in prod:
                                prod.pop("original_price")
                                res = supabase_admin.table("products").insert(prod).execute()
                                st.warning("⚠️ Saved without sale price — add an 'original_price' column in Supabase.")
                            else:
                                raise
                        pid = res.data[0]['id']
                        urls = []
                        if files:
                            for f in files[:5]:
                                path = f"{pid}/{f.name}"
                                supabase_admin.storage.from_('sk-store-images').upload(path, f.getvalue())
                                urls.append(supabase_admin.storage.from_('sk-store-images').get_public_url(path))
                        supabase_admin.table("products").update({"images": urls}).eq("id", pid).execute()
                    st.success(f"✅ '{name}' Added!"); st.rerun()
                except Exception as e:
                    st.error("❌ Failed to save product. Real error below 👇")
                    st.exception(e)
                    if pid:
                        st.warning(f"Note: a product row (id={pid}) may already exist — check Supabase.")
            else:
                st.warning("⚠️ Please fill Name, Price > 0, and select at least one Category.")

    with tab2:
        orders = supabase_admin.table("orders").select("*").order("created_at", desc=True).limit(30).execute()
        if orders.data: st.dataframe(pd.DataFrame(orders.data), use_container_width=True)
        else: st.info("No orders yet.")

# ============================================================
# HEADER / CATEGORY ROW / FOOTER
# ============================================================
def render_header():
    st.markdown('<div class="sk-topbar">✨ Free updates on new arrivals &nbsp;|&nbsp; 🔥 Shop the latest deals</div>',
                unsafe_allow_html=True)
    h1, h2, h3 = st.columns([1, 3, 1])
    with h1:
        with st.popover("☰ Menu"):
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.page = 'home'; st.session_state.cat_filter = 'All'; st.rerun()
            st.markdown("**Browse Categories**")
            for c in CATEGORIES:
                if st.button(f"{CATEGORY_EMOJI[c]} {c}", key=f"menu_{c}", use_container_width=True):
                    st.session_state.cat_filter = c; st.session_state.page = 'home'; st.rerun()
            st.markdown("---")
            if st.button("🛒 View Cart", use_container_width=True):
                st.session_state.page = 'cart'; st.rerun()
    with h2:
        st.markdown(f'<h1 style="text-align:center;margin:0;">🛍️ {STORE_NAME}</h1>', unsafe_allow_html=True)
    with h3:
        if st.button(f"🛒 ({len(st.session_state.cart)})", use_container_width=True):
            st.session_state.page = 'cart'; st.rerun()

def render_category_row():
    st.write("")
    st.markdown("#### Shop by Category")
    cols = st.columns(len(CATEGORIES) + 1)
    with cols[0]:
        if st.button("🛍️ All", key="cat_all", use_container_width=True):
            st.session_state.cat_filter = "All"; st.rerun()
    for i, c in enumerate(CATEGORIES):
        with cols[i + 1]:
            if st.button(f"{CATEGORY_EMOJI[c]} {c}", key=f"cat_{c}", use_container_width=True):
                st.session_state.cat_filter = c; st.rerun()

def render_footer():
    st.markdown(f"""
    <div class="sk-footer">
        <h4>We're Here To Help! 💬</h4>
        <p>📍 {STORE_ADDRESS}<br>📞 {STORE_PHONE}<br>✉️ {STORE_EMAIL}</p>
        {f'<a href="https://wa.me/{STORE_WHATSAPP}" target="_blank" class="sk-whatsapp-btn">💬 Chat on WhatsApp</a>' if STORE_WHATSAPP else ''}
        <div><span class="sk-pay-badge">Cash on Delivery</span>
             <span class="sk-pay-badge">VISA</span><span class="sk-pay-badge">Mastercard</span>
             <span class="sk-pay-badge">Secure Checkout via Safepay</span></div>
        <p style="margin-top:16px;">🇵🇰 We currently deliver within Pakistan only.<br>
        © {datetime.now().year} {STORE_NAME}. All Rights Reserved. Made with ❤️ in Pakistan</p>
    </div>
    """, unsafe_allow_html=True)
    if STORE_WHATSAPP:
        st.markdown(f'<a href="https://wa.me/{STORE_WHATSAPP}" target="_blank" class="sk-float-whatsapp">💬</a>',
                    unsafe_allow_html=True)

def render_flash_banner():
    if st.session_state.flash_add:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f'<div class="sk-flash">✅ <b>{st.session_state.flash_add}</b> added to cart — '
                        f'{len(st.session_state.cart)} item(s), Rs. {cart_subtotal():,.0f}</div>',
                        unsafe_allow_html=True)
        with c2:
            if st.button("🛒 View Your Cart →", type="primary", use_container_width=True):
                st.session_state.page = 'cart'; st.session_state.flash_add = None; st.rerun()

# ============================================================
# GEOLOCATION (browser-based, best-effort auto-detect)
# ============================================================
def render_location_detector():
    st.components.v1.html("""
    <button id="sk-geo-btn" style="background:#000;color:white;border:none;border-radius:8px;
        padding:10px 18px;font-weight:600;cursor:pointer;width:100%;">📍 Detect My Location Automatically</button>
    <p id="sk-geo-status" style="font-size:0.8rem;color:#888;margin-top:6px;"></p>
    <script>
    document.getElementById('sk-geo-btn').onclick = function() {
        var status = document.getElementById('sk-geo-status');
        status.innerText = "Detecting...";
        if (!navigator.geolocation) { status.innerText = "Geolocation not supported."; return; }
        navigator.geolocation.getCurrentPosition(function(pos) {
            var lat = pos.coords.latitude, lon = pos.coords.longitude;
            fetch("https://nominatim.openstreetmap.org/reverse?format=json&lat=" + lat + "&lon=" + lon)
                .then(r => r.json())
                .then(data => {
                    var addr = data.address || {};
                    var city = addr.city || addr.town || addr.village || "";
                    var street = data.display_name || "";
                    var country = addr.country_code || "";
                    var url = new URL(window.top.location.href);
                    url.searchParams.set("det_city", city);
                    url.searchParams.set("det_street", street);
                    url.searchParams.set("det_country", country);
                    window.top.location.href = url.toString();
                }).catch(() => { status.innerText = "Could not detect address — please enter manually."; });
        }, function() { status.innerText = "Location permission denied — please enter manually."; });
    };
    </script>
    """, height=90)

# ============================================================
# CUSTOMER STORE (home)
# ============================================================
def customer_store():
    render_header()
    render_flash_banner()
    st.markdown("""
    <div class="sk-hero"><h1>🛍️ Premium Quality, Unbeatable Prices</h1>
    <p>Fast Delivery Across Pakistan — Shop With Confidence</p></div>
    """, unsafe_allow_html=True)

    render_category_row()
    st.write("")
    search = st.text_input("🔍 Search products...", key="search", label_visibility="collapsed",
                            placeholder="🔍 Search products...")

    q = supabase_public.table("products").select("*").eq("is_active", True)
    if st.session_state.cat_filter != "All":
        q = q.contains("categories", [st.session_state.cat_filter])
    if search: q = q.ilike("name", f"%{search}%")
    products = q.execute().data

    st.write("")
    if not products:
        st.info("No products found.")
        render_footer(); return

    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i % 3]:
            with st.container(border=True):
                if p.get('images'): st.image(p['images'][0], use_container_width=True)
                else: st.image("https://via.placeholder.com/300x200?text=SK+Store", use_container_width=True)
                st.markdown(f"**{p['name']}**")
                cats = ", ".join(p.get("categories") or [p.get("category")] if p.get("category") else [])
                st.markdown(f'<div class="sk-stock">📂 {cats} &nbsp;|&nbsp; 📦 {p.get("stock")} left</div>',
                            unsafe_allow_html=True)
                price_block(p)
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("View", key=f"v_{p['id']}", use_container_width=True):
                        st.session_state.selected_product = p; st.session_state.page = 'detail'; st.rerun()
                with bc2:
                    if st.button("Add to cart", key=f"a_{p['id']}", type="primary", use_container_width=True):
                        add_to_cart(p); st.rerun()
    render_footer()

def product_detail():
    render_header()
    render_flash_banner()
    p = st.session_state.get('selected_product')
    if not p: st.session_state.page = 'home'; st.rerun(); return
    st.button("← Back", on_click=lambda: setattr(st.session_state, 'page', 'home'))
    c1, c2 = st.columns([1, 1])
    with c1:
        imgs = p.get('images', [])
        if imgs:
            idx = st.session_state.get('img_idx', 0)
            st.image(imgs[idx], use_container_width=True)
            if len(imgs) > 1:
                thumbs = st.columns(min(len(imgs), 5))
                for t in range(len(thumbs)):
                    with thumbs[t]:
                        if st.button(f"{t+1}", key=f"th_{t}"): st.session_state.img_idx = t; st.rerun()
    with c2:
        st.title(p['name'])
        price_block(p)
        st.write(p.get('description'))
        if p.get('youtube_url'):
            embed = get_youtube_embed(p['youtube_url'])
            if embed:
                st.components.v1.html(
                    f'<iframe width="100%" height="315" src="{embed}" frameborder="0" allowfullscreen></iframe>',
                    height=350)
        if st.button("🛒 Add to Cart", type="primary", use_container_width=True):
            add_to_cart(p); st.rerun()
    render_footer()

# ============================================================
# CART & CHECKOUT PAGE
# ============================================================
def cart_page():
    render_header()
    st.title("🛒 Your Cart")

    if st.button("← Continue Shopping"):
        st.session_state.page = 'home'; st.rerun()

    if not st.session_state.cart:
        st.info("Your cart is empty."); render_footer(); return

    for i, item in enumerate(st.session_state.cart):
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.write(item['name']); c2.write(f"Rs. {item['price']:,.2f}")
        if c3.button("🗑️", key=f"rm_{i}"): st.session_state.cart.pop(i); st.rerun()

    subtotal = cart_subtotal()
    grand_total = subtotal + DELIVERY_CHARGE

    st.markdown(f"""
    <div class="sk-summary-row"><span>Subtotal</span><span>Rs. {subtotal:,.2f}</span></div>
    <div class="sk-summary-row"><span>Delivery Charge</span><span>Rs. {DELIVERY_CHARGE:,.2f}</span></div>
    <div class="sk-summary-total"><span>Grand Total</span><span>Rs. {grand_total:,.2f}</span></div>
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📍 Delivery Address")

    render_location_detector()
    qp = st.query_params
    det_city = qp.get("det_city", "")
    det_street = qp.get("det_street", "")

    nm = st.text_input("Full Name *")
    em = st.text_input("Email (for order confirmation)")
    ph = st.text_input("Phone Number *")
    alt_ph = st.text_input("Alternative Phone Number (optional)")
    wa_num = st.text_input("WhatsApp Number (optional)")

    country = st.selectbox("Country *", ["Pakistan", "Other (not supported)"], index=0)
    city = st.text_input("City *", value=det_city)
    street1 = st.text_input("Street Address 1 *", value=det_street)
    street2 = st.text_input("Street Address 2 (optional)")

    if country != "Pakistan":
        st.error("😔 Sorry! We currently only deliver within Pakistan. Please select Pakistan to continue, "
                  "or check back later as we expand.")

    st.divider()
    st.subheader("💳 Payment Method")
    payment_method = st.radio("Choose how you'd like to pay",
                               ["💵 Cash on Delivery", "💳 Pay Online (Credit / Debit Card)"])

    card_type = None
    if payment_method.startswith("💳"):
        card_type = st.radio("Card Type", ["Credit Card", "Debit Card"], horizontal=True)
        if safepay_configured():
            st.info("🔒 You'll be redirected to our secure payment partner (Safepay) to enter your card details. "
                     "Your card number is never seen or stored by this site.")
        else:
            st.warning("⚠️ Online payment isn't configured yet on this store. Please choose Cash on Delivery, "
                       "or the store owner needs to add Safepay keys to secrets.")

    place_disabled = (country != "Pakistan")

    if st.button("✅ Place Order", type="primary", use_container_width=True, disabled=place_disabled):
        if not (nm and ph and city and street1):
            st.warning("⚠️ Please fill Name, Phone, City and Street Address.")
        else:
            full_address = f"{street1}, {street2 + ', ' if street2 else ''}{city}, {country}"
            items_payload = [{"name": x['name'], "price": x['price']} for x in st.session_state.cart]
            od = {
                "customer_name": nm, "email": em or None, "phone": ph,
                "alt_phone": alt_ph or None, "whatsapp": wa_num or None,
                "country": country, "city": city, "street1": street1, "street2": street2 or None,
                "address": full_address, "items": items_payload,
                "subtotal": subtotal, "delivery_charge": DELIVERY_CHARGE, "total_amount": grand_total,
                "payment_method": "COD" if payment_method.startswith("💵") else f"Online ({card_type})",
                "payment_status": "Pending" if payment_method.startswith("💵") else "Pending Payment",
                "status": "Pending",
            }
            try:
                res = supabase_admin.table("orders").insert(od).execute()
                order_id = res.data[0]['id']

                if payment_method.startswith("💵"):
                    ok, msg = send_order_emails(order_id, nm, em, ph, alt_ph, wa_num, full_address,
                                                 items_payload, subtotal, DELIVERY_CHARGE, grand_total, "Cash on Delivery")
                    if not ok: st.warning(f"Order placed, but email failed: {msg}")
                    st.success("🎉 Order placed! You'll pay cash on delivery. A confirmation has been sent.")
                    st.session_state.cart = []; st.rerun()
                else:
                    if not safepay_configured():
                        st.error("Online payment isn't set up. Please choose Cash on Delivery instead.")
                    else:
                        base_url = st.secrets.get("app", {}).get("base_url", "")
                        checkout_url, err = create_safepay_checkout(order_id, grand_total, nm, em, base_url)
                        if checkout_url:
                            st.session_state.pending_order_id = order_id
                            st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                                       unsafe_allow_html=True)
                            st.info(f"Redirecting you to secure payment... [click here if not redirected]({checkout_url})")
                        else:
                            st.error(f"Could not start online payment: {err}. Order saved as Pending — "
                                     f"you can contact us or try Cash on Delivery.")
            except Exception as e:
                st.error("❌ Failed to place order. Real error below 👇")
                st.exception(e)

    render_footer()

def order_result_page():
    """Handles the redirect back from Safepay after online payment."""
    qp = st.query_params
    status = qp.get("payment")
    order_id = qp.get("order_id")
    render_header()
    if status == "success" and order_id:
        confirmed = verify_safepay_payment(order_id)
        if confirmed:
            try:
                supabase_admin.table("orders").update({"payment_status": "Paid"}).eq("id", order_id).execute()
            except Exception:
                pass
            st.success(f"🎉 Payment confirmed for Order #{order_id}! Thank you for shopping with us.")
            st.session_state.cart = []
        else:
            st.warning(f"We couldn't verify payment for Order #{order_id} yet. If money was deducted, "
                       f"please contact support with your order ID — do not pay again.")
    elif status == "cancelled":
        st.info("Payment was cancelled. Your order is saved — you can try paying again or choose Cash on Delivery.")
    if st.button("Continue Shopping"):
        st.query_params.clear()
        st.session_state.page = 'home'; st.rerun()
    render_footer()

# ============================================================
# MAIN ROUTER
# ============================================================
params = st.query_params
if params.get("admin") == "1":
    if st.session_state.is_admin: admin_panel()
    else: admin_login_gate()
elif params.get("payment") in ("success", "cancelled"):
    order_result_page()
else:
    if st.session_state.page == 'detail': product_detail()
    elif st.session_state.page == 'cart': cart_page()
    else: customer_store()
