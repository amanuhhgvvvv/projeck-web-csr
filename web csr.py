import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")

# File database sederhana (CSV)
FILE_DB = 'database_csr.csv'

# --- FUNGSI UTILITAS ---
def load_data():
    if os.path.exists(FILE_DB):
        return pd.read_csv(FILE_DB)
    return pd.DataFrame(columns=[
        "Tanggal", "Pilar", "Jenis Bantuan", "Uraian Kegiatan", 
        "Jumlah", "Satuan", "Lokasi", "Input Waktu"
    ])

def save_data(data_baru):
    df = load_data()
    # Menggabungkan data baru dengan data lama
    df = pd.concat([pd.DataFrame([data_baru]), df], ignore_index=True)
    df.to_csv(FILE_DB, index=False)
    return df

# --- UI / TAMPILAN UTAMA ---
st.title("🏭 Sistem Pencatatan Bantuan CSR Terpadu")
st.markdown("---")

# Membagi layar menjadi 2 kolom: Kiri (Form Input), Kanan (Data View)
col_input, col_view = st.columns([1, 1.5])

with col_input:
    st.subheader("📝 Input Data Baru")
    
    with st.form("form_csr", clear_on_submit=False):
        # 1. Tanggal (Disatukan)
        tanggal = st.date_input("Tanggal Kegiatan", datetime.now())
        
        # 2. Pilar (Dropdown)
        opsi_pilar = [
            "Pendidikan", "Kesehatan", "Ekonomi", "Sosial Budaya Agama", 
            "Keamanan", "SDP", "Donation Cash", "Donation Goods", 
            "Public Relation Business", "Entertainment Business"
        ]
        pilar = st.selectbox("Pilih Pilar CSR", opsi_pilar)
        
        # 3. Jenis Bantuan
        jenis_bantuan = st.radio("Jenis Bantuan", ["Uang (Cash)", "Semen / Material", "Lainnya"], horizontal=True)
        
        # 4. Uraian
        uraian = st.text_area("Uraian Kegiatan", placeholder="Jelaskan detail kegiatan di sini...")
        
        # 5. Jumlah & Satuan (Side by side)
        c1, c2 = st.columns([2, 1])
        with c1:
            jumlah = st.number_input("Jumlah Penerima Manfaat / Nilai", min_value=0, step=1)
        with c2:
            satuan = st.selectbox("Satuan", ["Rupiah", "Ton", "Sak", "Paket", "Orang", "Unit"])
        
        # 6. Lokasi (Logika Cerdas: Dropdown + Manual Input)
        # Kita tempatkan logika ini di luar form agar interaktif, 
        # tapi karena keterbatasan 'st.form', kita gunakan trik session state atau logika visual
        st.markdown("**Lokasi Penyerahan**")
        opsi_lokasi = [
            "Tarjun", "Langadai", "Serongga", "Tegal Rejo", 
            "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang", 
            "Sidomulyo", "Dusun Simpang 3 Quary", "Lainnya (Input Manual)"
        ]
        # Catatan: Widget ini harus dibaca nilainya saat submit
        lokasi_select = st.selectbox("Pilih Desa/Lokasi", opsi_lokasi)
        
        # Conditional Input untuk Lokasi Manual
        lokasi_manual = ""
        if lokasi_select == "Lainnya (Input Manual)":
            lokasi_manual = st.text_input("Ketik Nama Desa/Lokasi Baru", placeholder="Masukkan nama lokasi...")
        
        # Tombol Submit
        submitted = st.form_submit_button("💾 Simpan Data")

    if submitted:
        # Validasi Logika Lokasi
        lokasi_final = lokasi_manual if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        if not uraian:
            st.error("⚠️ Uraian kegiatan tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_manual:
            st.error("⚠️ Anda memilih 'Lainnya', harap ketik nama lokasi.")
        else:
            # Packing Data
            data_baru = {
                "Tanggal": tanggal,
                "Pilar": pilar,
                "Jenis Bantuan": jenis_bantuan,
                "Uraian Kegiatan": uraian,
                "Jumlah": jumlah,
                "Satuan": satuan,
                "Lokasi": lokasi_final,
                "Input Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Proses Simpan
            save_data(data_baru)
            st.success(f"✅ Data untuk lokasi **{lokasi_final}** berhasil disimpan!")

with col_view:
    st.subheader("📊 Monitoring Data Real-time")
    
    # Load Data Terbaru
    df = load_data()
    
    if not df.empty:
        # Fitur Filter Sederhana
        filter_pilar = st.multiselect("Filter berdasarkan Pilar:", df["Pilar"].unique())
        if filter_pilar:
            df = df[df["Pilar"].isin(filter_pilar)]
            
        # Tampilkan Tabel
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistik Ringkas (Fitur IQ Tinggi untuk Analisis Cepat)
        st.info(f"Total Transaksi: {len(df)} | Total Lokasi Terjangkau: {df['Lokasi'].nunique()}")
        
        # Tombol Download Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Laporan (CSV)",
            data=csv,
            file_name='laporan_csr.csv',
            mime='text/csv',
        )
    else:
        st.info("Belum ada data yang tersimpan. Silakan input data di kolom sebelah kiri.")

# --- CSS Customization (Opsional untuk mempercantik) ---
st.markdown("""
<style>
    .stTextInput > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    .stSelectbox > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    div[data-testid="stForm"] {background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)