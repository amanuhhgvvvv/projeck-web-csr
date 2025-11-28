import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time 

# --- INI HARUS ADA DI AWAL SKRIP ---
if 'lokasi_manual_input' not in st.session_state:
    st.session_state['lokasi_manual_input'] = ""
if 'lokasi_select_state' not in st.session_state:
    st.session_state['lokasi_select_state'] = "Tarjun" # Nilai default awal

# --- KONFIGURASI KONEKSI GOOGLE SHEETS ---

# Nama worksheet (tab) yang digunakan di Google Sheet Anda
WORKSHEET_NAME = "Sheet1" 

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Menginisialisasi koneksi ke Google Sheets menggunakan st.secrets."""
    try:
        # Menggunakan st.secrets.gcp_service_account (disimpan sebagai TOML)
        creds = st.secrets["gcp_service_account"]
        client = gspread.service_account_from_dict(creds)
        return client
    except Exception as e:
        st.error(f"Gagal menginisialisasi koneksi Google Sheets. Pastikan Secrets sudah benar dan Service Account sudah diaktifkan. Error: {e}")
        st.stop()

@st.cache_data(ttl="10m")
def load_data():
    """Memuat semua data dari Google Sheet ke dalam DataFrame Pandas."""
    client = get_gspread_client()
    try:
        # Menggunakan ID Sheet dari st.secrets.gcp_sheet_key
        sheet_id = st.secrets["gcp_sheet_key"]
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(WORKSHEET_NAME) 
        
        # Ambil semua record sebagai list of dictionaries (baris pertama dianggap header)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Konversi Tanggal
        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce').dt.date

        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan ID Sheet dan izin Service Account sudah benar. Error: {e}")
        return pd.DataFrame()


# --- UI / TAMPILAN UTAMA ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Bantuan CSR")
st.markdown("---")

# Membagi layar menjadi 2 kolom: Kiri (Form Input), Kanan (Data View)
col_input, col_view = st.columns([1, 1.5])

with col_input:
    st.subheader("📝 Input Data Baru")
    
    # ----------------------------------------------------
    # LOGIKA FORM INPUT
    # ----------------------------------------------------
    with st.form("form_csr", clear_on_submit=False):
        # 1. Tanggal
        tanggal = st.date_input("Tanggal Kegiatan", datetime.now().date())
        
        # 2. Pilar
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
        
        # 5. Jumlah & Satuan
        c1, c2 = st.columns([2, 1])
        with c1:
            jumlah = st.number_input("Jumlah Penerima Manfaat / Nilai", min_value=0, step=1)
        with c2:
            satuan = st.selectbox("Satuan", ["Rupiah", "Ton", "Sak", "Paket", "Orang", "Unit"])
        
        # 6. Lokasi (Logika Cerdas)
        st.markdown("**Lokasi Penyerahan**")
        opsi_lokasi = [
            "Tarjun", "Langadai", "Serongga", "Tegal Rejo", 
            "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang", 
            "Sidomulyo", "Dusun Simpang 3 Quary", "Lainnya (Input Manual)"
        ]
        
        # Pilihan lokasi diikat ke session state
        lokasi_select = st.selectbox(
            "Pilih Desa/Lokasi", 
            opsi_lokasi,
            key='lokasi_select_state' 
        )
        
        # Conditional Input untuk Lokasi Manual
        lokasi_manual = ""
        if lokasi_select == "Lainnya (Input Manual)":
            # Input manual diikat ke session state
            lokasi_manual = st.text_input(
                "Ketik Nama Desa/Lokasi Baru", 
                placeholder="Masukkan nama lokasi...",
                key='lokasi_manual_input' 
            )
        
        # Tombol Submit
        submitted = st.form_submit_button("💾 Simpan Data")

    if submitted:
        # Validasi Logika Lokasi
        lokasi_final = st.session_state['lokasi_manual_input'] if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        if not uraian:
            st.error("⚠️ Uraian kegiatan tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠️ Anda memilih 'Lainnya', harap ketik nama lokasi.")
        elif jumlah <= 0:
            st.error("⚠️ Jumlah Penerima Manfaat / Nilai harus lebih dari nol.")
        else:
            # ----------------------------------------------------
            # LOGIKA PROSES SIMPAN BARU (MENGGUNAKAN GOOGLE SHEETS)
            # ----------------------------------------------------
            try:
                with st.spinner('⏳ Menyimpan data ke Google Sheets...'):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["gcp_sheet_key"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)
                    
                    # Data baru sebagai list
                    new_row = [
                        tanggal.strftime("%Y-%m-%d"), 
                        pilar, 
                        jenis_bantuan, 
                        uraian, 
                        jumlah, 
                        satuan, 
                        lokasi_final, 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Input Waktu
                    ]
                    
                    # Kirim data ke baris baru di Google Sheets
                    worksheet.append_row(new_row)
                    
                # Success message dan clear cache
                st.success(f"✅ Data untuk lokasi **{lokasi_final}** berhasil disimpan ke Google Sheets!")

                # --- PERUBAHAN UTAMA UNTUK MEMPERTAHANKAN INPUT MANUAL ---
                # HANYA reset lokasi selectbox ke default
                st.session_state['lokasi_select_state'] = "Tarjun" 
                # NILAI st.session_state['lokasi_manual_input'] TIDAK DIHAPUS, sehingga nilainya tetap
                
                load_data.clear() # Clear cache agar data Monitoring diperbarui
                time.sleep(1)
                st.rerun() # Refresh aplikasi
                
            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Pastikan Service Account memiliki izin Editor. Error: {e}")

with col_view:
    st.subheader("📊 Monitoring Data Real-time")
    
    # ----------------------------------------------------
    # LOGIKA LOAD DATA BARU (MENGGUNAKAN GOOGLE SHEETS)
    # ----------------------------------------------------
    df = load_data()
    
    if not df.empty:
        
        # Logika Gabungan Kolom untuk Tampilan dengan format Rupiah
        if 'Jumlah' in df.columns and 'Satuan' in df.columns:
            def format_jumlah(row):
                if row['Satuan'] == 'Rupiah':
                    try:
                        # Format angka besar dengan pemisah ribuan (menggunakan titik)
                        return f"Rp {int(row['Jumlah']):,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")
                    except:
                        # Fallback jika konversi gagal
                        return f"{row['Jumlah']} {row['Satuan']}"
                else:
                    return f"{row['Jumlah']} {row['Satuan']}"
            
            df['Jumlah Manfaat'] = df.apply(format_jumlah, axis=1) 
        else:
            st.warning("Kolom 'Jumlah' atau 'Satuan' tidak ditemukan di Google Sheet.")
            df['Jumlah Manfaat'] = ""
            
        # Fitur Filter Sederhana
        filter_pilar = st.multiselect("Filter berdasarkan Pilar:", df["Pilar"].unique())
        if filter_pilar:
            df_filtered = df[df["Pilar"].isin(filter_pilar)]
        else:
            df_filtered = df
            
        # Tampilkan Tabel
        kolom_tampilan = [
            "Tanggal", 
            "Pilar", 
            "Jenis Bantuan", 
            "Uraian Kegiatan", 
            "Jumlah Manfaat", # Kolom Gabungan
            "Lokasi", 
            "Input Waktu"
        ]
        
        # Pastikan kolom ada sebelum ditampilkan
        kolom_ada = [col for col in kolom_tampilan if col in df_filtered.columns]
        
        st.dataframe(df_filtered[kolom_ada], use_container_width=True, hide_index=True)
        
        # Statistik Ringkas
        st.info(f"Total Transaksi: {len(df_filtered)} | Total Lokasi Terjangkau: {df_filtered['Lokasi'].nunique()}")
        
        )
    else:
        st.info("Belum ada data yang tersimpan. Silakan input data di kolom sebelah kiri.")

# --- CSS Customization (Tidak Berubah) ---
st.markdown("""
<style>
    .stTextInput > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    .stSelectbox > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    div[data-testid="stForm"] {background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd;}
</style>

""", unsafe_allow_html=True)
