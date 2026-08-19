import streamlit as st
from PIL import Image
from google import genai
import re
import gspread
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Kasir RABAY CELL PRO", layout="centered")

# Inisialisasi Database
@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        return sh, "Aman"
    except Exception as e: return None, str(e)

db, error = konek_gsheets()
ws_transaksi = db.worksheet("Transaksi") if db else None
ws_kas = db.worksheet("Kas_Harian") if db else None

# Inisialisasi State
if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = 0
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = 0
if 'hasil_scan' not in st.session_state: st.session_state['hasil_scan'] = []

st.title("🚀 Kasir RABAY CELL PRO")

# MODUL MODAL AWAL
with st.expander("💰 Setel Modal Awal"):
    st.session_state['modal_cash'] = st.number_input("Modal Cash di Laci:", value=st.session_state['modal_cash'])
    st.session_state['modal_digi'] = st.number_input("Saldo Digital Awal:", value=st.session_state['modal_digi'])

# FUNGSI HITUNG & PROSES
def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 299000: return 4000
        else: return 10000
    else: # Tarik Tunai / Bank
        if nominal <= 400000: return 5000
        elif nominal <= 1000000: return 10000
        else: return 20000

# INPUT & SCANNER
quick = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200):")
if quick:
    code = quick.upper().strip()
    nominal = int(re.sub(r'[^0-9.]', '', code)) * 1000
    jenis = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
    st.session_state['hasil_scan'] = [{"Nominal": nominal, "Jenis": jenis}]

sumber_gambar = st.file_uploader("Atau Upload Screenshot Mutasi:", type=["jpg", "png"])
if sumber_gambar and st.button("🔍 Scan AI"):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    img = Image.open(sumber_gambar)
    res = client.models.generate_content(model='gemini-3.6-flash', contents=[img, "Tulis semua nominal transaksi, balas dengan format: 5000000,9000000"])
    nums = [int(x) for x in re.sub(r'[^0-9,]', '', res.text).split(',') if x.isdigit()]
    st.session_state['hasil_scan'] = [{"Nominal": n, "Jenis": "Bank"} for n in nums]

# PROSES TRANSAKSI
if st.session_state['hasil_scan']:
    st.subheader("Draf Transaksi")
    for i, item in enumerate(st.session_state['hasil_scan']):
        col1, col2 = st.columns([2,1])
        item['Jenis'] = col1.selectbox(f"Jenis #{i+1}", ["Bank", "E-Wallet", "Tarik Tunai"], index=["Bank", "E-Wallet", "Tarik Tunai"].index(item['Jenis']))
        st.write(f"Nominal: Rp {item['Nominal']:,}")
    
    if st.button("💾 Simpan & Update Kas"):
        tz = pytz.timezone('Asia/Jakarta')
        waktu = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        
        for item in st.session_state['hasil_scan']:
            admin = hitung_admin(item['Nominal'], item['Jenis'])
            
            # Update Logika Kas
            if item['Jenis'] == "Tarik Tunai":
                st.session_state['modal_cash'] -= item['Nominal']
                st.session_state['modal_digi'] += (item['Nominal'] - admin)
            elif item['Jenis'] == "E-Wallet":
                st.session_state['modal_cash'] += (item['Nominal'] + admin)
                st.session_state['modal_digi'] -= item['Nominal']
            else:
                st.session_state['modal_cash'] += admin
            
            if ws_transaksi: ws_transaksi.append_row([waktu, item['Jenis'], item['Nominal'], admin])
            
        st.session_state['hasil_scan'] = []
        st.rerun()

# DASHBOARD
st.markdown("---")
c1, c2 = st.columns(2)
c1.metric("Cash Laci", f"Rp {st.session_state['modal_cash']:,}")
c2.metric("Saldo Digi", f"Rp {st.session_state['modal_digi']:,}")

if st.button("📊 Rekap Harian ke Sheets"):
    if ws_kas: ws_kas.append_row([datetime.now().strftime("%Y-%m-%d"), st.session_state['modal_cash'], st.session_state['modal_digi']])
    st.success("Rekap tersimpan!")
