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

# Fungsi Menghubungkan ke Google Sheets dengan Pelacak Error
@st.cache_resource
def konek_gsheets():
    try:
        # Memastikan spasi/enter yang tidak sengaja terbawa bisa diabaikan
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh.get_worksheet(0), "Aman"
    except Exception as e:
        return None, str(e)

# Menyalakan Koneksi Database
worksheet, pesan_error_db = konek_gsheets()

# Inisialisasi Memori Transaksi (Web)
if 'riwayat' not in st.session_state:
    st.session_state['riwayat'] = []

st.title("🚀 Kasir RABAY CELL")

# Indikator Database Menyala/Mati
if worksheet:
    st.caption("🟢 Terkoneksi ke Google Sheets")
else:
    st.error(f"🔴 Database Terputus! Laporan Error Mesin: {pesan_error_db}")

# Fungsi Hitung Admin
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

# Fungsi Pembaca Struk OCR
def baca_nominal_ocr(gambar, key):
    client = genai.Client(api_key=key)
    prompt = "Temukan nominal bersih transaksi (jumlah uang utama yang ditransfer/ditopup). HANYA balas dengan angkanya saja secara mentah tanpa spasi, tanpa 'Rp', tanpa titik/koma. Abaikan nomor referensi atau saldo."
    response = client.models.generate_content(model='gemini-3.6-flash', contents=[gambar, prompt])
    angka_bersih = re.sub(r'\D', '', response.text)
    return int(angka_bersih)

# Fungsi Quick Code
def parse_quick_code(code):
    code = code.upper().strip()
    jenis = "Bank"
    if code.startswith("EW"): jenis = "E-Wallet"
    elif code.startswith("TK"): jenis = "Tarik Tunai"
    
    angka_str = re.sub(r'[^0-9.]', '', code)
    try:
        nominal = int(float(angka_str) * 1000)
        return nominal, jenis
    except:
        return 0, jenis

tab1, tab2 = st.tabs(["⚡ Input Kasir", "📊 Rekap Harian"])

with tab1:
    st.subheader("Input Transaksi Baru")
    quick_code = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200):")
    sumber_gambar = st.file_uploader("Atau Foto/Upload Struk:", type=["jpg", "jpeg", "png"])
    
    nominal_transaksi = 0
    jenis_transaksi = "Bank"
    
    if quick_code:
        nominal_transaksi, jenis_transaksi = parse_quick_code(quick_code)
        
    if sumber_gambar:
        if api_key:
            if st.button("🔍 Pindai Struk dengan AI", use_container_width=True):
                try:
                    gambar = Image.open(sumber_gambar)
                    st.image(gambar, width=200)
                    with st.spinner("AI sedang membaca angka di struk..."):
                        nominal_transaksi = baca_nominal_ocr(gambar, api_key)
                        st.success(f"Berhasil! Nominal terbaca: Rp {nominal_transaksi:,}")
                except Exception as e:
                    st.error(f"Pesan Error Asli: {e}")
        else:
            st.warning("API Key belum disetting.")

    # Kalkulator & Konfirmasi
    if nominal_transaksi > 0:
        st.markdown("---")
        jenis_transaksi = st.radio("Jenis Transaksi:", ["Bank", "E-Wallet", "Tarik Tunai"], index=["Bank", "E-Wallet", "Tarik Tunai"].index(jenis_transaksi), horizontal=True)
        nominal_akhir = st.number_input("Nominal Transaksi (Rp):", value=nominal_transaksi, step=10000)
        
        admin = hitung_admin(nominal_akhir, jenis_transaksi)
        total_uang = nominal_akhir + admin if jenis_transaksi != "Tarik Tunai" else nominal_akhir - admin
        
        c1, c2 = st.columns(2)
        c1.metric("Nominal Uang", f"Rp {nominal_akhir:,}")
        c2.metric("Biaya Admin", f"Rp {admin:,}")
        
        if jenis_transaksi == "Tarik Tunai":
            st.info(f"💵 Uang Tunai Diserahkan (Potong Admin): **Rp {total_uang:,}**")
        else:
            st.success(f"💰 Total Tagihan Pelanggan: **Rp {total_uang:,}**")
        
        if st.button("💾 Simpan Transaksi", type="primary", use_container_width=True):
            # Ambil Waktu Indonesia Barat (WIB)
            tz = pytz.timezone('Asia/Jakarta')
            waktu_sekarang = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. Simpan ke Google Sheets (Permanen)
            if worksheet:
                try:
                    worksheet.append_row([waktu_sekarang, jenis_transaksi, nominal_akhir, admin, total_uang])
                    st.success("✅ Transaksi berhasil disimpan permanen ke Google Sheets!")
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")
            else:
                st.warning("Database Google Sheets belum menyala. Hanya tersimpan di rekap web.")
            
            # 2. Simpan ke Layar Web (Sementara)
            st.session_state['riwayat'].append({
                "Waktu": waktu_sekarang,
                "Jenis": jenis_transaksi,
                "Nominal": nominal_akhir,
                "Admin": admin,
                "Total Uang": total_uang
            })

with tab2:
    st.subheader("Rekap Sementara Hari Ini")
    if st.session_state['riwayat']:
        st.dataframe(st.session_state['riwayat'], use_container_width=True)
        tot_admin = sum(x['Admin'] for x in st.session_state['riwayat'])
        st.metric("Total Keuntungan Admin", f"Rp {tot_admin:,}")
        
        if st.button("🗑️ Hapus Rekap Web"):
            st.session_state['riwayat'] = []
            st.rerun()
    else:
        st.info("Belum ada transaksi tersimpan.")
