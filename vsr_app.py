import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import io
from fpdf import FPDF
import os
import base64
import hashlib
import shutil
from urllib.parse import quote 
from cryptography.fernet import Fernet 
from PIL import Image, ImageDraw, ImageFont 
import socket 
import qrcode 

# ==========================================
# 1. CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="VSR Threads", layout="wide", page_icon="🧵")

# SECURITY KEY
SYSTEM_KEY = b'wJ-7x9Xo2yV_8eZ4p1qQ3kL5n0mR6tA8bC9dE2fG3hI=' 
cipher = Fernet(SYSTEM_KEY)

# CONSTANTS
ALL_PAGES = [
    "Dashboard", "Sales & Billing", "Purchases", "Expenses", 
    "Inventory Items", "Customers", "Staff Work", "Reports", 
    "Print Stickers", "Password Manager", "Data Inspector", "Settings"
]

# HELPER: Load Image
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# HELPER: QR & Network
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def show_connect_qr():
    ip = get_local_ip()
    port = 8501
    url = f"http://{ip}:{port}"
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 Connect Mobile/iPad")
    try:
        qr = qrcode.make(url)
        st.sidebar.image(qr.get_image(), width=150)
    except:
        qr = qrcode.make(url)
        st.sidebar.image(qr, width=150)
    st.sidebar.caption(f"Scan or type: **{url}**")

# CUSTOM CSS
st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #F0F4F9; border-right: none; }
    div.stButton > button {
        width: 100%; text-align: left; display: flex; justify-content: flex-start;
        padding-left: 20px; font-family: 'Segoe UI', sans-serif; font-weight: 500;
        font-size: 14px; height: 40px; border-radius: 20px; border: none;
        transition: background-color 0.2s; color: #444746; background-color: transparent;
    }
    div.stButton > button:hover { background-color: #E1E5EA; color: #1E3A8A; }
    div.stButton > button[kind="primary"] {
        background-color: #C2E7FF !important; color: #001D35 !important; font-weight: 600;
    }
    thead tr th { background-color: #EFF6FF !important; color: #1E3A8A !important; }
    .top-banner {
        background-color: #ffffff; padding: 15px 0px; margin-bottom: 20px;
        border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;
    }
    .top-banner h1 { margin: 0; font-size: 26px; font-weight: 700; color: #1E3A8A; }
    .top-banner p { margin: 0; font-size: 14px; color: #64748B; }
    div[data-testid="metric-container"] { 
        background-color: #F8FAFC; border: 1px solid #E2E8F0; 
        padding: 15px; border-radius: 12px; box-shadow: none; 
    }
</style>
""", unsafe_allow_html=True)

# LOGIN BG
if os.path.exists("logo.png") and 'auth' not in st.session_state:
    bin_str = get_base64_of_bin_file("logo.png")
    st.markdown(f"""<style>.stApp {{ background-image: linear-gradient(rgba(255,255,255,0.9), rgba(255,255,255,0.9)), url("data:image/png;base64,{bin_str}"); background-size: 50%; background-position: center; background-repeat: no-repeat; background-attachment: fixed; }}</style>""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE SETUP
# ==========================================
DB_FILE = 'vsr_threads_final_v86.db' # Version 86

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS master_names (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, opening_stock INTEGER, cost_price REAL, sell_price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, item_id INTEGER, qty_added INTEGER, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, opening_due REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer_id INTEGER, sub_total REAL, cgst_percent REAL, sgst_percent REAL, cgst_amount REAL, sgst_amount REAL, grand_total REAL, paid_amount REAL, notes TEXT, walkin_phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sale_items (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, item_id INTEGER, qty INTEGER, price_per_unit REAL, cost_per_unit REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT, bags REAL, kg_per_bag REAL, total_kg REAL, price_per_kg REAL, total_amount REAL, vendor_name TEXT, vendor_contact TEXT, is_gst INTEGER, cgst_percent REAL, sgst_percent REAL, bill_file BLOB, bill_filename TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, description TEXT, amount REAL, staff_entry_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS staff_work (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, staff_name TEXT, kg_provided REAL, total_salary REAL, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS staff_work_items (id INTEGER PRIMARY KEY AUTOINCREMENT, work_id INTEGER, item_id INTEGER, grams REAL, qty_produced INTEGER, rate REAL, amount REAL, item_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer_id INTEGER, sale_id INTEGER, amount REAL, note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS app_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, permissions TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pm_vault (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, website TEXT, login_id TEXT, enc_password TEXT, updated_at TEXT)''')

    try: c.execute("ALTER TABLE staff_work_items ADD COLUMN item_name TEXT")
    except: pass
    try: c.execute("ALTER TABLE sales ADD COLUMN walkin_phone TEXT")
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN vendor_name TEXT"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN vendor_contact TEXT"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN is_gst INTEGER DEFAULT 0"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN cgst_percent REAL DEFAULT 0"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN sgst_percent REAL DEFAULT 0"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN bill_file BLOB"); 
    except: pass
    try: c.execute("ALTER TABLE purchases ADD COLUMN bill_filename TEXT"); 
    except: pass

    defaults = {'gst_number': '', 'business_address': 'Chennai, Tamil Nadu', 'business_contact': '', 'cgst_percent': '0.0', 'sgst_percent': '0.0', 'expense_categories': 'Rent,Electricity,Salary,Transport,Misc'}
    for k, v in defaults.items(): c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    
    admin_check = c.execute("SELECT * FROM app_users WHERE username='admin'").fetchone()
    if not admin_check:
        all_perms = ",".join(ALL_PAGES)
        c.execute("INSERT INTO app_users (username, password_hash, role, permissions) VALUES (?,?,?,?)", ('admin', hash_pass('admin123'), 'Admin', all_perms))
    conn.commit(); conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute(query, params)
    if fetch: data = c.fetchall(); conn.close(); return data
    lid = c.lastrowid; conn.commit(); conn.close(); return lid

def get_setting(key):
    res = run_query("SELECT value FROM settings WHERE key=?", (key,), fetch=True)
    return res[0]['value'] if res else ""

def update_setting(key, value):
    run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))

# --- HELPERS ---
def encrypt_val(text): return cipher.encrypt(text.encode()).decode()
def decrypt_val(enc_text): return cipher.decrypt(enc_text.encode()).decode()

def get_stock(item_id, opening):
    sold = run_query("SELECT SUM(qty) FROM sale_items WHERE item_id=?", (item_id,), fetch=True)[0][0] or 0
    added = run_query("SELECT SUM(qty_added) FROM stock_logs WHERE item_id=?", (item_id,), fetch=True)[0][0] or 0
    return opening + added - sold

def get_customer_due(cust_id, opening):
    inv = run_query("SELECT SUM(grand_total) FROM sales WHERE customer_id=?", (cust_id,), fetch=True)[0][0] or 0
    pay = run_query("SELECT SUM(amount) FROM payments WHERE customer_id=?", (cust_id,), fetch=True)[0][0] or 0
    return opening + inv - pay

# --- PDF GENERATORS ---
def create_pdf(sale, items, customer, gst, addr, phone):
    pdf = FPDF(); pdf.add_page()
    logo_path = "logo.png"
    has_logo = os.path.exists(logo_path)
    if has_logo:
        pdf.image(logo_path, x=60, y=100, w=90); pdf.image(logo_path, x=10, y=8, w=25); pdf.set_xy(10, 35)
    else: pdf.set_y(10)

    pdf.set_font('Arial', 'B', 20); pdf.set_text_color(30, 58, 138)
    if has_logo: pdf.text(38, 18, 'VSR Threads')
    else: pdf.cell(0, 10, 'VSR Threads', 0, 1)

    pdf.set_font('Arial', '', 9); pdf.set_text_color(100, 100, 100)
    if has_logo: pdf.set_xy(38, 20)
    pdf.cell(0, 5, addr, 0, 1)
    if has_logo: pdf.set_x(38)
    pdf.cell(0, 5, f"Phone: {phone}", 0, 1)
    if gst: 
        if has_logo: pdf.set_x(38)
        pdf.cell(0, 5, f"GSTIN: {gst}", 0, 1)
    
    pdf.ln(10); 
    if has_logo: pdf.ln(5)
    
    pdf.set_text_color(0); pdf.set_font('Arial', 'B', 11)
    pdf.cell(100, 6, "Bill To:", 0, 0); pdf.cell(0, 6, "Invoice Details:", 0, 1)
    pdf.set_font('Arial', '', 10)
    cname = customer['name'] if customer else "Walk-in"
    cphone = customer['phone'] if customer else ""
    if not customer and sale.get('walkin_phone'): cphone = sale['walkin_phone']

    pdf.cell(100, 5, cname, 0, 0); pdf.cell(0, 5, f"Invoice #: {sale['id']}", 0, 1)
    pdf.cell(100, 5, cphone, 0, 0); pdf.cell(0, 5, f"Date: {sale['date']}", 0, 1)
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 10)
    
    pdf.cell(80, 8, "Item", 1, 0, 'L', True); pdf.cell(30, 8, "Color", 1, 0, 'C', True)
    pdf.cell(20, 8, "Qty", 1, 0, 'C', True); pdf.cell(30, 8, "Price (Inc)", 1, 0, 'R', True); pdf.cell(30, 8, "Total", 1, 1, 'R', True)
    pdf.set_font('Arial', '', 10)
    for i in items:
        tot = i['qty']*i['price_per_unit']
        try: i_name = str(i['name']).encode('latin-1', 'ignore').decode('latin-1')
        except: i_name = "Item"
        try: i_color = str(i['color']).encode('latin-1', 'ignore').decode('latin-1')
        except: i_color = "-"
        
        pdf.cell(80, 8, i_name, 1); pdf.cell(30, 8, i_color, 1, 0, 'C')
        pdf.cell(20, 8, str(i['qty']), 1, 0, 'C'); pdf.cell(30, 8, f"{i['price_per_unit']:.2f}", 1, 0, 'R')
        pdf.cell(30, 8, f"{tot:.2f}", 1, 1, 'R')
    pdf.ln(5)
    def tr(lbl, val, bold=False):
        pdf.set_font('Arial', 'B' if bold else '', 10)
        pdf.cell(130, 7, "", 0); pdf.cell(30, 7, lbl, 0, 0, 'R'); pdf.cell(30, 7, f"{val:.2f}", 1, 1, 'R')
    
    tr("Taxable Amt:", sale['sub_total'])
    if sale['cgst_amount'] > 0: tr(f"CGST:", sale['cgst_amount']); tr(f"SGST:", sale['sgst_amount'])
    tr("Grand Total:", sale['grand_total'], True); tr("Paid:", sale['paid_amount'])
    due = sale['grand_total'] - sale['paid_amount']
    if due > 0.01: tr("Balance Due:", due, True)
    
    temp_inv = f"temp_inv_{sale['id']}.pdf"
    pdf.output(temp_inv, "F")
    with open(temp_inv, "rb") as f:
        pdf_bytes = f.read()
    try: os.remove(temp_inv)
    except: pass
    
    return pdf_bytes

def create_pnl_pdf(d1, d2, rev, cogs, exp_data, net):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "Profit & Loss Statement", 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Period: {d1.strftime('%d-%m-%Y')} to {d2.strftime('%d-%m-%Y')}", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, "Description", 1); pdf.cell(50, 10, "Amount", 1, 1, 'R')
    pdf.set_font('Arial', '', 12)
    pdf.cell(100, 10, "Total Sales (Revenue)", 1); pdf.cell(50, 10, f"{rev:,.2f}", 1, 1, 'R')
    pdf.cell(100, 10, "Cost of Goods Sold (COGS)", 1); pdf.cell(50, 10, f"-{cogs:,.2f}", 1, 1, 'R')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, "Gross Profit", 1); pdf.cell(50, 10, f"{rev-cogs:,.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.cell(0, 10, "Expenses Breakdown:", 0, 1)
    pdf.set_font('Arial', '', 11)
    tot_exp = 0
    for e in exp_data:
        pdf.cell(100, 8, e['category'], 1); pdf.cell(50, 8, f"{e['total']:,.2f}", 1, 1, 'R')
        tot_exp += e['total']
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, "Total Expenses", 1); pdf.cell(50, 10, f"-{tot_exp:,.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_fill_color(220, 255, 220) 
    pdf.cell(100, 12, "NET PROFIT", 1, 0, 'L', True); pdf.cell(50, 12, f"{net:,.2f}", 1, 1, 'R', True)
    temp_file = "temp_pnl.pdf"
    pdf.output(temp_file, "F")
    with open(temp_file, "rb") as f: bytes_data = f.read()
    try: os.remove(temp_file)
    except: pass
    return bytes_data

# --- IMAGE STICKER GENERATOR ---
def create_sticker_image(thickness_val, title_text, cell_number):
    width = 1086; height = 744
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    border_color = (30, 58, 138)
    draw.rectangle([10, 10, width-10, height-10], outline=border_color, width=15)
    
    header_color = (239, 246, 255)
    draw.rectangle([25, 25, width-25, 180], fill=header_color)
    
    title_img_path = "title.png"
    title_drawn = False
    
    if os.path.exists(title_img_path):
        try:
            t_img = Image.open(title_img_path).convert("RGBA")
            max_h = 120
            h_ratio = (max_h / float(t_img.size[1]))
            w_size = int((float(t_img.size[0]) * float(h_ratio)))
            t_img = t_img.resize((w_size, max_h), Image.Resampling.LANCZOS)
            tx = int((width - w_size) / 2)
            ty = int(25 + (155 - max_h) / 2)
            bg = Image.new('RGBA', img.size, (255, 255, 255, 0))
            bg.paste(t_img, (tx, ty), mask=t_img)
            img.paste(bg, (0,0), mask=bg)
            title_drawn = True
        except: pass

    if not title_drawn:
        font_path = None
        possible = ["Nirmala.ttf", "tamil.ttf", "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/Latha.ttf", "arial.ttf"]
        for p in possible:
            if os.path.exists(p):
                font_path = p; break
        try:
            if font_path: title_font = ImageFont.truetype(font_path, 80)
            else: title_font = ImageFont.load_default()
        except: title_font = ImageFont.load_default()
        
        try:
            text_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            text_x = (width - text_w) / 2
            text_y = int(25 + (155 - text_h) / 2) - 15
            draw.text((text_x, text_y), title_text, font=title_font, fill=(0,0,0))
        except:
            draw.text((100, 75), "Nool Kandu", fill=(0,0,0))

    if os.path.exists("logo.png"):
        try:
            logo = Image.open("logo.png").convert("RGBA")
            header_end_y = 205; footer_start_y = height - 120 
            available_h = footer_start_y - header_end_y
            target_h = int(available_h * 0.8) 
            wpercent = (target_h / float(logo.size[1]))
            target_w = int((float(logo.size[0]) * float(wpercent)))
            if target_w > 900:
                target_w = 900
                wpercent = (target_w / float(logo.size[0]))
                target_h = int((float(logo.size[1]) * float(wpercent)))
            logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
            lx = int((width - target_w) / 2)
            ly = int(header_end_y + (available_h - target_h) / 2)
            bg = Image.new('RGBA', img.size, (255, 255, 255, 0))
            bg.paste(logo, (lx, ly), mask=logo)
            img.paste(bg, (0,0), mask=bg)
        except: pass

    try:
        num_font = ImageFont.truetype("arial.ttf", 450)
    except:
        num_font = ImageFont.load_default()
    
    num_text = str(thickness_val)
    try:
        num_bbox = draw.textbbox((0, 0), num_text, font=num_font)
        nw = num_bbox[2] - num_bbox[0]
        draw.text((width - nw - 50, height - 520), num_text, font=num_font, fill=(220, 38, 38))
    except:
        draw.text((width - 300, height - 400), num_text, fill=(220, 38, 38))

    try:
        cell_font = ImageFont.truetype("arial.ttf", 80)
    except:
        cell_font = ImageFont.load_default()
    
    cell_display_text = f"Cell: {cell_number}"
    draw.text((50, height - 120), cell_display_text, font=cell_font, fill=(0,0,0))
    return img

def generate_pdf_from_images(thickness_val, num_sheets, title_text, cell_text):
    master_img = create_sticker_image(thickness_val, title_text, cell_text)
    temp_img_path = "temp_sticker_master.png"
    master_img.save(temp_img_path)
    
    pdf = FPDF('L', 'mm', 'A4')
    pdf.set_auto_page_break(False)
    margin_x = 10; margin_y = 10
    sticker_w = 92; sticker_h = 63
    
    for _ in range(num_sheets):
        pdf.add_page()
        for i in range(3): 
            for j in range(3): 
                x = margin_x + (j * sticker_w)
                y = margin_y + (i * sticker_h)
                pdf.image(temp_img_path, x=x, y=y, w=sticker_w, h=sticker_h)
                
    out_file = "final_stickers.pdf"
    pdf.output(out_file, "F")
    
    with open(out_file, "rb") as f:
         pdf_bytes = f.read()

    # --- ADDED DOWNLOAD BUTTON LOGIC HERE ---
    
    try: os.remove(temp_img_path); os.remove(out_file)
    except: pass
    
    return pdf_bytes

# ==========================================
# 3. MAIN APP FLOW
# ==========================================
init_db()
if 'user' not in st.session_state: st.session_state.user = None
if 'menu_selection' not in st.session_state: st.session_state.menu_selection = "Dashboard"

if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            if os.path.exists("logo.png"): st.image("logo.png", width=120)
            st.markdown("<h2 style='text-align:center; color:#1E3A8A'>🔐 VSR Login</h2>", unsafe_allow_html=True)
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", type="primary", use_container_width=True, key="login_btn"):
                h = hash_pass(p)
                ud = run_query("SELECT * FROM app_users WHERE username=? AND password_hash=?", (u, h), fetch=True)
                if ud:
                    raw = ud[0]['permissions']; ups = raw.split(",") if raw else []
                    st.session_state.user = {"id": ud[0]['id'], "username": ud[0]['username'], "role": ud[0]['role'], "permissions": ups}
                    st.rerun()
                else: st.error("Invalid")
    st.stop()

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    else: st.markdown("<h2>VSR Threads</h2>", unsafe_allow_html=True)
    st.info(f"👤 {st.session_state.user['username']} ({st.session_state.user['role']})")
    
    if "Dashboard" in st.session_state.user['permissions']:
        if st.button("✨ Dashboard Home", type="primary" if st.session_state.menu_selection == "Dashboard" else "secondary"):
            st.session_state.menu_selection = "Dashboard"; st.rerun()
    
    st.markdown("###### Menu")
    icons = {"Sales & Billing": "🧾", "Purchases": "📦", "Expenses": "💸", "Inventory Items": "🧵", "Customers": "👥", "Staff Work": "👷", "Reports": "📊", "Print Stickers": "🖨️", "Password Manager": "🔐", "Data Inspector": "🔍", "Settings": "⚙️"}
    allowed = [p for p in ALL_PAGES if p in st.session_state.user['permissions'] and p != "Dashboard"]
    for p in allowed:
        bt = "primary" if st.session_state.menu_selection == p else "secondary"
        if st.button(f"{icons.get(p,'')}  {p}", type=bt):
            st.session_state.menu_selection = p; st.rerun()
    
    # QR Code at bottom
    show_connect_qr()

    st.markdown("---")
    if st.button("🚪 Logout"): st.session_state.user = None; st.rerun()

menu = st.session_state.menu_selection
st.markdown(f"""<div class="top-banner"><div><h1>VSR Threads</h1><p>{menu}</p></div><div style="color:#64748B;">{date.today().strftime("%d %B %Y")}</div></div>""", unsafe_allow_html=True)

if menu not in st.session_state.user['permissions']: st.error("⛔ Access Denied"); st.stop()

# ==========================================
# 4. PAGES
# ==========================================

if menu == "Dashboard":
    st.write("#### 📊 Financial Overview")
    c1, c2, c3 = st.columns(3)
    df = c1.date_input("From", None, key="dash_from"); dt = c2.date_input("To", None, key="dash_to")
    custs = run_query("SELECT id, name FROM customers", fetch=True)
    cmap = {c['name']: c['id'] for c in custs}; cmap["All Customers"] = None
    sc = c3.selectbox("Customer", list(cmap.keys()), index=len(cmap)-1, key="dash_cust"); cid = cmap[sc]

    p = []; wh = "WHERE 1=1"
    if df and dt: wh += " AND date BETWEEN ? AND ?"; p.extend([df, dt])
    if cid: wh += " AND customer_id=?"; p.append(cid)
    
    sales = run_query(f"SELECT SUM(grand_total) FROM sales {wh}", tuple(p), fetch=True)[0][0] or 0
    ids = [r[0] for r in run_query(f"SELECT id FROM sales {wh}", tuple(p), fetch=True)]
    cogs = 0
    if ids:
        ph = ",".join("?"*len(ids)); cogs = run_query(f"SELECT SUM(qty*cost_per_unit) FROM sale_items WHERE sale_id IN ({ph})", tuple(ids), fetch=True)[0][0] or 0
    exp = 0
    if cid is None:
        p2 = [df, dt] if df and dt else []; w2 = "WHERE date BETWEEN ? AND ?" if df and dt else ""
        exp = run_query(f"SELECT SUM(amount) FROM expenses {w2}", tuple(p2), fetch=True)[0][0] or 0
    
    taxable_sales = run_query(f"SELECT SUM(sub_total) FROM sales {wh}", tuple(p), fetch=True)[0][0] or 0
    
    all_op = run_query("SELECT SUM(opening_due) FROM customers", fetch=True)[0][0] or 0
    all_sales = run_query("SELECT SUM(grand_total) FROM sales", fetch=True)[0][0] or 0
    all_paid = run_query("SELECT SUM(amount) FROM payments", fetch=True)[0][0] or 0
    pending_payments = (all_op + all_sales) - all_paid

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Sales", f"₹{sales:,.0f}")
    c2.metric("Gross Profit", f"₹{taxable_sales-cogs:,.0f}")
    c3.metric("Expenses", f"₹{exp:,.0f}")
    c4.metric("Net Profit", f"₹{(taxable_sales-cogs)-exp:,.0f}")
    c5.metric("Pending Payments", f"₹{pending_payments:,.0f}")
    st.divider()

    st.write("#### ⚡ Daily Pulse")
    def day_stat(d):
        s = run_query("SELECT SUM(grand_total) FROM sales WHERE date=?", (d,), fetch=True)[0][0] or 0
        e = run_query("SELECT SUM(amount) FROM expenses WHERE date=?", (d,), fetch=True)[0][0] or 0
        return s, e
    ts, te = day_stat(date.today()); ys, ye = day_stat(date.today()-timedelta(days=1))
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Sales Today", f"₹{ts:,.0f}"); d2.metric("Expenses Today", f"₹{te:,.0f}")
    d3.metric("Sales Yesterday", f"₹{ys:,.0f}"); d4.metric("Expenses Yesterday", f"₹{ye:,.0f}")
    st.divider()

    st.write("#### 🧱 Purchases & Inventory")
    tp = run_query("SELECT SUM(bags), SUM(total_kg), SUM(total_amount) FROM purchases", fetch=True)[0]
    tbags = tp[0] or 0; tkg = tp[1] or 0; tamt = tp[2] or 0
    used_kg = run_query("SELECT SUM(kg_provided) FROM staff_work", fetch=True)[0][0] or 0
    rem_kg = tkg - used_kg
    items = run_query("SELECT * FROM items", fetch=True)
    total_qty = 0; total_val = 0
    if items:
        for i in items:
            curr_stock = get_stock(i['id'], i['opening_stock'])
            total_qty += curr_stock
            total_val += (curr_stock * i['cost_price'])
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Bags", tbags)
    m2.metric("Purchased Kg", f"{tkg:.2f}")
    m3.metric("Remaining Kg", f"{rem_kg:.2f}", delta_color="normal")
    m4.metric("Stock Qty", total_qty)
    m5.metric("Stock Value", f"₹{total_val:,.0f}")
    st.divider()
    
    cr = run_query(f"SELECT date, grand_total FROM sales {wh} ORDER BY date", tuple(p), fetch=True)
    c_data = {}
    for r in cr: c_data[r['date']] = c_data.get(r['date'], 0) + r['grand_total']
    if c_data: st.line_chart(pd.DataFrame(list(c_data.items()), columns=['Date','Sales']).set_index('Date'))

    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("⚠️ Low Stock (<=5)")
        low = []
        for i in items:
            cur = get_stock(i['id'], i['opening_stock'])
            if cur <= 5: low.append({"Item": f"{i['name']} {i['color']}", "Qty": cur})
        if low: st.dataframe(pd.DataFrame(low), hide_index=True, use_container_width=True)
        else: st.success("Stock Healthy")
    with c_r:
        st.subheader("💰 Pending Payments")
        custs = run_query("SELECT id, name, opening_due FROM customers", fetch=True)
        dues = []
        for c in custs:
            d = get_customer_due(c['id'], c['opening_due'])
            if d > 1: dues.append({"Customer": c['name'], "Due": f"₹{d:,.2f}"})
        if dues: st.dataframe(pd.DataFrame(dues), hide_index=True, use_container_width=True, column_config={"Due": st.column_config.NumberColumn(format="₹%.2f")})
        else: st.success("No Dues")

elif menu == "Sales & Billing":
    tabs = st.tabs(["New Invoice", "History"])
    with tabs[0]:
        if 'cart' not in st.session_state: st.session_state.cart = []
        c1, c2 = st.columns([2, 1])
        with c1: 
            st.subheader("Select Item")
            items = run_query("SELECT * FROM items", fetch=True)
            if items:
                i_map = {f"{i['name']} {i['color']}": i for i in items}
                sel_lbl = st.selectbox("Search Item", list(i_map.keys()), key="sales_item_sel"); sel_item = i_map[sel_lbl]
                cq, cb = st.columns([1, 1]); qty = cq.number_input("Qty", 1, key="sales_qty")
                price_in = cb.number_input("Selling Price (Per Unit)", 0.0, key="sales_price_in")
                if st.button("Add to Cart", key="sales_add") and price_in > 0:
                    st.session_state.cart.append({"id": sel_item['id'], "name": sel_item['name'], "color": sel_item['color'], "qty": qty, "price": price_in, "cost": sel_item['cost_price'], "total": qty*price_in})
            else: st.warning("No items found.")
        with c2:
            st.subheader("Billing")
            custs = run_query("SELECT id, name, phone FROM customers", fetch=True)
            cmap = {f"{c['name']}": c['id'] for c in custs}; cmap["Walk-in"] = None
            c_name = st.selectbox("Customer", list(cmap.keys()), key="sales_cust"); c_id = cmap[c_name]; d_inv = st.date_input("Date", date.today(), key="sales_date")
            
            walkin_mob = ""
            if c_name == "Walk-in":
                walkin_mob = st.text_input("Mobile No (Optional)", key="w_mob")

            if st.session_state.cart:
                df = pd.DataFrame(st.session_state.cart)
                st.dataframe(df[['name', 'qty', 'price', 'total']], hide_index=True, use_container_width=True, column_config={"total": st.column_config.NumberColumn("Total", format="₹%.2f"), "price": st.column_config.NumberColumn("Price", format="₹%.2f")})
                grand = df['total'].sum()
                cp = float(get_setting("cgst_percent")); sp = float(get_setting("sgst_percent")); tr = cp+sp
                taxable = grand / (1 + (tr/100)) if tr > 0 else grand
                st.markdown(f"### Total: ₹{grand:,.2f}"); st.caption(f"Taxable: ₹{taxable:,.2f}")
                paid = st.number_input("Paid", 0.0, value=grand, key="sales_paid"); note = st.text_input("Note", key="sales_note")
                if st.button("✅ Confirm Sale", type="primary", use_container_width=True, key="sales_confirm"):
                    sid = run_query("INSERT INTO sales (date, customer_id, sub_total, cgst_percent, sgst_percent, cgst_amount, sgst_amount, grand_total, paid_amount, notes, walkin_phone) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                              (d_inv, c_id, taxable, cp, sp, taxable*(cp/100), taxable*(sp/100), grand, paid, note, walkin_mob))
                    for x in st.session_state.cart: run_query("INSERT INTO sale_items (sale_id, item_id, qty, price_per_unit, cost_per_unit) VALUES (?,?,?,?,?)", (sid, x['id'], x['qty'], x['price'], x['cost']))
                    if paid > 0: run_query("INSERT INTO payments (date, customer_id, sale_id, amount, note) VALUES (?,?,?,?,?)", (d_inv, c_id, sid, paid, "Sale"))
                    st.session_state.cart = []; st.success("Saved!"); st.rerun()
                if st.button("Clear Cart", key="sales_clear"): st.session_state.cart = []; st.rerun()

    with tabs[1]:
        q_sales = '''SELECT s.id, s.date, c.name, s.grand_total, s.paid_amount, 
                     (s.grand_total - s.paid_amount) as balance, s.walkin_phone, c.phone as c_phone,
                     GROUP_CONCAT(i.name || ' (' || si.qty || ')', ', ') as items
                     FROM sales s 
                     LEFT JOIN customers c ON s.customer_id=c.id 
                     LEFT JOIN sale_items si ON s.id = si.sale_id
                     LEFT JOIN items i ON si.item_id = i.id
                     GROUP BY s.id ORDER BY s.id DESC'''
        sales = run_query(q_sales, fetch=True)
        if sales:
            s_data = []
            for r in sales:
                s_data.append({"ID": r['id'], "Date": r['date'], "Customer": r['name'], "Items": r['items'], "Total": r['grand_total'], "Paid": r['paid_amount'], "Balance": r['balance']})
            st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True, column_config={"Total": st.column_config.NumberColumn(format="₹%.2f"), "Paid": st.column_config.NumberColumn(format="₹%.2f"), "Balance": st.column_config.NumberColumn(format="₹%.2f")})
            
            sid = st.selectbox("Select Invoice", [r['id'] for r in sales], key="hist_sel")
            if sid:
                c1, c2 = st.columns([1.5, 1])
                inv = run_query("SELECT * FROM sales WHERE id=?", (sid,), fetch=True)[0]
                its = run_query("SELECT i.name, i.color, si.qty, si.price_per_unit FROM sale_items si JOIN items i ON si.item_id=i.id WHERE si.sale_id=?", (sid,), fetch=True)
                cdet = run_query("SELECT * FROM customers WHERE id=?", (inv['customer_id'],), fetch=True)[0] if inv['customer_id'] else None
                
                # GENERATE INVOICE
                if c1.button("🖨️ Generate Invoice for Print", type="primary", key=f"gen_{sid}"):
                    pdf_bytes = create_pdf(inv, its, cdet, get_setting('gst_number'), get_setting('business_address'), get_setting('business_contact'))
                    b64 = base64.b64encode(pdf_bytes).decode()
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="800"></iframe>', unsafe_allow_html=True)

                # WHATSAPP BUTTON LOGIC
                target_phone = inv['walkin_phone'] if not cdet else cdet['phone']
                if target_phone:
                    cname_str = cdet['name'] if cdet else "Customer"
                    msg = f"*🧾 INVOICE: #{inv['id']}*\n"
                    msg += f"📅 Date: {inv['date']}\n"
                    msg += f"👤 Customer: {cname_str}\n"
                    msg += "------------------------------\n"
                    msg += "*Item Details:*\n"
                    for item in its:
                         iname = item['name'] if 'name' in item.keys() else 'Item'
                         clr = item['color'] if 'color' in item.keys() else ''
                         tot_line = item['qty'] * item['price_per_unit']
                         msg += f"• {iname} {clr} (x{item['qty']}): ₹{tot_line:,.0f}\n"
                    msg += "------------------------------\n"
                    msg += f"*GRAND TOTAL: ₹{inv['grand_total']:,.0f}*\n"
                    msg += "------------------------------\n"
                    msg += "Thank you for shopping with VSR Threads! 🙏"
                    
                    encoded_msg = quote(msg)
                    wa_link = f"https://wa.me/91{target_phone}?text={encoded_msg}"
                    c2.link_button(f"💬 Open WhatsApp ({target_phone})", wa_link)
                    c2.caption("*Click to open WhatsApp web, then drag & drop the downloaded PDF.*")
                else:
                    c2.info("No phone number found for this invoice.")

                due = inv['grand_total'] - inv['paid_amount']
                if due > 0.01:
                    pay_now = c2.number_input(f"Receive Payment (Bal: ₹{due:.2f})", 0.0, value=float(due), key="pay_due_amt")
                    if c2.button("Update Payment", key="pay_due_btn"):
                        run_query("UPDATE sales SET paid_amount=? WHERE id=?", (inv['paid_amount']+pay_now, sid))
                        run_query("INSERT INTO payments (date, customer_id, sale_id, amount, note) VALUES (?,?,?,?,?)", (date.today(), inv['customer_id'], sid, pay_now, "Balance Recd"))
                        st.success("Updated!"); st.rerun()
                if st.button("Delete Invoice", key="del_inv"):
                    run_query("DELETE FROM sales WHERE id=?", (sid,)); run_query("DELETE FROM sale_items WHERE sale_id=?", (sid,)); run_query("DELETE FROM payments WHERE sale_id=?", (sid,))
                    st.warning("Deleted"); st.rerun()
        else: st.info("No sales history.")

elif menu == "Inventory Items":
    # ----------------------------------------------------
    # INVENTORY PAGE WITH FEATURES
    # ----------------------------------------------------
    
    # 1. METRICS DASHBOARD
    tot_items = run_query("SELECT COUNT(*) FROM items", fetch=True)[0][0] or 0
    tot_stock = run_query("SELECT SUM(CASE WHEN (opening_stock + (SELECT COALESCE(SUM(qty_added),0) FROM stock_logs WHERE item_id=items.id) - (SELECT COALESCE(SUM(qty),0) FROM sale_items WHERE item_id=items.id)) < 0 THEN 0 ELSE (opening_stock + (SELECT COALESCE(SUM(qty_added),0) FROM stock_logs WHERE item_id=items.id) - (SELECT COALESCE(SUM(qty),0) FROM sale_items WHERE item_id=items.id)) END) FROM items", fetch=True)[0][0] or 0
    # Approx Value logic
    tot_val = 0
    all_items = run_query("SELECT * FROM items", fetch=True)
    if all_items:
        for i in all_items:
            cur = get_stock(i['id'], i['opening_stock'])
            tot_val += (cur * i['cost_price'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Unique Items", tot_items)
    m2.metric("Total Stock Qty", tot_stock)
    m3.metric("Inventory Value (Cost)", f"₹{tot_val:,.0f}")
    st.divider()

    # 2. TABS
    inv_t1, inv_t2 = st.tabs(["📦 Manage Inventory", "📜 Stock History Log"])
    
    with inv_t1:
        # --- ADD / UPDATE SECTION ---
        with st.expander("➕ Add / Update Stock", expanded=False):
            c1, c2, c3 = st.columns(3)
            st_date = c1.date_input("Date", date.today(), key="stk_date")
            
            # Master Name Selection + Quick Add
            m_names = run_query("SELECT name FROM master_names", fetch=True)
            name_list = [m['name'] for m in m_names] if m_names else []
            
            # Layout for Name selection
            n_col, new_n_col = st.columns([2, 1])
            with n_col:
                n = st.selectbox("Item Name", name_list, key="inv_name") if name_list else None
            with new_n_col:
                # Mini-form to add name
                with st.popover("➕ New Name"):
                    new_m_name = st.text_input("Name")
                    if st.button("Add"):
                        try:
                            run_query("INSERT INTO master_names (name) VALUES (?)", (new_m_name,))
                            st.success("Added!")
                            st.rerun()
                        except: st.error("Exists")
            
            if not n and not name_list:
                st.warning("Please add an Item Name using the button above.")

            cl = c2.text_input("Color", key="inv_color")
            c4, c5 = st.columns(2)
            op = c4.number_input("Qty to Add", 1, key="inv_qty")
            cp = c5.number_input("Cost Price", 0.0, key="inv_cp")
            # Removed SP input

            if st.button("Save Stock", key="inv_save") and n:
                exist = run_query("SELECT id, opening_stock FROM items WHERE name=? AND color=?", (n, cl), fetch=True)
                if exist:
                    run_query("UPDATE items SET cost_price=? WHERE id=?", (cp, exist[0]['id']))
                    run_query("INSERT INTO stock_logs (date, item_id, qty_added, notes) VALUES (?,?,?,?)", (st_date, exist[0]['id'], op, "Updated Stock"))
                    st.success(f"Added {op} to {n} {cl}!")
                else:
                    # Pass 0.0 for sell_price as it's not in UI anymore
                    iid = run_query("INSERT INTO items (name, color, opening_stock, cost_price, sell_price) VALUES (?,?,?,?,0.0)", (n,cl,0,cp))
                    run_query("INSERT INTO stock_logs (date, item_id, qty_added, notes) VALUES (?,?,?,?)", (st_date, iid, op, "New Item"))
                    st.success("New Item Created!")
                st.rerun()

        # --- VIEW & EDIT TABLE ---
        st.write("### Current Stock")
        search_q = st.text_input("🔍 Search Items (Name or Color)", "")
        
        # Build Dataframe
        data_rows = []
        if all_items:
            for i in all_items:
                if search_q.lower() in i['name'].lower() or search_q.lower() in i['color'].lower():
                    curr_stock = get_stock(i['id'], i['opening_stock'])
                    status = "⚠️ Low" if curr_stock <= 5 else "✅ OK"
                    data_rows.append({
                        "ID": i['id'],
                        "Name": i['name'],
                        "Color": i['color'],
                        "Stock": curr_stock,
                        "Cost Price": i['cost_price'],
                        # Removed Sell Price column
                        "Value": curr_stock * i['cost_price'],
                        "Status": status
                    })
        
        if data_rows:
            df_inv = pd.DataFrame(data_rows)
            st.dataframe(
                df_inv, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Cost Price": st.column_config.NumberColumn(format="₹%.2f"),
                    "Value": st.column_config.NumberColumn(format="₹%.2f"),
                }
            )
            
            # --- EDIT/DELETE ACTION (FIXED WITH RETRIEVE BUTTON) ---
            with st.expander("🛠️ Edit / Delete Item"):
                sel_id = st.selectbox("Select Item ID to Edit", df_inv['ID'], key="inv_edit_id")
                
                # RETRIEVE BUTTON ADDED HERE
                if st.button("⬇️ Retrieve Details", key="inv_retr_btn"):
                    st.session_state.edit_inv_data = run_query("SELECT * FROM items WHERE id=?", (sel_id,), fetch=True)[0]

                if 'edit_inv_data' in st.session_state and st.session_state.edit_inv_data and st.session_state.edit_inv_data['id'] == sel_id:
                    item_det = st.session_state.edit_inv_data
                    
                    ec1, ec2, ec3 = st.columns(3)
                    e_name = ec1.text_input("Name", item_det['name'], key="e_nm")
                    e_col = ec2.text_input("Color", item_det['color'], key="e_col")
                    e_cp = ec3.number_input("Cost Price", 0.0, value=float(item_det['cost_price']), key="e_cp")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("Update Item"):
                        run_query("UPDATE items SET name=?, color=?, cost_price=? WHERE id=?", (e_name, e_col, e_cp, sel_id))
                        st.success("Updated!")
                        del st.session_state.edit_inv_data # Clear state
                        st.rerun()
                        
                    if b2.button("Delete Item (Permanently)", type="primary"):
                        run_query("DELETE FROM items WHERE id=?", (sel_id,))
                        st.warning("Deleted!")
                        del st.session_state.edit_inv_data
                        st.rerun()

        else:
            st.info("No items found.")

    with inv_t2:
        # --- STOCK LOGS ---
        st.write("### 📜 Recent Stock Additions")
        logs = run_query("""
            SELECT sl.date, i.name, i.color, sl.qty_added, sl.notes 
            FROM stock_logs sl 
            JOIN items i ON sl.item_id = i.id 
            ORDER BY sl.date DESC LIMIT 50
        """, fetch=True)
        
        if logs:
            st.dataframe(pd.DataFrame([dict(r) for r in logs]), use_container_width=True)
        else:
            st.info("No history logs yet.")

elif menu == "Purchases":
    with st.expander("Add Purchase", expanded=True):
        d = st.date_input("Date", date.today(), key="pur_date"); desc = st.text_input("Desc", key="pur_desc")
        c1, c2, c3 = st.columns(3)
        bags = c1.number_input("Bags", 0.0, key="pur_bag"); kg = c2.number_input("KG/Bag", 0.0, key="pur_kg"); rate = c3.number_input("Rate/KG", 0.0, key="pur_rate")
        
        # Vendor & GST
        vc1, vc2 = st.columns(2)
        vname = vc1.text_input("Vendor Name", key="p_vname")
        vcontact = vc2.text_input("Vendor Contact", key="p_vcontact")
        
        is_gst = st.toggle("GST Bill?", key="p_isgst")
        cgst_p = 0.0; sgst_p = 0.0
        if is_gst:
            g1, g2 = st.columns(2)
            cgst_p = g1.number_input("CGST %", 0.0, key="p_cgst")
            sgst_p = g2.number_input("SGST %", 0.0, key="p_sgst")
            
        p_file = st.file_uploader("Upload Bill", type=['pdf', 'png', 'jpg'], key="p_up")

        if st.button("Save", key="pur_save"): 
            total_kg = bags * kg
            total_amt = total_kg * rate
            fb = p_file.read() if p_file else None
            fn = p_file.name if p_file else None
            
            run_query("""INSERT INTO purchases (date, description, bags, kg_per_bag, total_kg, price_per_kg, total_amount, 
                         vendor_name, vendor_contact, is_gst, cgst_percent, sgst_percent, bill_file, bill_filename) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                      (d, desc, bags, kg, total_kg, rate, total_amt, vname, vcontact, 1 if is_gst else 0, cgst_p, sgst_p, fb, fn))
            st.rerun()

    # TABLE VIEW FOR PURCHASES
    purs = run_query("SELECT * FROM purchases ORDER BY date DESC", fetch=True)
    if purs:
        st.write("### Purchase History")
        df_p = pd.DataFrame([dict(r) for r in purs])
        st.dataframe(
            df_p[['id', 'date', 'vendor_name', 'description', 'total_amount', 'bill_filename']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "total_amount": st.column_config.NumberColumn("Total (₹)", format="₹%.2f"),
                "bill_filename": "Attached Bill"
            }
        )
        
        # Action Bar (FIXED WITH RETRIEVE BUTTON)
        pid = st.selectbox("Select Purchase ID to View/Delete", df_p['id'], key="p_sel")
        if st.button("⬇️ Retrieve Purchase Details", key="pur_retr_btn"):
             st.session_state.sel_pur_data = next((p for p in purs if p['id'] == pid), None)

        if 'sel_pur_data' in st.session_state and st.session_state.sel_pur_data and st.session_state.sel_pur_data['id'] == pid:
            sel = st.session_state.sel_pur_data
            c1, c2 = st.columns(2)
            c1.info(f"Vendor: {sel['vendor_name']} | Contact: {sel['vendor_contact']}")
            if sel['is_gst']:
                c1.warning(f"GST Included: {sel['cgst_percent']+sel['sgst_percent']}%")
            
            # Download Button
            if sel['bill_file']:
                b64 = base64.b64encode(sel['bill_file']).decode()
                mime = "application/pdf" if sel['bill_filename'].endswith(".pdf") else "image/png"
                c2.markdown(f'<a href="data:{mime};base64,{b64}" download="{sel["bill_filename"]}" style="background:#E2E8F0;padding:8px;border-radius:5px;text-decoration:none;">📥 Download Bill</a>', unsafe_allow_html=True)
            
            if c2.button("🗑️ Delete Purchase", key=f"del_p_{pid}"):
                run_query("DELETE FROM purchases WHERE id=?", (pid,))
                st.success("Deleted")
                del st.session_state.sel_pur_data
                st.rerun()

elif menu == "Expenses":
    cats = get_setting("expense_categories").split(',')
    with st.expander("Add Expense", expanded=True):
        d = st.date_input("Date", date.today(), key="exp_date"); cat = st.selectbox("Category", cats, key="exp_cat"); desc = st.text_input("Desc", key="exp_desc"); amt = st.number_input("Amount", 0.0, key="exp_amt")
        if st.button("Save", key="exp_save"): run_query("INSERT INTO expenses (date, category, description, amount) VALUES (?,?,?,?)", (d, cat, desc, amt)); st.rerun()
    exps = run_query("SELECT * FROM expenses ORDER BY date DESC", fetch=True)
    if exps:
        with st.expander("Edit / Delete Expense"):
            eid = st.selectbox("Select ID", [r['id'] for r in exps], key="exp_del_sel")
            
            # RETRIEVE BUTTON ADDED
            if st.button("⬇️ Retrieve Details", key="exp_retr_btn"):
                 st.session_state.edit_exp_data = run_query("SELECT * FROM expenses WHERE id=?", (eid,), fetch=True)[0]
            
            if 'edit_exp_data' in st.session_state and st.session_state.edit_exp_data and st.session_state.edit_exp_data['id'] == eid:
                e_dat = st.session_state.edit_exp_data
                ud = st.date_input("Edit Date", datetime.strptime(e_dat['date'], '%Y-%m-%d'), key="e_ed_d")
                udesc = st.text_input("Edit Desc", e_dat['description'], key="e_ed_desc")
                uamt = st.number_input("Edit Amount", e_dat['amount'], key="e_ed_amt")
                
                if st.button("Update Expense", key="e_upd_btn"):
                    run_query("UPDATE expenses SET date=?, description=?, amount=? WHERE id=?", (ud, udesc, uamt, eid)); st.success("Updated"); del st.session_state.edit_exp_data; st.rerun()
                if st.button("Delete Expense", key="exp_del_btn"): 
                    run_query("DELETE FROM expenses WHERE id=?", (eid,)); st.warning("Deleted"); del st.session_state.edit_exp_data; st.rerun()
                    
        st.dataframe(pd.DataFrame([dict(row) for row in exps]), hide_index=True, use_container_width=True, column_config={"amount": st.column_config.NumberColumn(format="₹%.2f")})

elif menu == "Customers":
    with st.expander("Add Customer", expanded=True):
        n = st.text_input("Name", key="cust_n"); p = st.text_input("Phone", key="cust_p"); a = st.text_area("Addr", key="cust_a"); od = st.number_input("Op Due", 0.0, key="cust_o")
        if st.button("Save", key="cust_s"): run_query("INSERT INTO customers (name, phone, address, opening_due) VALUES (?,?,?,?)", (n,p,a,od)); st.rerun()
    custs = run_query("SELECT * FROM customers", fetch=True)
    if custs:
        with st.expander("Edit / Delete Customer"):
            cid = st.selectbox("Select ID", [r['id'] for r in custs], key="cust_edit_sel")
            
            # RETRIEVE BUTTON ADDED
            if st.button("⬇️ Retrieve Details", key="cust_retr_btn"):
                 st.session_state.edit_cust_data = run_query("SELECT * FROM customers WHERE id=?", (cid,), fetch=True)[0]
                 
            if 'edit_cust_data' in st.session_state and st.session_state.edit_cust_data and st.session_state.edit_cust_data['id'] == cid:
                c = st.session_state.edit_cust_data
                un = st.text_input("Name", c['name'], key="ce_n"); up = st.text_input("Phone", c['phone'], key="ce_p"); ua = st.text_area("Addr", c['address'], key="ce_a")
                if st.button("Update", key="ce_upd"): run_query("UPDATE customers SET name=?, phone=?, address=? WHERE id=?", (un,up,ua,cid)); st.success("Updated"); del st.session_state.edit_cust_data; st.rerun()
                if st.button("Delete Customer", key="cust_del_btn"):
                    run_query("DELETE FROM customers WHERE id=?", (cid,)); st.warning("Deleted"); del st.session_state.edit_cust_data; st.rerun()
        st.dataframe(pd.DataFrame([dict(row) for row in custs]), hide_index=True, use_container_width=True, column_config={"opening_due": st.column_config.NumberColumn(format="₹%.2f")})

elif menu == "Staff Work":
    if 'staff_cart' not in st.session_state: st.session_state.staff_cart = []
    with st.container(border=True):
        st.write("#### Add Staff Work")
        c1, c2, c3 = st.columns(3)
        d = c1.date_input("Date", date.today(), key="sw_date"); nm = c2.text_input("Staff Name", key="sw_name"); kg_given = c3.number_input("KG Given", 0.0, key="sw_kg")
        st.markdown("---")
        ci, cg, cq, cr, ca = st.columns([2,1,1,1,1])
        m_names = run_query("SELECT name FROM master_names", fetch=True)
        name_list = [m['name'] for m in m_names] if m_names else []
        if name_list:
            sl = ci.selectbox("Item Name", name_list, key="sw_item"); clr = cg.text_input("Color", key="sw_clr_txt"); grams = cq.number_input("Gm/Pkt", 1.0, value=40.0, key="sw_gm"); qty = cr.number_input("Pkts", 0, key="sw_qty"); rate = ca.number_input("Rate", 0.0, key="sw_rate")
            if st.button("Add Item to List", key="sw_add"): 
                exist = run_query("SELECT id FROM items WHERE name=? AND color=?", (sl, clr), fetch=True)
                tid = exist[0]['id'] if exist else 0
                st.session_state.staff_cart.append({"id": tid, "name": f"{sl} ({clr})", "grams": grams, "qty": qty, "rate": rate, "total": qty*rate, "weight": (qty*grams)/1000})
        else: st.warning("Add Item Names in Settings first.")
        if st.session_state.staff_cart:
            df = pd.DataFrame(st.session_state.staff_cart)
            st.dataframe(df, use_container_width=True, column_config={"rate": st.column_config.NumberColumn(format="₹%.2f"), "total": st.column_config.NumberColumn(format="₹%.2f")})
            tsal = df['total'].sum(); tkg = df['weight'].sum(); tpkts = df['qty'].sum()
            avg_grams = df['grams'].mean(); exp_pkts = int((kg_given*1000)/avg_grams) if avg_grams > 0 else 0
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Salary", f"₹{tsal}"); m2.metric("Total Pkts", tpkts); m3.metric("Exp Pkts", f"~{exp_pkts}"); m4.metric("KG Ret", f"{tkg:.2f}", delta=f"{tkg-kg_given:.2f}")
            notes_sw = st.text_input("Notes (Optional)", key="sw_notes")
            if st.button("✅ Save Entry", type="primary", key="sw_confirm"):
                wid = run_query("INSERT INTO staff_work (date, staff_name, kg_provided, total_salary, notes) VALUES (?,?,?,?,?)", (d, nm, kg_given, tsal, notes_sw))
                for l in st.session_state.staff_cart: 
                    run_query("INSERT INTO staff_work_items (work_id, item_id, item_name, grams, qty_produced, rate, amount) VALUES (?,?,?,?,?,?,?)", (wid, l['id'], l['name'], l['grams'], l['qty'], l['rate'], l['total']))
                run_query("INSERT INTO expenses (date, category, description, amount, staff_entry_id) VALUES (?,?,?,?,?)", (d, "Salary", f"Salary: {nm}", tsal, wid))
                st.session_state.staff_cart = []; st.success("Saved!"); st.rerun()
            if st.button("Clear", key="sw_clr_btn"): st.session_state.staff_cart = []; st.rerun()
    st.subheader("History")
    q = '''SELECT sw.id, sw.date, sw.staff_name, sw.kg_provided, sw.total_salary, sw.notes, 
           COALESCE(SUM(swi.qty_produced), 0) as total_pkts, 
           COALESCE(SUM(swi.qty_produced * swi.grams)/1000, 0) as weight_ret,
           GROUP_CONCAT(COALESCE(swi.item_name, i.name, 'Generic') || ' (' || swi.qty_produced || ')', ', ') as breakdown
           FROM staff_work sw 
           LEFT JOIN staff_work_items swi ON sw.id = swi.work_id 
           LEFT JOIN items i ON swi.item_id = i.id
           GROUP BY sw.id ORDER BY sw.date DESC'''
    hist = run_query(q, fetch=True)
    if hist:
        table_data = []
        for r in hist:
            d = dict(r)
            d['Produced Details'] = d['breakdown'] if d['breakdown'] else "No Items"
            d['Weight Analysis'] = f"Given: {d['kg_provided']}kg | Ret: {d['weight_ret']:.2f}kg"
            del d['breakdown']
            table_data.append(d)
            
        with st.expander("View / Edit / Delete Entry"):
            did = st.selectbox("Select ID", [r['id'] for r in hist], key="sw_del_sel")
            
            # RETRIEVE BUTTON ADDED
            if st.button("⬇️ Retrieve Details", key="sw_retr_btn"):
                 st.session_state.edit_sw_data = run_query("SELECT * FROM staff_work WHERE id=?", (did,), fetch=True)[0]
            
            if 'edit_sw_data' in st.session_state and st.session_state.edit_sw_data and st.session_state.edit_sw_data['id'] == did:
                dets = run_query("SELECT COALESCE(swi.item_name, i.name, 'Generic') as name, swi.grams, swi.qty_produced, swi.rate, swi.amount FROM staff_work_items swi LEFT JOIN items i ON swi.item_id=i.id WHERE swi.work_id=?", (did,), fetch=True)
                st.write("**Batch Details:**")
                st.table(pd.DataFrame([dict(r) for r in dets]))
                w_dat = st.session_state.edit_sw_data
                ud = st.date_input("Edit Date", datetime.strptime(w_dat['date'], '%Y-%m-%d'), key="sw_ed_d")
                unm = st.text_input("Edit Name", w_dat['staff_name'], key="sw_ed_nm")
                ukg = st.number_input("Edit KG Provided", w_dat['kg_provided'], key="sw_ed_kg")
                c1, c2 = st.columns(2)
                if c1.button("Update Entry", key="sw_upd"):
                    run_query("UPDATE staff_work SET date=?, staff_name=?, kg_provided=? WHERE id=?", (ud, unm, ukg, did)); st.success("Updated"); del st.session_state.edit_sw_data; st.rerun()
                if c2.button("Delete Entry", key="sw_del_btn"):
                    run_query("DELETE FROM staff_work WHERE id=?", (did,)); run_query("DELETE FROM staff_work_items WHERE work_id=?", (did,)); run_query("DELETE FROM expenses WHERE staff_entry_id=?", (did,)); st.warning("Deleted"); del st.session_state.edit_sw_data; st.rerun()
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, column_config={"total_salary": st.column_config.NumberColumn(format="₹%.2f"), "kg_provided": st.column_config.NumberColumn(format="%.2f kg")})

elif menu == "Print Stickers":
    st.markdown("### 🖨️ Print Stickers (A4 Landscape)")
    
    st_title = st.text_input("Sticker Title", value="நூல் கண்டு")
    st_cell = st.text_input("Cell Number", value="7418570821")
    
    # Priority: Image (title.png) > Text
    if os.path.exists("title.png"):
        st.success("✅ Image title found (title.png). Using image instead of text.")
    elif not os.path.exists("tamil.ttf"):
        st.warning("⚠️ For Tamil text, please add 'tamil.ttf' or 'Nirmala.ttf' to the app folder. Currently using system defaults.")

    c1, c2 = st.columns(2)
    t_val = c1.number_input("Thread Thickness Value", 1, value=6)
    n_sheets = c2.number_input("Number of Sheets (9 stickers/sheet)", 1, value=1)
    
    if st.button("Generate Sticker PDF", type="primary"):
        pdf_bytes = generate_pdf_from_images(t_val, n_sheets, st_title, st_cell)
        
        # 1. Base64 Preview
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="900" type="application/pdf"></iframe>'
        
        st.markdown("### 🖨️ Sticker Preview")
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        # 2. Download Button
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name="sticker.pdf",
            mime="application/pdf"
        )
    
    st.info("💡 Pro Tip: For perfect Tamil text, you can upload an image of the text named 'title.png' to the app folder.")

elif menu == "Data Inspector":
    if st.session_state.user['role'] == 'Admin':
        st.markdown("### 🔍 Data Inspector")
        conn = sqlite3.connect(DB_FILE)
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        if not tables.empty:
            t_list = tables['name'].tolist()
            sel_table = st.selectbox("Select Table", t_list)
            if sel_table:
                schema = pd.read_sql(f"PRAGMA table_info({sel_table})", conn)
                with st.expander("Show Schema"): st.dataframe(schema)
                df = pd.read_sql(f"SELECT * FROM {sel_table}", conn)
                st.dataframe(df)
        else: st.warning("No tables found.")
        st.divider()
        st.subheader("2. Run Custom SQL")
        query = st.text_area("SQL Query", "SELECT * FROM sales LIMIT 5")
        if st.button("Run Query"):
            try:
                if query.lower().startswith("select"):
                    res = pd.read_sql(query, conn)
                    st.dataframe(res)
                else:
                    c = conn.cursor(); c.execute(query); conn.commit(); st.success("Query Executed Successfully")
            except Exception as e: st.error(f"Error: {e}")
        conn.close()
    else: st.error("Access Denied")

elif menu == "Password Manager":
    if st.session_state.user['role'] == 'Admin':
        st.markdown("### 👥 Admin User Management")
        t1, t2 = st.tabs(["Create User", "Edit User"])
        with t1:
            c1, c2, c3 = st.columns(3)
            nu = c1.text_input("New User", key="pm_nu"); np = c2.text_input("Password", type="password", key="pm_np"); nr = c3.selectbox("Role", ["Staff", "Admin"], key="pm_nr")
            perms = st.multiselect("Access", ALL_PAGES, default=["Sales & Billing"], key="pm_perms")
            if st.button("Create", key="pm_create"):
                try:
                    run_query("INSERT INTO app_users (username, password_hash, role, permissions) VALUES (?,?,?,?)", (nu, hash_pass(np), nr, ",".join(perms))); st.success("User Created")
                except: st.error("Exists")
        with t2:
            usrs = run_query("SELECT * FROM app_users", fetch=True)
            u_map = {u['username']: u for u in usrs}
            sel_u = st.selectbox("Select User to Edit", list(u_map.keys()), key="pm_edit_sel")
            if sel_u:
                curr_u = u_map[sel_u]
                curr_perms_list = curr_u['permissions'].split(",") if curr_u['permissions'] else []
                valid_defaults = [p for p in curr_perms_list if p in ALL_PAGES]
                c_role = st.selectbox("Role", ["Staff", "Admin"], index=0 if curr_u['role']=="Staff" else 1, key=f"pm_role_{sel_u}")
                c_perms = st.multiselect("Access", ALL_PAGES, default=valid_defaults, key=f"pm_perms_{sel_u}")
                new_pass = st.text_input("Reset Password (Optional)", type="password", key=f"pm_pass_{sel_u}")
                if st.button("Update User", key="pm_update_btn"):
                    p_sql = hash_pass(new_pass) if new_pass else curr_u['password_hash']
                    run_query("UPDATE app_users SET role=?, permissions=?, password_hash=? WHERE id=?", (c_role, ",".join(c_perms), p_sql, curr_u['id'])); st.success("Updated!"); st.rerun()
        st.divider()
    st.markdown("### 🔐 Team Vault")
    with st.expander("➕ Add Secret", expanded=False):
        c1, c2 = st.columns(2)
        web = c1.text_input("Site", key="vault_site"); lid = c2.text_input("Login ID", key="vault_lid"); pw = st.text_input("Password", type="password", key="vault_pw")
        vis = st.radio("Visibility", ["Private", "Shared"], horizontal=True, key="vault_vis")
        if st.button("Save Secret", key="vault_save"):
            enc = encrypt_val(pw)
            run_query("INSERT INTO pm_vault (user_id, type, website, login_id, enc_password, updated_at) VALUES (?,?,?,?,?,?)", (st.session_state.user['id'], vis, web, lid, enc, date.today())); st.success("Saved"); st.rerun()
    uid = st.session_state.user['id']
    rows = run_query("SELECT * FROM pm_vault WHERE user_id=? OR type='Shared' ORDER BY id DESC", (uid,), fetch=True)
    if rows:
        for r in rows:
            icon = "🌍" if r['type'] == 'Shared' else "🔒"
            with st.expander(f"{icon} {r['website']} ({r['login_id']})"):
                st.code(decrypt_val(r['enc_password']))
                if st.button("Delete", key=f"del_{r['id']}"):
                    if r['user_id'] == uid or st.session_state.user['role'] == 'Admin':
                        run_query("DELETE FROM pm_vault WHERE id=?", (r['id'],)); st.rerun()
                    else: st.error("Unauthorized")

elif menu == "Reports":
    c1, c2, c3 = st.columns(3)
    df = c1.date_input("From", key="rep_from"); dt = c2.date_input("To", key="rep_to"); 
    custs = run_query("SELECT id, name FROM customers", fetch=True)
    cmap = {c['name']: c['id'] for c in custs}; cmap["All Customers"] = None
    sc = c3.selectbox("Filter Customer", list(cmap.keys()), index=len(cmap)-1, key="rep_cust"); cid = cmap[sc]
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["Sales", "Purchases", "Expenses", "Dues", "Staff", "Stock History", "Profit & Loss"])
    
    # ----------------------------------------------------
    # FILTER LOGIC FOR REPORTS
    # ----------------------------------------------------
    # General Date Filter for Non-Customer Tabs (Purchases, Expenses, etc.)
    date_filter = "WHERE date BETWEEN ? AND ?" if (df and dt) else "WHERE 1=1"
    date_params = [df, dt] if (df and dt) else []

    # Specific Sales Filter (Date AND Customer)
    sales_where = "WHERE 1=1"
    sales_params = []
    if df and dt:
        sales_where += " AND s.date BETWEEN ? AND ?"
        sales_params.extend([df, dt])
    if cid:
        sales_where += " AND s.customer_id = ?"
        sales_params.append(cid)

    with t1:
        # SALES TAB
        q_sales_rep = f'''SELECT s.*, c.name as customer_name, (s.grand_total - s.paid_amount) as due_amount 
                          FROM sales s 
                          LEFT JOIN customers c ON s.customer_id=c.id 
                          {sales_where}'''
        d = run_query(q_sales_rep, tuple(sales_params), fetch=True)
        if d: st.dataframe(pd.DataFrame([dict(r) for r in d]), column_config={"grand_total": st.column_config.NumberColumn(format="₹%.2f"), "paid_amount": st.column_config.NumberColumn(format="₹%.2f")})
        else: st.info("No Data found for filters.")

    with t2:
        # PURCHASES TAB
        if cid: st.info("Not applicable for specific Customer filter")
        else:
            d = run_query(f"SELECT * FROM purchases {date_filter}", tuple(date_params), fetch=True)
            if d: st.dataframe(pd.DataFrame([dict(r) for r in d]), column_config={"total_amount": st.column_config.NumberColumn(format="₹%.2f")})
            else: st.info("No Data")

    with t3:
        # EXPENSES TAB
        if cid: st.info("Not applicable for specific Customer filter")
        else:
            d = run_query(f"SELECT * FROM expenses {date_filter}", tuple(date_params), fetch=True)
            if d: st.dataframe(pd.DataFrame([dict(r) for r in d]), column_config={"amount": st.column_config.NumberColumn(format="₹%.2f")})
            else: st.info("No Data")

    with t4:
        # DUES TAB
        cust_where = "WHERE id=?" if cid else ""
        cust_params = [cid] if cid else []
        q_dues = f"SELECT id, name, phone, opening_due FROM customers {cust_where}"
        custs_data = run_query(q_dues, tuple(cust_params), fetch=True)
        res = []
        for c in custs_data:
            due = get_customer_due(c['id'], c['opening_due'])
            if due > 1: res.append({"Name": c['name'], "Phone": c['phone'], "Current Due": due})
        if res: st.dataframe(pd.DataFrame(res), column_config={"Current Due": st.column_config.NumberColumn(format="₹%.2f")})
        else: st.info("No dues found.")

    with t5:
        # STAFF TAB
        if cid: st.info("Not applicable for specific Customer filter")
        else:
            q_stf = f'''SELECT sw.date, sw.staff_name, sw.kg_provided, 
                        COALESCE(SUM(swi.qty_produced), 0) as total_pkts, 
                        GROUP_CONCAT(COALESCE(swi.item_name, i.name, 'Generic') || ' (' || swi.qty_produced || ')', ', ') as details,
                        'Given: ' || sw.kg_provided || 'kg | Ret: ' || printf("%.2f", COALESCE(SUM(swi.qty_produced * swi.grams)/1000, 0)) || 'kg' as weight_analysis,
                        sw.total_salary 
                        FROM staff_work sw 
                        LEFT JOIN staff_work_items swi ON sw.id = swi.work_id 
                        LEFT JOIN items i ON swi.item_id = i.id
                        {date_filter} GROUP BY sw.id'''
            d = run_query(q_stf, tuple(date_params), fetch=True)
            if d: st.dataframe(pd.DataFrame([dict(r) for r in d]), column_config={"total_salary": st.column_config.NumberColumn(format="₹%.2f"), "kg_provided": st.column_config.NumberColumn(format="%.2f kg")})
            else: st.info("No Data")

    with t6:
        # STOCK LOGS TAB
        if cid: st.info("Not applicable for specific Customer filter")
        else:
            q_logs = f'''SELECT sl.date, i.name, i.color, sl.qty_added, sl.notes 
                         FROM stock_logs sl 
                         JOIN items i ON sl.item_id=i.id 
                         {date_filter.replace('date', 'sl.date')} ORDER BY sl.date DESC'''
            logs = run_query(q_logs, tuple(date_params), fetch=True)
            if logs: st.dataframe(pd.DataFrame([dict(r) for r in logs]))
            else: st.info("No stock logs.")

    with t7:
        # PROFIT & LOSS TAB
        if cid: 
            st.info("Not applicable for specific Customer filter")
        else:
            is_date_filtered = (df is not None and dt is not None)
            pnl_where = "WHERE date BETWEEN ? AND ?" if is_date_filtered else "" 
            pnl_params = [df, dt] if is_date_filtered else []
            
            title = f"({df} to {dt})" if is_date_filtered else "(Overall)"
            st.markdown(f"### 📈 Profit & Loss {title}")

            rev = run_query(f"SELECT SUM(sub_total) FROM sales {pnl_where}", tuple(pnl_params), fetch=True)[0][0] or 0
            
            sale_ids_query = f"SELECT id FROM sales {pnl_where}"
            sale_ids_rows = run_query(sale_ids_query, tuple(pnl_params), fetch=True)
            sale_ids = [row[0] for row in sale_ids_rows]
            
            cogs = 0
            if sale_ids:
                placeholders = ",".join("?" * len(sale_ids))
                cogs_q = f"SELECT SUM(qty * cost_per_unit) FROM sale_items WHERE sale_id IN ({placeholders})"
                cogs = run_query(cogs_q, tuple(sale_ids), fetch=True)[0][0] or 0

            exp_rows = run_query(f"SELECT category, SUM(amount) as total FROM expenses {pnl_where} GROUP BY category", tuple(pnl_params), fetch=True)
            tot_exp = sum([r['total'] for r in exp_rows])
            
            net = (rev - cogs) - tot_exp
            
            c1, c2 = st.columns(2)
            c1.metric("Revenue (Sales)", f"₹{rev:,.2f}")
            c1.metric("COGS (Item Cost)", f"- ₹{cogs:,.2f}")
            c1.markdown("---")
            c1.metric("Gross Profit", f"₹{rev-cogs:,.2f}")
            
            c2.write("**Expenses Breakdown**")
            if exp_rows:
                for r in exp_rows: c2.write(f"- {r['category']}: ₹{r['total']:,.2f}")
            c2.metric("Total Expenses", f"- ₹{tot_exp:,.2f}")
            c2.markdown("---")
            st.metric("NET PROFIT", f"₹{net:,.2f}", delta_color="normal")
            
            col_a, col_b = st.columns(2)
            d1_pdf = df if is_date_filtered else date(2020,1,1)
            d2_pdf = dt if is_date_filtered else date.today()
            pdf_bytes = create_pnl_pdf(d1_pdf, d2_pdf, rev, cogs, exp_rows, net)
            col_a.download_button("📄 Download PDF Statement", pdf_bytes, "PnL_Statement.pdf", "application/pdf")
            csv_data = [{"Category": "Revenue", "Amount": rev}, {"Category": "COGS", "Amount": -cogs}, {"Category": "Gross Profit", "Amount": rev-cogs}]
            for r in exp_rows: csv_data.append({"Category": f"Exp: {r['category']}", "Amount": -r['total']})
            csv_data.append({"Category": "NET PROFIT", "Amount": net})
            col_b.download_button("📊 Download Excel (CSV)", pd.DataFrame(csv_data).to_csv(index=False), "PnL.csv")


elif menu == "Settings":
    with st.container(border=True):
        st.subheader("Config")
        gst = st.text_input("GST", get_setting("gst_number"), key="set_gst")
        c = st.number_input("CGST %", value=float(get_setting("cgst_percent")), step=0.1, key="set_cgst")
        s = st.number_input("SGST %", value=float(get_setting("sgst_percent")), step=0.1, key="set_sgst")
        ba = st.text_area("Address", get_setting("business_address"), key="set_addr")
        bc = st.text_input("Business Contact", get_setting("business_contact"), key="set_contact")
        
        if st.button("Save", key="set_save"): 
            update_setting("gst_number", gst)
            update_setting("cgst_percent", c)
            update_setting("sgst_percent", s)
            update_setting("business_address", ba)
            update_setting("business_contact", bc)
            st.success("Saved")
            
    with st.expander("Master Item List"):
        c1, c2 = st.columns(2)
        new_m = c1.text_input("Add New Item Name", key="m_new")
        if c1.button("Add Master Name", key="m_add") and new_m:
            try: run_query("INSERT INTO master_names (name) VALUES (?)", (new_m,)); st.success("Added")
            except: st.error("Exists")
        m_list = run_query("SELECT name FROM master_names", fetch=True)
        if m_list:
            df_m = pd.DataFrame([m['name'] for m in m_list], columns=["Defined Names"]); st.dataframe(df_m, hide_index=True)
            d_name = c2.selectbox("Delete Name", [m['name'] for m in m_list], key="m_del_sel")
            if c2.button("Delete Selected", key="m_del_btn"): run_query("DELETE FROM master_names WHERE name=?", (d_name,)); st.rerun()
    with st.expander("Expense Categories"):
        curr = get_setting("expense_categories")
        new = st.text_area("Categories", curr, key="set_cats")
        if st.button("Update", key="set_upd_cat"): update_setting("expense_categories", new); st.success("Saved")
    with st.expander("Backup & Export Data"):
        st.write("### 📅 Date-Filtered Database Backup")
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Start Date", key="bk_d1"); d2 = c2.date_input("End Date", key="bk_d2")
        if st.button("Generate & Download Database", key="db_gen_btn"):
            try:
                shutil.copy(DB_FILE, "temp_backup.db"); conn_temp = sqlite3.connect("temp_backup.db"); ct = conn_temp.cursor()
                tables_to_prune = ['sales', 'purchases', 'expenses', 'staff_work', 'stock_logs', 'payments']
                for t in tables_to_prune: ct.execute(f"DELETE FROM {t} WHERE date < ? OR date > ?", (d1, d2))
                ct.execute("DELETE FROM sale_items WHERE sale_id NOT IN (SELECT id FROM sales)")
                ct.execute("DELETE FROM staff_work_items WHERE work_id NOT IN (SELECT id FROM staff_work)")
                conn_temp.commit(); ct.execute("VACUUM"); conn_temp.close()
                with open("temp_backup.db", "rb") as f: st.download_button("Download Filtered DB (.db)", f, f"backup_{d1}_{d2}.db", "application/x-sqlite3")
            except Exception as e: st.error(f"Error: {e}")
        st.divider()
        up = st.file_uploader("Restore Database", type="db", key="db_up")
        if up and st.button("Restore System", key="db_rst"):
            with open(DB_FILE, "wb") as f: f.write(up.getbuffer())
            st.success("Restored!"); st.rerun()
