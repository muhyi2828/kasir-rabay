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

# --- CSS KHUSUS UNTUK MEMAKSA SEJAJAR DI HP (FLEXBOX) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    
    /* Membungkus Header agar benar-benar sejajar kiri dan kanan */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 5px;
    }
    
    /* Membungkus Input Kode & Kamera agar sejajar */
    .input-row {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
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
if 'draf_scan' not in st.session_state: st.session_state['draf_scan'] = []
if 'nama_barang_ditemukan' not in st.session_state: st.session_state['nama_barang_ditemukan'] = ""
if 'baris_stok_ditemukan' not in st.session_state: st.session_state['baris_stok_ditemukan'] = None
if 'profit_barang_ini' not in st.session_state: st.session_state['profit_barang_ini'] = 0
if 'menu_aktif' not in st.session_state: st.session_state['menu_aktif'] = "Transaksi"

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

# --- HEADER: RABAY CELL (KIRI) & STOK BARANG (KANAN ATAS) ---
c_head1, c_head2 = st.columns([1.2, 1])
with c_head1:
    st.markdown("<h2 style='color:#00b4d8; margin:0; line-height:1.5;'>RABAY CELL</h2>", unsafe_allow_html=True)
with c_head2:
    if st.button("📦 STOK BARANG", use_container_width=True, type="secondary"):
        st.session_state['menu_aktif'] = "Stok Barang"
        st.rerun()

# --- MODAL CASH & SALDO DIGITAL DI BAWAHNYA ---
col_m1, col_m2 = st.columns(2)
with col_m1:
    st.markdown("<p style='font-size:11px; color:#aaa; margin:0;'>Modal Cash:</p>", unsafe_allow_html=True)
    st.session_state['modal_cash'] = st.number_input("Modal Cash", value=st.session_state['modal_cash'], step=50000, label_visibility="collapsed")
with col_m2:
    st.markdown("<p style='font-size:11px; color:#aaa; margin:0;'>Modal Saldo:</p>", unsafe_allow_html=True)
    st.session_state['modal_digi'] = st.number_input("Modal Saldo", value=st.session_state['modal_digi'], step=50000, label_visibility="collapsed")

st.markdown("<div style='margin: 5px 0;'></div>", unsafe_allow_html=True)

# --- MENU UTAMA (TRANSAKSI, RIWAYAT, DASHBOARD) ---
nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("⚡ TRANSAKSI", use_container_width=True, type="primary" if st.session_state['menu_aktif']=="Transaksi" else "secondary"):
        st.session_state['menu_aktif'] = "Transaksi"
        st.rerun()
with nav2:
    if st.button("📋 RIWAYAT", use_container_width=True, type="primary" if st.session_state['menu_aktif']=="Riwayat" else "secondary"):
        st.session_state['menu_aktif'] = "Riwayat"
        st.rerun()
with nav3:
    if st.button("📊 DASHBOARD", use_container_width=True, type="primary" if st.session_state['menu_aktif']=="Dashboard" else "secondary"):
        st.session_state['menu_aktif'] = "Dashboard"
        st.rerun()

st.markdown("---")

# ==================== KONTROL MENU: TRANSAKSI ====================
if st.session_state['menu_aktif'] == "Transaksi":
    
    # --- INPUT KODE CEPAT & TOMBOL KAMERA OCR DI SEBELAH KANANNYA (CUSTOM HTML WRAPPER) ---
    col_inp1, col_inp2 = st.columns([5, 1])
    
    with col_inp1:
        quick = st.text_input("Input Kode Cepat/Barcode", placeholder="TF100, EW50, Kode Barang...", label_visibility="collapsed")
    with col_inp2:
        btn_kamera = st.popover("📷", help="Scan Foto Mutasi AI")

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
                    
                    st.session_state['nama_barang_ditemukan'] = namabarang
                    st.session_state['baris_stok_ditemukan'] = row_idx
                    st.session_state['profit_barang_ini'] = hargajual - hargamodal
                    st.session_state['input_jenis'] = "Penjualan Barang"
                    st.session_state['input_nominal'] = hargajual

        if code.startswith("TF") or code.startswith("EW") or code.startswith("TK"):
            st.session_state['input_jenis'] = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
            angka_str = re.sub(r'[^0-9.]', '', code)
            try: st.session_state['input_nominal'] = int(float(angka_str) * 1000)
            except: pass

    # --- FITUR OCR KAMERA DALAM POPOVER ---
    with btn_kamera:
        st.write("### Scan Foto Mutasi AI")
        sumber_gambar = st.file_uploader("Upload Screenshot:", type=["jpg", "jpeg", "png"])
        if sumber_gambar and st.button("🔍 Pindai dengan AI", use_container_width=True):
            try:
                with st.spinner("AI membaca angka..."):
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    img = Image.open(sumber_gambar)
                    res = client.models.generate_content(model='gemini-3.6-flash', contents=[img, "Tulis semua nominal transaksi, balas dengan format angka dipisah koma: 5000000,9000000"])
                    nums = [int(x) for x in re.sub(r'[^0-9,]', '', res.text).split(',') if x.isdigit()]
                    st.session_state['draf_scan'] = nums
                    st.success(f"Ditemukan {len(nums)} nominal!")
            except Exception as e:
                st.error(f"Gagal: {e}")

        if st.session_state['draf_scan']:
            jenis_massal = st.radio("Jenis Transaksi Massal:", ["Bank", "E-Wallet", "Tarik Tunai"])
            if st.button("💾 Simpan Semua Data Scan", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                for nom in st.session_state['draf_scan']:
                    admin = hitung_admin(nom, jenis_massal)
                    total = nom + admin if jenis_massal != "Tarik Tunai" else nom - admin
                    if jenis_massal == "Tarik Tunai":
                        st.session_state['modal_cash'] -= total
                        st.session_state['modal_digi'] += nom
                    else:
                        st.session_state['modal_digi'] -= nom
                        st.session_state['modal_cash'] += total
                    if ws_t: ws_t.append_row([waktu, jenis_massal, nom, admin, total, admin])
                st.session_state['draf_scan'] = []
                st.success("Semua data scan tersimpan!")
                st.rerun()

    # --- PILIHAN JENIS TRANSAKSI ---
    st.markdown("<p style='font-weight:bold; margin-bottom:5px;'>Jenis Transaksi:</p>", unsafe_allow_html=True)
    pilihan_jenis = ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"]
    current_idx = pilihan_jenis.index(st.session_state['input_jenis']) if st.session_state['input_jenis'] in pilihan_jenis else 0
    st.session_state['input_jenis'] = st.radio("Jenis Transaksi:", pilihan_jenis, index=current_idx, horizontal=True, label_visibility="collapsed")

    if st.session_state['nama_barang_ditemukan'] and st.session_state['input_jenis'] == "Penjualan Barang":
        st.success(f"📦 Barang: **{st.session_state['nama_barang_ditemukan']}** | Untung: **Rp {st.session_state['profit_barang_ini']:,}**")

    nominal_trx = st.number_input("Nominal / Harga (Rp):", value=st.session_state['input_nominal'], step=10000)
    
    profit_manual = 0
    if st.session_state['input_jenis'] == "Transaksi Lainnya":
        profit_manual = st.number_input("Keuntungan / Cuan Manual (Rp):", value=0, step=1000)

    if nominal_trx > 0 or (st.session_state['input_jenis'] == "Transaksi Lainnya" and nominal_trx >= 0):
        if st.session_state['input_jenis'] == "Penjualan Barang":
            admin = 0
            total_uang = nominal_trx
            profit_bersih = st.session_state['profit_barang_ini'] if st.session_state['profit_barang_ini'] > 0 else 0
            st.info(f"🛒 **Penjualan Barang**\n- Masuk Cash: Rp {total_uang:,} | **Untung: Rp {profit_bersih:,}**")
        elif st.session_state['input_jenis'] == "Transaksi Lainnya":
            admin = 0
            total_uang = nominal_trx
            profit_bersih = profit_manual
            st.info(f"💼 **Transaksi Lainnya**\n- Masuk Cash: Rp {total_uang:,} | **Cuan: Rp {profit_bersih:,}**")
        else:
            admin = hitung_admin(nominal_trx, st.session_state['input_jenis'])
            total_uang = nominal_trx + admin if st.session_state['input_jenis'] != "Tarik Tunai" else nominal_trx - admin
            profit_bersih = admin
            
            c1, c2 = st.columns(2)
            c1.metric("Nominal", f"Rp {nominal_trx:,}")
            c2.metric("Admin (Cuan)", f"Rp {admin:,}")
            
            if st.session_state['input_jenis'] == "Tarik Tunai":
                st.info(f"💵 Tunai Diberikan: **Rp {total_uang:,}**")
            else:
                st.success(f"💰 Total Tagihan: **Rp {total_uang:,}**")
            
        if st.button("💾 Simpan & Perbarui Kas", type="primary", use_container_width=True):
            waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            if st.session_state['input_jenis'] in ["Penjualan Barang", "Transaksi Lainnya"]:
                st.session_state['modal_cash'] += nominal_trx
                if st.session_state['input_jenis'] == "Penjualan Barang" and ws_s and st.session_state['baris_stok_ditemukan']:
                    row_num = st.session_state['baris_stok_ditemukan']
                    stok_skg = int(ws_s.cell(row_num, 3).value)
                    if stok_skg > 0: ws_s.update_cell(row_num, 3, stok_skg - 1)
            elif st.session_state['input_jenis'] == "Tarik Tunai":
                st.session_state['modal_cash'] -= total_uang
                st.session_state['modal_digi'] += nominal_trx
            else:
                st.session_state['modal_digi'] -= nominal_trx
                st.session_state['modal_cash'] += total_uang
            
            if ws_t: ws_t.append_row([waktu, st.session_state['input_jenis'], nominal_trx, admin, total_uang, profit_bersih])
            st.success("✅ Berhasil Disimpan!")
            st.session_state['input_nominal'] = 0
            st.session_state['nama_barang_ditemukan'] = ""
            st.session_state['baris_stok_ditemukan'] = None
            st.session_state['profit_barang_ini'] = 0
            st.rerun()

# ==================== KONTROL MENU: STOK BARANG ====================
elif st.session_state['menu_aktif'] == "Stok Barang":
    st.subheader("📦 Manajemen Stok Barang")
    
    with st.expander("➕ Tambah Barang Baru"):
        with st.form("form_tambah_stok", clear_on_submit=True):
            barcode_input = st.text_input("Barcode / Label:")
            nama_barang = st.text_input("Nama Barang:")
            stok_awal = st.number_input("Jumlah Stok:", min_value=1, step=1)
            harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
            harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
            kode_cepat_brg = st.text_input("Kode Cepat Barang:")
            
            if st.form_submit_button("💾 Simpan Barang Baru"):
                if ws_s and nama_barang:
                    ws_s.append_row([barcode_input, nama_barang, stok_awal, harga_modal, harga_jual, kode_cepat_brg])
                    st.success("Barang tersimpan!")
                    st.rerun()

    if ws_s:
        data_s = ws_s.get_all_values()
        if len(data_s) > 1:
            df_s = pd.DataFrame(data_s[1:], columns=data_s[0])
            df_s['No_Baris'] = range(2, len(df_s) + 2)
            st.dataframe(df_s, use_container_width=True)
            
            st.markdown("---")
            st.subheader("✏️ Edit Stok")
            pilih_nama_edit = st.selectbox("Pilih Barang:", options=["-- Pilih --"] + df_s['Nama_Barang'].tolist())
            if pilih_nama_edit != "-- Pilih --":
                match_row = df_s[df_s['Nama_Barang'] == pilih_nama_edit]
                if not match_row.empty:
                    pib = int(match_row.iloc[0]['No_Baris'])
                    rd = ws_s.row_values(pib)
                    while len(rd) < 6: rd.append("")
                    with st.form("form_edit"):
                        eb = st.text_input("Barcode:", value=rd[0])
                        en = st.text_input("Nama:", value=rd[1])
                        es = st.number_input("Stok:", value=int(rd[2]) if rd[2].isdigit() else 0)
                        em = st.number_input("Modal:", value=int(rd[3]) if rd[3].isdigit() else 0)
                        ej = st.number_input("Jual:", value=int(rd[4]) if rd[4].isdigit() else 0)
                        ek = st.text_input("Kode Cepat:", value=rd[5])
                        if st.form_submit_button("🔄 Update"):
                            ws_s.update(f"A{pib}:F{pib}", [[eb, en, es, em, ej, ek]])
                            st.success("Diperbarui!")
                            st.rerun()

# ==================== KONTROL MENU: RIWAYAT ====================
elif st.session_state['menu_aktif'] == "Riwayat":
    st.subheader("📋 Kelola & Filter Riwayat")
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_t = pd.DataFrame(data_t[1:], columns=data_t[0])
            df_t['No_Baris'] = range(2, len(df_t) + 2)
            df_t['Tanggal_Saja'] = pd.to_datetime(df_t.iloc[:, 0], errors='coerce').dt.date
            
            c1, c2 = st.columns(2)
            with c1:
                kj = df_t.columns[1] if len(df_t.columns) > 1 else 'Jenis'
                pfj = st.selectbox("Filter Jenis:", options=["Semua"] + df_t[kj].unique().tolist())
            with c2:
                pft = st.selectbox("Filter Tanggal:", options=["Semua Tanggal"] + [str(t) for t in sorted(df_t['Tanggal_Saja'].dropna().unique(), reverse=True)])
            
            df_tf = df_t.copy()
            if pfj != "Semua": df_tf = df_tf[df_tf[kj] == pfj]
            if pft != "Semua Tanggal": df_tf = df_tf[df_tf['Tanggal_Saja'].astype(str) == pft]
            
            st.dataframe(df_tf.drop(columns=['Tanggal_Saja']), use_container_width=True)
            
            bh = st.multiselect("Pilih Baris Hapus:", options=df_tf['No_Baris'].tolist())
            if st.button("❌ Hapus Terpilih", type="primary"):
                if bh:
                    for b in sorted(bh, reverse=True): ws_t.delete_rows(int(b))
                    st.success("Terhapus!")
                    st.rerun()

# ==================== KONTROL MENU: DASHBOARD ====================
elif st.session_state['menu_aktif'] == "Dashboard":
    st.subheader("📊 Dashboard Keuangan & Profit")
    
    profit_hari_ini = 0
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_trx = pd.DataFrame(data_t[1:])
            if len(df_trx.columns) >= 6:
                df_trx['Tanggal'] = pd.to_datetime(df_trx.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
                tni = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d')
                df_hi = df_trx[df_trx['Tanggal'] == tni].copy()
                if not df_hi.empty:
                    profit_hari_ini = pd.to_numeric(df_hi.iloc[:, 5], errors='coerce').fillna(0).sum()

    st.markdown(f"""
        <div style="background-color: #161b22; padding: 15px; border-radius: 10px; border-left: 4px solid #2ea043; margin-bottom: 15px;">
            <h4 style="margin:0; color:#2ea043;">🔥 Total Keuntungan Hari Ini</h4>
            <h1 style="margin:5px 0 0 0; color:#2ea043;">Rp {profit_hari_ini:,}</h1>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("💾 Simpan Rekap Harian", type="primary", use_container_width=True):
        if ws_k:
            ws_k.append_row([datetime.now().strftime("%Y-%m-%d"), st.session_state['modal_cash'], st.session_state['modal_digi']])
            st.success("Rekap tersimpan!")

    st.markdown("### 📈 Grafik Profit Harian")
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_all = pd.DataFrame(data_t[1:])
            if len(df_all.columns) >= 6:
                df_all['Tanggal'] = pd.to_datetime(df_all.iloc[:, 0], errors='coerce').dt.strftime('%Y-%m-%d')
                df_all['Profit_Val'] = pd.to_numeric(df_all.iloc[:, 5], errors='coerce').fillna(0)
                fig = px.bar(df_all.groupby('Tanggal')['Profit_Val'].sum().reset_index(), x='Tanggal', y='Profit_Val', title="Grafik Profit")
                st.plotly_chart(fig, use_container_width=True)
