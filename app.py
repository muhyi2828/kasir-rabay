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

st.set_page_config(page_title="RABAY CELL PRO - ERP SYSTEM", layout="centered", page_icon="🚀")

# --- CUSTOM CSS TAMPILAN MODERN ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #00b4d8 !important;
        border-bottom-color: #00b4d8 !important;
    }
    .stTabs [data-baseweb="tab-list"] button:hover {
        color: #00b4d8 !important;
    }
    .metric-card-blue {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #1f77b4;
    }
    .metric-card-green {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #2ca02c;
    }
    h1 { color: #1E1E1E; font-weight: 800; letter-spacing: -0.5px; }
    h3 { color: #333333; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

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

# STATE MANAGEMENT
if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = 0
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = 0
if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = 0
if 'input_jenis' not in st.session_state: st.session_state['input_jenis'] = "Bank"
if 'draf_scan_smart' not in st.session_state: st.session_state['draf_scan_smart'] = []
if 'nama_barang_ditemukan' not in st.session_state: st.session_state['nama_barang_ditemukan'] = ""
if 'baris_stok_ditemukan' not in st.session_state: st.session_state['baris_stok_ditemukan'] = None
if 'profit_barang_ini' not in st.session_state: st.session_state['profit_barang_ini'] = 0

st.markdown("<h3 style='color:#00b4d8; margin:0;'>RABAY CELL</h3>", unsafe_allow_html=True)
st.caption("Sistem Kasir & Manajemen Stok Konter Profesional")

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
        else:
            sisa = nominal - 20000000
            kelipatan = -(-sisa // 5000000)
            return 35000 + (kelipatan * 5000)
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
        else:
            sisa = nominal - 10000000
            kelipatan = -(-sisa // 5000000)
            return 35000 + (kelipatan * 5000)

# --- URUTAN TAB: Transaksi, Riwayat, Dashboard, Stok Barang ---
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Transaksi", "📋 Riwayat", "📊 Dashboard & Untung", "📦 Stok Barang"])

with tab1:
    st.subheader("⚡ Input Transaksi Baru")
    metode = st.radio("Pilih Metode:", ["Ketik Manual / Kode Cepat / Barang", "Scan Foto Mutasi (Banyak)"], horizontal=True)
    
    if metode == "Ketik Manual / Kode Cepat / Barang":
        quick = st.text_input("🔍 Masukkan Kode Cepat (TF100, EW50, TK200) atau Kode/Barcode Stok:")
        if quick:
            code = quick.upper().strip()
            st.session_state['nama_barang_ditemukan'] = ""
            st.session_state['baris_stok_ditemukan'] = None
            st.session_state['profit_barang_ini'] = 0
            
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
                        row_idx = int(match_barang.iloc[0]['Row_Idx'])
                        
                        profit_item = hargajual - hargamodal
                        st.session_state['nama_barang_ditemukan'] = namabarang
                        st.session_state['baris_stok_ditemukan'] = row_idx
                        st.session_state['profit_barang_ini'] = profit_item
                        st.session_state['input_jenis'] = "Penjualan Barang"
                        st.session_state['input_nominal'] = hargajual

            if code.startswith("TF") or code.startswith("EW") or code.startswith("TK"):
                st.session_state['input_jenis'] = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
                angka_str = re.sub(r'[^0-9.]', '', code)
                try: st.session_state['input_nominal'] = int(float(angka_str) * 1000)
                except: pass

        st.markdown("---")
        pilihan_jenis = ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"]
        current_idx = pilihan_jenis.index(st.session_state['input_jenis']) if st.session_state['input_jenis'] in pilihan_jenis else 0
        
        st.session_state['input_jenis'] = st.radio("Jenis Transaksi:", pilihan_jenis, index=current_idx, horizontal=True)
        
        if st.session_state['nama_barang_ditemukan'] and st.session_state['input_jenis'] == "Penjualan Barang":
            st.success(f"📦 Barang Terdeteksi: **{st.session_state['nama_barang_ditemukan']}** | Estimasi Untung: **Rp {st.session_state['profit_barang_ini']:,}**")

        nominal_trx = st.number_input("Nominal / Harga (Rp):", value=st.session_state['input_nominal'], step=10000)
        
        profit_manual = 0
        if st.session_state['input_jenis'] == "Transaksi Lainnya":
            profit_manual = st.number_input("Keuntungan / Cuan Manual (Rp):", value=0, step=1000)

        if nominal_trx > 0 or (st.session_state['input_jenis'] == "Transaksi Lainnya" and nominal_trx >= 0):
            if st.session_state['input_jenis'] == "Penjualan Barang":
                admin = 0
                total_uang = nominal_trx
                profit_bersih = st.session_state['profit_barang_ini'] if st.session_state['profit_barang_ini'] > 0 else 0
                st.info(f"🛒 **Penjualan Barang Fisik**\n- Uang Masuk Cash: **Rp {total_uang:,}**\n- Perkiraan Untung: **Rp {profit_bersih:,}**")
            elif st.session_state['input_jenis'] == "Transaksi Lainnya":
                admin = 0
                total_uang = nominal_trx
                profit_bersih = profit_manual
                st.info(f"💼 **Transaksi Lainnya (Jasa/Servis/Lainnya)**\n- Uang Masuk Cash: **Rp {total_uang:,}**\n- Keuntungan Manual: **Rp {profit_bersih:,}**")
            else:
                admin = hitung_admin(nominal_trx, st.session_state['input_jenis'])
                total_uang = nominal_trx + admin if st.session_state['input_jenis'] != "Tarik Tunai" else nominal_trx - admin
                profit_bersih = admin
                
                c1, c2 = st.columns(2)
                c1.metric("Nominal", f"Rp {nominal_trx:,}")
                c2.metric("Admin (Cuan)", f"Rp {admin:,}")
                
                if st.session_state['input_jenis'] == "Tarik Tunai":
                    st.info(f"💵 Uang Tunai Diberikan ke Pelanggan: **Rp {total_uang:,}**")
                else:
                    st.success(f"💰 Total Tagihan Pelanggan: **Rp {total_uang:,}**")
                
            if st.button("💾 Simpan & Perbarui Kas / Stok", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                
                if st.session_state['input_jenis'] == "Penjualan Barang":
                    st.session_state['modal_cash'] += nominal_trx
                    if ws_s and st.session_state['baris_stok_ditemukan']:
                        row_num = st.session_state['baris_stok_ditemukan']
                        stok_sekarang = int(ws_s.cell(row_num, 3).value)
                        if stok_sekarang > 0:
                            ws_s.update_cell(row_num, 3, stok_sekarang - 1)
                elif st.session_state['input_jenis'] == "Transaksi Lainnya":
                    st.session_state['modal_cash'] += nominal_trx
                elif st.session_state['input_jenis'] == "Tarik Tunai":
                    st.session_state['modal_cash'] -= total_uang
                    st.session_state['modal_digi'] += nominal_trx
                else:
                    st.session_state['modal_digi'] -= nominal_trx
                    st.session_state['modal_cash'] += total_uang
                
                if ws_t: ws_t.append_row([waktu, st.session_state['input_jenis'], nominal_trx, admin, total_uang, profit_bersih])
                st.success("✅ Transaksi Berhasil Disimpan!")
                st.session_state['input_nominal'] = 0
                st.session_state['nama_barang_ditemukan'] = ""
                st.session_state['baris_stok_ditemukan'] = None
                st.session_state['profit_barang_ini'] = 0
                st.rerun()

    else: 
        sumber_gambar = st.file_uploader("Upload Screenshot Mutasi:", type=["jpg", "jpeg", "png"])
        if sumber_gambar and st.button("🔍 Pindai Cerdas (+/-) dengan AI", use_container_width=True):
            try:
                with st.spinner("AI sedang membaca nominal & mendeteksi tanda +/-..."):
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    img = Image.open(sumber_gambar)
                    res = client.models.generate_content(
                        model='gemini-3.6-flash', 
                        contents=[img, "Tulis semua nominal transaksi beserta tandanya (+ atau -). Balas dengan format angka dipisah koma, contoh: +9067000,-75000,-5000000"]
                    )
                    
                    raw_text = res.text.replace(" ", "")
                    items = raw_text.split(',')
                    processed_data = []
                    for item in items:
                        if '+' in item or '-' in item:
                            nom_val = int(re.sub(r'[^0-9]', '', item))
                            # Tanda + otomatis jadi Tarik Tunai, - otomatis jadi Bank
                            kategori = 'Tarik Tunai' if '+' in item else 'Bank'
                            tanda_simbol = '+' if '+' in item else '-'
                            processed_data.append({
                                'Tanda': tanda_simbol,
                                'Jenis Otomatis': kategori,
                                'Nominal (Rp)': nom_val
                            })
                    
                    st.session_state['draf_scan_smart'] = processed_data
            except Exception as e:
                st.error(f"Gagal scan: {e}")

        # --- PREVIEW HASIL SCAN CERDAS (+ / -) ---
        if st.session_state['draf_scan_smart']:
            st.markdown("---")
            jumlah_draf = len(st.session_state['draf_scan_smart'])
            st.info(f"✨ Berhasil mendeteksi {jumlah_draf} transaksi dari gambar:")
            
            df_preview = pd.DataFrame(st.session_state['draf_scan_smart'])
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
            
            if st.button("💾 Simpan Semua ke Database & Perbarui Kas", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state['draf_scan_smart']:
                    nom = item['Nominal (Rp)']
                    jenis = item['Jenis Otomatis']
                    admin = hitung_admin(nom, jenis)
                    
                    if jenis == "Tarik Tunai":
                        total = nom - admin
                        st.session_state['modal_cash'] -= total
                        st.session_state['modal_digi'] += nom
                    else:
                        total = nom + admin
                        st.session_state['modal_digi'] -= nom
                        st.session_state['modal_cash'] += total
                        
                    profit_scan = admin
                    if ws_t: ws_t.append_row([waktu, jenis, nom, admin, total, profit_scan])
                
                st.session_state['draf_scan_smart'] = []
                st.success("Semua data berhasil disimpan sesuai kategori (+/-) & profit tercatat!")
                st.rerun()

# --- TAB 2: RIWAYAT ---
with tab2:
    st.subheader("📋 Kelola & Filter Riwayat Transaksi")
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_t = pd.DataFrame(data_t[1:], columns=data_t[0])
            df_t['No_Baris'] = range(2, len(df_t) + 2)
            df_t['Tanggal_Saja'] = pd.to_datetime(df_t.iloc[:, 0], errors='coerce').dt.date
            
            st.write("### 🔍 Filter Pencarian")
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                kolom_jenis = df_t.columns[1] if len(df_t.columns) > 1 else 'Jenis'
                jenis_tersedia = ["Semua"] + df_t[kolom_jenis].unique().tolist()
                pilih_filter_jenis = st.selectbox("Jenis Transaksi:", options=jenis_tersedia)
                
            with col_f2:
                tanggal_tersedia = sorted(df_t['Tanggal_Saja'].dropna().unique(), reverse=True)
                pilih_filter_tgl = st.selectbox("Tanggal Transaksi:", options=["Semua Tanggal"] + [str(t) for t in tanggal_tersedia])
            
            df_t_filtered = df_t.copy()
            if pilih_filter_jenis != "Semua":
                df_t_filtered = df_t_filtered[df_t_filtered[kolom_jenis] == pilih_filter_jenis]
            if pilih_filter_tgl != "Semua Tanggal":
                df_t_filtered = df_t_filtered[df_t_filtered['Tanggal_Saja'].astype(str) == pilih_filter_tgl]
                
            df_t_display = df_t_filtered.drop(columns=['Tanggal_Saja'])
            
            st.markdown("---")
            st.dataframe(df_t_display, use_container_width=True)
            
            st.markdown("---")
            st.write("### 🗑️ Hapus Transaksi Terpilih")
            baris_hapus_trx = st.multiselect("Pilih Nomor Baris Transaksi:", options=df_t_filtered['No_Baris'].tolist(), key="del_trx")
            if st.button("❌ Hapus Transaksi Terpilih", type="primary"):
                if baris_hapus_trx:
                    for baris in sorted(baris_hapus_trx, reverse=True):
                        ws_t.delete_rows(int(baris))
                    st.success("Transaksi terpilih berhasil dihapus!")
                    st.rerun()
                else:
                    st.warning("Pilih minimal 1 baris transaksi.")
        else:
            st.info("Belum ada riwayat transaksi.")

# --- TAB 3: DASHBOARD & UNTUNG ---
with tab3:
    st.subheader("📊 Dashboard Keuangan & Profit")
    
    with st.expander("💰 Atur Modal Awal Hari Ini", expanded=False):
        st.session_state['modal_cash'] = st.number_input("Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
        st.session_state['modal_digi'] = st.number_input("Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)

    st.markdown("---")

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#1f77b4;">💵 Cash di Laci</h4>
            <h2 style="margin:5px 0 0 0; color:#333;">Rp {st.session_state['modal_cash']:,}</h2>
        </div>
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#1f77b4;">💳 Saldo Digital</h4>
            <h2 style="margin:5px 0 0 0; color:#333;">Rp {st.session_state['modal_digi']:,}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
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
            <h4 style="margin:0; color:#2ca02c;">🔥 Total Keuntungan (Profit) Hari Ini</h4>
            <h1 style="margin:5px 0 0 0; color:#2ca02c;">Rp {profit_hari_ini:,}</h1>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("💾 Simpan Rekap Harian ke Sheets", type="primary", use_container_width=True):
        if ws_k:
            tanggal = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")
            ws_k.append_row([tanggal, st.session_state['modal_cash'], st.session_state['modal_digi']])
            st.success("Rekap harian berhasil dikirim ke Sheets!")

    st.markdown("### 📈 Grafik Riwayat Profit Harian")
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_trx_all = pd.DataFrame(data_t[1:])
            if len(df_trx_all.columns) >= 6:
                df_trx_all['Tanggal'] = pd.to_datetime(df_trx_all.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
                df_trx_all['Profit_Val'] = pd.to_numeric(df_trx_all.iloc[:, 5], errors='coerce').fillna(0)
                
                df_profit_harian = df_trx_all.groupby('Tanggal')['Profit_Val'].sum().reset_index()
                
                fig_profit = px.bar(df_profit_harian, x='Tanggal', y='Profit_Val', 
                                    labels={'Profit_Val': 'Keuntungan (Rp)', 'Tanggal': 'Tanggal'},
                                    title="Grafik Keuntungan (Profit) Harian Toko")
                st.plotly_chart(fig_profit, use_container_width=True)
        else:
            st.info("Belum ada data transaksi untuk ditampilkan dalam grafik profit.")

# --- TAB 4: STOK BARANG ---
with tab4:
    st.subheader("📦 Manajemen Stok Barang")
    
    with st.expander("➕ Tambah Barang Baru"):
        with st.form("form_tambah_stok", clear_on_submit=True):
            barcode_input = st.text_input("Nomor Barcode / Label:")
            nama_barang = st.text_input("Nama Barang:")
            stok_awal = st.number_input("Jumlah Stok:", min_value=1, step=1)
            harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
            harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
            kode_cepat_brg = st.text_input("Kode Cepat Barang (Contoh: SPI, VCG1):")
            
            submit_stok = st.form_submit_button("💾 Simpan Barang Baru")
            if submit_stok:
                if ws_s and nama_barang:
                    ws_s.append_row([barcode_input, nama_barang, stok_awal, harga_modal, harga_jual, kode_cepat_brg])
                    st.success(f"Barang **{nama_barang}** berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.warning("Nama barang wajib diisi!")

    st.markdown("---")
    st.subheader("📋 Daftar Stok Tersedia")
    if ws_s:
        data_s = ws_s.get_all_values()
        if len(data_s) > 1:
            df_s = pd.DataFrame(data_s[1:], columns=data_s[0])
            df_s['No_Baris'] = range(2, len(df_s) + 2)
            st.dataframe(df_s, use_container_width=True)
            
            st.markdown("---")
            st.subheader("✏️ Edit Data Stok Barang")
            daftar_nama_barang = df_s['Nama_Barang'].tolist()
            pilih_nama_edit = st.selectbox("Pilih Nama Barang yang mau di-edit:", options=["-- Pilih Barang --"] + daftar_nama_barang)
            
            if pilih_nama_edit != "-- Pilih Barang --":
                match_row = df_s[df_s['Nama_Barang'] == pilih_nama_edit]
                if not match_row.empty:
                    pilih_baris_edit = int(match_row.iloc[0]['No_Baris'])
                    row_data = ws_s.row_values(pilih_baris_edit)
                    while len(row_data) < 6: row_data.append("")
                    
                    with st.form("form_edit_stok"):
                        st.write(f"Sedang mengedit: **{pilih_nama_edit}**")
                        edit_barcode = st.text_input("Barcode / Label:", value=row_data[0])
                        edit_nama = st.text_input("Nama Barang:", value=row_data[1])
                        edit_stok = st.number_input("Jumlah Stok:", value=int(row_data[2]) if row_data[2].isdigit() else 0, step=1)
                        edit_modal = st.number_input("Harga Modal (Rp):", value=int(row_data[3]) if row_data[3].isdigit() else 0, step=1000)
                        edit_jual = st.number_input("Harga Jual (Rp):", value=int(row_data[4]) if row_data[4].isdigit() else 0, step=1000)
                        edit_kode = st.text_input("Kode Cepat Barang:", value=row_data[5])
                        
                        btn_update = st.form_submit_button("🔄 Update Perubahan Stok", type="primary")
                        if btn_update:
                            ws_s.update(f"A{pilih_baris_edit}:F{pilih_baris_edit}", [[edit_barcode, edit_nama, edit_stok, edit_modal, edit_jual, edit_kode]])
                            st.success(f"Data barang **{edit_nama}** berhasil diperbarui!")
                            st.rerun()

            st.markdown("---")
            baris_hapus_stok = st.multiselect("Pilih Baris Stok yang ingin dihapus:", options=df_s['No_Baris'].tolist(), key="del_stok")
            if st.button("❌ Hapus Stok Terpilih", type="primary"):
                if baris_hapus_stok:
                    for b in sorted(baris_hapus_stok, reverse=True):
                        ws_s.delete_rows(int(b))
                    st.success("Stok berhasil dihapus!")
                    st.rerun()
        else:
            st.info("Belum ada data stok.")
