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
if 'riwayat' not in st.session_state:
    st.session_state['riwayat'] = []
if 'hasil_scan_banyak' not in st.session_state:
    st.session_state['hasil_scan_banyak'] = []

st.title("🚀 Kasir RABAY CELL")

if worksheet:
    st.caption("🟢 Terkoneksi ke Google Sheets")
else:
    st.error(f"🔴 Database Terputus! {pesan_error_db}")

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

# FUNGSI BARU: Baca Banyak Nominal Sekaligus
def baca_nominal_ocr_banyak(gambar, key):
    client = genai.Client(api_key=key)
    prompt = """
    Temukan SEMUA angka nominal transaksi utama (uang masuk/keluar) di gambar riwayat/struk ini. 
    Abaikan tanggal, jam, atau teks lainnya.
    HANYA balas dengan angka mentahnya saja, PISAHKAN DENGAN KOMA. 
    Contoh balasan: 5000000,9000000,4000000,5000000
    """
    response = client.models.generate_content(model='gemini-3.6-flash', contents=[gambar, prompt])
    
    # Membersihkan balasan AI agar cuma tersisa angka dan koma
    teks_bersih = re.sub(r'[^0-9,]', '', response.text)
    
    # Memecah angka berdasarkan koma dan mengubahnya jadi list angka
    if not teks_bersih: return []
    return [int(x) for x in teks_bersih.split(',') if x.isdigit()]

tab1, tab2 = st.tabs(["⚡ Input Kasir", "📊 Rekap Harian"])

with tab1:
    st.subheader("Input Transaksi Baru")
    sumber_gambar = st.file_uploader("Upload Foto Struk / Screenshot Mutasi:", type=["jpg", "jpeg", "png"])
    
    # Tombol Scan AI
    if sumber_gambar and api_key:
        if st.button("🔍 Pindai Gambar dengan AI", use_container_width=True):
            try:
                gambar = Image.open(sumber_gambar)
                st.image(gambar, width=250)
                with st.spinner("AI sedang mengumpulkan semua angka di gambar..."):
                    daftar_angka = baca_nominal_ocr_banyak(gambar, api_key)
                    
                    if daftar_angka:
                        st.session_state['hasil_scan_banyak'] = daftar_angka
                        st.success(f"Berhasil menemukan {len(daftar_angka)} transaksi!")
                    else:
                        st.warning("Tidak ada nominal yang terdeteksi.")
            except Exception as e:
                st.error(f"Gagal memindai: {e}")

    # Area Pemrosesan Banyak Data
    if st.session_state['hasil_scan_banyak']:
        st.markdown("---")
        st.info("### 📑 Draf Transaksi (Cek Sebelum Disimpan)")
        
        jenis_massal = st.radio("Pilih Jenis Transaksi untuk data di bawah ini:", ["Bank", "E-Wallet", "Tarik Tunai"], horizontal=True)
        
        # Buat tabel preview sementara
        preview_data = []
        total_admin_massal = 0
        
        for nominal in st.session_state['hasil_scan_banyak']:
            admin = hitung_admin(nominal, jenis_massal)
            total_uang = nominal + admin if jenis_massal != "Tarik Tunai" else nominal - admin
            total_admin_massal += admin
            
            preview_data.append({
                "Nominal": nominal,
                "Admin": admin,
                "Total Uang": total_uang
            })
            
        st.dataframe(preview_data, use_container_width=True)
        st.write(f"**Potensi Keuntungan Admin:** Rp {total_admin_massal:,}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("❌ Batal / Hapus", use_container_width=True):
                st.session_state['hasil_scan_banyak'] = []
                st.rerun()
        with c2:
            if st.button("💾 Simpan Semua ke Database", type="primary", use_container_width=True):
                tz = pytz.timezone('Asia/Jakarta')
                waktu_sekarang = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                
                baris_untuk_gsheets = []
                
                for data in preview_data:
                    # Siapkan data untuk ke Web
                    st.session_state['riwayat'].append({
                        "Waktu": waktu_sekarang,
                        "Jenis": jenis_massal,
                        "Nominal": data['Nominal'],
                        "Admin": data['Admin'],
                        "Total Uang": data['Total Uang']
                    })
                    # Siapkan data untuk ke Google Sheets
                    baris_untuk_gsheets.append([
                        waktu_sekarang, jenis_massal, data['Nominal'], data['Admin'], data['Total Uang']
                    ])
                
                # Masukkan ke Google Sheets secara massal (sekali kirim)
                if worksheet:
                    try:
                        worksheet.append_rows(baris_untuk_gsheets)
                        st.toast("✅ Semua data masuk ke Google Sheets!")
                    except Exception as e:
                        st.error(f"Gagal simpan ke database: {e}")
                
                st.session_state['hasil_scan_banyak'] = []
                st.success("Selesai! Semua transaksi berhasil diproses.")
                st.rerun()

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
