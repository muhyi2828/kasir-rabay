import streamlit as st
from PIL import Image
from google import genai
import re
import gspread
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Kasir RABAY CELL", page_icon="🚀", layout="centered")

# Mengambil API Key dari Brankas
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = ""
    st.warning("API Key Gemini belum disetting.")

# Fungsi Menghubungkan ke Google Sheets
@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh.get_worksheet(0), "Aman"
    except Exception as e:
        return None, str(e)

worksheet, pesan_error_db = konek_gsheets()

# Inisialisasi Memori Web
if 'riwayat' not in st.session_state: st.session_state['riwayat'] = []
if 'hasil_scan_banyak' not in st.session_state: st.session_state['hasil_scan_banyak'] = []

st.title("🚀 Kasir RABAY CELL")
if worksheet: st.caption("🟢 Terkoneksi ke Google Sheets")
else: st.error(f"🔴 Database Terputus! {pesan_error_db}")

# Fungsi Hitung Admin
def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 199000: return 3000
        elif nominal <= 299000: return 4000
        elif nominal <= 699000: return 5000
        elif nominal <= 1000000: return 8000
        else: return 10000
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

# Fungsi OCR Banyak (Diperbaiki agar stabil menerima objek gambar)
def baca_nominal_ocr_banyak(file_gambar, key):
    client = genai.Client(api_key=key)
    img = Image.open(file_gambar)
    prompt = "Temukan SEMUA angka nominal transaksi utama pada gambar ini. Balas hanya dengan angka mentahnya saja dan pisahkan menggunakan koma (contoh: 5000000,9000000,4000000)."
    response = client.models.generate_content(model='gemini-3.6-flash', contents=[img, prompt])
    teks_bersih = re.sub(r'[^0-9,]', '', response.text)
    if not teks_bersih: return []
    return [int(x) for x in teks_bersih.split(',') if x.isdigit()]

# Fungsi Quick Code
def parse_quick_code(code):
    code = code.upper().strip()
    jenis = "Bank"
    if code.startswith("EW"): jenis = "E-Wallet"
    elif code.startswith("TK"): jenis = "Tarik Tunai"
    angka_str = re.sub(r'[^0-9.]', '', code)
    try: return int(float(angka_str) * 1000), jenis
    except: return 0, jenis

tab1, tab2 = st.tabs(["⚡ Input Kasir", "📊 Rekap Harian"])

with tab1:
    st.subheader("Input Transaksi")
    
    # 1. Fitur Quick Code
    quick_code = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200):")
    if quick_code:
        nominal, jenis = parse_quick_code(quick_code)
        if nominal > 0:
            st.info(f"Terbaca Cepat: **{jenis} - Rp {nominal:,}**")
            st.session_state['hasil_scan_banyak'] = [nominal]
            st.session_state['jenis_default'] = jenis

    # 2. Fitur Scan Mutasi Banyak
    sumber_gambar = st.file_uploader("Atau Upload Screenshot Mutasi:", type=["jpg", "jpeg", "png"])
    if sumber_gambar and api_key and st.button("🔍 Pindai Gambar dengan AI", use_container_width=True):
        try:
            with st.spinner("AI sedang membaca semua angka di gambar..."):
                daftar_angka = baca_nominal_ocr_banyak(sumber_gambar, api_key)
                if daftar_angka:
                    st.session_state['hasil_scan_banyak'] = daftar_angka
                    st.session_state['jenis_default'] = "Bank"
                    st.success(f"Berhasil menemukan {len(daftar_angka)} transaksi!")
                else:
                    st.warning("Tidak ada nominal yang terbaca oleh AI.")
        except Exception as e:
            st.error(f"Gagal memindai gambar: {e}")

    # 3. Draf Pemrosesan
    if st.session_state['hasil_scan_banyak']:
        st.markdown("---")
        st.info("### 📑 Draf Transaksi Massal")
        jenis_massal = st.radio("Jenis Transaksi:", ["Bank", "E-Wallet", "Tarik Tunai"], 
                               index=["Bank", "E-Wallet", "Tarik Tunai"].index(st.session_state.get('jenis_default', 'Bank')), horizontal=True)
        
        preview_data = []
        for nominal in st.session_state['hasil_scan_banyak']:
            admin = hitung_admin(nominal, jenis_massal)
            total = nominal + admin if jenis_massal != "Tarik Tunai" else nominal - admin
            preview_data.append({"Nominal": nominal, "Admin": admin, "Total Uang": total})
            
        st.dataframe(preview_data, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("❌ Batalkan", use_container_width=True):
                st.session_state['hasil_scan_banyak'] = []
                st.rerun()
        with c2:
            if st.button("💾 Simpan Semua", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                baris_data = [[waktu, jenis_massal, d['Nominal'], d['Admin'], d['Total Uang']] for d in preview_data]
                
                if worksheet: worksheet.append_rows(baris_data)
                for b in baris_data: st.session_state['riwayat'].append({"Waktu": b[0], "Jenis": b[1], "Nominal": b[2], "Admin": b[3], "Total Uang": b[4]})
                
                st.session_state['hasil_scan_banyak'] = []
                st.success("Semua data berhasil disimpan permanen!")
                st.rerun()

with tab2:
    st.subheader("Rekap Hari Ini")
    if st.session_state['riwayat']:
        st.dataframe(st.session_state['riwayat'], use_container_width=True)
        tot_admin = sum(x['Admin'] for x in st.session_state['riwayat'])
        st.metric("Total Keuntungan Admin", f"Rp {tot_admin:,}")
        if st.button("🗑️ Hapus Rekap"): st.session_state['riwayat'] = []; st.rerun()
    else:
        st.info("Belum ada transaksi tersimpan.")
