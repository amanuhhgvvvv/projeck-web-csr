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
WORKSHEET_NAME = "CSR" 

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Menginisialisasi koneksi ke Google Sheets menggunakan struktur secret baru."""
    try:
        creds = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["client_x509_cert_url"]
        }

        client = gspread.service_account_from_dict(creds)
        return client

    except Exception as e:
        st.error(f"Gagal menginisialisasi koneksi Google Sheets. Error: {e}")
        st.stop()

@st.cache_data(ttl="10m")
def load_data():
    client = get_gspread_client()
    try:
        SHEET_ID = st.secrets["SHEET_ID"]
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce').dt.date

        return df

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Error: {e}")
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
            lokasi_manual = st.text_input(
                "Ketik Nama Desa/Lokasi Baru", 
                placeholder="Masukkan nama lokasi...",
                key='lokasi_manual_input' 
            )
        
        # Tombol Submit
        submitted = st.form_submit_button("💾 Simpan Data")

    if submitted:
        lokasi_final = st.session_state['lokasi_manual_input'] if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        if not uraian:
            st.error("⚠️ Uraian kegiatan tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠️ Anda memilih 'Lainnya', harap ketik nama lokasi.")
        elif jumlah <= 0:
            st.error("⚠️ Jumlah Penerima Manfaat / Nilai harus lebih dari nol.")
        else:
            try:
                with st.spinner('⏳ Menyimpan data ke Google Sheets...'):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
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
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    
                    worksheet.append_row(new_row)
                    
                st.success(f"✅ Data untuk lokasi **{lokasi_final}** berhasil disimpan ke Google Sheets!")

                st.session_state['lokasi_select_state'] = "Tarjun"
                
                load_data.clear()
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Error: {e}")

with col_view:
    st.subheader("📊 Monitoring data")
    
    df = load_data()
    
    if not df.empty:
        
        if 'Jumlah' in df.columns and 'Satuan' in df.columns:
            def format_jumlah(row):
                if row['Satuan'] == 'Rupiah':
                    try:
                        return f"Rp {int(row['Jumlah']):,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")
                    except:
                        return f"{row['Jumlah']} {row['Satuan']}"
                else:
                    return f"{row['Jumlah']} {row['Satuan']}"
            
            df['Jumlah Manfaat'] = df.apply(format_jumlah, axis=1) 
        else:
            st.warning("Kolom 'Jumlah' atau 'Satuan' tidak ditemukan di Google Sheet.")
            df['Jumlah Manfaat'] = ""
            
        filter_pilar = st.multiselect("Filter berdasarkan Pilar:", df["Pilar"].unique())
        if filter_pilar:
            df_filtered = df[df["Pilar"].isin(filter_pilar)]
        else:
            df_filtered = df
            
        kolom_tampilan = [
            "Tanggal", 
            "Pilar", 
            "Jenis Bantuan", 
            "Uraian Kegiatan", 
            "Jumlah Manfaat",
            "Lokasi", 
            "Input Waktu"
        ]
        
        kolom_ada = [col for col in df_filtered.columns if col in kolom_tampilan]
        
        st.dataframe(df_filtered[kolom_ada], use_container_width=True, hide_index=True)
        
        st.info(f"Total Transaksi: {len(df_filtered)} | Total Lokasi Terjangkau: {df_filtered['Lokasi'].nunique()}")
        
    else:
        st.info("Belum ada data yang tersimpan. Silakan input data di kolom sebelah kiri.")

# --- CSS Customization ---
st.markdown("""
<style>
    .stTextInput > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    .stSelectbox > label {font-size:105%; font-weight:bold; color:#2c3e50;}
    div[data-testid="stForm"] {background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)















