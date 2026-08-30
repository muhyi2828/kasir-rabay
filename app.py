import streamlit as st
import pandas as pd
from PIL import Image
from google import genai
import re
from supabase import create_client, Client
import json
from datetime import datetime
import pytz
import io
import base64
import time

# --- KONFIGURASI HALAMAN HARUS PALING ATAS ---
st.set_page_config(page_title="RABAY CELL PRO", layout="centered", page_icon="🚀", initial_sidebar_state="collapsed")

# --- CUSTOM CSS UI MODERN DARK MODE & POPUP MENU ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ffffff; }
    .rabay-header {
        background-color: #14B8A6;
        padding: 12px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: -65px;
        margin-bottom: 15px;
        margin-left: -1rem;
        margin-right: -1rem;
        border-radius: 0px;
    }
    .rabay-header h1 { color: white; margin: 0; font-size: 22px; font-weight: 800; font-family: sans-serif; letter-spacing: 1px;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; overflow-x: auto; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px !important; color: #cccccc !important; background-color: transparent !important; padding: 10px 15px !important; font-weight: 600 !important; white-space: nowrap; }
    .stTabs [aria-selected="true"] { background-color: #14B8A6 !important; color: white !important; }
    div[data-baseweb="input"] { background-color: #1E1E1E !important; border-radius: 8px !important; border: 1px solid #14B8A6 !important; }
    input { color: #14B8A6 !important; font-weight: bold !important; text-align: center !important; font-size: 18px !important;}
    .barcode-box { margin-bottom: 20px; margin-top: 10px; }
    label, .stRadio label { color: #cccccc !important; }
    .metric-card-blue { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid #14B8A6; margin-bottom: 15px; }
    .floating-container { position: fixed; bottom: 0; left: 0; right: 0; background-color: rgba(5, 5, 5, 0.95); padding: 12px 16px; z-index: 99999; border-top: 1px solid #222; box-shadow: 0 -4px 10px rgba(0,0,0,0.8); }
    .main .block-container { padding-bottom: 90px; }
    .login-box { background-color: #111; padding: 30px; border-radius: 12px; border: 1px solid #14B8A6; margin-top: 50px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI FORMAT UANG ---
def f_uang(val):
    try:
        val_int = int(val)
        return f"Rp {val_int:,}".replace(",", ".")
    except:
        return str(val)

# --- FUNGSI KONEKSI SUPABASE ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        return None

supabase = init_supabase()

# --- FUNGSI AMBIL KREDENSIAL AKUN MASTER ---
def get_master_credentials(sb):
    if not sb: return "admin", "123"
    try:
        res = sb.table("pengaturan_akun").select("*").execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("username", "admin"), res.data[0].get("password", "123")
    except:
        pass
    return "admin", "123"

db_user, db_pass = get_master_credentials(supabase)

# --- AMBIL DAFTAR CABANG DARI DATABASE ---
def fetch_daftar_cabang(sb):
    default_cabang = {"RABAY01": "Pusat", "Medang": "Cabang 2", "G. BATU": "Cabang 3"}
    if not sb: return default_cabang
    try:
        res = sb.table("cabang").select("*").execute()
        if res.data and len(res.data) > 0:
            return {item['kode']: item['nama_tampilan'] for item in res.data}
        else:
            for k, v in default_cabang.items():
                sb.table("cabang").insert({"kode": k, "nama_tampilan": v}).execute()
            return default_cabang
    except:
        return default_cabang

mapping_cabang = fetch_daftar_cabang(supabase)
daftar_tampilan_cabang = list(mapping_cabang.keys())

# --- SISTEM LOGIN MASTER ---
if 'is_logged_in' not in st.session_state:
    if st.query_params.get("auth") == "1":
        st.session_state['is_logged_in'] = True
    else:
        st.session_state['is_logged_in'] = False

if 'cabang_terpilih' not in st.session_state:
    if st.query_params.get("cabang") and st.query_params.get("cabang") in daftar_tampilan_cabang:
        st.session_state['cabang_terpilih'] = st.query_params.get("cabang")
    else:
        st.session_state['cabang_terpilih'] = daftar_tampilan_cabang[0] if daftar_tampilan_cabang else "RABAY01"

if not st.session_state['is_logged_in']:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: #14B8A6; margin-bottom: 20px;'>LOGIN MASTER<br>RABAY CELL</h2>", unsafe_allow_html=True)
    input_user = st.text_input("Username:")
    input_pass = st.text_input("Password:", type="password")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 MASUK SISTEM", type="primary", use_container_width=True):
        if input_user == db_user and input_pass == db_pass:
            st.session_state['is_logged_in'] = True
            st.query_params["auth"] = "1"
            st.query_params["cabang"] = st.session_state['cabang_terpilih']
            st.success("Akses Diterima!")
            st.rerun()
        else:
            st.error("❌ Username atau Password salah!")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- FUNGSI DATABASE SUPABASE (CRUD) ---
cabang_aktif = st.session_state['cabang_terpilih']

@st.cache_data(ttl=5)
def fetch_table_data(table_name, cabang):
    if not supabase: return []
    try:
        res = supabase.table(table_name).select("*").eq("cabang", cabang).execute()
        return res.data if res.data else []
    except:
        return []

def db_insert(table_name, data_dict):
    if not supabase: return False, "Supabase client tidak terhubung"
    try:
        data_dict["cabang"] = cabang_aktif
        supabase.table(table_name).insert(data_dict).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def db_update(table_name, row_id, data_dict):
    if not supabase: return False, "Supabase client tidak terhubung"
    try:
        supabase.table(table_name).update(data_dict).eq("id", row_id).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def db_delete(table_name, row_id):
    if not supabase: return False
    try:
        supabase.table(table_name).delete().eq("id", row_id).execute()
        return True
    except:
        return False

# AMBIL DATA DARI SUPABASE
with st.spinner("⏳ Sinkronisasi Database Supabase..."):
    data_t = fetch_table_data("transaksi", cabang_aktif)
    data_s = fetch_table_data("stok", cabang_aktif)
    data_k = fetch_table_data("kas", cabang_aktif)
    data_sesi = fetch_table_data("riwayat_sesi", cabang_aktif)
    data_gaji = fetch_table_data("gaji_karyawan", cabang_aktif)
    
    try:
        res_cat = supabase.table("catatan_harian").select("*").eq("cabang", cabang_aktif).order("waktu", desc=True).execute()
        data_catatan = res_cat.data if res_cat.data else []
    except:
        data_catatan = []

if data_t is None or data_s is None or data_k is None or data_sesi is None or data_gaji is None:
    st.error("⚠️ Gagal terhubung ke Supabase. Periksa kembali URL dan Kunci API Anda.")
    st.stop()

# AMBIL DATA SESI AKTIF & WAKTU MULAI DARI SUPABASE
def load_active_session_from_db(data_kas_db, data_sesi_db):
    cash = 0
    digi = 0
    waktu_mulai = "2020-01-01 00:00:00"

    if data_sesi_db and len(data_sesi_db) > 0:
        sorted_sesi = sorted(data_sesi_db, key=lambda x: x.get('waktu_tutup_sesi', ''), reverse=True)
        waktu_mulai = sorted_sesi[0].get('waktu_tutup_sesi', waktu_mulai)

    if data_kas_db and len(data_kas_db) > 0:
        sorted_kas = sorted(data_kas_db, key=lambda x: x.get('waktu', ''), reverse=True)
        latest = sorted_kas[0]
        latest_waktu_kas = latest.get('waktu', '')
        
        if latest_waktu_kas > waktu_mulai:
            waktu_mulai = latest_waktu_kas
            cash = int(latest.get('cash', 0))
            digi = int(latest.get('digital', 0))

    return cash, digi, waktu_mulai

db_cash, db_digi, db_waktu_mulai = load_active_session_from_db(data_k, data_sesi)

if 'waktu_mulai_sesi' not in st.session_state:
    st.session_state['waktu_mulai_sesi'] = db_waktu_mulai

if 'modal_cash' not in st.session_state: 
    st.session_state['modal_cash'] = db_cash

if 'modal_digi' not in st.session_state: 
    st.session_state['modal_digi'] = db_digi

if 'penyesuaian_cash' not in st.session_state: st.session_state['penyesuaian_cash'] = 0
if 'penyesuaian_digi' not in st.session_state: st.session_state['penyesuaian_digi'] = 0
if 'draf_scan_smart' not in st.session_state: st.session_state['draf_scan_smart'] = []
if 'gambar_scan_terakhir' not in st.session_state: st.session_state['gambar_scan_terakhir'] = None
if 'keranjang_belanja' not in st.session_state: st.session_state['keranjang_belanja'] = []
if 'is_submitting' not in st.session_state: st.session_state['is_submitting'] = False

# --- FUNGSI HITUNG ADMIN ---
def hitung_admin(nominal, jenis):
    if jenis == "E-Wallet" and nominal <= 1500000:
        if nominal <= 98000: return 2000
        elif nominal <= 199000: return 3000
        elif nominal <= 299000: return 4000
        elif nominal <= 699000: return 5000
        elif nominal <= 1000000: return 8000
        else: return 10000
    elif jenis == "Tarik Tunai":
        if nominal <= 303000: return 3000
        elif nominal <= 1005000: return 5000
        elif nominal <= 2008000: return 8000
        elif nominal <= 3010000: return 10000
        elif nominal <= 5015000: return 15000
        elif nominal <= 7020000: return 20000
        elif nominal <= 10025000: return 25000
        elif nominal <= 15030000: return 30000
        elif nominal <= 20035000: return 35000
        else: return 35000 + (-(-(nominal - 20035000) // 5000000) * 5000)
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

# --- HEADER UTAMA DENGAN TOMBOL POPUP MENU DI DALAMNYA ---
col_head1, col_head2 = st.columns([6, 1])
with col_head1:
    nama_cabang_tampil = mapping_cabang.get(st.session_state['cabang_terpilih'], st.session_state['cabang_terpilih'])
    st.markdown(f"""
        <div class="rabay-header">
            <h1>RABAY CELL - {nama_cabang_tampil.upper()}</h1>
        </div>
    """, unsafe_allow_html=True)

with col_head2:
    st.markdown("<div style='margin-top: -53px;'>", unsafe_allow_html=True)
    with st.popover("≡", help="Menu Setelan"):
        
        total_profit_bulan_ini = 0
        total_omzet_bulan_ini = 0
        
        now_jkt = datetime.now(pytz.timezone('Asia/Jakarta'))
        current_year = now_jkt.year
        current_month = now_jkt.month

        if data_sesi and len(data_sesi) > 0:
            df_sesi_prof = pd.DataFrame(data_sesi)
            df_sesi_prof['Waktu_Tutup_Parsed'] = pd.to_datetime(df_sesi_prof['waktu_tutup_sesi'], errors='coerce')
            
            df_sesi_bulan_ini = df_sesi_prof[
                (df_sesi_prof['Waktu_Tutup_Parsed'].dt.year == current_year) & 
                (df_sesi_prof['Waktu_Tutup_Parsed'].dt.month == current_month)
            ]
            if not df_sesi_bulan_ini.empty:
                total_profit_bulan_ini += pd.to_numeric(df_sesi_bulan_ini['total_profit'], errors='coerce').fillna(0).sum()

        if data_t and len(data_t) > 0:
            df_trx_all = pd.DataFrame(data_t)
            df_trx_all['Waktu_Parsed'] = pd.to_datetime(df_trx_all['waktu'], errors='coerce')
            df_trx_bulan_ini = df_trx_all[
                (df_trx_all['Waktu_Parsed'].dt.year == current_year) & 
                (df_trx_all['Waktu_Parsed'].dt.month == current_month)
            ]
            if not df_trx_bulan_ini.empty:
                total_profit_bulan_ini += pd.to_numeric(df_trx_bulan_ini['profit'], errors='coerce').fillna(0).sum()
                total_omzet_bulan_ini += pd.to_numeric(df_trx_bulan_ini['total'], errors='coerce').fillna(0).sum()

        st.markdown(f"""
            <div style="background-color:#1E1E1E; padding:15px; border-radius:10px; border:1px solid #14B8A6; text-align:center; margin-bottom:20px;">
                <span style="color:#aaa; font-size:12px; font-weight:bold;">TOTAL OMZET BULAN INI</span><br>
                <span style="color:#ffffff; font-size:18px; font-weight:bold; margin-bottom:8px; display:block;">{f_uang(total_omzet_bulan_ini)}</span>
                <hr style="border-color:#333; margin:8px 0;">
                <span style="color:#aaa; font-size:12px; font-weight:bold;">TOTAL PROFIT BULAN INI</span><br>
                <span style="color:#14B8A6; font-size:20px; font-weight:bold;">{f_uang(total_profit_bulan_ini)}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.write("**Ganti Akses Cabang Ke:**")
        idx_cabang_aktif = daftar_tampilan_cabang.index(st.session_state['cabang_terpilih']) if st.session_state['cabang_terpilih'] in daftar_tampilan_cabang else 0
        pilihan_pindah = st.selectbox("Cabang", daftar_tampilan_cabang, format_func=lambda x: f"{x} ({mapping_cabang.get(x, '')})", index=idx_cabang_aktif, label_visibility="collapsed")
        
        if st.button("PINDAH CABANG", type="primary", use_container_width=True):
            st.session_state['cabang_terpilih'] = pilihan_pindah
            st.query_params["cabang"] = pilihan_pindah
            if 'modal_cash' in st.session_state: del st.session_state['modal_cash']
            if 'modal_digi' in st.session_state: del st.session_state['modal_digi']
            st.session_state['keranjang_belanja'] = []
            st.session_state['draf_scan_smart'] = []
            st.session_state['gambar_scan_terakhir'] = None
            st.cache_data.clear()
            st.success(f"Berhasil pindah akses ke {pilihan_pindah}!")
            st.rerun()

        st.markdown("---")
        st.markdown("🏢 **Manajemen Cabang**")
        with st.expander("➕ Tambah / Kelola Cabang"):
            with st.form("form_tambah_cabang_baru"):
                kode_baru = st.text_input("Kode Cabang (Unik, misal: Cabang4)")
                nama_tampil_baru = st.text_input("Nama Tampilan (misal: Cabang 4)")
                if st.form_submit_button("Simpan Cabang Baru"):
                    if kode_baru and nama_tampil_baru:
                        try:
                            supabase.table("cabang").insert({"kode": kode_baru.strip(), "nama_tampilan": nama_tampil_baru.strip()}).execute()
                            st.cache_data.clear()
                            st.success("Cabang baru berhasil ditambahkan!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal tambah cabang: {e}")
                    else:
                        st.error("Semua kolom harus diisi!")

            if len(daftar_tampilan_cabang) > 1:
                cabang_dihapus = st.selectbox("Pilih Cabang untuk Dihapus:", options=daftar_tampilan_cabang)
                if st.button("🗑️ Hapus Cabang Ini", type="primary"):
                    try:
                        supabase.table("cabang").delete().eq("kode", cabang_dihapus).execute()
                        st.cache_data.clear()
                        st.success(f"Cabang {cabang_dihapus} berhasil dihapus!")
                        if st.session_state['cabang_terpilih'] == cabang_dihapus:
                            st.session_state['cabang_terpilih'] = "RABAY01"
                            st.query_params["cabang"] = "RABAY01"
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus cabang: {e}")

        st.markdown("---")
        st.markdown("🔐 **Akun Master (Kontrol Cabang)**")
        
        with st.form("form_ubah_akun_pop"):
            user_baru = st.text_input("Username Master Baru", value=db_user)
            pass_baru = st.text_input("Password Master Baru", value=db_pass, type="password")
            
            if st.form_submit_button("Simpan Perubahan Akun"):
                if user_baru and pass_baru:
                    try:
                        res_akun = supabase.table("pengaturan_akun").select("id").execute()
                        if res_akun.data and len(res_akun.data) > 0:
                            akun_id = res_akun.data[0]['id']
                            supabase.table("pengaturan_akun").update({"username": user_baru, "password": pass_baru}).eq("id", akun_id).execute()
                        else:
                            supabase.table("pengaturan_akun").insert({"username": user_baru, "password": pass_baru}).execute()
                        st.success("Akun berhasil diperbarui!")
                    except Exception as e:
                        st.error(f"Gagal: {e}")
                else: st.error("Tidak boleh kosong!")

        st.markdown("---")
        if st.button("🚪 Keluar / Logout Aplikasi", use_container_width=True):
            st.session_state['is_logged_in'] = False
            if "auth" in st.query_params: del st.query_params["auth"]
            if "cabang" in st.query_params: del st.query_params["cabang"]
            st.cache_data.clear()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB UTAMA (5 TAB) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["TRANSAKSI", "RIWAYAT", "DASHBOARD", "STOK BARANG", "💰 GAJI"])

with tab1:
    modal_belum_diisi = (st.session_state['modal_cash'] == 0 and st.session_state['modal_digi'] == 0)
    
    if modal_belum_diisi:
        st.error("⚠️ MASUKAN MODAL AWAL DULU")
        st.info("Silakan buka Tab **DASHBOARD** lalu isi **Setel Modal Awal Sesi Ini** untuk mulai bertransaksi.")
    
    metode = st.radio("Metode Input:", ["Ketik Manual / Barcode", "AI Scan Catatan Voucher / Mutasi"], horizontal=True, label_visibility="collapsed")
    
    if metode == "Ketik Manual / Barcode":
        st.markdown('<div class="barcode-box">', unsafe_allow_html=True)
        quick = st.text_input("INPUT KODE CEPAT/BARCODE", placeholder="Ketik kode cepat / barcode", label_visibility="collapsed", disabled=modal_belum_diisi)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- FITUR SARAN / PENCARIAN BARANG OTOMATIS ---
        if quick and not modal_belum_diisi and len(data_s) > 0:
            query_input = quick.upper().strip()
            saran_barang = [
                item for item in data_s 
                if query_input in str(item.get('kode_cepat', '')).upper() 
                or query_input in str(item.get('barcode', '')).upper()
                or query_input in str(item.get('nama_barang', '')).upper()
            ]
            
            if saran_barang:
                st.caption(f"🔍 Ditemukan {len(saran_barang)} barang yang cocok:")
                pilihan_saran = st.selectbox(
                    "Pilih dari saran:",
                    options=saran_barang,
                    format_func=lambda x: f"{x.get('nama_barang')} | Kode: {x.get('kode_cepat')} | Harga: {f_uang(x.get('harga_jual'))} (Stok: {x.get('stok')})",
                    key="select_saran_barang",
                    label_visibility="collapsed"
                )
                if pilihan_saran:
                    quick = pilihan_saran.get('kode_cepat', '')

        nama_brg_det = ""
        row_id_stok = None
        stok_sisa_brg = 0
        profit_brg_det = 0
        jenis_trx_manual = "Bank"
        nominal_val = 0

        if quick and not modal_belum_diisi:
            code = quick.upper().strip()
            if len(data_s) > 0:
                for item in data_s:
                    if str(item.get('kode_cepat', '')).upper() == code or str(item.get('barcode', '')).upper() == code:
                        nama_brg_det = item.get('nama_barang', '')
                        row_id_stok = item.get('id')
                        stok_sisa_brg = int(item.get('stok', 0))
                        hargamodal = int(item.get('harga_modal', 0))
                        hargajual = int(item.get('harga_jual', 0))
                        profit_brg_det = hargajual - hargamodal
                        jenis_trx_manual = "Penjualan Barang"
                        nominal_val = hargajual
                        break

            if code.startswith("TF") or code.startswith("EW") or code.startswith("TK"):
                jenis_trx_manual = "E-Wallet" if code.startswith("EW") else "Tarik Tunai" if code.startswith("TK") else "Bank"
                angka_str = re.sub(r'[^0-9.]', '', code)
                try: nominal_val = int(float(angka_str) * 1000)
                except: pass

        st.caption("Jenis Transaksi:")
        pilihan_jenis = ["Bank", "E-Wallet", "Tarik Tunai", "Penjualan Barang", "Transaksi Lainnya"]
        current_idx = pilihan_jenis.index(jenis_trx_manual) if jenis_trx_manual in pilihan_jenis else 0
        
        jenis_terpilih = st.radio("Jenis", pilihan_jenis, index=current_idx, horizontal=True, label_visibility="collapsed", disabled=modal_belum_diisi)
        
        if nama_brg_det and jenis_terpilih == "Penjualan Barang":
            if stok_sisa_brg <= 0:
                st.error(f"📦 Terdeteksi: **{nama_brg_det}** | ⚠️ **STOK HABIS (0)** | Untung: **{f_uang(profit_brg_det)}**")
            else:
                st.success(f"📦 Terdeteksi: **{nama_brg_det}** (Sisa Stok: {stok_sisa_brg}) | Untung: **{f_uang(profit_brg_det)}**")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Nominal / Harga (Rp):")
        nominal_trx = st.number_input("Nominal", value=nominal_val, step=10000, label_visibility="collapsed", disabled=modal_belum_diisi)
        if nominal_trx > 0:
            st.markdown(f"<p style='color:#14B8A6; font-size:18px; font-weight:bold;'>Format: {f_uang(nominal_trx)}</p>", unsafe_allow_html=True)
        
        profit_manual = 0
        if jenis_terpilih == "Transaksi Lainnya":
            st.caption("Keuntungan Manual (Rp):")
            profit_manual = st.number_input("Profit", value=0, step=1000, label_visibility="collapsed", disabled=modal_belum_diisi)

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
            
            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 SIMPAN LANGSUNG", type="primary", use_container_width=True, disabled=st.session_state['is_submitting'] or modal_belum_diisi):
                    if jenis_terpilih == "Penjualan Barang" and row_id_stok and stok_sisa_brg <= 0:
                        st.error("❌ Gagal! Stok barang ini sudah habis (0) dan tidak bisa dijual.")
                    else:
                        st.session_state['is_submitting'] = True
                        waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                        
                        if jenis_terpilih == "Penjualan Barang" and row_id_stok:
                            db_update("stok", row_id_stok, {"stok": max(0, stok_sisa_brg - 1)})
                        
                        ket_simpan = nama_brg_det if jenis_terpilih == "Penjualan Barang" else ""
                        
                        sukses, err_msg = db_insert("transaksi", {
                            "waktu": waktu, "jenis": jenis_terpilih, "nominal": int(nominal_trx),
                            "admin": int(admin), "total": int(total_uang), "profit": int(profit_bersih),
                            "keterangan": ket_simpan
                        })
                        
                        st.session_state['is_submitting'] = False
                        if sukses:
                            st.cache_data.clear()
                            st.success("Tersimpan!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Gagal simpan! Error: {err_msg}")

            with col_b2:
                if st.button("🛒 MASUK KERANJANG", use_container_width=True, disabled=modal_belum_diisi):
                    if jenis_terpilih == "Penjualan Barang" and row_id_stok and stok_sisa_brg <= 0:
                        st.error("❌ Gagal! Stok barang ini sudah habis (0).")
                    else:
                        st.session_state['keranjang_belanja'].append({
                            'Jenis': jenis_terpilih, 'Nama': nama_brg_det if nama_brg_det else jenis_terpilih,
                            'Nominal Satuan': int(nominal_trx), 'Admin/Profit Satuan': int(profit_bersih), 
                            'Qty': 1, 'Row_Stok': row_id_stok, 'Sisa_Stok': stok_sisa_brg
                        })
                        st.success("Masuk keranjang!")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state['keranjang_belanja']:
            st.markdown("---")
            st.write("### 🛒 Keranjang Belanjaan")
            
            for idx_c, cart_item in enumerate(st.session_state['keranjang_belanja']):
                c_nama = cart_item['Nama']
                c_jenis = cart_item['Jenis']
                c_satuan = cart_item['Nominal Satuan']
                
                st.markdown(f"**{c_nama}** (<span style='color:#14B8A6;'>{c_jenis}</span>)<br>Harga Satuan: {f_uang(c_satuan)}", unsafe_allow_html=True)
                
                col_q1, col_q2 = st.columns([2, 8])
                with col_q1:
                    new_qty = st.number_input("Qty", min_value=1, value=cart_item['Qty'], step=1, key=f"qty_cart_{idx_c}", label_visibility="collapsed")
                    cart_item['Qty'] = new_qty
                with col_q2:
                    subtotal_item = (c_satuan + (cart_item['Admin/Profit Satuan'] if c_jenis == "Transaksi Lainnya" else 0)) * new_qty
                    st.markdown(f"<p style='padding-top:6px; font-weight:bold; color:#2ca02c;'>Subtotal: {f_uang(subtotal_item)}</p>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)

            total_belanja = sum(
                (item['Nominal Satuan'] + (item['Admin/Profit Satuan'] if item['Jenis'] == "Transaksi Lainnya" else 0)) * item['Qty']
                for item in st.session_state['keranjang_belanja']
            )
            st.info(f"💵 Total Tagihan: **{f_uang(total_belanja)}**")
            
            c_k1, c_k2 = st.columns(2)
            if c_k1.button("🚀 PROSES SEMUA", type="primary", use_container_width=True, disabled=st.session_state['is_submitting'] or modal_belum_diisi):
                # Validasi kumulatif stok pada keranjang
                permintaan_keranjang = {}
                for item in st.session_state['keranjang_belanja']:
                    if item['Jenis'] == "Penjualan Barang" and item['Row_Stok']:
                        r_id = item['Row_Stok']
                        permintaan_keranjang[r_id] = permintaan_keranjang.get(r_id, 0) + item['Qty']

                stok_cukup = True
                for r_id, total_minta in permintaan_keranjang.items():
                    for s_item in data_s:
                        if s_item.get('id') == r_id:
                            current_stk = int(s_item.get('stok', 0))
                            nama_brg_db = s_item.get('nama_barang', 'Barang')
                            if total_minta > current_stk:
                                stok_cukup = False
                                st.error(f"❌ Stok tidak cukup untuk barang: **{nama_brg_db}** (Sisa stok: {current_stk}, Total diminta di keranjang: {total_minta})")
                            break
                    if not stok_cukup:
                        break
                
                if stok_cukup:
                    st.session_state['is_submitting'] = True
                    waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                    berhasil = True
                    err_terakhir = ""
                    
                    for item in st.session_state['keranjang_belanja']:
                        j_trx = item['Jenis']
                        qty = item['Qty']
                        r_stok = item['Row_Stok']
                        ket_item = item['Nama'] if item['Nama'] else ""
                        
                        if j_trx == "Penjualan Barang" and r_stok:
                            for s_item in data_s:
                                if s_item.get('id') == r_stok:
                                    current_stk = int(s_item.get('stok', 0))
                                    stok_baru = max(0, current_stk - qty)
                                    db_update("stok", r_stok, {"stok": stok_baru})
                                    s_item['stok'] = stok_baru
                                    break
                        
                        for _ in range(qty):
                            nom_trx = item['Nominal Satuan']
                            adm_trx = item['Admin/Profit Satuan']
                            tot_trx = nom_trx + adm_trx if j_trx == "Transaksi Lainnya" else (nom_trx - adm_trx if j_trx == "Tarik Tunai" else nom_trx)
                            prof_trx = adm_trx
                            
                            sukses_ins, err_ins = db_insert("transaksi", {
                                "waktu": waktu, "jenis": j_trx, "nominal": int(nom_trx),
                                "admin": int(adm_trx), "total": int(tot_trx), "profit": int(prof_trx),
                                "keterangan": ket_item
                            })
                            if not sukses_ins: 
                                berhasil = False
                                err_terakhir = err_ins
                    
                    st.session_state['is_submitting'] = False
                    if berhasil:
                        st.session_state['keranjang_belanja'] = []
                        st.cache_data.clear()
                        st.success("Semua keranjang selesai diproses!")
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error(f"Sebagian data gagal disimpan! Error: {err_terakhir}")
                
            if c_k2.button("🗑️ KOSONGKAN", use_container_width=True):
                st.session_state['keranjang_belanja'] = []
                st.rerun()

    else: 
        st.info("💡 **Tips AI Scan Multifungsi:** Upload foto catatan voucher fisik (misal `AXIS:13+13`) atau screenshot mutasi bank/e-wallet. AI akan otomatis mendeteksi jenis gambar dan memprosesnya ke draf!")
        sumber_gambar = st.file_uploader("Upload Foto Catatan / Mutasi:", type=["jpg", "jpeg", "png"], disabled=modal_belum_diisi)

        if sumber_gambar and st.button("🔍 AI SCAN MULTIFUNGSI", use_container_width=True, type="primary", disabled=modal_belum_diisi):
            try:
                st.session_state['gambar_scan_terakhir'] = sumber_gambar

                img_temp = Image.open(sumber_gambar)
                buffered = io.BytesIO()
                img_temp.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                # --- ANIMASI PEMINDAI GOOGLE LENS ---
                lens_placeholder = st.empty()
                lens_placeholder.markdown(f"""
                    <style>
                    @keyframes scanGlow {{
                        0% {{ top: 0%; opacity: 0.8; }}
                        50% {{ opacity: 1; }}
                        100% {{ top: 95%; opacity: 0.8; }}
                    }}
                    .lens-container {{
                        position: relative;
                        width: 100%;
                        max-height: 250px;
                        overflow: hidden;
                        border-radius: 10px;
                        border: 2px solid #14B8A6;
                        background-color: #000;
                        text-align: center;
                        margin-bottom: 10px;
                    }}
                    .lens-img {{
                        width: 100%;
                        height: auto;
                        opacity: 0.6;
                        display: block;
                        margin: 0 auto;
                    }}
                    .scan-beam {{
                        position: absolute;
                        left: 0;
                        right: 0;
                        height: 4px;
                        background-color: #14B8A6;
                        box-shadow: 0 0 15px #14B8A6, 0 0 30px #14B8A6;
                        animation: scanGlow 1.5s infinite alternate ease-in-out;
                    }}
                    </style>
                    <div class="lens-container">
                        <div class="scan-beam"></div>
                        <img src="data:image/jpeg;base64,{img_str}" class="lens-img">
                    </div>
                    <p style="text-align:center; color:#14B8A6; font-weight:bold; font-size:15px;">🔍 AI Sedang Memindai Gambar...</p>
                """, unsafe_allow_html=True)

                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                
                prompt_text = """
                Analisis gambar yang diunggah ini. Gambar bisa berupa dua jenis:
                JENIS A (Catatan Voucher Fisik): Tulisan tangan berisi nama provider dan deretan angka harga jual dipisah tanda tambah (+) seperti 'AXIS:13+13+14'.
                JENIS B (Mutasi Bank / E-Wallet): Tangkapan layar daftar transaksi keuangan yang memiliki tanda minus (-) untuk uang keluar atau tanda plus (+) / tanpa tanda untuk uang masuk.
                
                Tugas Anda:
                - Jika JENIS A, ekstrak setiap item menjadi baris dengan format: VOUCHER [PROVIDER] [NOMINAL_ANGKA]
                - Jika JENIS B, ekstrak setiap baris transaksi yang terlihat. Jika suatu baris tidak memiliki nama atau keterangan teks, berikan keterangan default berupa waktu atau tulisan 'Mutasi' diikuti nominalnya dengan format: MUTASI [TANDA (+ atau -)] [KETERANGAN_ATAU_WAKTU] [NOMINAL_ANGKA]
                
                Contoh format balasan:
                VOUCHER AXIS 13000
                VOUCHER TSEL 10000
                MUTASI - NURYANIH 9067000
                MUTASI + QRIS TIZC 75000
                
                Jangan sertakan tanda kutip markdown (seperti ```), jangan berikan teks pengantar, langsung tulis daftar itemnya baris per baris saja.
                """
                
                res = client.models.generate_content(model='gemini-3.6-flash', contents=[img_temp, prompt_text])
                lens_placeholder.empty()

                raw_text = res.text.strip()
                raw_text = re.sub(r'```[a-zA-Z]*', '', raw_text)
                raw_text = raw_text.replace('```', '').strip()
                
                lines = raw_text.split('\n')
                processed_data = []
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    if line.startswith("VOUCHER"):
                        parts = line.split()
                        if len(parts) >= 3:
                            prov = parts[1]
                            try:
                                nom_str = parts[2].split(',')[0]
                                nom_val = int(re.sub(r'[^0-9]', '', nom_str))
                                if nom_val < 1000: nom_val = nom_val * 1000
                                
                                matched_nama = None
                                matched_row_id = None
                                matched_profit = 0
                                
                                for st_item in data_s:
                                    nm_stk = st_item.get('nama_barang', '').upper()
                                    hj_stk = int(st_item.get('harga_jual', 0))
                                    hm_stk = int(st_item.get('harga_modal', 0))
                                    if prov.upper() in nm_stk and hj_stk == nom_val:
                                        matched_nama = st_item.get('nama_barang')
                                        matched_row_id = st_item.get('id')
                                        matched_profit = hj_stk - hm_stk
                                        break
                                
                                if matched_row_id is not None:
                                    processed_data.append({
                                        'Tipe': 'Voucher',
                                        'Nama Barang': matched_nama,
                                        'Nominal (Rp)': nom_val,
                                        'Profit': matched_profit,
                                        'Row_Stok': matched_row_id,
                                        'Jenis Trx': 'Penjualan Barang'
                                    })
                            except: pass
                            
                    elif line.startswith("MUTASI"):
                        clean_line = line.replace("MUTASI", "").strip()
                        if clean_line.startswith("-"):
                            tanda = "-"
                            rest = clean_line[1:].strip()
                        elif clean_line.startswith("+"):
                            tanda = "+"
                            rest = clean_line[1:].strip()
                        else:
                            tanda = "+"
                            rest = clean_line
                            
                        parts = rest.rsplit(' ', 1)
                        if len(parts) >= 2:
                            keterangan = parts[0].strip()
                            try:
                                nom_str = parts[1].split(',')[0]
                                nom_val = int(re.sub(r'[^0-9]', '', nom_str))
                                if nom_val > 0:
                                    if tanda == "-":
                                        default_jenis = "Bank"
                                    else:
                                        default_jenis = "Tarik Tunai"
                                        
                                    processed_data.append({
                                        'Tipe': 'Mutasi',
                                        'Nama Barang': keterangan,
                                        'Nominal (Rp)': nom_val,
                                        'Profit': 0,
                                        'Row_Stok': None,
                                        'Jenis Trx': default_jenis
                                    })
                            except: pass

                st.session_state['draf_scan_smart'] = processed_data
                st.rerun()
            except Exception as e: st.error(f"Gagal scan gambar: {e}")

        if st.session_state.get('gambar_scan_terakhir') is not None:
            st.markdown("---")
            st.write("📷 **Foto Asli (Untuk Sinkronisasi):**")
            st.image(st.session_state['gambar_scan_terakhir'], use_container_width=True)

        if st.session_state['draf_scan_smart']:
            st.markdown("---")
            st.info(f"✨ Berhasil memindai {len(st.session_state['draf_scan_smart'])} item transaksi.")
            
            indices_to_delete = []
            for i, item in enumerate(st.session_state['draf_scan_smart']):
                st.markdown(f"**Item #{i+1} [{item['Tipe']}]**: {item['Nama Barang']} - Nominal: {f_uang(item['Nominal (Rp)'])}")
                
                if item['Tipe'] == 'Mutasi':
                    if item['Jenis Trx'] in ["Bank", "E-Wallet"]:
                        pilihan_opsi_mutasi = st.selectbox("Pilih Jenis Trx:", options=["Bank", "E-Wallet"], index=0 if item['Jenis Trx']=="Bank" else 1, key=f"sel_mut_jenis_{i}")
                        item['Jenis Trx'] = pilihan_opsi_mutasi
                    else:
                        st.markdown(f"<span style='color:#14B8A6; font-weight:bold;'>Jenis Trx: Tarik Tunai (Otomatis)</span>", unsafe_allow_html=True)
                    
                    est_profit = hitung_admin(item['Nominal (Rp)'], item['Jenis Trx'])
                    st.markdown(f"<span style='color:#2ca02c; font-size:14px;'>Estimasi Admin/Profit: {f_uang(est_profit)}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:#14B8A6; font-weight:bold;'>Jenis Trx: Penjualan Barang (Untung: {f_uang(item['Profit'])})</span>", unsafe_allow_html=True)
                
                if st.button("❌ Hapus Item Ini", key=f"del_ocr_item_{i}"):
                    indices_to_delete.append(i)
                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
            
            if indices_to_delete:
                st.session_state['draf_scan_smart'] = [item for idx, item in enumerate(st.session_state['draf_scan_smart']) if idx not in indices_to_delete]
                st.rerun()

            st.markdown('<div class="floating-container">', unsafe_allow_html=True)
            if st.button("💾 SIMPAN SEMUA TRANSAKSI DRAF", type="primary", use_container_width=True, disabled=st.session_state['is_submitting'] or modal_belum_diisi):
                # Validasi kumulatif stok pada draf OCR
                permintaan_barang = {}
                for item in st.session_state['draf_scan_smart']:
                    if item['Tipe'] == 'Voucher' and item['Row_Stok']:
                        r_id = item['Row_Stok']
                        permintaan_barang[r_id] = permintaan_barang.get(r_id, 0) + 1

                stok_draf_cukup = True
                for r_id, total_minta in permintaan_barang.items():
                    for s_item in data_s:
                        if s_item.get('id') == r_id:
                            current_stk = int(s_item.get('stok', 0))
                            nama_brg_db = s_item.get('nama_barang', 'Barang')
                            if total_minta > current_stk:
                                stok_draf_cukup = False
                                st.error(f"❌ Gagal! Stok **'{nama_brg_db}'** tidak cukup. Sisa stok: {current_stk}, diminta pada draf: {total_minta} item.")
                            break
                
                if stok_draf_cukup:
                    st.session_state['is_submitting'] = True
                    waktu = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                    berhasil = True
                    err_terakhir = ""
                    
                    for item in st.session_state['draf_scan_smart']:
                        nom = item['Nominal (Rp)']
                        j_trx = item['Jenis Trx']
                        r_id = item['Row_Stok']
                        
                        if item['Tipe'] == 'Voucher':
                            prof = item['Profit']
                            tot = nom
                            admin_val = prof
                            ket_item = item['Nama Barang']
                            if r_id:
                                for s_item in data_s:
                                    if s_item.get('id') == r_id:
                                        current_stk = int(s_item.get('stok', 0))
                                        db_update("stok", r_id, {"stok": max(0, current_stk - 1)})
                                        s_item['stok'] = max(0, current_stk - 1)
                                        break
                        else:
                            admin_val = hitung_admin(nom, j_trx)
                            if j_trx == "Tarik Tunai":
                                tot = nom - admin_val
                            else:
                                tot = nom + admin_val
                            prof = admin_val
                            ket_item = item['Nama Barang']

                        sukses_ins, err_ins = db_insert("transaksi", {
                            "waktu": waktu, "jenis": j_trx, "nominal": int(nom),
                            "admin": int(admin_val), "total": int(tot), "profit": int(prof),
                            "keterangan": ket_item
                        })
                        if not sukses_ins: 
                            berhasil = False
                            err_terakhir = err_ins
                    
                    st.session_state['is_submitting'] = False
                    if berhasil:
                        st.session_state['draf_scan_smart'] = []
                        st.session_state['gambar_scan_terakhir'] = None
                        st.cache_data.clear()
                        st.success("Semua transaksi berhasil disimpan & dihitung otomatis!")
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error(f"Sebagian data gagal disimpan! Error: {err_terakhir}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            if sumber_gambar:
                st.warning("⚠️ Gambar terbaca, namun tidak ada item valid yang berhasil diekstrak. Pastikan foto catatan atau mutasi Anda terlihat jelas.")

# --- TAB 2: RIWAYAT ---
with tab2:
    if data_t and len(data_t) > 0:
        df_t = pd.DataFrame(data_t)
        df_t['Waktu_Parsed'] = pd.to_datetime(df_t['waktu'], errors='coerce')
        
        daftar_pilihan_sesi = ["Sesi Aktif Saat Ini"]
        rentang_sesi_dict = {}
        
        if data_sesi and len(data_sesi) > 0:
            sorted_sesi = sorted(data_sesi, key=lambda x: x.get('waktu_tutup_sesi', ''))
            for i, s_item in enumerate(sorted_sesi):
                w_tutup_str = s_item.get('waktu_tutup_sesi')
                w_mulai_str = sorted_sesi[i-1].get('waktu_tutup_sesi') if i > 0 else str(data_k[0].get('waktu', "2020-01-01 00:00:00") if len(data_k) > 0 else "2020-01-01 00:00:00")
                
                label_s = f"Sesi Selesai: {w_tutup_str}"
                daftar_pilihan_sesi.append(label_s)
                rentang_sesi_dict[label_s] = (pd.to_datetime(w_mulai_str), pd.to_datetime(w_tutup_str))

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            pilih_filter_jenis = st.selectbox("Jenis:", options=["Semua"] + df_t['jenis'].unique().tolist(), key="filter_j_trx")
        with col_f2:
            pilih_filter_sesi = st.selectbox("Filter Sesi:", options=daftar_pilihan_sesi, key="filter_s_trx")
        
        df_t_filtered = df_t.copy()
        
        if pilih_filter_sesi == "Sesi Aktif Saat Ini":
            t_mulai_aktif = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
            df_t_filtered = df_t_filtered[df_t_filtered['Waktu_Parsed'] >= t_mulai_aktif]
        else:
            w_mulai, w_tutup = rentang_sesi_dict[pilih_filter_sesi]
            df_t_filtered = df_t_filtered[(df_t_filtered['Waktu_Parsed'] >= w_mulai) & (df_t_filtered['Waktu_Parsed'] <= w_tutup)]

        if pilih_filter_jenis != "Semua": 
            df_t_filtered = df_t_filtered[df_t_filtered['jenis'] == pilih_filter_jenis]
        
        # --- URUTKAN RIWAYAT: TERBARU DI ATAS, PALING LAMA DI BAWAH ---
        df_t_filtered = df_t_filtered.sort_values(by='Waktu_Parsed', ascending=False).reset_index(drop=True)
        
        profit_filter_val = pd.to_numeric(df_t_filtered['profit'], errors='coerce').fillna(0).sum() if len(df_t_filtered) > 0 else 0
        omzet_filter_val = pd.to_numeric(df_t_filtered['total'], errors='coerce').fillna(0).sum() if len(df_t_filtered) > 0 else 0

        st.markdown(f"""
            <div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border:1px solid #14B8A6; text-align:center; margin:15px 0 10px 0;">
                <span style="color:#14B8A6; font-size:14px; font-weight:bold;">📦 TOTAL OMZET (SESI & FILTER AKTIF):</span><br>
                <span style="color:#fff; font-size:20px; font-weight:bold;">{f_uang(omzet_filter_val)}</span>
            </div>
            <div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border:1px solid #2ca02c; text-align:center; margin-bottom:15px;">
                <span style="color:#2ca02c; font-size:14px; font-weight:bold;">🔥 TOTAL PROFIT (SESI & FILTER AKTIF):</span><br>
                <span style="color:#fff; font-size:20px; font-weight:bold;">{f_uang(profit_filter_val)}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        
        if not df_t_filtered.empty:
            list_trx_terpilih = []
            for index, row in df_t_filtered.iterrows():
                r_id = row['id']
                waktu_trx = row['waktu']
                jns_trx = row['jenis']
                nom_trx = f_uang(row['nominal'])
                tot_trx = f_uang(row['total'])
                
                profit_trx = f_uang(row.get('profit', 0))
                ket_val = row.get('keterangan', '')
                ket_tampil = f" - <b>{ket_val}</b>" if pd.notna(ket_val) and str(ket_val).strip() else ""
                
                c_chk, c_info = st.columns([1, 9])
                with c_chk:
                    is_checked = st.checkbox("Pilih", key=f"chk_trx_{r_id}", label_visibility="collapsed")
                    if is_checked: list_trx_terpilih.append(row)
                with c_info:
                    st.markdown(f"**{waktu_trx}** | <span style='color:#14B8A6;'>{jns_trx}</span><span style='color:#ccc;'>{ket_tampil}</span><br>Nominal: {nom_trx} | Total: {tot_trx} | <b style='color:#2ca02c;'>Profit: {profit_trx}</b>", unsafe_allow_html=True)
                
                if st.button("✏️ Edit Transaksi", key=f"edit_trx_{r_id}", use_container_width=True):
                    st.session_state[f"mode_edit_trx_{r_id}"] = True

                if st.session_state.get(f"mode_edit_trx_{r_id}", False):
                    with st.form(key=f"form_edit_trx_{r_id}"):
                        st.write(f"Edit Transaksi ID: {r_id}")
                        e_waktu = st.text_input("Waktu", value=row['waktu'])
                        e_jenis = st.text_input("Jenis", value=row['jenis'])
                        e_ket = st.text_input("Keterangan/Produk", value=row.get('keterangan', ''))
                        e_nom = st.number_input("Nominal", value=int(row['nominal']), step=1000)
                        e_adm = st.number_input("Admin", value=int(row['admin']), step=1000)
                        e_tot = st.number_input("Total", value=int(row['total']), step=1000)
                        e_prof = st.number_input("Profit", value=int(row['profit']), step=1000)
                        
                        if st.form_submit_button("Simpan Perubahan"):
                            sukses_up, _ = db_update("transaksi", r_id, {
                                "waktu": e_waktu, "jenis": e_jenis, "nominal": int(e_nom),
                                "admin": int(e_adm), "total": int(e_tot), "profit": int(e_prof),
                                "keterangan": e_ket
                            })
                            if sukses_up:
                                st.session_state[f"mode_edit_trx_{r_id}"] = False
                                st.cache_data.clear()
                                st.success("Perubahan disimpan!")
                                time.sleep(0.5)
                                st.rerun()
                            else: st.error("Gagal update!")

                st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)

            if list_trx_terpilih:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"🗑️ HAPUS {len(list_trx_terpilih)} TRANSAKSI TERPILIH", type="primary", use_container_width=True):
                    fresh_stok_res = supabase.table("stok").select("*").eq("cabang", cabang_aktif).execute()
                    fresh_stok = fresh_stok_res.data if fresh_stok_res and fresh_stok_res.data else []

                    for sel_row in list_trx_terpilih:
                        trx_id = sel_row['id']
                        trx_jenis = sel_row['jenis']
                        trx_nominal = int(sel_row['nominal'])
                        
                        if trx_jenis == "Penjualan Barang" and fresh_stok:
                            trx_ket = str(sel_row.get('keterangan', '')).strip().upper()
                            for stok_item in fresh_stok:
                                nama_stok_db = str(stok_item.get('nama_barang', '')).strip().upper()
                                if (trx_ket and trx_ket == nama_stok_db) or (not trx_ket and int(stok_item.get('harga_jual', 0)) == trx_nominal):
                                    s_id = stok_item.get('id')
                                    s_stok_lama = int(stok_item.get('stok', 0))
                                    db_update("stok", s_id, {"stok": s_stok_lama + 1})
                                    stok_item['stok'] = s_stok_lama + 1
                                    break
                        
                        db_delete("transaksi", trx_id)
                        
                    st.cache_data.clear()
                    st.success("Transaksi terpilih berhasil dihapus & stok dikembalikan!")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("Tidak ada transaksi pada sesi ini.")
    else:
        st.info("Belum ada riwayat transaksi.")

# --- TAB 3: DASHBOARD ---
with tab3:
    if st.button("🔴 AKHIRI SESI SEKARANG", type="primary", use_container_width=True):
        st.session_state['konfirmasi_tutup_sesi'] = True

    if st.session_state.get('konfirmasi_tutup_sesi', False):
        st.warning("⚠️ Apakah Anda yakin ingin mengakhiri sesi ini? Semua kalkulasi kas dan profit sesi ini akan ditutup dan diarsipkan.")
        col_ks1, col_ks2 = st.columns(2)
        if col_ks1.button("✅ Ya, Tutup Sesi", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
            st.session_state['is_submitting'] = True
            tot_cash_s = 0
            tot_digi_s = 0
            prof_s = 0
            
            if data_t and len(data_t) > 0:
                df_t_all = pd.DataFrame(data_t)
                df_t_all['Waktu_Parsed'] = pd.to_datetime(df_t_all['waktu'], errors='coerce')
                t_mulai = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
                df_sesi_ini = df_t_all[df_t_all['Waktu_Parsed'] >= t_mulai].copy()
                
                if not df_sesi_ini.empty:
                    prof_s = pd.to_numeric(df_sesi_ini['profit'], errors='coerce').fillna(0).sum()
                    for idx, r in df_sesi_ini.iterrows():
                        jns = r['jenis']
                        nom = float(r['nominal'])
                        tot = float(r['total'])
                        if jns in ["Penjualan Barang", "Transaksi Lainnya"]: tot_cash_s += tot
                        elif jns == "Tarik Tunai":
                            tot_cash_s -= tot
                            tot_digi_s += nom
                        else: 
                            tot_digi_s -= nom
                            tot_cash_s += tot

            akhir_c = int(st.session_state['modal_cash'] + tot_cash_s + st.session_state['penyesuaian_cash'])
            akhir_d = int(st.session_state['modal_digi'] + tot_digi_s + st.session_state['penyesuaian_digi'])
            waktu_tutup = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")

            try:
                b_sesi, _ = db_insert("riwayat_sesi", {
                    "waktu_tutup_sesi": waktu_tutup, "modal_cash": int(st.session_state['modal_cash']),
                    "modal_digital": int(st.session_state['modal_digi']), "total_cash_akhir": akhir_c,
                    "total_digital_akhir": akhir_d, "total_profit": int(prof_s)
                })

                st.session_state['is_submitting'] = False
                if b_sesi:
                    st.session_state['modal_cash'] = 0
                    st.session_state['modal_digi'] = 0
                    st.session_state['penyesuaian_cash'] = 0
                    st.session_state['penyesuaian_digi'] = 0
                    st.session_state['waktu_mulai_sesi'] = waktu_tutup
                    st.session_state['reset_session_flag'] = True
                    st.session_state['konfirmasi_tutup_sesi'] = False
                    
                    st.cache_data.clear()
                    st.success("🎉 Sesi Berhasil Diakhiri & Diarsipkan!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Gagal menyimpan data ke Supabase.")
            except Exception as e:
                st.session_state['is_submitting'] = False
                st.error(f"Detail Error: {e}")

        if col_ks2.button("❌ Batal", use_container_width=True):
            st.session_state['konfirmasi_tutup_sesi'] = False
            st.rerun()

    st.markdown("---")

    with st.expander("💰 Setel Modal Awal Sesi Ini", expanded=True if (st.session_state['modal_cash'] == 0 and st.session_state['modal_digi'] == 0) else False):
        input_cash_baru = st.number_input("Setel Cash di Laci (Rp):", value=st.session_state['modal_cash'], step=50000)
        if input_cash_baru > 0: st.caption(f"👀 Terbaca: **{f_uang(input_cash_baru)}**")
            
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            input_ewallet_baru = st.number_input("Setel Saldo E-Wallet (Rp):", value=0, step=50000)
            if input_ewallet_baru > 0: st.caption(f"👀 {f_uang(input_ewallet_baru)}")
        with col_m2:
            input_bank_baru = st.number_input("Setel Saldo Bank (Rp):", value=int(st.session_state['modal_digi']), step=50000)
            if input_bank_baru > 0: st.caption(f"👀 {f_uang(input_bank_baru)}")

        total_digi_gabungan = input_ewallet_baru + input_bank_baru
        if total_digi_gabungan > 0:
            st.markdown(f"<p style='color:#14B8A6; font-size:16px; font-weight:bold;'>Total Saldo Digital Gabungan: {f_uang(total_digi_gabungan)}</p>", unsafe_allow_html=True)
            
        if st.button("💾 Simpan Modal Sesi", type="primary", use_container_width=True):
            waktu_sekarang = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            try:
                supabase.table("kas").insert({
                    "waktu": waktu_sekarang,
                    "cash": int(input_cash_baru),
                    "digital": int(total_digi_gabungan),
                    "cabang": cabang_aktif
                }).execute()

                st.session_state['modal_cash'] = int(input_cash_baru)
                st.session_state['modal_digi'] = int(total_digi_gabungan)
                st.session_state['waktu_mulai_sesi'] = waktu_sekarang
                st.cache_data.clear()
                st.success("Modal awal sesi berhasil disimpan permanen ke database!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan modal ke database: {e}")

    st.markdown("---")

    tot_transaksi_cash = 0
    tot_transaksi_digi = 0
    
    if data_t and len(data_t) > 0:
        df_trx = pd.DataFrame(data_t)
        if 'waktu' in df_trx.columns:
            df_trx['Waktu_Parsed'] = pd.to_datetime(df_trx['waktu'], errors='coerce')
            t_mulai_sesi = pd.to_datetime(st.session_state['waktu_mulai_sesi'])
            
            df_sesi = df_trx[df_trx['Waktu_Parsed'] >= t_mulai_sesi].copy()
            if not df_sesi.empty:
                for idx, r in df_sesi.iterrows():
                    jns = r['jenis']
                    nom = float(r['nominal'])
                    tot = float(r['total'])
                    if jns in ["Penjualan Barang", "Transaksi Lainnya"]: tot_transaksi_cash += tot
                    elif jns == "Tarik Tunai":
                        tot_transaksi_cash -= tot
                        tot_transaksi_digi += nom
                    else: 
                        tot_transaksi_digi -= nom
                        tot_transaksi_cash += tot

    total_cash_sistem = st.session_state['modal_cash'] + tot_transaksi_cash
    total_digi_sistem = st.session_state['modal_digi'] + tot_transaksi_digi

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💵 Cash di Laci (Sesi Aktif)</h4>
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

    st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#14B8A6;">💳 Saldo Digital Gabungan (Sesi Aktif)</h4>
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
    st.markdown("### 📝 Catatan / Catatan Penting Sesi Ini")
    
    with st.form("form_tambah_catatan_baru"):
        input_catatan_baru = st.text_area("Tulis catatan atau pengingat baru di sini:", placeholder="Tulis catatan harian, hutang pelanggan, dll...")
        if st.form_submit_button("💾 Tambah Catatan Baru"):
            if input_catatan_baru.strip():
                waktu_buat = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                db_insert("catatan_harian", {
                    "waktu": waktu_buat,
                    "cabang": cabang_aktif,
                    "isi_catatan": input_catatan_baru.strip()
                })
                st.success("Catatan berhasil ditambahkan!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Catatan tidak boleh kosong!")

    st.markdown("#### 📋 Daftar Catatan Aktif")
    if data_catatan and len(data_catatan) > 0:
        for cat_row in data_catatan:
            c_id = cat_row.get('id')
            c_waktu = cat_row.get('waktu', '')
            c_isi = cat_row.get('isi_catatan', '')
            
            c_box1, c_box2 = st.columns([8, 2])
            with c_box1:
                st.markdown(f"**🕒 {c_waktu}**<br>{c_isi}", unsafe_allow_html=True)
            with c_box2:
                if st.button("🗑️ Hapus", key=f"del_cat_{c_id}", use_container_width=True):
                    db_delete("catatan_harian", c_id)
                    st.cache_data.clear()
                    st.success("Catatan dihapus!")
                    time.sleep(0.5)
                    st.rerun()
            st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)
    else:
        st.info("Belum ada catatan tersimpan.")

    st.markdown("---")
    st.markdown("### 📜 Riwayat Sesi Kerja Sebelumnya")
    
    if data_sesi and len(data_sesi) > 0:
        df_riwayat_sesi = pd.DataFrame(data_sesi)
        df_sesi_display = df_riwayat_sesi[['waktu_tutup_sesi', 'modal_cash', 'modal_digital', 'total_cash_akhir', 'total_digital_akhir', 'total_profit']].copy()
        for col in ['modal_cash', 'modal_digital', 'total_cash_akhir', 'total_digital_akhir', 'total_profit']:
            if col in df_sesi_display.columns:
                df_sesi_display[col] = df_sesi_display[col].apply(lambda x: f_uang(x))
        
        st.dataframe(df_sesi_display, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🗑️ Hapus Sesi Tertentu Dari Database"):
            list_pilihan_sesi_hapus = []
            map_id_sesi = {}
            map_obj_sesi = {}
            
            sorted_sesi_list = sorted(data_sesi, key=lambda x: x.get('waktu_tutup_sesi', ''))
            
            for idx_s, s_row in enumerate(sorted_sesi_list):
                s_id = s_row.get('id')
                label_sesi_h = f"ID: {s_id} | Waktu Tutup: {s_row.get('waktu_tutup_sesi')} (Profit: {f_uang(s_row.get('total_profit', 0))})"
                list_pilihan_sesi_hapus.append(label_sesi_h)
                map_id_sesi[label_sesi_h] = s_id
                
                w_tutup = s_row.get('waktu_tutup_sesi')
                w_mulai = sorted_sesi_list[idx_s-1].get('waktu_tutup_sesi') if idx_s > 0 else (data_k[0].get('waktu', "2020-01-01 00:00:00") if len(data_k) > 0 else "2020-01-01 00:00:00")
                map_obj_sesi[s_id] = (w_mulai, w_tutup)

            pilihan_target_hapus = st.selectbox("Pilih Sesi Yang Ingin Dihapus:", options=list_pilihan_sesi_hapus)
            konfirm_h_sesi_db = st.checkbox("Saya yakin ingin menghapus data riwayat sesi ini beserta SEMUA transaksi didalamnya secara permanen", key="chk_del_sesi_db")
            
            if konfirm_h_sesi_db:
                if st.button("❌ Hapus Sesi & Transaksinya", type="primary"):
                    target_id = map_id_sesi[pilihan_target_hapus]
                    w_mulai_target, w_tutup_target = map_obj_sesi[target_id]
                    
                    if data_t:
                        for t_row in data_t:
                            t_waktu = t_row.get('waktu', '')
                            if w_mulai_target <= t_waktu <= w_tutup_target:
                                db_delete("transaksi", t_row['id'])

                    if db_delete("riwayat_sesi", target_id):
                        if 'waktu_mulai_sesi' in st.session_state: del st.session_state['waktu_mulai_sesi']
                        st.cache_data.clear()
                        st.success("Sesi dan seluruh transaksi di dalamnya berhasil dihapus permanen!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Gagal menghapus baris sesi!")

    else: st.info("Belum ada riwayat sesi yang ditutup.")

# --- TAB 4: STOK BARANG ---
with tab4:
    existing_categories = []
    if data_s and len(data_s) > 0:
        for r in data_s:
            kat_val = r.get('kategori')
            if kat_val and kat_val.strip():
                clean_kat = kat_val.strip()
                if clean_kat not in existing_categories:
                    existing_categories.append(clean_kat)
    
    if not existing_categories:
        existing_categories = ["Umum"]
    else:
        existing_categories = sorted(existing_categories)

    with st.expander("➕ Tambah Barang Baru"):
        nama_barang = st.text_input("Nama Barang:")
        opsi_kategori = existing_categories + ["+ Buat Kategori Baru..."]
        pilih_kat_tambah = st.selectbox("Pilih Kategori Barang:", options=opsi_kategori, key="sel_kat_tambah")
        
        if pilih_kat_tambah == "+ Buat Kategori Baru...":
            kategori_barang = st.text_input("Ketik Nama Kategori Baru:", value="", key="input_kat_baru_tambah")
        else: kategori_barang = pilih_kat_tambah

        stok_awal = st.number_input("Jumlah Stok:", min_value=0, step=1, value=1)
        harga_modal = st.number_input("Harga Modal (Rp):", min_value=0, step=1000)
        if harga_modal > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_modal)}**")
            
        harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=1000)
        if harga_jual > 0: st.caption(f"👀 Terbaca: **{f_uang(harga_jual)}**")
            
        kode_cepat_brg = st.text_input("Kode Cepat / Barcode (Contoh: AXIS99, VCG1):")
        
        if st.button("💾 Simpan Barang", type="primary", use_container_width=True, disabled=st.session_state['is_submitting']):
            final_kat = kategori_barang.strip() if kategori_barang.strip() else "Umum"
            
            kode_sudah_pakai = False
            if kode_cepat_brg.strip() and data_s:
                for item_cek in data_s:
                    if str(item_cek.get('kode_cepat', '')).upper() == kode_cepat_brg.strip().upper():
                        kode_sudah_pakai = True
                        break

            if kode_sudah_pakai:
                st.error(f"❌ Gagal menyimpan! Kode cepat / barcode '**{kode_cepat_brg.strip()}**' sudah digunakan oleh barang lain.")
            elif not nama_barang:
                st.error("Nama barang tidak boleh kosong!")
            else:
                st.session_state['is_submitting'] = True
                sukses_s, err_s = db_insert("stok", {
                    "barcode": kode_cepat_brg.strip(), "nama_barang": nama_barang, "stok": int(stok_awal),
                    "harga_modal": int(harga_modal), "harga_jual": int(harga_jual),
                    "kode_cepat": kode_cepat_brg.strip(), "kategori": final_kat
                })
                st.cache_data.clear()
                st.session_state['is_submitting'] = False
                if sukses_s:
                    st.success("Tersimpan!")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error(f"Gagal simpan barang! Error: {err_s}")

    st.markdown("---")

    total_modal_fisik_semua = 0
    if data_s and len(data_s) > 0:
        for item_s in data_s:
            s_qty = int(item_s.get('stok', 0))
            s_mod = int(item_s.get('harga_modal', 0))
            total_modal_fisik_semua += (s_qty * s_mod)

    st.markdown(f"""
        <div style="text-align: center; margin: 10px 0 20px 0;">
            <span style="color: #aaa; font-size: 14px; font-weight: bold;">TOTAL MODAL SEMUA BARANG FISIK:</span><br>
            <span style="color: #14B8A6; font-size: 32px; font-weight: bold;">{f_uang(total_modal_fisik_semua)}</span>
        </div>
    """, unsafe_allow_html=True)

    if data_s and len(data_s) > 0:
        df_s = pd.DataFrame(data_s)

        list_kategori_filter = ["Semua Kategori"] + sorted(df_s['kategori'].dropna().unique().tolist())
        pilih_filter_kat = st.selectbox("Filter Berdasarkan Kategori:", options=list_kategori_filter)
        
        df_s_filtered = df_s.copy()
        if pilih_filter_kat != "Semua Kategori": 
            df_s_filtered = df_s_filtered[df_s_filtered['kategori'] == pilih_filter_kat]

        pilihan_urut = st.selectbox(
            "Urutkan Berdasarkan:", 
            options=[
                "Nama Barang (A-Z)", 
                "Stok: Sedikit ke Terbanyak (0 -> Max)", 
                "Stok: Terbanyak ke Sedikit (Max -> 0)"
            ]
        )

        if pilihan_urut == "Stok: Sedikit ke Terbanyak (0 -> Max)":
            df_s_filtered = df_s_filtered.sort_values(by='stok', ascending=True).reset_index(drop=True)
        elif pilihan_urut == "Stok: Terbanyak ke Sedikit (Max -> 0)":
            df_s_filtered = df_s_filtered.sort_values(by='stok', ascending=False).reset_index(drop=True)
        else:
            df_s_filtered = df_s_filtered.sort_values(by='nama_barang', key=lambda col: col.str.lower()).reset_index(drop=True)

        st.markdown("---")
        
        list_stok_terpilih = []
        for index, row in df_s_filtered.iterrows():
            r_id = row['id']
            nm = row.get('nama_barang', '')
            stk = int(row.get('stok', 0))
            mod_val = int(row.get('harga_modal', 0))
            jul_val = int(row.get('harga_jual', 0))
            kat = row.get('kategori', 'Umum')
            
            total_modal_item = stk * mod_val
            
            c_chk, c_info = st.columns([1, 9])
            with c_chk:
                is_checked_stok = st.checkbox("Pilih Stok", key=f"chk_stok_{r_id}", label_visibility="collapsed")
                if is_checked_stok: list_stok_terpilih.append(r_id)
            with c_info:
                if stk == 0:
                    st.markdown(f"<span style='color:#FF4B4B; font-weight:bold; font-size:16px;'>⚠️ [STOK KOSONG] {nm}</span> | <span style='color:#14B8A6;'>[{kat}]</span> (Stok: 0)<br>Modal: {f_uang(mod_val)} | Jual: {f_uang(jul_val)}<br><b style='color:#14B8A6;'>TOTAL MODAL: {f_uang(total_modal_item)}</b>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{nm}** | <span style='color:#14B8A6;'>[{kat}]</span> (Stok: {stk})<br>Modal: {f_uang(mod_val)} | Jual: {f_uang(jul_val)}<br><b style='color:#14B8A6;'>TOTAL MODAL: {f_uang(total_modal_item)}</b>", unsafe_allow_html=True)
            
            if st.button("✏️ Edit Data Barang", key=f"edit_stok_btn_{r_id}", use_container_width=True): 
                st.session_state[f"mode_edit_stk_{r_id}"] = True

            if st.session_state.get(f"mode_edit_stk_{r_id}", False):
                with st.form(key=f"form_edit_stok_{r_id}"):
                    st.write(f"Edit Data: {nm}")
                    es_nm = st.text_input("Nama Barang", value=nm)
                    es_stk = st.number_input("Stok", min_value=0, value=int(stk), step=1)
                    es_mod = st.number_input("Harga Modal", value=int(mod_val), step=1000)
                    es_jul = st.number_input("Harga Jual", value=int(jul_val), step=1000)
                    es_kod = st.text_input("Kode Cepat / Barcode", value=row.get('kode_cepat', ''))
                    
                    opsi_kat_edit = existing_categories + ["+ Buat Kategori Baru..."]
                    default_kat_idx = opsi_kat_edit.index(kat) if kat in opsi_kat_edit else 0
                    es_pilih_kat = st.selectbox("Kategori Barang", options=opsi_kat_edit, index=default_kat_idx)
                    if es_pilih_kat == "+ Buat Kategori Baru...":
                        es_kat = st.text_input("Ketik Kategori Baru", value="", key=f"input_kat_baru_edit_{r_id}")
                    else: es_kat = es_pilih_kat
                    
                    if st.form_submit_button("Simpan Perubahan Stok"):
                        final_es_kat = es_kat.strip() if es_kat.strip() else kat
                        
                        kode_edit_sudah_pakai = False
                        if es_kod.strip() and data_s:
                            for item_cek in data_s:
                                if item_cek.get('id') != r_id and str(item_cek.get('kode_cepat', '')).upper() == es_kod.strip().upper():
                                    kode_edit_sudah_pakai = True
                                    break

                        if kode_edit_sudah_pakai:
                            st.error(f"❌ Gagal menyimpan! Kode cepat / barcode '**{es_kod.strip()}**' sudah digunakan oleh barang lain.")
                        else:
                            sukses_up_stk, _ = db_update("stok", r_id, {
                                "barcode": es_kod.strip(), "nama_barang": es_nm, "stok": int(es_stk),
                                "harga_modal": int(es_mod), "harga_jual": int(es_jul),
                                "kode_cepat": es_kod.strip(), "kategori": final_es_kat
                            })
                            if sukses_up_stk:
                                st.session_state[f"mode_edit_stk_{r_id}"] = False
                                st.cache_data.clear()
                                st.success("Stok diperbarui!")
                                time.sleep(0.5)
                                st.rerun()
                            else: st.error("Gagal perbarui stok!")

            st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)

        if list_stok_terpilih:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🗑️ HAPUS {len(list_stok_terpilih)} BARANG TERPILIH", type="primary", use_container_width=True):
                for r_id in list_stok_terpilih:
                    db_delete("stok", r_id)
                st.cache_data.clear()
                st.success("Barang terpilih berhasil dihapus!")
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("Belum ada data stok.")

# --- TAB 5: GAJI KARYAWAN ---
with tab5:
    data_gaji_aktif = [g for g in data_gaji if g.get('status', 'Aktif') == 'Aktif']
    data_gaji_arsip = [g for g in data_gaji if g.get('status', 'Aktif') == 'Arsip']

    with st.form("form_input_gaji_tabel"):
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            input_k1 = st.number_input("Gaji / Upah Karyawan 1 (Rp):", min_value=0, step=10000, value=0)
            if input_k1 > 0: st.caption(f"👀 {f_uang(input_k1)}")
        with col_k2:
            input_k2 = st.number_input("Gaji / Upah Karyawan 2 (Rp):", min_value=0, step=10000, value=0)
            if input_k2 > 0: st.caption(f"👀 {f_uang(input_k2)}")

        input_bonus = st.number_input("Bonus / Tambahan Lainnya (Rp):", min_value=0, step=10000, value=0)
        if input_bonus > 0: st.caption(f"👀 {f_uang(input_bonus)}")

        total_sementara = input_k1 + input_k2 + input_bonus
        if total_sementara > 0:
            st.markdown(f"<p style='color:#14B8A6; font-size:16px; font-weight:bold;'>Total Input Ini: {f_uang(total_sementara)}</p>", unsafe_allow_html=True)

        if st.form_submit_button("💾 Tambah Baris Gaji Baru"):
            if total_sementara > 0:
                waktu_str = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
                db_insert("gaji_karyawan", {
                    "waktu": waktu_str,
                    "karyawan_1": int(input_k1),
                    "karyawan_2": int(input_k2),
                    "bonus": int(input_bonus),
                    "total_gaji": int(total_sementara),
                    "status": "Aktif"
                })
                st.cache_data.clear()
                st.success("Baris gaji baru berhasil ditambahkan!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Silakan isi minimal salah satu nominal gaji atau bonus!")

    st.markdown("---")
    st.markdown("### 📋 Tabel Gaji Berjalan (Aktif)")

    if data_gaji_aktif:
        for idx_g, g_row in enumerate(data_gaji_aktif):
            g_id = g_row['id']
            w_str = g_row.get('waktu', '')
            val_k1 = int(g_row.get('karyawan_1', 0))
            val_k2 = int(g_row.get('karyawan_2', 0))
            val_bon = int(g_row.get('bonus', 0))
            val_tot = int(g_row.get('total_gaji', 0))

            c_info, c_btn = st.columns([8, 2])
            with c_info:
                st.markdown(f"**🕒 {w_str}**<br>Karyawan 1: {f_uang(val_k1)} | Karyawan 2: {f_uang(val_k2)} | Bonus: {f_uang(val_bon)}<br><b>Total Baris: {f_uang(val_tot)}</b>", unsafe_allow_html=True)
            with c_btn:
                if st.button("✏️ Edit", key=f"edit_gaji_btn_{g_id}", use_container_width=True):
                    st.session_state[f"mode_edit_gaji_{g_id}"] = True

            if st.session_state.get(f"mode_edit_gaji_{g_id}", False):
                with st.form(key=f"form_edit_gaji_row_{g_id}CURR"):
                    st.write(f"Edit Baris Gaji ID: {g_id}")
                    ed_k1 = st.number_input("Karyawan 1 (Rp)", value=val_k1, step=10000)
                    ed_k2 = st.number_input("Karyawan 2 (Rp)", value=val_k2, step=10000)
                    ed_bon = st.number_input("Bonus (Rp)", value=val_bon, step=10000)
                    
                    if st.form_submit_button("Simpan Perubahan"):
                        new_tot_row = ed_k1 + ed_k2 + ed_bon
                        db_update("gaji_karyawan", g_id, {
                            "karyawan_1": int(ed_k1),
                            "karyawan_2": int(ed_k2),
                            "bonus": int(ed_bon),
                            "total_gaji": int(new_tot_row)
                        })
                        st.session_state[f"mode_edit_gaji_{g_id}"] = False
                        st.cache_data.clear()
                        st.success("Perubahan gaji disimpan!")
                        time.sleep(0.5)
                        st.rerun()

            st.markdown("<hr style='margin:5px 0; border-color:#333;'>", unsafe_allow_html=True)

        grand_total_aktif = sum(int(r.get('total_gaji', 0)) for r in data_gaji_aktif)
        
        st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <span style="color: #aaa; font-size: 14px;">TOTAL KESELURUHAN GAJI AKTIF:</span><br>
                <span style="color: #14B8A6; font-size: 32px; font-weight: bold;">{f_uang(grand_total_aktif)}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📦 ARSIPKAN & RESET GAJI", type="primary", use_container_width=True):
            waktu_arsip = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
            for row_a in data_gaji_aktif:
                db_update("gaji_karyawan", row_a['id'], {
                    "status": "Arsip",
                    "waktu": waktu_arsip
                })
            st.cache_data.clear()
            st.success("✅ Periode gaji berhasil diarsipkan dan tabel di-reset bersih!")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Belum ada data input gaji. Silakan tambahkan baris melalui form di atas.")

    st.markdown("---")
    st.markdown("### 📜 Riwayat Arsip Gaji Sebelumnya")
    if data_gaji_arsip:
        df_ARS = pd.DataFrame(data_gaji_arsip)
        df_arsip_disp = df_ARS[['waktu', 'karyawan_1', 'karyawan_2', 'bonus', 'total_gaji']].copy()
        for col in ['karyawan_1', 'karyawan_2', 'bonus', 'total_gaji']:
            df_arsip_disp[col] = df_arsip_disp[col].apply(lambda x: f_uang(x))
        df_arsip_disp.columns = ['Waktu Diarsipkan', 'Karyawan 1', 'Karyawan 2', 'Bonus', 'Total Gaji']
        st.dataframe(df_arsip_disp, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada riwayat arsip gaji.")
