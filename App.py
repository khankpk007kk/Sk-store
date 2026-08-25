import streamlit as st
from supabase import create_client, Client
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
st.set_page_config(page_title="SK Store", page_icon="🛍️", layout="wide")

# --- CUSTOM CSS — ToyZone.pk INSPIRED LOOK ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #1a1a1a; }

    header[data-testid="stHeader"] {
        background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        position: sticky; top: 0; z-index: 100;
    }

    .sk-hero {
        background: linear-gradient(135deg,#111 0%,#333 100%);
        border-radius: 16px; padding: 34px 30px; margin-bottom: 22px;
        color: white; text-align: center;
    }
    .sk-hero h1 { color: white; margin-bottom: 4px; font-size: 2.1rem; }
    .sk-hero p { color: #ddd; margin: 0; font-size: 0.95rem; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: white; border-radius: 14px; padding: 14px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); transition: transform 0.15s, box-shadow 0.15s;
        border: none !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }

    .sk-badge {
        display: inline-block; background: #e11d48; color: white; font-size: 0.7rem;
        font-weight: 700; padding: 2px 9px; border-radius: 999px; margin-bottom: 6px;
        letter-spacing: 0.3px;
    }
    .sk-price-row { display: flex; align-items: baseline; gap: 8px; margin: 2px 0 6px 0; }
    .sk-price-now { font-size: 1.15rem; font-weight: 700; color: #111; }
    .sk-price-old { font-size: 0.85rem; color: #999; text-decoration: line-through; }
    .sk-stock { color: #6b7280; font-size: 0.78rem; margin-bottom: 4px; }

    button[kind="primary"] {
        background-color: #000 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600; border: none !important;
    }
    button[kind="primary"]:hover { background-color: #222 !important; }
    button[kind="secondary"] {
        background-color: transparent !important; color: #333 !important;
        border: 1px solid #ddd !important; border-radius: 8px !important;
    }

    .sk-footer {
        margin-top: 40px; padding: 24px 10px; text-align: center;
        color: #888; font-size: 0.8rem; border-top: 1px solid #eee;
    }
    .sk-footer b { color: #333; }

    #MainMenu, footer, .viewerBadge_container__1QSob { display: none !important; }
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

if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = 'home'

CATEGORIES = ["Electronics", "Fashion", "Accessories", "Home"]

# --- HELPER FUNCTIONS ---
def get_youtube_embed(url):
    if not url or ('youtube.com' not in url and 'youtu.be' not in url): return None
    video_id = ""
    if 'youtu.be/' in url: video_id = url.split('youtu.be/')[1].split('?')[0]
    elif 'v=' in url: video_id = url.split('v=')[1].split('&')[0]
    return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&rel=0" if video_id else None

def price_block(p):
    old_price = p.get('original_price')
    now = p['price']
    if old_price and old_price > now:
        st.markdown(f"""
        <span class="sk-badge">SALE</span>
        <div class="sk-price-row">
            <span class="sk-price-now">Rs. {now:,.0f}</span>
            <span class="sk-price-old">Rs. {old_price:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="sk-price-row"><span class="sk-price-now">Rs. {now:,.0f}</span></div>""",
                    unsafe_allow_html=True)

# --- EMAIL SENDING (Gmail SMTP) ---
def send_order_emails(order_id, customer_name, customer_email, phone, address, items, total):
    """
    Sends a nice confirmation email to the customer (if they gave an email)
    and a packing-alert email to the store admin, with full order details.
    Returns (success: bool, message: str) — never raises, so checkout never breaks
    even if Gmail secrets are missing or sending fails.
    """
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

    customer_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #eee;border-radius:12px;overflow:hidden;">
      <div style="background:#111;color:white;padding:20px;text-align:center;">
        <h2 style="margin:0;">🛍️ SK Store</h2>
      </div>
      <div style="padding:24px;">
        <h3 style="color:#111;">Thank you, {customer_name}! 🎉</h3>
        <p>Your order <b>#{order_id}</b> has been received and is now being processed.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#f4f4f4;">
            <th style="text-align:left;padding:8px;">Item</th>
            <th style="text-align:right;padding:8px;">Price</th>
          </tr>
          {items_rows}
        </table>
        <p style="font-size:1.1rem;text-align:right;"><b>Total: Rs. {total:,.2f}</b></p>
        <p>📦 <b>Delivery Address:</b> {address}<br>📞 <b>Contact:</b> {phone}</p>
        <p style="color:#666;">We'll notify you once your order ships. Thank you for shopping with us!</p>
      </div>
    </div>
    """

    admin_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #eee;border-radius:12px;overflow:hidden;">
      <div style="background:#e11d48;color:white;padding:20px;text-align:center;">
        <h2 style="margin:0;">📦 New Order — Packing Required</h2>
      </div>
      <div style="padding:24px;">
        <p><b>Order ID:</b> {order_id}</p>
        <p>
          <b>Customer:</b> {customer_name}<br>
          <b>Phone:</b> {phone}<br>
          <b>Email:</b> {customer_email or 'Not provided'}<br>
          <b>Address:</b> {address}
        </p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#f4f4f4;">
            <th style="text-align:left;padding:8px;">Item</th>
            <th style="text-align:right;padding:8px;">Price</th>
          </tr>
          {items_rows}
        </table>
        <p style="font-size:1.1rem;text-align:right;"><b>Total: Rs. {total:,.2f}</b></p>
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
            msg1["Subject"] = f"✅ Order Confirmed — SK Store (Order #{order_id})"
            msg1["From"] = gmail_sender
            msg1["To"] = customer_email
            msg1.attach(MIMEText(customer_body, "html"))
            server.sendmail(gmail_sender, customer_email, msg1.as_string())

        msg2 = MIMEMultipart("alternative")
        msg2["Subject"] = f"📦 New Order #{order_id} — Packing Required"
        msg2["From"] = gmail_sender
        msg2["To"] = admin_email
        msg2.attach(MIMEText(admin_body, "html"))
        server.sendmail(gmail_sender, admin_email, msg2.as_string())

        server.quit()
        return True, "Emails sent successfully."
    except Exception as e:
        return False, str(e)

# --- ADMIN PANEL ---
def admin_panel():
    st.title("🔐 Admin Dashboard")
    tab1, tab2 = st.tabs(["➕ Add Product", " Orders"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Product Name *")
            price = st.number_input("Price (PKR) *", min_value=0.0)
            original_price = st.number_input("Original Price (optional, for sale badge)", min_value=0.0, value=0.0)
            category = st.selectbox("Category", CATEGORIES)
            stock = st.number_input("Stock", min_value=0, value=10)
        with col2:
            desc = st.text_area("Description")
            yt_url = st.text_input("YouTube Link")
            active = st.checkbox("Active", value=True)

        st.markdown("---")
        files = st.file_uploader("Upload Images (Max 5)", type=['png', 'jpg'], accept_multiple_files=True)

        if st.button("💾 Save Product", type="primary"):
            if name and price > 0:
                prod = {"name": name, "description": desc, "price": float(price),
                        "category": category, "stock": int(stock), "youtube_url": yt_url,
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
                                st.warning("⚠️ Saved without sale price — add an 'original_price' "
                                           "numeric column in Supabase to enable SALE badges.")
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
                    st.success(f"✅ '{name}' Added!")
                    st.rerun()
                except Exception as e:
                    st.error("❌ Failed to save product. Real error below 👇")
                    st.exception(e)
                    if pid:
                        st.warning(f"Note: a product row (id={pid}) may have been created "
                                   f"before this failed — check your Supabase 'products' table.")
            else:
                st.warning("⚠️ Please fill Product Name and a Price greater than 0.")

    with tab2:
        orders = supabase_admin.table("orders").select("*").order("created_at", desc=True).limit(20).execute()
        if orders.data: st.dataframe(pd.DataFrame(orders.data), use_container_width=True)
        else: st.info("No orders yet.")

# --- CUSTOMER STORE ---
def customer_store():
    try:
        st.image("store logo.png", use_container_width=True)
    except Exception:
        st.markdown("""
        <div class="sk-hero">
            <h1>🛍️ SK Store</h1>
            <p>Premium Quality Marketplace — Fast Delivery Across Pakistan</p>
        </div>
        """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    search = c1.text_input("🔍 Search products...", key="search", label_visibility="collapsed",
                            placeholder="🔍 Search products...")
    cat_filter = c2.selectbox("Category", ["All"] + CATEGORIES, label_visibility="collapsed")

    st.write("")

    q = supabase_public.table("products").select("*").eq("is_active", True)
    if cat_filter != "All": q = q.eq("category", cat_filter)
    if search: q = q.ilike("name", f"%{search}%")
    products = q.execute().data

    if not products:
        st.info("No products found.")
        return

    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i % 3]:
            with st.container(border=True):
                if p.get('images'): st.image(p['images'][0], use_container_width=True)
                else: st.image("https://via.placeholder.com/300x200?text=SK+Store", use_container_width=True)

                st.markdown(f"**{p['name']}**")
                st.markdown(f'<div class="sk-stock">📂 {p.get("category")} &nbsp;|&nbsp; 📦 {p.get("stock")} left</div>',
                            unsafe_allow_html=True)
                price_block(p)

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("View", key=f"v_{p['id']}", use_container_width=True):
                        st.session_state.selected_product = p; st.session_state.page = 'detail'; st.rerun()
                with bc2:
                    if st.button("Add to cart", key=f"a_{p['id']}", type="primary", use_container_width=True):
                        st.session_state.cart.append(p); st.toast("Added!", icon="🛒")

    st.markdown("""
    <div class="sk-footer">
        Bringing happiness to customers with quality, original products.<br>
        <b>📍 Pakistan</b> &nbsp;|&nbsp; ✉️ support@skstore.pk
    </div>
    """, unsafe_allow_html=True)

# --- PRODUCT DETAIL ---
def product_detail():
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
            st.session_state.cart.append(p); st.success("Added!"); st.rerun()

# --- CART SIDEBAR ---
def show_cart():
    with st.sidebar:
        st.header("🛒 Cart")
        if not st.session_state.cart:
            st.write("Empty cart")
            return

        total = sum(i['price'] for i in st.session_state.cart)
        for i, item in enumerate(st.session_state.cart):
            cx, cy = st.columns([3, 1])
            cx.write(f"{item['name']}"); cx.caption(f"Rs. {item['price']:,.2f}")
            if cy.button("×", key=f"r_{i}"): st.session_state.cart.pop(i); st.rerun()

        st.divider(); st.markdown(f"### Total: Rs. {total:,.2f}")

        with st.form("co"):
            nm = st.text_input("Name *")
            em = st.text_input("Email (for order confirmation)")
            ph = st.text_input("Phone *")
            ad = st.text_area("Address *")
            if st.form_submit_button("Checkout ✅", type="primary"):
                if nm and ph and ad:
                    items_payload = [{"name": x['name'], "price": x['price']} for x in st.session_state.cart]
                    od = {"customer_name": nm, "email": em or None, "phone": ph, "address": ad,
                          "items": items_payload, "total_amount": total, "status": "Pending"}
                    try:
                        # Uses the ADMIN (service_role) client so this never fails on
                        # Row Level Security, regardless of anon-key policy config.
                        res = supabase_admin.table("orders").insert(od).execute()
                        order_id = res.data[0]['id']

                        ok, msg = send_order_emails(order_id, nm, em, ph, ad, items_payload, total)
                        if not ok:
                            st.warning(f"Order placed, but email notification failed: {msg}")

                        st.success("Order Placed! 🎉 A confirmation has been sent.")
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        st.error("❌ Failed to place order. Real error below 👇")
                        st.exception(e)
                else:
                    st.warning("⚠️ Please fill Name, Phone and Address.")

# --- MAIN ROUTER ---
show_cart()
nav = st.sidebar.radio("Menu", ["🏠 Home", "🔐 Admin"], index=0)
if nav == "🔐 Admin": admin_panel()
elif st.session_state.page == 'detail': product_detail()
else: customer_store()
