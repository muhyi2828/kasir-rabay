import streamlit as st
from PIL import Image
from google import genai
import re

st.set_page_config(page_title="Kasir RABAY CELL", page_icon="🚀", layout="centered")

# Inisialisasi Memori Transaksi
if 'riwayat' not in st.session_state:
    st.session_state['riwayat'] = []

st.title("🚀 Kasir RABAY CELL")
st.caption("Sistem POS & Pemindai Struk Otomatis")

# Sidebar untuk API Key
st.sidebar.header("🔑 Pengaturan Sistem")
api_key = st.sidebar.text_input("Masukkan API Key Gemini:", type="password")
st.sidebar.info("API Key aman dan tidak disimpan permanen di publik.")

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
    response = client.models.generate_content(model='gemini-2.5-flash', contents=[gambar, prompt])
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
    
    # 1. Fitur Quick Code
    quick_code = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200):")
    
    # 2. Fitur Kamera OCR
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
                    st.error("Gagal membaca gambar. Pastikan API Key benar.")
        else:
            st.warning("Masukkan API Key di menu samping (>) dulu untuk scan struk.")

    # 3. Kalkulator & Konfirmasi
    if nominal_transaksi > 0:
        st.markdown("---")
        jenis_transaksi = st.radio("Jenis Transaksi:", ["Bank", "E-Wallet", "Tarik Tunai"], index=["Bank", "E-Wallet", "Tarik Tunai"].index(jenis_transaksi), horizontal=True)
        nominal_akhir = st.number_input("Nominal Transaksi (Rp):", value=nominal_transaksi, step=10000)
        
        admin = hitung_admin(nominal_akhir, jenis_transaksi)
        
        c1, c2 = st.columns(2)
        c1.metric("Nominal Uang", f"Rp {nominal_akhir:,}")
        c2.metric("Biaya Admin", f"Rp {admin:,}")
        
        if jenis_transaksi == "Tarik Tunai":
            st.info(f"💵 Uang Tunai Diserahkan (Potong Admin): **Rp {nominal_akhir - admin:,}**")
        else:
            st.success(f"💰 Total Tagihan Pelanggan: **Rp {nominal_akhir + admin:,}**")
        
        if st.button("💾 Simpan Transaksi", type="primary", use_container_width=True):
            st.session_state['riwayat'].append({
                "Jenis": jenis_transaksi,
                "Nominal": nominal_akhir,
                "Admin": admin
            })
            st.success("Transaksi berhasil dicatat!")

with tab2:
    st.subheader("Rekap Sementara Hari Ini")
    if st.session_state['riwayat']:
        st.dataframe(st.session_state['riwayat'], use_container_width=True)
        tot_admin = sum(x['Admin'] for x in st.session_state['riwayat'])
        st.metric("Total Keuntungan Admin", f"Rp {tot_admin:,}")
        
        if st.button("🗑️ Hapus Rekap"):
            st.session_state['riwayat'] = []
            st.rerun()
    else:
        st.info("Belum ada transaksi tersimpan.")
