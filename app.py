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

# --- KONFIGURASI HALAMAN HARUS PALING ATAS ---
st.set_page_config(page_title="RABAY CELL PRO", layout="centered", page_icon="🚀", initial_sidebar_state="collapsed")

# --- CUSTOM CSS UI MODERN DARK MODE, FLOATING BUTTON & ANIMASI GOOGLE LENS ---
st.markdown("""
    <style>
    /* Paksa Background Gelap */
    .stApp { background-color: #050505; color: #ffffff; }
    
    /* Header Kustom */
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
    
    /* Styling Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px !important;
        color: #cccccc !important;
        background-color: transparent !important;
        padding: 10px 15px !important;
        font-weight: 600 !important;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #14B8A6 !important;
        color: white !important;
    }
    
    /* Styling Input Box & Container */
    div[data-baseweb="input"] {
        background-color: #1E1E1E !important;
        border-radius: 8px !important;
        border: 1px solid #14B8A6 !important;
    }
    input { color: #14B8A6 !important; font-weight: bold !important; text-align: center !important; font-size: 18px !important;}
    
    /* Barcode Box Area */
    .barcode-box {
        margin-bottom: 20px;
        margin-top: 10px;
    }
    
    /* Sembunyikan Label Default */
    label, .stRadio label { color: #cccccc !important; }
    
    /* Kartu Metrik Dashboard (Dark Mode) */
    .metric-card-blue { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid #14B8A6; margin-bottom: 15px; }
    .metric-card-green { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid #2ca02c; margin-bottom: 15px; }
    
    /* Tombol Floating Melayang di Bagian Bawah Layar */
    .floating-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: rgba(5, 5, 5, 0.95);
        padding: 12px 16px;
        z-index: 99999;
        border-top: 1px solid #222;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.8);
    }
    
    /* Berijarak bawah pada konten agar tidak tertutup tombol floating */
    .main .block-container {
        padding-bottom: 90px;
    }

    /* Login Box */
    .login-box {
        background-color: #111;
        padding: 30px;
        border-radius: 12px;
        border: 1px solid #14B8A6;
        margin-top: 50px;
        text-align: center;
    }
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

# --- FUNGSI AMBIL KREDENSIAL AKUN MASTER DARI DATABASE ---
def get_master_credentials(sh):
    if not sh: return "admin", "123", None
    try:
        ws_akun = sh.worksheet("Pengaturan_Akun")
    except:
        ws_akun = sh.add_worksheet(title="Pengaturan_Akun", rows=2, cols=2)
        
    data = ws_akun.get_all_values()
    if len(data) > 1 and len(data[1]) >= 2:
        return data[1][0], data[1][1], ws_akun
    else:
        ws_akun.clear()
        ws_akun.append_row(["Username", "Password"])
        ws_akun.append_row(["admin", "123"])
        return "admin", "123", ws_akun

db_user, db_pass, ws_akun_master = get_master_credentials(sh_master)

# --- SISTEM LOGIN MASTER TAHAN REFRESH ---
if 'is_logged_in' not in st.session_state:
    if st.query_params.get("auth") == "1":
        st.session_state['is_logged_in'] = True
    else:
        st.session_state['is_logged_in'] = False

if 'cabang_terpilih' not in st.session_state:
    if st.query_params.get("cabang"):
        st.session_state['cabang_terpilih'] = st.query_params.get("cabang")
    else:
        st.session_state['cabang_terpilih'] = "Pusat"

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

# --- FUNGSI AMBIL DATABASE BERDASARKAN CABANG TERPILIH ---
def get_branch_worksheets(sh, cabang):
    if not sh: return None, None, None
    s_tr, s_ks, s_st = f"Transaksi_{cabang}", f"Kas_Harian_{cabang}", f"Stok_{cabang}"
    try: ws_t = sh.worksheet(s_tr)
    except: ws_t = sh.add_worksheet(title=s_tr, rows=1000, cols=6)
    try: ws_k = sh.worksheet(s_ks)
    except: ws_k = sh.add_worksheet(title=s_ks, rows=1000, cols=5)
    try: ws_s = sh.worksheet(s_st)
    except: ws_s = sh.add_worksheet(title=s_st, rows=1000, cols=7)
    return ws_t, ws_k, ws_s

ws_t, ws_k, ws_s = get_branch_worksheets(sh_master, st.session_state['cabang_terpilih'])

def ambil_modal_terakhir():
    if ws_k:
        try:
            data_k = ws_k.get_all_values()
            if len(data_k) > 1: return int(data_k[-1][1]), int(data_k[-1][2])
        except: pass
    return 0, 0

if 'modal_cash' not in st.session_state or 'modal_digi' not in st.session_state:
    c_awal, d_awal = ambil_modal_terakhir()
    st.session_state['modal_cash'] = c_awal
    st.session_state['modal_digi'] = d_awal

if 'penyesuaian_cash' not in st.session_state: st.session_state['penyesuaian_cash'] = 0
if 'penyesuaian_digi' not in st.session_state: st.session_state['penyesuaian_digi'] = 0
if 'draf_scan_smart' not in st.session_state: st.session_state['draf_scan_smart'] = []
if 'keranjang_belanja' not in st.session_state: st.session_state['keranjang_belanja'] = []

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

# --- HEADER CUSTOM UI ---
st.markdown(f"""
    <div class="rabay-header">
        <h1>RABAY CELL - {st.session_state['cabang_terpilih'].upper()}</h1>
    </div>
""", unsafe_allow_html=True)

# --- TAB NAVIGASI ---
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
            if ws_s:
                stok_data = ws_s.get_all_values()
                if len(stok_data) > 1:
                    df_s_check = pd.DataFrame(stok_data[1:])
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
            
            # --- TOMBOL SIMPAN LANGSUNG FLOATING ---
            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 SIMPAN LANGSUNG", type="primary", use_container_width=True):
                    waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                    if jenis_terpilih == "Penjualan Barang" and ws_s and row_brg_det:
                        stok_skrg = int(ws_s.cell(row_brg_det, 3).value)
                        if stok_skrg > 0: ws_s.update_cell(row_brg_det, 3, stok_skrg - 1)
                    
                    if ws_t: ws_t.append_row([waktu, jenis_terpilih, nominal_trx, admin, total_uang, profit_bersih])
                    st.success("Tersimpan!")
                    st.rerun()

            with col_b2:
                if st.button("🛒 MASUK KERANJANG", use_container_width=True):
                    st.session_state['keranjang_belanja'].append({
                        'Jenis': jenis_terpilih, 'Nama': nama_brg_det if nama_brg_det else jenis_terpilih,
                        'Nominal': nominal_trx, 'Admin/Profit': profit_bersih, 'Total': total_uang, 'Row_Stok': row_brg_det
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
            if c_k1.button("🚀 PROSES SEMUA", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state['keranjang_belanja']:
                    j_trx, nom_trx, adm_trx, tot_trx, r_stok = item['Jenis'], item['Nominal'], item['Admin/Profit'], item['Total'], item['Row_Stok']
                    if j_trx == "Penjualan Barang" and ws_s and r_stok:
                        stok_skrg = int(ws_s.cell(r_stok, 3).value)
                        if stok_skrg > 0: ws_s.update_cell(r_stok, 3, stok_skrg - 1)
                        
                    if ws_t: ws_t.append_row([waktu, j_trx, nom_trx, adm_trx, tot_trx, adm_trx])
                st.session_state['keranjang_belanja'] = []
                st.success("Selesai!")
                st.rerun()
                
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
            except Exception as e: 
                st.error(f"Gagal scan: {e}")

        if st.session_state['draf_scan_smart']:
            st.markdown("---")
            st.info(f"✨ Berhasil mendeteksi {len(st.session_state['draf_scan_smart'])} transaksi.")
            
            st.markdown("<b>Ubah Jenis Semua Transaksi Minus (-) Sekaligus:</b>", unsafe_allow_html=True)
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
                with col_h1:
                    st.markdown(f"**Trx #{i+1} ({item['Tanda']})** - {f_uang(item['Nominal (Rp)'])}")
                with col_h2:
                    if st.button("❌", key=f"del_ocr_{i}", help="Hapus item"):
                        indices_to_delete.append(i)
                
                if item['Tanda'] == '+':
                    jns_pilih = "Tarik Tunai"
                    st.markdown("<p style='color:#14B8A6; font-size:13px; margin:0;'>Jenis: <b>Tarik Tunai (Otomatis)</b></p>", unsafe_allow_html=True)
                else:
                    pilihan_opsi_ocr = ["Bank", "E-Wallet", "Tarik Tunai"]
                    if f"ocr_jns_{i}" not in st.session_state:
                        st.session_state[f"ocr_jns_{i}"] = item['Jenis Otomatis']
                    
                    jns_pilih = st.selectbox(f"Pilih Jenis Trx #{i+1}", options=pilihan_opsi_ocr, key=f"ocr_jns_{i}")
                    item['Jenis Otomatis'] = jns_pilih
                
                est_admin = hitung_admin(item['Nominal (Rp)'], jns_pilih)
                st.markdown(f"<p style='color:#2ca02c; font-size:13px; margin-top:2px;'>💰 Estimasi Admin (Cuan): <b>{f_uang(est_admin)}</b></p>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:10px 0; border-color:#333;'>", unsafe_allow_html=True)
            
            if indices_to_delete:
                st.session_state['draf_scan_smart'] = [item for idx, item in enumerate(st.session_state['draf_scan_smart']) if idx not in indices_to_delete]
                st.rerun()

            # --- TOMBOL SIMPAN SEMUA OCR FLOATING ---
            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            if st.button("💾 SIMPAN SEMUA TRANSAKSI OCR", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for i, item in enumerate(st.session_state['draf_scan_smart']):
                    jenis = "Tarik Tunai" if item['Tanda'] == '+' else st.session_state.get(f"ocr_jns_{i}", item['Jenis Otomatis'])
                    nom = item['Nominal (Rp)']
                    admin = hitung_admin(nom, jenis)
                    total = nom - admin if jenis == "Tarik Tunai" else nom + admin
                    profit_ocr = admin
                    if ws_t: ws_t.append_row([waktu, jenis, nom, admin, total, profit_ocr])
                    
                st.session_state['draf_scan_smart'] = []
                st.success("Semua transaksi berhasil disimpan!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: RIWAYAT ---
with tab2:
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_t = pd.DataFrame(data_t[1:], columns=data_t[0])
            df_t['No_Baris'] = range(2, len(df_t) + 2)
            df_t['Tanggal_Saja'] = pd.to_datetime(df_t.iloc[:, 0], errors='coerce').dt.date
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                kolom_jenis = df_t.columns[1] if len(df_t.columns) > 1 else 'Jenis'
                pilih_filter_jenis = st.selectbox("Jenis:", options=["Semua"] + df_t[kolom_jenis].unique().tolist(), key="filter_j_trx")
            with col_f2:
                pilih_filter_tgl = st.selectbox("Tanggal:", options=["Semua Tanggal"] + [str(t) for t in sorted(df_t['Tanggal_Saja'].dropna().unique(), reverse=True)], key="filter_t_trx")
            
            df_t_filtered = df_t.copy()
            if pilih_filter_jenis != "Semua": df_t_filtered = df_t_filtered[df_t_filtered[kolom_jenis] == pilih_filter_jenis]
            if pilih_filter_tgl != "Semua Tanggal": df_t_filtered = df_t_filtered[df_t_filtered['Tanggal_Saja'].astype(str) == pilih_filter_tgl]
            
            profit_filter_val = pd.to_numeric(df_t_filtered.iloc[:, 5], errors='coerce').fillna(0).sum() if len(df_t_filtered) > 0 else 0
            st.markdown(f"""
                <div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border:1px solid #2ca02c; text-align:center; margin:15px 0;">
                    <span style="color:#2ca02c; font-size:14px; font-weight:bold;">🔥 TOTAL PROFIT (FILTER AKTIF):</span><br>
                    <span style="color:#fff; font-size:20px; font-weight:bold;">{f_uang(profit_filter_val)}</span>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚠️ Hapus Semua Riwayat Transaksi"):
                st.warning(f"PERINGATAN: Seluruh riwayat transaksi di cabang {st.session_state['cabang_terpilih']} akan dihapus!")
                konfirm_hapus_semua = st.checkbox("Iya, saya yakin ingin menghapus semua riwayat", key="chk_del_all_trx")
                if konfirm_hapus_semua:
                    if st.button("🗑️ Hapus Permanen", type="primary"):
                        ws_t.clear()
                        ws_t.append_row(data_t[0])
                        st.success("Semua riwayat berhasil dihapus!")
                        st.rerun()

            st.markdown("---")
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
                        st.session_state[f"konfirm_trx_{b_num}"] = True
                with col_btn2:
                    if st.button("✏️ Edit", key=f"edit_trx_{b_num}", use_container_width=True):
                        st.session_state[f"mode_edit_trx_{b_num}"] = True
                
                if st.session_state.get(f"konfirm_trx_{b_num}", False):
                    st.error(f"Yakin ingin menghapus baris {b_num}?")
                    c_y, c_n = st.columns(2)
                    if c_y.button("Ya, Hapus!", key=f"y_trx_{b_num}", type="primary"):
                        ws_t.delete_rows(b_num)
                        st.success("Berhasil dihapus!")
                        st.session_state[f"konfirm_trx_{b_num}"] = False
                        st.rerun()
                    if c_n.button("Batal", key=f"n_trx_{b_num}"):
                        st.session_state[f"konfirm_trx_{b_num}"] = False
                        st.rerun()

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
                            ws_t.update(f"A{b_num}:F{b_num}", [[e_waktu, e_jenis, e_nom, e_adm, e_tot, e_prof]])
                            st.session_state[f"mode_edit_trx_{b_num}"] = False
                            st.success("Perubahan disimpan!")
                            st.rerun()

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
        else: 
            st.info("Belum ada riwayat transaksi.")
            if len(data_t) == 0:
                ws_t.append_row(["Waktu", "Jenis", "Nominal", "Admin", "Total", "Profit"])
                st.rerun()

# --- TAB 3: DASHBOARD ---
with tab3:
    with st.expander("💰 Setel Modal Awal Hari Ini", expanded=False):
        input_cash_baru = st.number_input("Setel Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
        if input_cash_baru > 0: st.caption(f"👀 Terbaca: **{f_uang(input_cash_baru)}**")
            
        input_digi_baru = st.number_input("Setel Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)
        if input_digi_baru > 0: st.caption(f"👀 Terbaca: **{f_uang(input_digi_baru)}**")
            
        if st.button("💾 Simpan Modal Baru", type="primary", use_container_width=True):
            st.session_state['modal_cash'] = input_cash_baru
            st.session_state['modal_digi'] = input_digi_baru
            waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            if ws_k: ws_k.append_row([waktu, input_cash_baru, input_digi_baru]) 
            st.success("Modal awal diperbarui!")
            st.rerun()

    st.markdown("---")

    tot_transaksi_cash = 0
    tot_transaksi_digi = 0
    profit_hari_ini = 0
    
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_trx = pd.DataFrame(data_t[1:])
            if len(df_trx.columns) >= 6:
                df_trx['Tanggal'] = pd.to_datetime(df_trx.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
                tgl_hari_ini = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d')
                df_hari_ini = df_trx[df_trx['Tanggal'] == tgl_hari_ini].copy()
                
                if not df_hari_ini.empty:
                    profit_hari_ini = pd.to_numeric(df_hari_ini.iloc[:, 5], errors='coerce').fillna(0).sum()
                    for idx, r in df_hari_ini.iterrows():
                        jns = r.iloc[1]
                        nom = float(r.iloc[2]) if str(r.iloc[2]).replace('.','',1).isdigit() else 0
                        tot = float(r.iloc[4]) if str(r.iloc[4]).replace('.','',1).isdigit() else 0
                        
                        if jns in ["Penjualan Barang", "Transaksi Lainnya"]:
                            tot_transaksi_cash += tot
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
            <h4 style="margin:0; color:#14B8A6;">💵 Cash di Laci</h4>
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
            <h4 style="margin:0; color:#14B8A6;">💳 Saldo Digital</h4>
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
            <h4 style="margin:0; color:#2ca02c;">🔥 Profit Hari Ini</h4>
            <h1 style="margin:5px 0 0 0; color:#fff;">{f_uang(profit_hari_ini)}</h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📈 Grafik Profit Harian")
    if ws_t and len(data_t) > 1:
        df_trx_all = pd.DataFrame(data_t[1:])
        if len(df_trx_all.columns) >= 6:
            df_trx_all['Tanggal'] = pd.to_datetime(df_trx_all.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
            df_trx_all['Profit_Val'] = pd.to_numeric(df_trx_all.iloc[:, 5], errors='coerce').fillna(0)
            df_profit_harian = df_trx_all.groupby('Tanggal')['Profit_Val'].sum().reset_index()
            
            fig_profit = px.bar(df_profit_harian, x='Tanggal', y='Profit_Val', template="plotly_dark", color_discrete_sequence=['#14B8A6'])
            st.plotly_chart(fig_profit, use_container_width=True)

# --- TAB 4: STOK BARANG ---
with tab4:
    existing_categories = ["Perdana", "Voucher", "Aksesoris", "Umum"]
    if ws_s:
        data_s_raw = ws_s.get_all_values()
        if len(data_s_raw) > 1:
            for r in data_s_raw[1:]:
                if len(r) > 6 and r[6] and r[6] not in existing_categories:
                    existing_categories.append(r[6])

    with st.expander("➕ Tambah Barang Baru"):
        barcode_input = st.text_input("Nomor Barcode / Label:")
        nama_barang = st.text_input("Nama Barang:")
        
        opsi_kategori = existing_categories + ["+ Buat Kategori Baru..."]
        pilih_kat_tambah = st.selectbox("Pilih Kategori Barang:", options=opsi_kategori, key="sel_kat_tambah")
        
        if pilih_kat_tambah == "+ Buat Kategori Baru...":
            kategori_barang = st.text_input("Ketik Nama Kategori Baru:", value="", key="input_kat_baru_tambah")
        else:
            kategori_barang = pilih_kat_tambah

        stok_awal = st.number_input("Jumlah Stok:", min_value=1, step=1)
        
        harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
        if harga_modal > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_modal)}**")
            
        harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
        if harga_jual > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_jual)}**")
            
        kode_cepat_brg = st.text_input("Kode Cepat Barang (Contoh: SPI, VCG1):")
        
        if st.button("💾 Simpan Barang", type="primary", use_container_width=True):
            final_kat = kategori_barang if kategori_barang.strip() else "Umum"
            if ws_s and nama_barang:
                ws_s.append_row([barcode_input, nama_barang, stok_awal, harga_modal, harga_jual, kode_cepat_brg, final_kat])
                st.success("Tersimpan!")
                st.rerun()

    st.markdown("---")
    if ws_s:
        data_s = ws_s.get_all_values()
        if len(data_s) > 1:
            rows_stok = data_s[1:]
            normalized_rows = []
            for r in rows_stok:
                while len(r) < 7:
                    r.append("Umum")
                normalized_rows.append(r)
                
            df_s = pd.DataFrame(normalized_rows, columns=['Barcode', 'Nama_Barang', 'Stok', 'Harga_Modal', 'Harga_Jual', 'Kode_Cepat', 'Kategori'])
            df_s['No_Baris'] = range(2, len(df_s) + 2)

            list_kategori_filter = ["Semua Kategori"] + sorted(df_s['Kategori'].dropna().unique().tolist())
            pilih_filter_kat = st.selectbox("Filter Berdasarkan Kategori:", options=list_kategori_filter)
            
            df_s_filtered = df_s.copy()
            if pilih_filter_kat != "Semua Kategori":
                df_s_filtered = df_s_filtered[df_s_filtered['Kategori'] == pilih_filter_kat]

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
                    if st.button("❌ Hapus", key=f"del_stk_{b_stok}", use_container_width=True):
                        st.session_state[f"konfirm_stk_{b_stok}"] = True
                with col_stk2:
                    if st.button("✏️ Edit", key=f"edit_stok_btn_{b_stok}", use_container_width=True):
                        st.session_state[f"mode_edit_stk_{b_stok}"] = True
                
                if st.session_state.get(f"konfirm_stk_{b_stok}", False):
                    st.error(f"Yakin ingin menghapus {nm}?")
                    cs_y, cs_n = st.columns(2)
                    if cs_y.button("Ya, Hapus Stok!", key=f"y_stk_{b_stok}", type="primary"):
                        ws_s.delete_rows(b_stok)
                        st.success("Stok dihapus!")
                        st.session_state[f"konfirm_stk_{b_stok}"] = False
                        st.rerun()
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
                        else:
                            es_kat = es_pilih_kat
                        
                        if st.form_submit_button("Simpan Perubahan Stok"):
                            final_es_kat = es_kat if es_kat.strip() else kat
                            ws_s.update(f"A{b_stok}:G{b_stok}", [[es_bc, es_nm, es_stk, es_mod, es_jul, es_kod, final_es_kat]])
                            st.session_state[f"mode_edit_stk_{b_stok}"] = False
                            st.success("Stok diperbarui!")
                            st.rerun()

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
        else:
            st.info("Belum ada data stok.")
            if len(data_s) == 0:
                ws_s.append_row(["Barcode", "Nama_Barang", "Stok", "Harga_Modal", "Harga_Jual", "Kode_Cepat", "Kategori"])
                st.rerun()

# --- TAB 5: SETELAN & AKUN ---
with tab5:
    daftar_cabang = ["Pusat", "Cabang 2", "Cabang 3"]
    idx_cabang_aktif = daftar_cabang.index(st.session_state['cabang_terpilih']) if st.session_state['cabang_terpilih'] in daftar_cabang else 0
    pilihan_pindah = st.selectbox("Ganti Akses Cabang Ke:", daftar_cabang, index=idx_cabang_aktif)
    
    if st.button("PINDAH CABANG", type="primary", use_container_width=True):
        st.session_state['cabang_terpilih'] = pilihan_pindah
        st.query_params["cabang"] = pilihan_pindah
        if 'modal_cash' in st.session_state: del st.session_state['modal_cash']
        if 'modal_digi' in st.session_state: del st.session_state['modal_digi']
        st.session_state['keranjang_belanja'] = []
        st.session_state['draf_scan_smart'] = []
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
                    ws_akun_master.update_cell(2, 1, user_baru)
                    ws_akun_master.update_cell(2, 2, pass_baru)
                    st.success("Username & Password berhasil diperbarui!")
                else:
                    st.error("Gagal terhubung ke database setelan.")
            else:
                st.error("Form tidak boleh kosong!")

    st.markdown("---")
    if st.button("🚪 Keluar / Logout Aplikasi", use_container_width=True):
        st.session_state['is_logged_in'] = False
        if "auth" in st.query_params: del st.query_params["auth"]
        if "cabang" in st.query_params: del st.query_params["cabang"]
        st.rerun()
