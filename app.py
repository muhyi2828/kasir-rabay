import streamlit as st
from PIL import Image
from google import genai
import re
import gspread
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Kasir RABAY CELL PRO", layout="centered")

# Inisialisasi Database
@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh, "Aman"
    except Exception as e: return None, str(e)

db, error = konek_gsheets()
ws_transaksi = db.worksheet("Transaksi") if db else None
ws_kas = db.worksheet("Kas_Harian") if db else None

# State Kas Harian
if 'modal_awal_cash' not in st.session_state: st.session_state['modal_awal_cash'] = 0
if 'modal_awal_digi' not in st.session_state: st.session_state['modal_awal_digi'] = 0

st.title("🚀 Kasir RABAY CELL PRO")

# MODUL MODAL AWAL
with st.expander("💰 Setel Modal Awal Hari Ini"):
    st.session_state['modal_awal_cash'] = st.number_input("Modal Cash di Laci:", value=st.session_state['modal_awal_cash'])
    st.session_state['modal_awal_digi'] = st.number_input("Saldo Digital Awal:", value=st.session_state['modal_awal_digi'])

# FUNGSI SIMPAN & HITUNG SALDO
def proses_transaksi(nominal, jenis, admin):
    tz = pytz.timezone('Asia/Jakarta')
    waktu = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    # Logika Potong/Tambah Kas
    if jenis == "Tarik Tunai":
        # Cash berkurang, Digital bertambah (setelah dikurangi admin)
        st.session_state['modal_awal_cash'] -= nominal
        st.session_state['modal_awal_digi'] += (nominal - admin)
    elif jenis == "E-Wallet":
        # Saldo digital terpotong (transfer), Cash bertambah (bayaran customer + admin)
        st.session_state['modal_awal_cash'] += (nominal + admin)
        st.session_state['modal_awal_digi'] -= nominal
    else: # Bank
        st.session_state['modal_awal_cash'] += admin
        
    total_uang = nominal + admin if jenis != "Tarik Tunai" else nominal - admin
    
    # Simpan ke Sheets
    if ws_transaksi:
        ws_transaksi.append_row([waktu, jenis, nominal, admin, total_uang])
    st.success(f"Transaksi {jenis} berhasil diproses!")

# INPUT TRANSAKSI (Sama seperti sebelumnya, tapi panggil fungsi di atas)
# [Tambahkan fungsi scan dan input manual di sini seperti kode sebelumnya]
# ... (Anda bisa tempelkan logika OCR dan Input Cepat yang sudah kita buat tadi) ...

# DASHBOARD REKAP
st.markdown("---")
st.subheader("📊 Laporan Kas Saat Ini")
c1, c2 = st.columns(2)
c1.metric("Sisa Cash di Laci", f"Rp {st.session_state['modal_awal_cash']:,}")
c2.metric("Sisa Saldo Digital", f"Rp {st.session_state['modal_awal_digi']:,}")

if st.button("💾 Tutup Kas / Rekap Hari Ini"):
    if ws_kas:
        ws_kas.append_row([datetime.now().strftime("%Y-%m-%d"), 
                           st.session_state['modal_awal_cash'], 
                           st.session_state['modal_awal_digi'], 
                           0, 0, 0])
        st.success("Rekap harian tersimpan!")
