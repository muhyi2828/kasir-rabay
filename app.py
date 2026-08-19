import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# ... (kode koneksi database dan fungsi hitung_admin tetap sama) ...

with tab2:
    st.subheader("📊 Laporan & Grafik")
    
    # 1. Menampilkan Tabel Rekap Harian
    if ws_k:
        data = ws_k.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
            
            # Filter Bulanan
            bulan_pilih = st.selectbox("Pilih Bulan Rekap:", df['Tanggal'].dt.strftime('%B %Y').unique())
            df_filter = df[df['Tanggal'].dt.strftime('%B %Y') == bulan_pilih]
            
            st.dataframe(df_filter, use_container_width=True)
            
            # 2. Grafik Penjualan (Tren Cash & Saldo Digital)
            st.write(f"### Grafik Tren Keuangan - {bulan_pilih}")
            fig = px.line(df_filter, x='Tanggal', y=['Modal_Cash', 'Modal_Digital'], 
                          labels={'value': 'Jumlah (Rp)', 'variable': 'Jenis Kas'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data rekap harian.")
    
    # 3. Tombol Rekap Harian (Tetap ada)
    if st.button("💾 Simpan Rekap Hari Ini ke Sheets"):
        if ws_k:
            tanggal = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d")
            ws_k.append_row([tanggal, st.session_state['modal_cash'], st.session_state['modal_digi']])
            st.success("Rekap tersimpan!")
