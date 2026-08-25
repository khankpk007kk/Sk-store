import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- CUSTOM CSS FOR SK STORE EU LOOK ---
st.markdown("""
<style>
    /* Global Styles */
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #1a1a1a; }
    
    /* Sticky Header */
    header[data-testid="stHeader"] { 
        background-color: white; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        position: sticky; top: 0; z-index: 100;
    }
    
    /* Product Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: white; border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); transition: transform 0.2s;
        border: none !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    /* Buttons */
    button[kind="primary"] {
        background-color: #000 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600; border: none !important;
    }
    button[kind="secondary"] {
        background-color: transparent !important; color: #333 !important;
        border: 1px solid #ddd !important; border-radius: 8px !important;
    }
    
    /* Hide Streamlit Footer/Menu for Clean Look */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .viewerBadge_container__1QSob { display: none; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
st.set_page_config(page_title="SK Store", page_icon="🛍️", layout="wide")

try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    SUPABASE_ADMIN_KEY = st.secrets["supabase"]["admin_key"]
except KeyError:
    st.error("⚠️ Secrets missing! Please configure in Streamlit Cloud settings.")
    st.stop()

supabase_public = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_ADMIN_KEY)

if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = 'home'

# --- HELPER FUNCTIONS ---
def get_youtube_embed(url):
    if not url or ('youtube.com' not in url and 'youtu.be' not in url): return None
    video_id = ""
    if 'youtu.be/' in url: video_id = url.split('youtu.be/')[1].split('?')[0]
    elif 'v=' in url: video_id = url.split('v=')[1].split('&')[0]
    return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&rel=0" if video_id else None

# --- ADMIN PANEL ---
def admin_panel():
    st.title("🔐 Admin Dashboard")
    tab1, tab2 = st.tabs(["➕ Add Product", "📦 Orders"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Product Name *")
            price = st.number_input("Price (PKR) *", min_value=0.0)
            category = st.selectbox("Category", ["Electronics", "Fashion", "Accessories", "Home"])
            stock = st.number_input("Stock", min_value=0, value=10)
        with col2:
            desc = st.text_area("Description")
            yt_url = st.text_input("YouTube Link")
            active = st.checkbox("Active", value=True)
        
        st.markdown("---")
        files = st.file_uploader("Upload Images (Max 5)", type=['png','jpg'], accept_multiple_files=True)
        
        if st.button("💾 Save Product", type="primary"):
            if name and price > 0:
                with st.spinner("Saving..."):
                    prod = {"name": name, "description": desc, "price": float(price), 
                            "category": category, "stock": int(stock), "youtube_url": yt_url, 
                            "is_active": active, "images": []}
                    res = supabase_admin.table("products").insert(prod).execute()
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

    with tab2:
        orders = supabase_admin.table("orders").select("*").order("created_at", desc=True).limit(20).execute()
        if orders.data: st.dataframe(pd.DataFrame(orders.data), use_container_width=True)
        else: st.info("No orders yet.")

# --- CUSTOMER STORE ---
def customer_store():
    # Hero Section
    try: st.image("store logo.png", use_container_width=True)
    except: st.title("Welcome to SK Store"); st.write("Premium Quality Marketplace")
    
    st.markdown("---")
    
    # Search & Filter Bar
    c1, c2 = st.columns([3, 1])
    search = c1.text_input("🔍 Search products...", key="search")
    cat_filter = c2.selectbox("Category", ["All", "Electronics", "Fashion", "Accessories", "Home"])
    
    # Fetch Products
    q = supabase_public.table("products").select("*").eq("is_active", True)
    if cat_filter != "All": q = q.eq("category", cat_filter)
    if search: q = q.ilike("name", f"%{search}%")
    products = q.execute().data
    
    if not products: st.info("No products found."); return
    
    # Product Grid
    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i % 3]:
            with st.container():  # Uses CSS class defined above
                if p.get('images'): st.image(p['images'][0], use_container_width=True)
                else: st.image("https://via.placeholder.com/300x200?text=SK+Store", use_container_width=True)
                
                st.markdown(f"### {p['name']}")
                st.caption(f"📂 {p.get('category')} | 📦 {p.get('stock')} left")
                st.markdown(f"**Rs. {p['price']:,.2f}**")
                
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("View", key=f"v_{p['id']}"):
                        st.session_state.selected_product = p; st.session_state.page = 'detail'; st.rerun()
                with bc2:
                    if st.button("Add ", key=f"a_{p['id']}"):
                        st.session_state.cart.append(p); st.toast("Added!", icon="")

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
                for t, img in enumerate(thumbs):
                    with img:
                        if st.button(f"{t+1}", key=f"th_{t}"): st.session_state.img_idx = t; st.rerun()
    
    with c2:
        st.title(p['name'])
        st.markdown(f"## Rs. {p['price']:,.2f}")
        st.write(p.get('description'))
        
        if p.get('youtube_url'):
            embed = get_youtube_embed(p['youtube_url'])
            if embed:
                st.components.v1.html(f'<iframe width="100%" height="315" src="{embed}" frameborder="0" allowfullscreen></iframe>', height=350)
        
        if st.button("🛒 Add to Cart", type="primary", use_container_width=True):
            st.session_state.cart.append(p); st.success("Added!"); st.rerun()

# --- CART SIDEBAR ---
def show_cart():
    with st.sidebar:
        st.header("🛒 Cart")
        if not st.session_state.cart: st.write("Empty cart "); return
        
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
                    except Exception as e: st.error(str(e))

# --- MAIN ROUTER ---
show_cart()
nav = st.sidebar.radio("Menu", ["🏠 Home", "🔐 Admin"], index=0)
if nav == "🔐 Admin": admin_panel()
elif st.session_state.page == 'detail': product_detail()
else: customer_store()                        "stock": int(stock),
                        "youtube_url": youtube_url,
                        "is_active": is_active,
                        "images": []
                    }
                    
                    response = supabase_admin.table("products").insert(product_data).execute()
                    new_product = response.data[0]
                    product_id = new_product['id']
                    
                    # Ab images upload karein
                    image_urls = []
                    if uploaded_files:
                        for i, file in enumerate(uploaded_files[:5]): # Max 5 images
                            url = upload_image_to_supabase(file, product_id)
                            if url:
                                image_urls.append(url)
                    
                    # Images array update karein
                    supabase_admin.table("products").update({
                        "images": image_urls
                    }).eq("id", product_id).execute()
                    
                    st.success(f"✅ '{name}' successfully add ho gaya!")
                    st.rerun()
    
    with tab2:
        st.subheader("Recent Orders")
        try:
            orders = supabase_admin.table("orders").select("*").order("created_at", desc=True).limit(20).execute()
            if orders.data:
                df = pd.DataFrame(orders.data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Abhi koi orders nahi hain.")
        except Exception as e:
            st.error(f"Orders load error: {e}")

# --- CUSTOMER STORE PAGE ---
def customer_store():
    # Hero Section with Logo
    try:
        st.image("store logo.png", use_container_width=True)
    except FileNotFoundError:
        st.title("🛍️ Welcome to SK Store")
        st.write("Premium Quality Products at Best Prices!")
    
    st.markdown("---")
    
    # Search & Filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search products...", key="search")
    with col2:
        category_filter = st.selectbox("Filter by Category", ["All", "Electronics", "Fashion", "Accessories", "Home", "Other"])
    
    # Fetch Products
    query = supabase_public.table("products").select("*").eq("is_active", True)
    if category_filter != "All":
        query = query.eq("category", category_filter)
    if search:
        query = query.ilike("name", f"%{search}%")
    
    response = query.execute()
    products = response.data
    
    if not products:
        st.info("Koi products nahi mile. Admin panel se add karein.")
        return
    
    # Product Grid
    cols = st.columns(3)
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            with st.container(border=True):
                # Main Image
                if product.get('images') and len(product['images']) > 0:
                    st.image(product['images'][0], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                
                st.markdown(f"### {product['name']}")
                st.caption(f"📂 {product.get('category', 'N/A')}")
                st.markdown(f"** Rs. {product['price']:,.2f}**")
                
                # YouTube Video Preview (Small)
                if product.get('youtube_url'):
                    embed = get_youtube_embed(product['youtube_url'])
                    if embed:
                        st.video(embed)
                
                # Buttons
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️ View Details", key=f"view_{product['id']}"):
                        st.session_state.selected_product = product
                        st.session_state.page = 'detail'
                        st.rerun()
                with c2:
                    if st.button("🛒 Add to Cart", key=f"cart_{product['id']}"):
                        st.session_state.cart.append(product)
                        st.toast(f"✅ {product['name']} added!", icon="")

# --- PRODUCT DETAIL PAGE ---
def product_detail():
    product = st.session_state.get('selected_product')
    if not product:
        st.session_state.page = 'home'
        st.rerun()
        return
    
    st.button("← Back to Store", on_click=lambda: setattr(st.session_state, 'page', 'home'))
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Image Gallery
        images = product.get('images', [])
        if images:
            main_img = st.session_state.get('main_img_idx', 0)
            st.image(images[main_img], use_container_width=True)
            
            if len(images) > 1:
                thumbs = st.columns(min(len(images), 5))
                for i, thumb in enumerate(thumbs):
                    with thumb:
                        if st.button(f"Img {i+1}", key=f"thumb_{i}"):
                            st.session_state.main_img_idx = i
                            st.rerun()
        else:
            st.image("https://via.placeholder.com/500x400?text=No+Image", use_container_width=True)
    
    with col2:
        st.title(product['name'])
        st.markdown(f"## 💰 Rs. {product['price']:,.2f}")
        st.write(product.get('description', 'No description available.'))
        st.badge(f"📦 Stock: {product.get('stock', 0)}", color="green" if product.get('stock', 0) > 0 else "red")
        
        # YouTube Full Player
        if product.get('youtube_url'):
            embed = get_youtube_embed(product['youtube_url'])
            if embed:
                st.markdown("### 🎥 Product Video")
                st.components.v1.html(
                    f'<iframe width="100%" height="315" src="{embed}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>',
                    height=350
                )
        
        st.divider()
        if st.button("🛒 Add to Cart", type="primary", use_container_width=True):
            st.session_state.cart.append(product)
            st.success("Added to cart!")

# --- CART SIDEBAR ---
def show_cart_sidebar():
    with st.sidebar:
        st.header("🛒 Your Cart")
        
        if not st.session_state.cart:
            st.write("Cart is empty 😢")
        else:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"{item['name']}")
                    st.caption(f"Rs. {item['price']:,.2f}")
                with col_b:
                    if st.button("", key=f"rm_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
                total += item['price']
            
            st.divider()
            st.markdown(f"### Total: Rs. {total:,.2f}")
            
            # Checkout Form
            with st.form("checkout"):
                st.write("#### Shipping Details")
                cname = st.text_input("Full Name *")
                cphone = st.text_input("Phone *")
                caddr = st.text_area("Address *")
                
                if st.form_submit_button("Place Order ✅", type="primary"):
                    if cname and cphone and caddr:
                        order_data = {
                            "customer_name": cname,
                            "phone": cphone,
                            "address": caddr,
                            "items": [{"name": p['name'], "price": p['price']} for p in st.session_state.cart],
                            "total_amount": total,
                            "status": "Pending"
                        }
                        try:
                            supabase_public.table("orders").insert(order_data).execute()
                            st.success("🎉 Order Placed!")
                            st.session_state.cart = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"Order failed: {e}")
                    else:
                        st.warning("Please fill all fields!")

# --- MAIN APP ROUTER ---
show_cart_sidebar()

# Navigation
nav = st.sidebar.radio("Navigate", ["🏠 Home", " Admin"], index=0)

if nav == "🔐 Admin":
    admin_panel()
elif st.session_state.page == 'detail':
    product_detail()
else:
    customer_store()
