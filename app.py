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

st.set_page_config(page_title="Kasir RABAY CELL PRO", layout="centered")

@st.cache_resource
def konek_gsheets():
    try:
        json_string = st.secrets["GOOGLE_JSON"].strip()
        kredensial = json.loads(json_string)
        gc = gspread.service_account_from_dict(kredensial)
        sh = gc.open("Database Kasir")
        
        # Pengaman otomatis membuat tab jika belum ada
        try: ws_t = sh.worksheet("Transaksi")
        except: ws_t = sh.add_worksheet(title="Transaksi", rows=1000, cols=5)
            
        try: ws_k = sh.worksheet("Kas_Harian")
        except: ws_k = sh.add_worksheet(title="Kas_Harian", rows=1000, cols=5)
            
        return sh, ws_t, ws_k
    except: return None, None, None

db, ws_t, ws_k = konek_gsheets()

# 2. STATE MANAGEMENT
if 'modal_cash' not in st.session_state: st.session_state['modal_cash'] = 0
if 'modal_digi' not in st.session_state: st.session_state['modal_digi'] = 0
if 'input_nominal' not in st.session_state: st.session_state['input_nominal'] = 0
if 'input_jenis' not in st.session_state: st.session_state['input_jenis'] = "Bank"
if 'draf_scan' not in st.session_state: st.session_state['draf_scan'] = []

st.title("🚀 Kasir RABAY CELL PRO")

with st.expander("💰 Modal Awal Hari Ini"):
    st.session_state['modal_cash'] = st.number_input("Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
    st.session_state['modal_digi'] = st.number_input("Saldo Digital (Rp):", value=st.session_state['modal_digi'], step=50000)

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

tab1, tab2, tab3 = st.tabs(["⚡ Input Transaksi", "📋 Riwayat Transaksi", "📊 Dashboard & Grafik"])

with tab1:
    st.subheader("Pilih Metode Input")
    metode = st.radio("Metode:", ["Ketik Manual / Kode Cepat", "Scan Foto Mutasi (Banyak)"], horizontal=True)
    
    if metode == "Ketik Manual / Kode Cepat":
        quick = st.text_input("Kode Cepat (Contoh: TF100, EW50, TK200) atau kosongkan untuk manual:")
        if quick:
            code = quick.upper().strip()
            st.session_state['input_jenis'] = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
            angka_str = re.sub(r'[^0-9.]', '', code)
            try: st.session_state['input_nominal'] = int(float(angka_str) * 1000)
            except: pass

        st.markdown("---")
        st.session_state['input_jenis'] = st.radio("Jenis Transaksi:", ["Bank", "E-Wallet", "Tarik Tunai"], 
                                                    index=["Bank", "E-Wallet", "Tarik Tunai"].index(st.session_state['input_jenis']), horizontal=True)
        
        nominal_trx = st.number_input("Nominal Transaksi (Rp):", value=st.session_state['input_nominal'], step=10000)
        
        if nominal_trx > 0:
            admin = hitung_admin(nominal_trx, st.session_state['input_jenis'])
            total_uang = nominal_trx + admin if st.session_state['input_jenis'] != "Tarik Tunai" else nominal_trx - admin
            
            c1, c2 = st.columns(2)
            c1.metric("Nominal", f"Rp {nominal_trx:,}")
            c2.metric("Admin", f"Rp {admin:,}")
            
            if st.session_state['input_jenis'] == "Tarik Tunai":
                st.info(f"💵 Uang Tunai Diberikan ke Pelanggan: **Rp {total_uang:,}**")
            else:
                st.success(f"💰 Total Tagihan Pelanggan: **Rp {total_uang:,}**")
                
            if st.button("💾 Simpan & Update Kas", type="primary", use_container_width=True):
                waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                
                if st.session_state['input_jenis'] == "Tarik Tunai":
                    st.session_state['modal_cash'] -= total_uang
                    st.session_state['modal_digi'] += nominal_trx
                else:
                    st.session_state['modal_digi'] -= nominal_trx
                    st.session_state['modal_cash'] += total_uang
                
                if ws_t: ws_t.append_row([waktu, st.session_state['input_jenis'], nominal_trx, admin, total_uang])
                st.success("✅ Transaksi tersimpan & Kas diperbarui!")
                st.session_state['input_nominal'] = 0
                st.rerun()

    else: 
        sumber_gambar = st.file_uploader("Upload Screenshot Mutasi:", type=["jpg", "jpeg", "png"])
        if sumber_gambar and st.button("🔍 Pindai Gambar dengan AI", use_container_width=True):
            try:
                with st.spinner("AI sedang membaca semua angka..."):
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    img = Image.open(sumber_gambar)
                    res = client.models.generate_content(model='gemini-3.6-flash', contents=[img, "Tulis semua nominal transaksi, balas dengan format angka dipisah koma: 5000000,9000000"])
                    nums = [int(x) for x in re.sub(r'[^0-9,]', '', res.text).split(',') if x.isdigit()]
                    st.session_state['draf_scan'] = nums
            except Exception as e:
                st.error(f"Gagal scan: {e}")

        if st.session_state['draf_scan']:
            st.markdown("---")
            jumlah_draf = len(st.session_state['draf_scan'])
            st.info(f"Ditemukan {jumlah_draf} nominal transaksi.")
            jenis_massal = st.radio("Jenis untuk semua data di atas:", ["Bank", "E-Wallet", "Tarik Tunai"], horizontal=True)
            
            if st.button("💾 Simpan Semua ke Database & Kas", type="primary", use_container_width=True):
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
                        
                    if ws_t: ws_t.append_row([waktu, jenis_massal, nom, admin, total])
                
                st.session_state['draf_scan'] = []
                st.success("Semua data berhasil disimpan & kas terupdate!")
                st.rerun()

with tab2:
    st.subheader("📋 Kelola Riwayat Transaksi Terakhir")
    if ws_t:
        data_t = ws_t.get_all_values()
        if len(data_t) > 1:
            df_t = pd.DataFrame(data_t[1:], columns=data_t[0])
            df_t['No_Baris'] = range(2, len(df_t) + 2)
            st.dataframe(df_t, use_container_width=True)
            
            st.markdown("---")
            st.write("### 🗑️ Hapus Transaksi Salah")
            baris_hapus = st.number_input("Masukkan Nomor Baris yang ingin dihapus:", min_value=2, max_value=len(df_t)+1, step=1)
            
            if st.button("❌ Hapus Baris Terpilih dari Database", type="primary"):
                try:
                    ws_t.delete_rows(int(baris_hapus))
                    st.success(f"Berhasil menghapus baris ke-{baris_hapus}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus: {e}")
        else:
            st.info("Belum ada riwayat transaksi tersimpan.")

with tab3:
    st.subheader("📊 Posisi Keuangan & Grafik Bulanan")
    
    c1, c2 = st.columns(2)
    c1.metric("Cash di Laci", f"Rp {st.session_state['modal_cash']:,}")
    c2.metric("Saldo Digital", f"Rp {st.session_state['modal_digi']:,}")
    
    st.markdown("---")
    if st.button("💾 Simpan Rekap Hari Ini ke Sheets", type="primary"):
        if ws_k:
            tanggal = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")
            ws_k.append_row([tanggal, st.session_state['modal_cash'], st.session_state['modal_digi']])
            st.success("Rekap harian berhasil dikirim ke Sheets!")

    st.markdown("### Riwayat & Tren Bulanan")
    if ws_k:
        data = ws_k.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
            df['Bulan'] = df['Tanggal'].dt.strftime('%B %Y')
            
            bulan_pilih = st.selectbox("Pilih Bulan Rekap:", df['Bulan'].unique())
            df_filter = df[df['Bulan'] == bulan_pilih]
            
            st.dataframe(df_filter, use_container_width=True)
            
            fig = px.line(df_filter, x='Tanggal', y=['Modal_Cash', 'Modal_Digital'], 
                          labels={'value': 'Jumlah (Rp)', 'variable': 'Jenis Kas'},
                          title=f"Grafik Perkembangan Kas - {bulan_pilih}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data rekap di Google Sheets.")
