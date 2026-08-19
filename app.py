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

# --- CUSTOM CSS: WARNA TEMA SENADA & TAB AKTIF ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #00b4d8 !important;
        border-bottom-color: #00b4d8 !important;
    }
    .stTabs [data-baseweb="tab-list"] button:hover {
        color: #00b4d8 !important;
    }
    .metric-card-blue {
        background-color: #161b22; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px; border-left: 4px solid #00b4d8;
    }
    .metric-card-green {
        background-color: #161b22; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px; border-left: 4px solid #2ea043;
    }
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

st.markdown("<h3 style='color:#00b4d8; margin:0;'>RABAY CELL</h3>", unsafe_allow_html=True)
st.markdown("<div style='margin: 5px 0;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Transaksi", "📦 Stok Barang", "📋 Riwayat", "📊 Dashboard"])

with tab1:
    st.subheader("⚡ Input Transaksi Baru")
    metode = st.radio("Metode:", ["Ketik Manual / Kode Cepat / Barang", "Scan Foto Mutasi (Banyak)"], horizontal=True)
    
    if metode == "Ketik Manual / Kode Cepat / Barang":
        quick = st.text_input("🔍 Kode Cepat/Barcode:")
        # ... (Logika Transaksi Manual tetap sama)
        pilihan_jenis = ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"]
        st.session_state['input_jenis'] = st.radio("Jenis:", pilihan_jenis, horizontal=True)
        nominal_trx = st.number_input("Nominal (Rp):", step=10000)
        if st.button("💾 Simpan Transaksi", type="primary"):
            st.success("Tersimpan!")

with tab4:
    st.subheader("📊 Dashboard Keuangan")
    
    # --- PANEL MODAL DIPINDAHKAN KE SINI ---
    with st.expander("💰 Atur / Update Modal Hari Ini", expanded=True):
        st.session_state['modal_cash'] = st.number_input("Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
        st.session_state['modal_digi'] = st.number_input("Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)

    st.markdown("---")
    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#00b4d8;">💵 Cash di Laci</h4>
            <h2 style="margin:5px 0 0 0; color:#fff;">Rp {st.session_state['modal_cash']:,}</h2>
        </div>
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#00b4d8;">💳 Saldo Digital</h4>
            <h2 style="margin:5px 0 0 0; color:#fff;">Rp {st.session_state['modal_digi']:,}</h2>
        </div>
    """, unsafe_allow_html=True)

    # ... (Logika Profit & Grafik tetap sama)
    st.success("Dashboard Siap!")
