import streamlit as st
from PIL import Image
from google import genai
import re
import gspread
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Kasir RABAY CELL PRO", layout="centered")

# 1. KONEKSI DATABASE
@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        return gc.open("Database Kasir")
    except: return None

db = konek_gsheets()
ws_t = db.worksheet("Transaksi") if db else None
ws_k = db.worksheet("Kas_Harian") if db else None

# 2. STATE MANAGEMENT
if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = 0
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = 0
if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = 0
if 'input_jenis' not in st.session_state: st.session_state['input_jenis'] = "Bank"

st.title("🚀 Kasir RABAY CELL PRO")

# 3. MODUL KAS AWAL
with st.expander("💰 Modal Awal Hari Ini"):
    st.session_state['modal_cash'] = st.number_input("Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
    st.session_state['modal_digi'] = st.number_input("Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)

# 4. FUNGSI HITUNG ADMIN LENGKAP
def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 199000: return 3000
        elif nominal <= 299000: return 4000
        elif nominal <= 699000: return 5000
        elif nominal <= 1000000: return 8000
        else: return 10000
    else: # Tarif Bank / Tarik Tunai
        if nominal <= 98000: return 3000
        elif nominal <= 400000: return 5000
        elif nominal <= 700000: return 8000
        elif nominal <= 1200000: return 10000
        elif nominal <= 1700000: return 13000
        elif nominal <= 2500000: return 15000
        elif nominal <= 3500000: return 20000
        elif nominal <= 5000000: return 25000
        elif nominal <= 7000000: return 30000
        elif nominal <= 10000000: return 35000
        else:
            sisa = nominal - 10000000
            kelipatan = -(-sisa // 5000000)
            return 35000 + (kelipatan * 5000)

tab1, tab2 = st.tabs(["⚡ Input Transaksi", "📊 Dashboard Kas"])

with tab1:
    # A. Input Cepat
    quick = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200):")
    if quick:
        code = quick.upper().strip()
        st.session_state['input_jenis'] = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
        angka_str = re.sub(r'[^0-9.]', '', code)
        try: st.session_state['input_nominal'] = int(float(angka_str) * 1000)
        except: pass

    # B. Pilihan & Kalkulasi Rinci
    st.markdown("---")
    st.session_state['input_jenis'] = st.radio("Jenis Transaksi:", ["Bank", "E-Wallet", "Tarik Tunai"], 
                                                index=["Bank", "E-Wallet", "Tarik Tunai"].index(st.session_state['input_jenis']), horizontal=True)
    
    nominal_trx = st.number_input("Nominal Transaksi (Rp):", value=st.session_state['input_nominal'], step=10000)
    
    if nominal_trx > 0:
        admin = hitung_admin(nominal_trx, st.session_state['input_jenis'])
        total_uang = nominal_trx + admin if st.session_state['input_jenis'] != "Tarik Tunai" else nominal_trx - admin
        
        c1, c2 = st.columns(2)
        c1.metric("Nominal", f"Rp {nominal_trx:,}")
        c2.metric("Admin", f"Rp {admin:,}")
        
        if st.session_state['input_jenis'] == "Tarik Tunai":
            st.info(f"💵 Uang Tunai Diberikan ke Pelanggan: **Rp {total_uang:,}**")
        else:
            st.success(f"💰 Total Tagihan Pelanggan: **Rp {total_uang:,}**")
            
        if st.button("💾 Simpan & Update Kas", type="primary", use_container_width=True):
            waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            
            # --- LOGIKA KAS OTOMATIS ---
            if st.session_state['input_jenis'] == "Tarik Tunai":
                # Tarik tunai: Cash di laci berkurang (diberikan ke orang), Saldo digital bertambah dari admin/potongan
                st.session_state['modal_cash'] -= total_uang
                st.session_state['modal_digi'] += nominal_trx
            elif st.session_state['input_jenis'] == "E-Wallet":
                # E-Wallet: Saldo digital berkurang (untuk topup), Cash di laci bertambah (terima uang fisik + admin dari customer)
                st.session_state['modal_digi'] -= nominal_trx
                st.session_state['modal_cash'] += total_uang
            else: # Bank (Transfer)
                # Bank: Saldo digital berkurang (transfer keluar), Cash di laci bertambah (uang fisik dari customer + admin)
                st.session_state['modal_digi'] -= nominal_trx
                st.session_state['modal_cash'] += total_uang
            
            # Simpan ke Google Sheets Transaksi
            if ws_t:
                ws_t.append_row([waktu, st.session_state['input_jenis'], nominal_trx, admin, total_uang])
                
            st.success("✅ Transaksi tersimpan & Kas berhasil diperbarui!")
            st.session_state['input_nominal'] = 0
            st.rerun()

with tab2:
    st.subheader("Posisi Keuangan Sekarang")
    c1, c2 = st.columns(2)
    c1.metric("Cash di Laci", f"Rp {st.session_state['modal_cash']:,}")
    c2.metric("Saldo Digital", f"Rp {st.session_state['modal_digi']:,}")
    
    if st.button("📊 Rekap Harian ke Google Sheets"):
        if ws_k:
            ws_k.append_row([datetime.now().strftime("%Y-%m-%d"), st.session_state['modal_cash'], st.session_state['modal_digi']])
            st.success("Rekap harian berhasil dikirim ke Sheets!")
