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
import io
import base64
import time

# --- KONFIGURASI HALAMAN HARUS PALING ATAS ---
st.set_page_config(page_title="RABAY CELL PRO", layout="centered", page_icon="🚀", initial_sidebar_state="collapsed")

# --- CUSTOM CSS UI MODERN DARK MODE, FLOATING BUTTON & ANIMASI GOOGLE LENS ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ffffff; }
    .rabay-header {
        background-color: #14B8A6;
        padding: 15px 20px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        margin-top: -60px;
        margin-bottom: 15px;
        margin-left: -1rem;
        margin-right: -1rem;
    }
    .rabay-header h1 { color: white; margin: 0; font-size: 28px; font-weight: 800; font-family: sans-serif; letter-spacing: 1px;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; overflow-x: auto; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px !important; color: #cccccc !important; background-color: transparent !important; padding: 10px 15px !important; font-weight: 600 !important; white-space: nowrap; }
    .stTabs [aria-selected="true"] { background-color: #14B8A6 !important; color: white !important; }
    div[data-baseweb="input"] { background-color: #1E1E1E !important; border-radius: 8px !important; border: 1px solid #14B8A6 !important; }
    input { color: #14B8A6 !important; font-weight: bold !important; text-align: center !important; font-size: 18px !important;}
    .barcode-box { margin-bottom: 20px; margin-top: 10px; }
    label, .stRadio label { color: #cccccc !important; }
    .metric-card-blue { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid #14B8A6; margin-bottom: 15px; }
    .metric-card-green { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid #2ca02c; margin-bottom: 15px; }
    .floating-container { position: fixed; bottom: 0; left: 0; right: 0; background-color: rgba(5, 5, 5, 0.95); padding: 12px 16px; z-index: 99999; border-top: 1px solid #222; box-shadow: 0 -4px 10px rgba(0,0,0,0.8); }
    .main .block-container { padding-bottom: 90px; }
    .login-box { background-color: #111; padding: 30px; border-radius: 12px; border: 1px solid #14B8A6; margin-top: 50px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI FORMAT UANG ---
def f_uang(val):
    try:
        val_int = int(val)
        return f"Rp {val_int:,}".replace(",", ".")
    except:
        return str(val)

# --- FUNGSI KONEKSI MASTER GOOGLE SHEETS ---
@st.cache_resource
def init_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh
    except: return None

sh_master = init_gsheets()

# --- FUNGSI AMBIL KREDENSIAL AKUN MASTER ---
def get_master_credentials(sh):
    if not sh: return "admin", "123", None
    try:
        ws_akun = sh.worksheet("Pengaturan_Akun")
        data = ws_akun.get_all_values()
        if len(data) > 0 and len(data[0]) >= 2:
            return data[0][0], data[0][1], ws_akun
        elif len(data) > 1 and len(data[1]) >= 2:
            return data[1][0], data[1][1], ws_akun
    except:
        pass
    return "admin", "123", None

db_user, db_pass, ws_akun_master = get_master_credentials(sh_master)

# --- SISTEM LOGIN MASTER TAHAN REFRESH ---
if 'is_logged_in' not in st.session_state:
    if st.query_params.get("auth") == "1":
        st.session_state['is_logged_in'] = True
    else:
        st.session_state['is_logged_in'] = False

mapping_cabang = {
    "RABAY01": "Pusat",
    "Medang": "Cabang 2",
    "G. BATU": "Cabang 3"
}
daftar_tampilan_cabang = list(mapping_cabang.keys())

if 'cabang_terpilih' not in st.session_state:
    if st.query_params.get("cabang") and st.query_params.get("cabang") in daftar_tampilan_cabang:
        st.session_state['cabang_terpilih'] = st.query_params.get("cabang")
    else:
        st.session_state['cabang_terpilih'] = "RABAY01"

# Tampilan Login Jika Belum Masuk
if not st.session_state['is_logged_in']:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: #14B8A6; margin-bottom: 20px;'>LOGIN MASTER<br>RABAY CELL</h2>", unsafe_allow_html=True)
    input_user = st.text_input("Username:")
    input_pass = st.text_input("Password:", type="password")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 MASUK SISTEM", type="primary", use_container_width=True):
        if input_user == db_user and input_pass == db_pass:
            st.session_state['is_logged_in'] = True
            st.query_params["auth"] = "1"
            st.query_params["cabang"] = st.session_state['cabang_terpilih']
            st.success("Akses Diterima!")
            st.rerun()
        else:
            st.error("❌ Username atau Password salah! (Default: admin / 123)")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- FUNGSI AMBIL WORKSEET ---
def get_or_create_sheet(sh, title, headers):
    if not sh: return None
    try:
        return sh.worksheet(title)
    except:
        try:
            ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))
            ws.append_row(headers)
            return ws
        except:
            time.sleep(1)
            try: return sh.worksheet(title)
            except: return None

def get_branch_worksheets(sh, tampilan_cabang):
    if not sh: return None, None, None, None
    nama_sheet_asli = mapping_cabang.get(tampilan_cabang, "Pusat")
    ws_t = get_or_create_sheet(sh, f"Transaksi_{nama_sheet_asli}", ["Waktu", "Jenis", "Nominal", "Admin", "Total", "Profit"])
    ws_k = get_or_create_sheet(sh, f"Kas_Harian_{nama_sheet_asli}", ["Waktu", "Cash", "Digital"])
    ws_s = get_or_create_sheet(sh, f"Stok_{nama_sheet_asli}", ["Barcode", "Nama_Barang", "Stok", "Harga_Modal", "Harga_Jual", "Kode_Cepat", "Kategori"])
    ws_sesi = get_or_create_sheet(sh, f"RiwayatSesi_{nama_sheet_asli}", ["Waktu_Tutup_Sesi", "Modal_Cash", "Modal_Digital", "Total_Cash_Akhir", "Total_Digital_Akhir", "Total_Profit"])
    return ws_t, ws_k, ws_s, ws_sesi

ws_t, ws_k, ws_s, ws_sesi = get_branch_worksheets(sh_master, st.session_state['cabang_terpilih'])

# --- CACHE DATA (5 DETIK TTL) ---
@st.cache_data(ttl=5)
def fetch_data_from_sheet(_ws, sheet_name, branch):
    if not _ws: return []
    for _ in range(3):
        try:
            return _ws.get_all_values()
        except:
            time.sleep(0.5)
    return []

def clean_row_data(data_list):
    cleaned = []
    for item in data_list:
        if hasattr(item, 'item'): cleaned.append(item.item())
        else: cleaned.append(item)
    return cleaned

def safe_append(ws, data):
    if not ws: return False
    cleaned_data = clean_row_data(data)
    for _ in range(3):
        try:
            ws.append_row(cleaned_data)
            return True
        except: time.sleep(1)
    return False

def safe_update(ws, cell_range, data):
    if not ws: return False
    cleaned_data = [clean_row_data(row) for row in data]
    for _ in range(3):
        try:
            ws.update(cell_range, cleaned_data)
            return True
        except: time.sleep(1)
    return False

def safe_update_cell(ws, row, col, val):
    if not ws: return False
    clean_val = val.item() if hasattr(val, 'item') else val
    for _ in range(3):
        try:
            ws.update_cell(row, col, clean_val)
            return True
        except: time.sleep(1)
    return False

def safe_delete(ws, row_idx):
    if not ws: return False
    for _ in range(3):
        try:
            ws.delete_rows(row_idx)
            return True
        except: time.sleep(1)
    return False

# AMBIL DATA
with st.spinner("⏳ Sinkronisasi Database..."):
    data_t = fetch_data_from_sheet(ws_t, "Transaksi", st.session_state['cabang_terpilih'])
    data_s = fetch_data_from_sheet(ws_s, "Stok", st.session_state['cabang_terpilih'])
    data_k = fetch_data_from_sheet(ws_k, "Kas", st.session_state['cabang_terpilih'])
    data_sesi = fetch_data_from_sheet(ws_sesi, "Sesi", st.session_state['cabang_terpilih'])

# CARI SESI VALID SECARA PRESISI
def load_valid_session(data_kas):
    waktu_default = "2020-01-01 00:00:00"
    if data_kas and len(data_kas) > 1:
        row_terakhir = data_kas[-1]
        if len(row_terakhir) >= 3:
            c_val = int(row_terakhir[1]) if str(row_terakhir[1]).isdigit() else 0
            d_val = int(row_terakhir[2]) if str(row_terakhir[2]).isdigit() else 0
            return row_terakhir[0], c_val, d_val
    return waktu_default, 0, 0

waktu_mulai_db, modal_cash_db, modal_digi_db = load_valid_session(data_k)

if 'waktu_mulai_sesi' not in st.session_state or st.session_state.get('reset_session_flag', False):
    st.session_state['waktu_mulai_sesi'] = waktu_mulai_db
    st.session_state['reset_session_flag'] = False

if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = modal_cash_db
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = modal_digi_db
if 'penyesuaian_cash' not in st.session_state: st.session_state['penyesuaian_cash'] = 0
if 'penyesuaian_digi' not in st.session_state: st.session_state['penyesuaian_digi'] = 0
if 'draf_scan_smart' not in st.session_state: st.session_state['draf_scan_smart'] = []
if 'keranjang_belanja' not in st.session_state: st.session_state['keranjang_belanja'] = []
if 'is_submitting' not in st.session_state: st.session_state['is_submitting'] = False

def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 199000: return 3000
        elif nominal <= 299000: return 4000
        elif nominal <= 699000: return 5000
        elif nominal <= 1000000: return 8000
        else: return 10000
    elif jenis == "Tarik Tunai":
        if nominal <= 300000: return 3000
        elif nominal <= 1000000: return 5000
        elif nominal <= 2000000: return 8000
        elif nominal <= 3000000: return 10000
        elif nominal <= 5000000: return 15000
        elif nominal <= 7000000: return 20000
        elif nominal <= 10000000: return 25000
        elif nominal <= 15000000: return 30000
        elif nominal <= 20000000: return 35000
        else: return 35000 + (-(-(nominal - 20000000) // 5000000) * 5000)
    else: 
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
        else: return 35000 + (-(-(nominal - 10000000) // 5000000) * 5000)

st.markdown(f"""
    <div class="rabay-header">
        <h1>RABAY CELL - {st.session_state['cabang_terpilih'].upper()}</h1>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["TRANSAKSI", "RIWAYAT", "DASHBOARD", "STOK BARANG", "⚙️ SETELAN"])

with tab1:
    metode = st.radio("Metode Input:", ["Ketik Manual / Barcode", "AI Scan Mutasi Foto"], horizontal=True, label_visibility="collapsed")
    
    if metode == "Ketik Manual / Barcode":
        st.markdown('<div class="barcode-box">', unsafe_allow_html=True)
        quick = st.text_input("INPUT KODE CEPAT/BARCODE", placeholder="Ketik kode cepat / barcode", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        nama_brg_det = ""
        row_brg_det = None
        profit_brg_det = 0
        jenis_trx_manual = "Bank"
        nominal_val = 0

        if quick:
            code = quick.upper().strip()
            if len(data_s) > 1:
                df_s_check = pd.DataFrame(data_s[1:])
                df_s_check['Row_Idx'] = range(2, len(df_s_check) + 2)
                match_barang = df_s_check[(df_s_check[5].str.upper() == code) | (df_s_check[0].str.upper() == code)]
                if not match_barang.empty:
                    namabarang = match_barang.iloc[0][1]
                    hargamodal = int(match_barang.iloc[0][3])
                    hargajual = int(match_barang.iloc[0][4])
                    profit_item = hargajual - hargamodal
                    nama_brg_det = namabarang
                    row_brg_det = int(match_barang.iloc[0]['Row_Idx'])
                    profit_brg_det = profit_item
                    jenis_trx_manual = "Penjualan Barang"
                    nominal_val = hargajual

            if code.startswith("TF") or code.startswith("EW") or code.startswith("TK"):
                jenis_trx_manual = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
                angka_str = re.sub(r'[^0-9.]', '', code)
                try: nominal_val = int(float(angka_str) * 1000)
                except: pass

        st.caption("Jenis Transaksi:")
        pilihan_jenis = ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"]
        current_idx = pilihan_jenis.index(jenis_trx_manual) if jenis_trx_manual in pilihan_jenis else 0
        
        jenis_terpilih = st.radio("Jenis", pilihan_jenis, index=current_idx, horizontal=True, label_visibility="collapsed")
        
        if nama_brg_det and jenis_terpilih == "Penjualan Barang":
            st.success(f"📦 Terdeteksi: **{nama_brg_det}** | Untung: **{f_uang(profit_brg_det)}**")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Nominal / Harga (Rp):")
        nominal_trx = st.number_input("Nominal", value=nominal_val, step=10000, label_visibility="collapsed")
        if nominal_trx > 0:
            st.markdown(f"<p style='color:#14B8A6; font-size:18px; font-weight:bold;'>Format: {f_uang(nominal_trx)}</p>", unsafe_allow_html=True)
        
        profit_manual = 0
        if jenis_terpilih == "Transaksi Lainnya":
            st.caption("Keuntungan Manual (Rp):")
            profit_manual = st.number_input("Profit", value=0, step=1000, label_visibility="collapsed")

        if nominal_trx > 0 or (jenis_terpilih == "Transaksi Lainnya" and (nominal_trx > 0 or profit_manual > 0)):
            if jenis_terpilih == "Penjualan Barang":
                admin = 0
                total_uang = nominal_trx
                profit_bersih = profit_brg_det if profit_brg_det > 0 else 0
            elif jenis_terpilih == "Transaksi Lainnya":
                admin = profit_manual
                total_uang = nominal_trx + admin
                profit_bersih = admin
            else:
                admin = hitung_admin(nominal_trx, jenis_terpilih)
                total_uang = nominal_trx + admin if jenis_terpilih != "Tarik Tunai" else nominal_trx - admin
                profit_bersih = admin
                
            c1, c2 = st.columns(2)
            c1.metric("Admin (Cuan)", f"{f_uang(admin)}")
            if jenis_terpilih == "Tarik Tunai":
                c2.metric("Berikan Tunai", f"{f_uang(total_uang)}")
            elif jenis_terpilih == "Transaksi Lainnya" or jenis_terpilih == "Penjualan Barang":
                c2.metric("Total Pemasukan", f"{f_uang(total_uang)}")
            else:
                c2.metric("Tagih Pelanggan", f"{f_uang(total_uang)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 SIMPAN LANGSUNG", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
                    st.session_state['is_submitting'] = True
                    waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                    if jenis_terpilih == "Penjualan Barang" and ws_s and row_brg_det:
                        stok_skrg = int(data_s[row_brg_det - 1][2]) if str(data_s[row_brg_det - 1][2]).isdigit() else 0
                        if stok_skrg > 0: safe_update_cell(ws_s, row_brg_det, 3, stok_skrg - 1)
                    
                    if safe_append(ws_t, [waktu, jenis_terpilih, int(nominal_trx), int(admin), int(total_uang), int(profit_bersih)]):
                        st.cache_data.clear()
                        st.session_state['is_submitting'] = False
                        st.success("Tersimpan!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.session_state['is_submitting'] = False
                        st.error("Gagal simpan ke server!")

            with col_b2:
                if st.button("🛒 MASUK KERANJANG", use_container_width=True):
                    st.session_state['keranjang_belanja'].append({
                        'Jenis': jenis_terpilih, 'Nama': nama_brg_det if nama_brg_det else jenis_terpilih,
                        'Nominal': int(nominal_trx), 'Admin/Profit': int(profit_bersih), 'Total': int(total_uang), 'Row_Stok': row_brg_det
                    })
                    st.success("Masuk keranjang!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state['keranjang_belanja']:
            st.markdown("---")
            st.write("### 🛒 Keranjang Belanjaan")
            df_cart_raw = pd.DataFrame(st.session_state['keranjang_belanja'])
            df_cart_display = df_cart_raw.copy()
            df_cart_display['Nominal'] = df_cart_display['Nominal'].apply(lambda x: f_uang(x))
            df_cart_display['Total'] = df_cart_display['Total'].apply(lambda x: f_uang(x))
            
            st.dataframe(df_cart_display[['Jenis', 'Nama', 'Nominal', 'Total']], use_container_width=True, hide_index=True)
            total_belanja = df_cart_raw['Total'].sum()
            st.info(f"💵 Total Tagihan: **{f_uang(total_belanja)}**")
            
            c_k1, c_k2 = st.columns(2)
            if c_k1.button("🚀 PROSES SEMUA", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
                st.session_state['is_submitting'] = True
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                berhasil = True
                for item in st.session_state['keranjang_belanja']:
                    j_trx, nom_trx, adm_trx, tot_trx, r_stok = item['Jenis'], item['Nominal'], item['Admin/Profit'], item['Total'], item['Row_Stok']
                    if j_trx == "Penjualan Barang" and ws_s and r_stok:
                        stok_skrg = int(data_s[r_stok - 1][2]) if str(data_s[r_stok - 1][2]).isdigit() else 0
                        if stok_skrg > 0: safe_update_cell(ws_s, r_stok, 3, stok_skrg - 1)
                    if not safe_append(ws_t, [waktu, j_trx, int(nom_trx), int(adm_trx), int(tot_trx), int(adm_trx)]): berhasil = False
                
                st.session_state['is_submitting'] = False
                if berhasil:
                    st.session_state['keranjang_belanja'] = []
                    st.cache_data.clear()
                    st.success("Semua keranjang selesai diproses!")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("Sebagian data gagal disimpan!")
                
            if c_k2.button("🗑️ KOSONGKAN", use_container_width=True):
                st.session_state['keranjang_belanja'] = []
                st.rerun()

    else: 
        sumber_gambar = st.file_uploader("Upload Screenshot Mutasi:", type=["jpg", "jpeg", "png"])

        if sumber_gambar and st.button("🔍 AI SCAN OTOMATIS (+/-)", use_container_width=True, type="primary"):
            try:
                lens_placeholder = st.empty()
                img_temp = Image.open(sumber_gambar)
                buffered = io.BytesIO()
                img_temp.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                lens_placeholder.markdown(f"""
                    <div class="lens-container">
                        <div class="scan-line"></div>
                        <img src="data:image/jpeg;base64,{img_str}"/>
                    </div>
                    <p style="text-align:center; color:#14B8A6; font-weight:bold; font-size:15px; margin-top:10px;">🔍 Sedang Membaca Angka Transaksi...</p>
                """, unsafe_allow_html=True)

                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                res = client.models.generate_content(model='gemini-3.5-flash-lite', contents=[img_temp, "Tulis semua nominal transaksi beserta tandanya (+ atau -). Balas dengan format angka dipisah koma, contoh: +9067000,-75000,-5000000"])
                lens_placeholder.empty()

                raw_text = res.text.replace(" ", "")
                items = raw_text.split(',')
                processed_data = []
                for idx, item in enumerate(items):
                    if '+' in item or '-' in item:
                        nom_val = int(re.sub(r'[^0-9]', '', item))
                        kategori = 'Tarik Tunai' if '+' in item else 'Bank'
                        tanda_simbol = '+' if '+' in item else '-'
                        processed_data.append({'Tanda': tanda_simbol, 'Jenis Otomatis': kategori, 'Nominal (Rp)': nom_val})
                        st.session_state[f"ocr_jns_{idx}"] = kategori
                st.session_state['draf_scan_smart'] = processed_data
                st.rerun()
            except Exception as e: st.error(f"Gagal scan: {e}")

        if st.session_state['draf_scan_smart']:
            st.markdown("---")
            st.info(f"✨ Berhasil mendeteksi {len(st.session_state['draf_scan_smart'])} transaksi.")
            mass_minus_choice = st.selectbox("Pilih Jenis untuk Semua Min (-)", options=["Bank", "E-Wallet", "Tarik Tunai"], key="mass_min_select")
            if st.button("🔄 Terapkan ke Semua Min (-)", use_container_width=True):
                for idx, item in enumerate(st.session_state['draf_scan_smart']):
                    if item['Tanda'] == '-':
                        item['Jenis Otomatis'] = mass_minus_choice
                        st.session_state[f"ocr_jns_{idx}"] = mass_minus_choice
                st.success("Semua transaksi minus (-) berhasil diubah!")
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            indices_to_delete = []
            for i, item in enumerate(st.session_state['draf_scan_smart']):
                col_h1, col_h2 = st.columns([6, 1])
                with col_h1: st.markdown(f"**Trx #{i+1} ({item['Tanda']})** - {f_uang(item['Nominal (Rp)'])}")
                with col_h2:
                    if st.button("❌", key=f"del_ocr_{i}", help="Hapus item"): indices_to_delete.append(i)
                
                if item['Tanda'] == '+':
                    jns_pilih = "Tarik Tunai"
                    st.markdown("<p style='color:#14B8A6; font-size:13px; margin:0;'>Jenis: <b>Tarik Tunai (Otomatis)</b></p>", unsafe_allow_html=True)
                else:
                    pilihan_opsi_ocr = ["Bank", "E-Wallet", "Tarik Tunai"]
                    if f"ocr_jns_{i}" not in st.session_state: st.session_state[f"ocr_jns_{i}"] = item['Jenis Otomatis']
                    jns_pilih = st.selectbox(f"Pilih Jenis Trx #{i+1}", options=pilihan_opsi_ocr, key=f"ocr_jns_{i}")
                    item['Jenis Otomatis'] = jns_pilih
                
                est_admin = hitung_admin(item['Nominal (Rp)'], jns_pilih)
                st.markdown(f"<p style='color:#2ca02c; font-size:13px; margin-top:2px;'>💰 Estimasi Admin (Cuan): <b>{f_uang(est_admin)}</b></p>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:10px 0; border-color:#333;'>", unsafe_allow_html=True)
            
            if indices_to_delete:
                st.session_state['draf_scan_smart'] = [item for idx, item in enumerate(st.session_state['draf_scan_smart']) if idx not in indices_to_delete]
                st.rerun()

            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            if st.button("💾 SIMPAN SEMUA TRANSAKSI OCR", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
                st.session_state['is_submitting'] = True
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                berhasil = True
                for i, item in enumerate(st.session_state['draf_scan_smart']):
                    jenis = "Tarik Tunai" if item['Tanda'] == '+' else st.session_state.get(f"ocr_jns_{i}", item['Jenis Otomatis'])
                    nom = item['Nominal (Rp)']
                    admin = hitung_admin(nom, jenis)
                    total = nom - admin if jenis == "Tarik Tunai" else nom + admin
                    if not safe_append(ws_t, [waktu, jenis, int(nom), int(admin), int(total), int(admin)]): berhasil = False
                
                st.session_state['is_submitting'] = False
                if berhasil:
                    st.session_state['draf_scan_smart'] = []
                    st.cache_data.clear()
                    st.success("Semua transaksi berhasil disimpan!")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("Sebagian data gagal disimpan!")
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: RIWAYAT ---
with tab2:
    if data_t and len(data_t) > 1:
        df_t = pd.DataFrame(data_t[1:], columns=data_t[0])
        df_t['No_Baris'] = range(2, len(df_t) + 2)
        df_t['Waktu_Parsed'] = pd.to_datetime(df_t.iloc[:, 0], errors='coerce')
        
        daftar_pilihan_sesi = ["Sesi Aktif Saat Ini"]
        rentang_sesi_dict = {}
        
        if data_sesi and len(data_sesi) > 1:
            for i in range(1, len(data_sesi)):
                w_tutup_str = data_sesi[i][0]
                w_mulai_str = data_sesi[i-1][0] if i > 1 else str(data_k[1][0] if len(data_k) > 1 else "2020-01-01 00:00:00")
                
                label_s = f"Sesi Selesai: {w_tutup_str}"
                daftar_pilihan_sesi.append(label_s)
                rentang_sesi_dict[label_s] = (pd.to_datetime(w_mulai_str), pd.to_datetime(w_tutup_str))

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            kolom_jenis = df_t.columns[1] if len(df_t.columns) > 1 else 'Jenis'
            pilih_filter_jenis = st.selectbox("Jenis:", options=["Semua"] + df_t[kolom_jenis].unique().tolist(), key="filter_j_trx")
        with col_f2:
            pilih_filter_sesi = st.selectbox("Filter Sesi:", options=daftar_pilihan_sesi, key="filter_s_trx")
        
        df_t_filtered = df_t.copy()
        
        if pilih_filter_sesi == "Sesi Aktif Saat Ini":
            t_mulai_aktif = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
            df_t_filtered = df_t_filtered[df_t_filtered['Waktu_Parsed'] >= t_mulai_aktif]
        else:
            w_mulai, w_tutup = rentang_sesi_dict[pilih_filter_sesi]
            df_t_filtered = df_t_filtered[(df_t_filtered['Waktu_Parsed'] >= w_mulai) & (df_t_filtered['Waktu_Parsed'] <= w_tutup)]

        if pilih_filter_jenis != "Semua": 
            df_t_filtered = df_t_filtered[df_t_filtered[kolom_jenis] == pilih_filter_jenis]
        
        profit_filter_val = pd.to_numeric(df_t_filtered.iloc[:, 5], errors='coerce').fillna(0).sum() if len(df_t_filtered) > 0 else 0
        st.markdown(f"""
            <div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border:1px solid #2ca02c; text-align:center; margin:15px 0;">
                <span style="color:#2ca02c; font-size:14px; font-weight:bold;">🔥 TOTAL PROFIT (SESI & FILTER AKTIF):</span><br>
                <span style="color:#fff; font-size:20px; font-weight:bold;">{f_uang(profit_filter_val)}</span>
            </div>
        """, unsafe_allow_html=True)
        
        if not df_t_filtered.empty:
            with st.expander("⚠️ Hapus Riwayat Transaksi Sesi Ini"):
                st.warning(f"PERINGATAN: Hanya transaksi yang ada di '{pilih_filter_sesi}' yang akan dihapus. Sesi lain tetap aman.")
                konfirm_hapus_sesi = st.checkbox("Iya, hapus transaksi sesi ini", key="chk_del_sesi_trx")
                if konfirm_hapus_sesi:
                    if st.button("🗑️ Hapus Transaksi Sesi Ini", type="primary"):
                        rows_to_delete = df_t_filtered['No_Baris'].tolist()
                        for r_idx in sorted(rows_to_delete, reverse=True):
                            safe_delete(ws_t, r_idx)
                        st.cache_data.clear()
                        st.success("Transaksi pada sesi ini berhasil dibersihkan!")
                        time.sleep(0.5)
                        st.rerun()

        st.markdown("---")
        if not df_t_filtered.empty:
            for index, row in df_t_filtered.iterrows():
                b_num = int(row['No_Baris'])
                waktu_trx = row.iloc[0]
                jns_trx = row.iloc[1]
                nom_trx = f_uang(row.iloc[2]) if str(row.iloc[2]).isdigit() else row.iloc[2]
                tot_trx = f_uang(row.iloc[4]) if str(row.iloc[4]).isdigit() else row.iloc[4]
                
                st.markdown(f"**{waktu_trx}** | <span style='color:#14B8A6;'>{jns_trx}</span><br>Nominal: {nom_trx} | Total: {tot_trx}", unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("❌ Hapus", key=f"del_trx_{b_num}", use_container_width=True):
                        if safe_delete(ws_t, b_num):
                            st.cache_data.clear()
                            st.success("Berhasil dihapus!")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("Gagal hapus!")
                with col_btn2:
                    if st.button("✏️ Edit", key=f"edit_trx_{b_num}", use_container_width=True):
                        st.session_state[f"mode_edit_trx_{b_num}"] = True

                if st.session_state.get(f"mode_edit_trx_{b_num}", False):
                    with st.form(key=f"form_edit_trx_{b_num}"):
                        st.write(f"Edit Transaksi Baris {b_num}")
                        e_waktu = st.text_input("Waktu", value=row.iloc[0])
                        e_jenis = st.text_input("Jenis", value=row.iloc[1])
                        e_nom = st.number_input("Nominal", value=int(row.iloc[2]) if str(row.iloc[2]).isdigit() else 0, step=1000)
                        e_adm = st.number_input("Admin", value=int(row.iloc[3]) if str(row.iloc[3]).isdigit() else 0, step=1000)
                        e_tot = st.number_input("Total", value=int(row.iloc[4]) if str(row.iloc[4]).isdigit() else 0, step=1000)
                        e_prof = st.number_input("Profit", value=int(row.iloc[5]) if str(row.iloc[5]).isdigit() else 0, step=1000)
                        
                        if st.form_submit_button("Simpan Perubahan"):
                            if safe_update(ws_t, f"A{b_num}:F{b_num}", [[e_waktu, e_jenis, int(e_nom), int(e_adm), int(e_tot), int(e_prof)]]):
                                st.session_state[f"mode_edit_trx_{b_num}"] = False
                                st.cache_data.clear()
                                st.success("Perubahan disimpan!")
                                time.sleep(0.5)
                                st.rerun()
                            else: st.error("Gagal update!")

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
        else:
            st.info("Tidak ada transaksi pada sesi ini.")
    else:
        st.info("Belum ada riwayat transaksi.")
        if ws_t and data_t is not None and len(data_t) == 0:
            safe_append(ws_t, ["Waktu", "Jenis", "Nominal", "Admin", "Total", "Profit"])
            st.cache_data.clear()
            st.rerun()

# --- TAB 3: DASHBOARD ---
with tab3:
    if st.button("🔴 AKHIRI SESI SEKARANG", type="primary", use_container_width=True):
        st.session_state['konfirmasi_tutup_sesi'] = True

    if st.session_state.get('konfirmasi_tutup_sesi', False):
        st.warning("⚠️ Apakah Anda yakin ingin mengakhiri sesi ini? Semua kalkulasi kas dan profit sesi ini akan ditutup dan diarsipkan.")
        col_ks1, col_ks2 = st.columns(2)
        if col_ks1.button("✅ Ya, Tutup Sesi", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
            st.session_state['is_submitting'] = True
            tot_cash_s = 0
            tot_digi_s = 0
            prof_s = 0
            
            if data_t and len(data_t) > 1:
                df_t_all = pd.DataFrame(data_t[1:])
                df_t_all['Waktu_Parsed'] = pd.to_datetime(df_t_all.iloc[:, 0], errors='coerce')
                t_mulai = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
                df_sesi_ini = df_t_all[df_t_all['Waktu_Parsed'] >= t_mulai].copy()
                
                if not df_sesi_ini.empty:
                    prof_s = pd.to_numeric(df_sesi_ini.iloc[:, 5], errors='coerce').fillna(0).sum()
                    for idx, r in df_sesi_ini.iterrows():
                        jns = r.iloc[1]
                        nom = float(r.iloc[2]) if str(r.iloc[2]).replace('.','',1).isdigit() else 0
                        tot = float(r.iloc[4]) if str(r.iloc[4]).replace('.','',1).isdigit() else 0
                        if jns in ["Penjualan Barang", "Transaksi Lainnya"]: tot_cash_s += tot
                        elif jns == "Tarik Tunai":
                            tot_cash_s -= tot
                            tot_digi_s += nom
                        else: 
                            tot_digi_s -= nom
                            tot_cash_s += tot

            akhir_c = int(st.session_state['modal_cash'] + tot_cash_s + st.session_state['penyesuaian_cash'])
            akhir_d = int(st.session_state['modal_digi'] + tot_digi_s + st.session_state['penyesuaian_digi'])
            waktu_tutup = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")

            try:
                nama_asli = mapping_cabang.get(st.session_state['cabang_terpilih'], "Pusat")
                target_ws_sesi = ws_sesi or get_or_create_sheet(sh_master, f"RiwayatSesi_{nama_asli}", ["Waktu_Tutup_Sesi", "Modal_Cash", "Modal_Digital", "Total_Cash_Akhir", "Total_Digital_Akhir", "Total_Profit"])
                target_ws_k = ws_k or get_or_create_sheet(sh_master, f"Kas_Harian_{nama_asli}", ["Waktu", "Cash", "Digital"])

                b_sesi = safe_append(target_ws_sesi, [waktu_tutup, int(st.session_state['modal_cash']), int(st.session_state['modal_digi']), akhir_c, akhir_d, int(prof_s)])
                b_kas = safe_append(target_ws_k, [waktu_tutup, 0, 0])

                st.session_state['is_submitting'] = False
                if b_sesi and b_kas:
                    # PERSIAPAN STATE DAN QUERY PARAMS TAHAN REFRESH
                    st.session_state['modal_cash'] = 0
                    st.session_state['modal_digi'] = 0
                    st.session_state['penyesuaian_cash'] = 0
                    st.session_state['penyesuaian_digi'] = 0
                    st.session_state['waktu_mulai_sesi'] = waktu_tutup
                    st.session_state['reset_session_flag'] = True
                    st.session_state['konfirmasi_tutup_sesi'] = False
                    
                    st.cache_data.clear()
                    st.success("🎉 Sesi Berhasil Diakhiri & Diarsipkan!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Gagal menyimpan data ke Google Sheets. Coba klik lagi.")
            except Exception as e:
                st.session_state['is_submitting'] = False
                st.error(f"Detail Error Server: {e}")

        if col_ks2.button("❌ Batal", use_container_width=True):
            st.session_state['konfirmasi_tutup_sesi'] = False
            st.rerun()

    st.markdown("---")

    with st.expander("💰 Setel Modal Awal Sesi Ini", expanded=False):
        input_cash_baru = st.number_input("Setel Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
        if input_cash_baru > 0: st.caption(f"👀 Terbaca: **{f_uang(input_cash_baru)}**")
            
        input_digi_baru = st.number_input("Setel Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)
        if input_digi_baru > 0: st.caption(f"👀 Terbaca: **{f_uang(input_digi_baru)}**")
            
        if st.button("💾 Simpan Modal Sesi", type="primary", use_container_width=True):
            waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            if safe_append(ws_k, [waktu, int(input_cash_baru), int(input_digi_baru)]):
                st.session_state['modal_cash'] = int(input_cash_baru)
                st.session_state['modal_digi'] = int(input_digi_baru)
                st.cache_data.clear()
                st.success("Modal awal sesi diperbarui!")
                time.sleep(0.5)
                st.rerun()
            else: st.error("Gagal update modal!")

    st.markdown("---")

    tot_transaksi_cash = 0
    tot_transaksi_digi = 0
    profit_sesi_ini = 0
    
    if data_t and len(data_t) > 1:
        df_trx = pd.DataFrame(data_t[1:])
        if len(df_trx.columns) >= 6:
            df_trx['Waktu_Parsed'] = pd.to_datetime(df_trx.iloc[:, 0], errors='coerce')
            t_mulai_sesi = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
            
            df_sesi = df_trx[df_trx['Waktu_Parsed'] >= t_mulai_sesi].copy()
            if not df_sesi.empty:
                profit_sesi_ini = pd.to_numeric(df_sesi.iloc[:, 5], errors='coerce').fillna(0).sum()
                for idx, r in df_sesi.iterrows():
                    jns = r.iloc[1]
                    nom = float(r.iloc[2]) if str(r.iloc[2]).replace('.','',1).isdigit() else 0
                    tot = float(r.iloc[4]) if str(r.iloc[4]).replace('.','',1).isdigit() else 0
                    if jns in ["Penjualan Barang", "Transaksi Lainnya"]: tot_transaksi_cash += tot
                    elif jns == "Tarik Tunai":
                        tot_transaksi_cash -= tot
                        tot_transaksi_digi += nom
                    else: 
                        tot_transaksi_digi -= nom
                        tot_transaksi_cash += tot

    total_cash_sistem = st.session_state['modal_cash'] + tot_transaksi_cash
    total_digi_sistem = st.session_state['modal_digi'] + tot_transaksi_digi

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💵 Cash di Laci (Sesi Aktif)</h4>
            <p style="margin:5px 0 0 0; color:#ccc; font-size:14px;">TOTAL: {f_uang(total_cash_sistem)}</p>
        </div>
    """, unsafe_allow_html=True)
    
    penyesuaian_cash = st.number_input("Koreksi / Penyesuaian Cash (+ / - Rp):", value=st.session_state['penyesuaian_cash'], step=10000, key="peny_cash")
    hasil_akhir_cash = total_cash_sistem + penyesuaian_cash
    st.markdown(f"""
        <div style="background-color:#111; padding:15px; border-radius:8px; border:1px solid #14B8A6; text-align:center; margin-bottom:20px;">
            <span style="color:#aaa; font-size:14px;">HASIL AKHIR CASH DI LACI:</span><br>
            <span style="color:#14B8A6; font-size:24px; font-weight:bold;">{f_uang(hasil_akhir_cash)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💳 Saldo Digital (Sesi Aktif)</h4>
            <p style="margin:5px 0 0 0; color:#ccc; font-size:14px;">TOTAL: {f_uang(total_digi_sistem)}</p>
        </div>
    """, unsafe_allow_html=True)
    
    penyesuaian_digi = st.number_input("Koreksi / Penyesuaian Saldo (+ / - Rp):", value=st.session_state['penyesuaian_digi'], step=10000, key="peny_digi")
    hasil_akhir_digi = total_digi_sistem + penyesuaian_digi
    st.markdown(f"""
        <div style="background-color:#111; padding:15px; border-radius:8px; border:1px solid #14B8A6; text-align:center; margin-bottom:20px;">
            <span style="color:#aaa; font-size:14px;">HASIL AKHIR SALDO DIGITAL:</span><br>
            <span style="color:#14B8A6; font-size:24px; font-weight:bold;">{f_uang(hasil_akhir_digi)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(f"""
        <div class="metric-card-green">
            <h4 style="margin:0; color:#2ca02c;">🔥 Profit Sesi Ini</h4>
            <h1 style="margin:5px 0 0 0; color:#fff;">{f_uang(profit_sesi_ini)}</h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📈 Grafik Profit Berdasarkan Sesi")
    if data_t and len(data_t) > 1:
        df_trx_all = pd.DataFrame(data_t[1:])
        if len(df_trx_all.columns) >= 6:
            df_trx_all['Tanggal'] = pd.to_datetime(df_trx_all.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
            df_trx_all['Profit_Val'] = pd.to_numeric(df_trx_all.iloc[:, 5], errors='coerce').fillna(0)
            df_profit_harian = df_trx_all.groupby('Tanggal')['Profit_Val'].sum().reset_index()
            fig_profit = px.bar(df_profit_harian, x='Tanggal', y='Profit_Val', template="plotly_dark", color_discrete_sequence=['#14B8A6'])
            st.plotly_chart(fig_profit, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📜 Riwayat Sesi Kerja Sebelumnya")
    
    if data_sesi and len(data_sesi) > 1:
        df_riwayat_sesi = pd.DataFrame(data_sesi[1:], columns=data_sesi[0])
        df_sesi_display = df_riwayat_sesi.copy()
        for col in ['Modal_Cash', 'Modal_Digital', 'Total_Cash_Akhir', 'Total_Digital_Akhir', 'Total_Profit']:
            if col in df_sesi_display.columns:
                df_sesi_display[col] = df_sesi_display[col].apply(lambda x: f_uang(x) if str(x).isdigit() else x)
        
        st.dataframe(df_sesi_display, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Hapus Baris Sesi Tertentu Dari Database"):
            list_pilihan_sesi_hapus = []
            map_row_sesi = {}
            for idx_s, row_s in enumerate(data_sesi[1:], start=2):
                label_sesi_h = f"Baris #{idx_s} | Waktu Tutup: {row_s[0]} (Profit: {f_uang(row_s[5]) if len(row_s)>5 else 'Rp 0'})"
                list_pilihan_sesi_hapus.append(label_sesi_h)
                map_row_sesi[label_sesi_h] = idx_s

            pilihan_target_hapus = st.selectbox("Pilih Sesi Yang Ingin Dihapus:", options=list_pilihan_sesi_hapus)
            konfirm_h_sesi_db = st.checkbox("Saya yakin ingin menghapus data riwayat sesi ini secara permanen", key="chk_del_sesi_db")
            
            if konfirm_h_sesi_db:
                if st.button("❌ Hapus Sesi Dari Database", type="primary"):
                    row_index_target = map_row_sesi[pilihan_target_hapus]
                    if safe_delete(ws_sesi, row_index_target):
                        st.cache_data.clear()
                        st.success("Baris riwayat sesi berhasil dihapus!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Gagal menghapus baris sesi!")

    else: st.info("Belum ada riwayat sesi yang ditutup.")

# --- TAB 4: STOK BARANG ---
with tab4:
    existing_categories = ["Perdana", "Voucher", "Aksesoris", "Umum"]
    if data_s and len(data_s) > 1:
        for r in data_s[1:]:
            if len(r) > 6 and r[6] and r[6] not in existing_categories: existing_categories.append(r[6])

    with st.expander("➕ Tambah Barang Baru"):
        barcode_input = st.text_input("Nomor Barcode / Label:")
        nama_barang = st.text_input("Nama Barang:")
        opsi_kategori = existing_categories + ["+ Buat Kategori Baru..."]
        pilih_kat_tambah = st.selectbox("Pilih Kategori Barang:", options=opsi_kategori, key="sel_kat_tambah")
        
        if pilih_kat_tambah == "+ Buat Kategori Baru...":
            kategori_barang = st.text_input("Ketik Nama Kategori Baru:", value="", key="input_kat_baru_tambah")
        else: kategori_barang = pilih_kat_tambah

        stok_awal = st.number_input("Jumlah Stok:", min_value=1, step=1)
        harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
        if harga_modal > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_modal)}**")
            
        harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
        if harga_jual > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_jual)}**")
            
        kode_cepat_brg = st.text_input("Kode Cepat Barang (Contoh: SPI, VCG1):")
        
        if st.button("💾 Simpan Barang", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
            st.session_state['is_submitting'] = True
            final_kat = kategori_barang if kategori_barang.strip() else "Umum"
            if nama_barang:
                if safe_append(ws_s, [barcode_input, nama_barang, int(stok_awal), int(harga_modal), int(harga_jual), kode_cepat_brg, final_kat]):
                    st.cache_data.clear()
                    st.session_state['is_submitting'] = False
                    st.success("Tersimpan!")
                    time.sleep(0.5)
                    st.rerun()
                else: 
                    st.session_state['is_submitting'] = False
                    st.error("Gagal simpan barang!")

    st.markdown("---")
    if data_s and len(data_s) > 1:
        rows_stok = data_s[1:]
        normalized_rows = []
        for r in rows_stok:
            while len(r) < 7: r.append("Umum")
            normalized_rows.append(r)
            
        df_s = pd.DataFrame(normalized_rows, columns=['Barcode', 'Nama_Barang', 'Stok', 'Harga_Modal', 'Harga_Jual', 'Kode_Cepat', 'Kategori'])
        df_s['No_Baris'] = range(2, len(df_s) + 2)

        list_kategori_filter = ["Semua Kategori"] + sorted(df_s['Kategori'].dropna().unique().tolist())
        pilih_filter_kat = st.selectbox("Filter Berdasarkan Kategori:", options=list_kategori_filter)
        
        df_s_filtered = df_s.copy()
        if pilih_filter_kat != "Semua Kategori": df_s_filtered = df_s_filtered[df_s_filtered['Kategori'] == pilih_filter_kat]

        st.markdown("---")
        for index, row in df_s_filtered.iterrows():
            b_stok = int(row['No_Baris'])
            bc = row['Barcode']
            nm = row['Nama_Barang']
            stk = row['Stok']
            h_modal = f_uang(row['Harga_Modal']) if str(row['Harga_Modal']).isdigit() else row['Harga_Modal']
            h_jual = f_uang(row['Harga_Jual']) if str(row['Harga_Jual']).isdigit() else row['Harga_Jual']
            kat = row['Kategori'] if row['Kategori'] else "Umum"
            
            st.markdown(f"**{nm}** | <span style='color:#14B8A6;'>[{kat}]</span> (Stok: {stk})<br>Modal: {h_modal} | Jual: {h_jual}<br>Barcode: {bc}", unsafe_allow_html=True)
            
            col_stk1, col_stk2 = st.columns(2)
            with col_stk1:
                if st.button("❌ Hapus", key=f"del_stk_{b_stok}", use_container_width=True): st.session_state[f"konfirm_stk_{b_stok}"] = True
            with col_stk2:
                if st.button("✏️ Edit", key=f"edit_stok_btn_{b_stok}", use_container_width=True): st.session_state[f"mode_edit_stk_{b_stok}"] = True
            
            if st.session_state.get(f"konfirm_stk_{b_stok}", False):
                st.error(f"Yakin ingin menghapus {nm}?")
                cs_y, cs_n = st.columns(2)
                if cs_y.button("Ya, Hapus Stok!", key=f"y_stk_{b_stok}", type="primary"):
                    if safe_delete(ws_s, b_stok):
                        st.cache_data.clear()
                        st.success("Stok dihapus!")
                        st.session_state[f"konfirm_stk_{b_stok}"] = False
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error("Gagal hapus stok!")
                if cs_n.button("Batal", key=f"n_stk_{b_stok}"):
                    st.session_state[f"konfirm_stk_{b_stok}"] = False
                    st.rerun()

            if st.session_state.get(f"mode_edit_stk_{b_stok}", False):
                with st.form(key=f"form_edit_stok_{b_stok}"):
                    st.write(f"Edit Data: {nm}")
                    es_bc = st.text_input("Barcode", value=bc)
                    es_nm = st.text_input("Nama Barang", value=nm)
                    es_stk = st.number_input("Stok", value=int(stk) if str(stk).isdigit() else 0, step=1)
                    es_mod = st.number_input("Harga Modal", value=int(row['Harga_Modal']) if str(row['Harga_Modal']).isdigit() else 0, step=1000)
                    es_jul = st.number_input("Harga Jual", value=int(row['Harga_Jual']) if str(row['Harga_Jual']).isdigit() else 0, step=1000)
                    es_kod = st.text_input("Kode Cepat", value=row['Kode_Cepat'])
                    
                    opsi_kat_edit = existing_categories + ["+ Buat Kategori Baru..."]
                    default_kat_idx = opsi_kat_edit.index(kat) if kat in opsi_kat_edit else 0
                    es_pilih_kat = st.selectbox("Kategori Barang", options=opsi_kat_edit, index=default_kat_idx)
                    if es_pilih_kat == "+ Buat Kategori Baru...":
                        es_kat = st.text_input("Ketik Kategori Baru", value="", key=f"input_kat_baru_edit_{b_stok}")
                    else: es_kat = es_pilih_kat
                    
                    if st.form_submit_button("Simpan Perubahan Stok"):
                        final_es_kat = es_kat if es_kat.strip() else kat
                        if safe_update(ws_s, f"A{b_stok}:G{b_stok}", [[es_bc, es_nm, int(es_stk), int(es_mod), int(es_jul), es_kod, final_es_kat]]):
                            st.session_state[f"mode_edit_stk_{b_stok}"] = False
                            st.cache_data.clear()
                            st.success("Stok diperbarui!")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("Gagal perbarui stok!")

            st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
    else:
        st.info("Belum ada data stok.")
        if ws_s and data_s is not None and len(data_s) == 0:
            safe_append(ws_s, ["Barcode", "Nama_Barang", "Stok", "Harga_Modal", "Harga_Jual", "Kode_Cepat", "Kategori"])
            st.cache_data.clear()
            st.rerun()

# --- TAB 5: SETELAN & AKUN ---
with tab5:
    idx_cabang_aktif = daftar_tampilan_cabang.index(st.session_state['cabang_terpilih']) if st.session_state['cabang_terpilih'] in daftar_tampilan_cabang else 0
    pilihan_pindah = st.selectbox("Ganti Akses Cabang Ke:", daftar_tampilan_cabang, index=idx_cabang_aktif)
    
    if st.button("PINDAH CABANG", type="primary", use_container_width=True):
        st.session_state['cabang_terpilih'] = pilihan_pindah
        st.query_params["cabang"] = pilihan_pindah
        if 'modal_cash' in st.session_state: del st.session_state['modal_cash']
        if 'modal_digi' in st.session_state: del st.session_state['modal_digi']
        st.session_state['keranjang_belanja'] = []
        st.session_state['draf_scan_smart'] = []
        st.cache_data.clear()
        st.success(f"Berhasil pindah akses ke {pilihan_pindah}!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔐 Pengaturan Akun Master")
    st.info("Akun ini digunakan untuk mengontrol seluruh cabang.")
    
    with st.form("form_ubah_akun"):
        user_baru = st.text_input("Username Master Baru", value=db_user)
        pass_baru = st.text_input("Password Master Baru", value=db_pass, type="password")
        
        if st.form_submit_button("Simpan Perubahan Akun"):
            if user_baru and pass_baru:
                if ws_akun_master:
                    ws_akun_master.update_cell(1, 1, user_baru)
                    ws_akun_master.update_cell(1, 2, pass_baru)
                    st.success("Username & Password berhasil diperbarui!")
                else: st.error("Gagal terhubung ke database setelan.")
            else: st.error("Form tidak boleh kosong!")

    st.markdown("---")
    if st.button("🚪 Keluar / Logout Aplikasi", use_container_width=True):
        st.session_state['is_logged_in'] = False
        if "auth" in st.query_params: del st.query_params["auth"]
        if "cabang" in st.query_params: del st.query_params["cabang"]
        st.cache_data.clear()
        st.rerun()
