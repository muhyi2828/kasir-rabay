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

# --- KONFIGURASI HALAMAN HARUS PALING ATAS ---
st.set_page_config(page_title="RABAY CELL PRO", layout="centered", page_icon="🚀", initial_sidebar_state="collapsed")

# --- CUSTOM CSS UI MODERN DARK MODE ALA RABAY CELL ---
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
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px !important;
        color: #cccccc !important;
        background-color: transparent !important;
        padding: 10px 15px !important;
        font-weight: 600 !important;
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
    
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI FORMAT UANG ---
def f_uang(val):
    try:
        val_int = int(val)
        return f"Rp {val_int:,}".replace(",", ".")
    except:
        return str(val)

@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        
        try: ws_t = sh.worksheet("Transaksi")
        except: ws_t = sh.add_worksheet(title="Transaksi", rows=1000, cols=6)
            
        try: ws_k = sh.worksheet("Kas_Harian")
        except: ws_k = sh.add_worksheet(title="Kas_Harian", rows=1000, cols=5)

        try: ws_s = sh.worksheet("Stok")
        except: ws_s = sh.add_worksheet(title="Stok", rows=1000, cols=6)
            
        return sh, ws_t, ws_k, ws_s
    except: return None, None, None, None

db, ws_t, ws_k, ws_s = konek_gsheets()

# --- FUNGSI BACA & UPDATE MODAL KE DATABASE ---
def ambil_modal_terakhir():
    if ws_k:
        try:
            data_k = ws_k.get_all_values()
            if len(data_k) > 1: 
                baris_terakhir = data_k[-1]
                return int(baris_terakhir[1]), int(baris_terakhir[2])
        except: pass
    return 0, 0

def update_kas_db():
    if ws_k:
        try:
            data_k = ws_k.get_all_values()
            if len(data_k) > 1:
                last_row = len(data_k)
                ws_k.update_cell(last_row, 2, st.session_state['modal_cash'])
                ws_k.update_cell(last_row, 3, st.session_state['modal_digi'])
            else:
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                ws_k.append_row([waktu, st.session_state['modal_cash'], st.session_state['modal_digi']])
        except: pass

# --- INISIALISASI STATE ---
if 'modal_cash' not in st.session_state or 'modal_digi' not in st.session_state:
    c_awal, d_awal = ambil_modal_terakhir()
    st.session_state['modal_cash'] = c_awal
    st.session_state['modal_digi'] = d_awal

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
st.markdown("""
    <div class="rabay-header">
        <h1>RABAY CELL</h1>
    </div>
""", unsafe_allow_html=True)

# --- TAB NAVIGASI ---
tab1, tab2, tab3, tab4 = st.tabs(["TRANSAKSI", "RIWAYAT", "DASHBOARD", "STOK BARANG"])

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
                    df_s_check = pd.DataFrame(stok_data[1:], columns=stok_data[0])
                    df_s_check['Row_Idx'] = range(2, len(df_s_check) + 2)
                    
                    match_barang = df_s_check[(df_s_check['Kode_Cepat'].str.upper() == code) | (df_s_check['Barcode'].str.upper() == code)]
                    if not match_barang.empty:
                        namabarang = match_barang.iloc[0]['Nama_Barang']
                        hargamodal = int(match_barang.iloc[0]['Harga_Modal'])
                        hargajual = int(match_barang.iloc[0]['Harga_Jual'])
                        
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

        if nominal_trx > 0 or (jenis_terpilih == "Transaksi Lainnya" and nominal_trx >= 0):
            if jenis_terpilih == "Penjualan Barang":
                admin = 0
                total_uang = nominal_trx
                profit_bersih = profit_brg_det if profit_brg_det > 0 else 0
            elif jenis_terpilih == "Transaksi Lainnya":
                admin = 0
                total_uang = nominal_trx
                profit_bersih = profit_manual
            else:
                admin = hitung_admin(nominal_trx, jenis_terpilih)
                total_uang = nominal_trx + admin if jenis_terpilih != "Tarik Tunai" else nominal_trx - admin
                profit_bersih = admin
                
                c1, c2 = st.columns(2)
                c1.metric("Admin (Cuan)", f"{f_uang(admin)}")
                if jenis_terpilih == "Tarik Tunai":
                    c2.metric("Berikan Tunai", f"{f_uang(total_uang)}")
                else:
                    c2.metric("Tagih Pelanggan", f"{f_uang(total_uang)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 SIMPAN LANGSUNG", type="primary", use_container_width=True):
                    waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                    if jenis_terpilih == "Penjualan Barang":
                        st.session_state['modal_cash'] += nominal_trx
                        if ws_s and row_brg_det:
                            stok_skrg = int(ws_s.cell(row_brg_det, 3).value)
                            if stok_skrg > 0: ws_s.update_cell(row_brg_det, 3, stok_skrg - 1)
                    elif jenis_terpilih == "Transaksi Lainnya":
                        st.session_state['modal_cash'] += nominal_trx
                    elif jenis_terpilih == "Tarik Tunai":
                        st.session_state['modal_cash'] -= total_uang
                        st.session_state['modal_digi'] += nominal_trx
                    else:
                        st.session_state['modal_digi'] -= nominal_trx
                        st.session_state['modal_cash'] += total_uang
                    
                    if ws_t: ws_t.append_row([waktu, jenis_terpilih, nominal_trx, admin, total_uang, profit_bersih])
                    update_kas_db() 
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

        # Fitur Keranjang
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
                    
                    if j_trx == "Penjualan Barang":
                        st.session_state['modal_cash'] += nom_trx
                        if ws_s and r_stok:
                            stok_skrg = int(ws_s.cell(r_stok, 3).value)
                            if stok_skrg > 0: ws_s.update_cell(r_stok, 3, stok_skrg - 1)
                    elif j_trx == "Transaksi Lainnya": st.session_state['modal_cash'] += nom_trx
                    elif j_trx == "Tarik Tunai":
                        st.session_state['modal_cash'] -= tot_trx
                        st.session_state['modal_digi'] += nom_trx
                    else:
                        st.session_state['modal_digi'] -= nom_trx
                        st.session_state['modal_cash'] += tot_trx
                        
                    if ws_t: ws_t.append_row([waktu, j_trx, nom_trx, adm_trx, tot_trx, adm_trx])
                update_kas_db()
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
                with st.spinner("Membaca angka..."):
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    img = Image.open(sumber_gambar)
                    res = client.models.generate_content(model='gemini-3.6-flash', contents=[img, "Tulis semua nominal transaksi beserta tandanya (+ atau -). Balas dengan format angka dipisah koma, contoh: +9067000,-75000,-5000000"])
                    
                    raw_text = res.text.replace(" ", "")
                    items = raw_text.split(',')
                    processed_data = []
                    for item in items:
                        if '+' in item or '-' in item:
                            nom_val = int(re.sub(r'[^0-9]', '', item))
                            kategori = 'Tarik Tunai' if '+' in item else 'Bank'
                            tanda_simbol = '+' if '+' in item else '-'
                            processed_data.append({'Tanda': tanda_simbol, 'Jenis Otomatis': kategori, 'Nominal (Rp)': nom_val})
                    st.session_state['draf_scan_smart'] = processed_data
            except Exception as e: st.error(f"Gagal scan: {e}")

        if st.session_state['draf_scan_smart']:
            st.markdown("---")
            st.info(f"✨ Berhasil mendeteksi {len(st.session_state['draf_scan_smart'])} transaksi:")
            
            df_preview_raw = pd.DataFrame(st.session_state['draf_scan_smart'])
            df_preview_disp = df_preview_raw.copy()
            df_preview_disp['Nominal (Rp)'] = df_preview_disp['Nominal (Rp)'].apply(lambda x: f_uang(x))
            st.dataframe(df_preview_disp, use_container_width=True, hide_index=True)
            
            if st.button("💾 SIMPAN SEMUA & UPDATE KAS", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state['draf_scan_smart']:
                    nom, jenis = item['Nominal (Rp)'], item['Jenis Otomatis']
                    admin = hitung_admin(nom, jenis)
                    
                    if jenis == "Tarik Tunai":
                        total = nom - admin
                        st.session_state['modal_cash'] -= total
                        st.session_state['modal_digi'] += nom
                    else:
                        total = nom + admin
                        st.session_state['modal_digi'] -= nom
                        st.session_state['modal_cash'] += total
                        
                    if ws_t: ws_t.append_row([waktu, jenis, nom, admin, total, admin])
                update_kas_db()
                st.session_state['draf_scan_smart'] = []
                st.success("Tersimpan!")
                st.rerun()

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
                pilih_filter_jenis = st.selectbox("Jenis:", options=["Semua"] + df_t[kolom_jenis].unique().tolist())
            with col_f2:
                pilih_filter_tgl = st.selectbox("Tanggal:", options=["Semua Tanggal"] + [str(t) for t in sorted(df_t['Tanggal_Saja'].dropna().unique(), reverse=True)])
            
            df_t_filtered = df_t.copy()
            if pilih_filter_jenis != "Semua": df_t_filtered = df_t_filtered[df_t_filtered[kolom_jenis] == pilih_filter_jenis]
            if pilih_filter_tgl != "Semua Tanggal": df_t_filtered = df_t_filtered[df_t_filtered['Tanggal_Saja'].astype(str) == pilih_filter_tgl]
            
            df_t_display = df_t_filtered.drop(columns=['Tanggal_Saja'])
            for c_nm in ['Nominal', 'Admin', 'Total', 'Profit']:
                if c_nm in df_t_display.columns: df_t_display[c_nm] = df_t_display[c_nm].apply(lambda x: f_uang(x) if str(x).isdigit() else x)
            
            st.dataframe(df_t_display, use_container_width=True)
            
            baris_hapus_trx = st.multiselect("Hapus Transaksi (No Baris):", options=df_t_filtered['No_Baris'].tolist())
            if st.button("❌ Hapus Terpilih", type="primary"):
                if baris_hapus_trx:
                    for baris in sorted(baris_hapus_trx, reverse=True): ws_t.delete_rows(int(baris))
                    st.success("Terhapus!")
                    st.rerun()
        else: st.info("Belum ada riwayat transaksi.")

# --- TAB 3: DASHBOARD ---
with tab3:
    with st.expander("💰 Setel Ulang Modal / Buka Kasir", expanded=False):
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

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💵 Cash di Laci</h4>
            <h2 style="margin:5px 0 0 0; color:#fff;">{f_uang(st.session_state['modal_cash'])}</h2>
        </div>
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💳 Saldo Digital</h4>
            <h2 style="margin:5px 0 0 0; color:#fff;">{f_uang(st.session_state['modal_digi'])}</h2>
        </div>
    """, unsafe_allow_html=True)

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
                    df_hari_ini['Profit_Val'] = pd.to_numeric(df_hari_ini.iloc[:, 5], errors='coerce').fillna(0)
                    profit_hari_ini = df_hari_ini['Profit_Val'].sum()

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
    with st.expander("➕ Tambah Barang Baru"):
        barcode_input = st.text_input("Nomor Barcode / Label:")
        nama_barang = st.text_input("Nama Barang:")
        stok_awal = st.number_input("Jumlah Stok:", min_value=1, step=1)
        
        harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
        if harga_modal > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_modal)}**")
            
        harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
        if harga_jual > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_jual)}**")
            
        kode_cepat_brg = st.text_input("Kode Cepat Barang (Contoh: SPI, VCG1):")
        
        if st.button("💾 Simpan Barang", type="primary", use_container_width=True):
            if ws_s and nama_barang:
                ws_s.append_row([barcode_input, nama_barang, stok_awal, harga_modal, harga_jual, kode_cepat_brg])
                st.success("Tersimpan!")
                st.rerun()

    st.markdown("---")
    if ws_s:
        data_s = ws_s.get_all_values()
        if len(data_s) > 1:
            df_s = pd.DataFrame(data_s[1:], columns=data_s[0])
            df_s['No_Baris'] = range(2, len(df_s) + 2)
            if 'Harga_Modal' in df_s.columns: df_s['Harga_Modal'] = df_s['Harga_Modal'].apply(lambda x: f_uang(x) if str(x).isdigit() else x)
            if 'Harga_Jual' in df_s.columns: df_s['Harga_Jual'] = df_s['Harga_Jual'].apply(lambda x: f_uang(x) if str(x).isdigit() else x)
            st.dataframe(df_s, use_container_width=True)
            
            pilih_nama_edit = st.selectbox("Edit Data Stok:", options=["-- Pilih Barang --"] + df_s['Nama_Barang'].tolist())
            if pilih_nama_edit != "-- Pilih Barang --":
                match_row = df_s[df_s['Nama_Barang'] == pilih_nama_edit]
                if not match_row.empty:
                    pilih_baris_edit = int(match_row.iloc[0]['No_Baris'])
                    row_data = ws_s.row_values(pilih_baris_edit)
                    while len(row_data) < 6: row_data.append("")
                    
                    edit_barcode = st.text_input("Barcode / Label:", value=row_data[0])
                    edit_nama = st.text_input("Nama Barang:", value=row_data[1])
                    edit_stok = st.number_input("Jumlah Stok:", value=int(row_data[2]) if row_data[2].isdigit() else 0, step=1)
                    edit_modal = st.number_input("Edit Modal (Rp):", value=int(row_data[3]) if row_data[3].isdigit() else 0, step=1000)
                    edit_jual = st.number_input("Edit Jual (Rp):", value=int(row_data[4]) if row_data[4].isdigit() else 0, step=1000)
                    edit_kode = st.text_input("Kode Cepat:", value=row_data[5])
                    
                    if st.button("🔄 Update Stok", type="primary", use_container_width=True):
                        ws_s.update(f"A{pilih_baris_edit}:F{pilih_baris_edit}", [[edit_barcode, edit_nama, edit_stok, edit_modal, edit_jual, edit_kode]])
                        st.success("Updated!")
                        st.rerun()

            baris_hapus_stok = st.multiselect("Hapus Stok (No Baris):", options=df_s['No_Baris'].tolist())
            if st.button("❌ Hapus Terpilih", type="primary"):
                if baris_hapus_stok:
                    for b in sorted(baris_hapus_stok, reverse=True): ws_s.delete_rows(int(b))
                    st.rerun()
