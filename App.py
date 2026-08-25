import streamlit as st
from supabase import create_client, Client
import pandas as pd

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

    /* --- Hero banner --- */
    .sk-hero {
        background: linear-gradient(135deg,#111 0%,#333 100%);
        border-radius: 16px; padding: 34px 30px; margin-bottom: 22px;
        color: white; text-align: center;
    }
    .sk-hero h1 { color: white; margin-bottom: 4px; font-size: 2.1rem; }
    .sk-hero p { color: #ddd; margin: 0; font-size: 0.95rem; }

    /* --- Category pills --- */
    div[data-testid="stRadio"] > div { flex-wrap: wrap; gap: 8px; }
    div[data-testid="stRadio"] label {
        background: white; border: 1px solid #e2e2e2; border-radius: 999px;
        padding: 6px 16px !important; margin: 0 !important; font-size: 0.85rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    /* --- Product cards --- */
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

    /* --- Buttons --- */
    button[kind="primary"] {
        background-color: #000 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600; border: none !important;
    }
    button[kind="primary"]:hover { background-color: #222 !important; }
    button[kind="secondary"] {
        background-color: transparent !important; color: #333 !important;
        border: 1px solid #ddd !important; border-radius: 8px !important;
    }

    /* --- Footer --- */
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
    st.error("⚠️ Secrets missing! Configure in Streamlit Cloud Settings > Secrets.")
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
    """Renders a ToyZone-style price row: sale badge + old/new price if a discount exists."""
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
                        except Exception as e:
                            # Fallback: 'original_price' column probably doesn't exist yet.
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
            nm = st.text_input("Name *"); ph = st.text_input("Phone *"); ad = st.text_area("Address *")
            if st.form_submit_button("Checkout ✅", type="primary"):
                if nm and ph and ad:
                    od = {"customer_name": nm, "phone": ph, "address": ad,
                          "items": [{"name": x['name'], "price": x['price']} for x in st.session_state.cart],
                          "total_amount": total, "status": "Pending"}
                    try:
                        supabase_public.table("orders").insert(od).execute()
                        st.success("Order Placed! 🎉"); st.session_state.cart = []; st.rerun()
                    except Exception as e:
                        st.error(str(e))

# --- MAIN ROUTER ---
show_cart()
nav = st.sidebar.radio("Menu", ["🏠 Home", "🔐 Admin"], index=0)
if nav == "🔐 Admin": admin_panel()
elif st.session_state.page == 'detail': product_detail()
else: customer_store()
