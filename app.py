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
            
            if st.button("💾 SIMPAN SEMUA TRANSAKSI", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state['draf_scan_smart']:
                    nom, jenis = item['Nominal (Rp)'], item['Jenis Otomatis']
                    admin = hitung_admin(nom, jenis)
                    total = nom - admin if jenis == "Tarik Tunai" else nom + admin
                    if ws_t: ws_t.append_row([waktu, jenis, nom, admin, total, admin])
                st.session_state['draf_scan_smart'] = []
                st.success("Tersimpan!")
                st.rerun()

# --- TAB 2: RIWAYAT (DENGAN KONFIRMASI HAPUS, EDIT, & TOTAL PROFIT FILTER) ---
with tab2:
    st.subheader("📋 Daftar Riwayat Transaksi")
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
            
            # Hitung Total Profit dari filter yang sedang aktif
            profit_filter_val = pd.to_numeric(df_t_filtered.iloc[:, 5], errors='coerce').fillna(0).sum() if len(df_t_filtered) > 0 else 0
            st.markdown(f"""
                <div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border:1px solid #2ca02c; text-align:center; margin:15px 0;">
                    <span style="color:#2ca02c; font-size:14px; font-weight:bold;">🔥 TOTAL PROFIT (FILTER AKTIF):</span><br>
                    <span style="color:#fff; font-size:20px; font-weight:bold;">{f_uang(profit_filter_val)}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Tombol Hapus Semua Riwayat dengan Konfirmasi
            with st.expander("⚠️ Hapus Semua Riwayat Transaksi"):
                st.warning("PERINGATAN: Seluruh data riwayat transaksi akan dihapus permanen!")
                konfirm_hapus_semua = st.checkbox("Saya yakin ingin menghapus semua riwayat", key="chk_del_all_trx")
                if konfirm_hapus_semua:
                    if st.button("🗑️ Hapus Permanen Semua Riwayat", type="primary"):
                        # Kosongkan sheet dengan menghapus semua baris kecuali header
                        ws_t.clear()
                        ws_t.append_row(data_t[0]) # Kembalikan Header
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
                
                # TOMBOL KONFIRMASI HAPUS & EDIT
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("❌ Hapus", key=f"del_trx_{b_num}", use_container_width=True):
                        st.session_state[f"konfirm_trx_{b_num}"] = True
                with col_btn2:
                    if st.button("✏️ Edit", key=f"edit_trx_{b_num}", use_container_width=True):
                        st.session_state[f"mode_edit_trx_{b_num}"] = True
                
                # Eksekusi Konfirmasi Hapus
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

                # Eksekusi Edit Riwayat
                if st.session_state.get(f"mode_edit_trx_{b_num}", False):
                    with st.form(key=f"form_edit_trx_{b_num}"):
                        st.write(f"Edit Transaksi Baris {b_num}")
                        e_waktu = st.text_input("Waktu", value=row.iloc[0])
                        e_jenis = st.text_input("Jenis", value=row.iloc[1])
                        e_nom = st.number_input("Nominal", value=int(row.iloc[2]) if str(row.iloc[2]).isdigit() else 0, step=1000)
                        e_adm = st.number_input("Admin", value=int(row.iloc[3]) if str(row.iloc[3]).isdigit() else 0, step=1000)
                        e_tot = st.number_input("Total", value=int(row.iloc[4]) if str(row.iloc[4]).isdigit() else 0, step=1000)
                        e_prof = st.number_input("Profit", value=int(row.iloc[5]) if str(row.iloc[5]).isdigit() else 0, step=1000)
                        
                        btn_save_edit = st.form_submit_button("Simpan Perubahan")
                        if btn_save_edit:
                            ws_t.update(f"A{b_num}:F{b_num}", [[e_waktu, e_jenis, e_nom, e_adm, e_tot, e_prof]])
                            st.session_state[f"mode_edit_trx_{b_num}"] = False
                            st.success("Perubahan disimpan!")
                            st.rerun()

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
        else: st.info("Belum ada riwayat transaksi.")

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

    # Cash di Laci Card
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

    # Saldo Digital Card
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

# --- TAB 4: STOK BARANG (DENGAN HARGA MODAL, KONFIRMASI HAPUS, & EDIT) ---
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
    st.subheader("📋 Daftar Stok Tersedia")
    if ws_s:
        data_s = ws_s.get_all_values()
        if len(data_s) > 1:
            df_s = pd.DataFrame(data_s[1:], columns=data_s[0])
            df_s['No_Baris'] = range(2, len(df_s) + 2)
            
            for index, row in df_s.iterrows():
                b_stok = int(row['No_Baris'])
                bc = row.iloc[0]
                nm = row.iloc[1]
                stk = row.iloc[2]
                h_modal = f_uang(row.iloc[3]) if str(row.iloc[3]).isdigit() else row.iloc[3]
                h_jual = f_uang(row.iloc[4]) if str(row.iloc[4]).isdigit() else row.iloc[4]
                
                st.markdown(f"**{nm}** (Stok: <span style='color:#14B8A6;'>{stk}</span>)<br>Modal: {h_modal} | Jual: {h_jual}<br>Barcode: {bc}", unsafe_allow_html=True)
                
                # TOMBOL KONFIRMASI HAPUS & EDIT STOK
                col_stk1, col_stk2 = st.columns(2)
                with col_stk1:
                    if st.button("❌ Hapus", key=f"del_stk_{b_stok}", use_container_width=True):
                        st.session_state[f"konfirm_stk_{b_stok}"] = True
                with col_stk2:
                    if st.button("✏️ Edit", key=f"edit_stok_btn_{b_stok}", use_container_width=True):
                        st.session_state[f"mode_edit_stk_{b_num}"] = True
                
                # Konfirmasi Hapus Stok
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

                # Form Edit Stok Langsung di Baris / Expander
                if st.session_state.get(f"mode_edit_stk_{b_num}", False):
                    with st.form(key=f"form_edit_stok_{b_stok}"):
                        st.write(f"Edit Data: {nm}")
                        es_bc = st.text_input("Barcode", value=row.iloc[0])
                        es_nm = st.text_input("Nama Barang", value=row.iloc[1])
                        es_stk = st.number_input("Stok", value=int(row.iloc[2]) if str(row.iloc[2]).isdigit() else 0, step=1)
                        es_mod = st.number_input("Harga Modal", value=int(row.iloc[3]) if str(row.iloc[3]).isdigit() else 0, step=1000)
                        es_jul = st.number_input("Harga Jual", value=int(row.iloc[4]) if str(row.iloc[4]).isdigit() else 0, step=1000)
                        es_kod = st.text_input("Kode Cepat", value=row.iloc[5])
                        
                        if st.form_submit_button("Simpan Perubahan Stok"):
                            ws_s.update(f"A{b_stok}:F{b_stok}", [[es_bc, es_nm, es_stk, es_mod, es_jul, es_kod]])
                            st.session_state[f"mode_edit_stk_{b_num}"] = False
                            st.success("Stok diperbarui!")
                            st.rerun()

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
        else:
            st.info("Belum ada data stok.")
