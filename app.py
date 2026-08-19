import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
from google import genai
import re
import gspread
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="RABAY CELL PRO", layout="centered", page_icon="🚀")

# --- CUSTOM CSS: WARNA TEMA SENADA ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { color: #00b4d8 !important; border-bottom-color: #00b4d8 !important; }
    .stTabs [data-baseweb="tab-list"] button:hover { color: #00b4d8 !important; }
    .metric-card-blue { background-color: #161b22; padding: 15px; border-radius: 10px; border-left: 4px solid #00b4d8; margin-bottom: 10px; }
    .metric-card-green { background-color: #161b22; padding: 15px; border-radius: 10px; border-left: 4px solid #2ea043; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh, sh.worksheet("Transaksi"), sh.worksheet("Kas_Harian"), sh.worksheet("Stok")
    except: return None, None, None, None

db, ws_t, ws_k, ws_s = konek_gsheets()

# STATE MANAGEMENT
if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = 0
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = 0
if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = 0
if 'input_jenis' not in st.session_state: st.session_state['input_jenis'] = "Bank"

def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 1000000: return 8000
        else: return 10000
    elif jenis == "Tarik Tunai":
        if nominal <= 300000: return 3000
        elif nominal <= 10000000: return 25000
        else: return 35000
    else: 
        if nominal <= 400000: return 5000
        elif nominal <= 10000000: return 35000
        else: return 40000
    return 0

st.markdown("<h3 style='color:#00b4d8; margin:0;'>RABAY CELL</h3>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Transaksi", "📦 Stok Barang", "📋 Riwayat", "📊 Dashboard"])

with tab1:
    st.subheader("⚡ Input Transaksi Baru")
    metode = st.radio("Metode:", ["Ketik Manual", "Scan AI"], horizontal=True)
    if metode == "Ketik Manual":
        quick = st.text_input("Kode/Barcode:")
        jenis = st.radio("Jenis:", ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"], horizontal=True)
        nominal = st.number_input("Nominal (Rp):", step=10000)
        cuan = st.number_input("Profit Manual (Rp):", step=1000) if jenis == "Transaksi Lainnya" else 0
        if st.button("💾 Simpan"):
            st.session_state['modal_cash'] += nominal
            st.success("Tersimpan!")
    else:
        file = st.file_uploader("Upload Foto Mutasi", type=["jpg","png"])
        if file and st.button("🔍 Scan AI"):
            st.info("Fitur Scan AI aktif...")

with tab2:
    st.subheader("📦 Manajemen Stok")
    with st.expander("Tambah Barang"):
        nama = st.text_input("Nama Barang")
        if st.button("Simpan Barang"):
            ws_s.append_row([nama, 0, 0, 0, 0])
            st.success("Tersimpan!")
    if ws_s: st.dataframe(pd.DataFrame(ws_s.get_all_values()[1:], columns=ws_s.get_all_values()[0]))

with tab3:
    st.subheader("📋 Riwayat Transaksi")
    if ws_t: st.dataframe(pd.DataFrame(ws_t.get_all_values()[1:], columns=ws_t.get_all_values()[0]))

with tab4:
    st.subheader("📊 Dashboard")
    # --- MODAL DIPINDAHKAN KE SINI ---
    st.write("### 💰 Atur Modal Awal")
    st.session_state['modal_cash'] = st.number_input("Cash di Laci:", value=st.session_state['modal_cash'], step=50000)
    st.session_state['modal_digi'] = st.number_input("Saldo Digital:", value=st.session_state['modal_digi'], step=50000)
    
    st.markdown("---")
    st.markdown(f"""
        <div class="metric-card-blue">
            <h4>💵 Cash: Rp {st.session_state['modal_cash']:,}</h4>
            <h4>💳 Saldo: Rp {st.session_state['modal_digi']:,}</h4>
        </div>
    """, unsafe_allow_html=True)
    
    if ws_t:
        data = ws_t.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            st.write("Grafik Profit akan muncul di sini...")
