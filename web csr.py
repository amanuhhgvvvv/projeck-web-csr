import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time
from google.oauth2.service_account import Credentials

# --- SESSION STATE ---
if 'lokasi_manual_input' not in st.session_state:
    st.session_state['lokasi_manual_input'] = ""
if 'lokasi_select_state' not in st.session_state:
    st.session_state['lokasi_select_state'] = "Tarjun"
# Inisialisasi tambahan untuk memastikan key jenis bantuan ada
if 'jenis_bantuan_key' not in st.session_state:
    st.session_state['jenis_bantuan_key'] = "Uang" 

# --- KONFIGURASI ---
WORKSHEET_NAME = "CSR"

# --- GOOGLE SHEETS CLIENT ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        # Menggunakan st.secrets untuk kredensial
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

        credentials = Credentials.from_service_account_info(
            creds,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(credentials)
        return client

    except Exception as e:
        st.error(f"Gagal menginisialisasi koneksi Google Sheets. Error: {e}")
        st.stop()

# --- LOAD DATA ---
@st.cache_data(ttl="10m")
def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(st.secrets["SHEET_ID"])
        worksheet = sheet.worksheet(WORKSHEET_NAME)

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Membersihkan kolom yang tidak diperlukan
        kolom_hapus = [col for col in df.columns if 'Unnamed:' in col or col == '']
        if kolom_hapus:
            df = df.drop(columns=kolom_hapus)

        # Mengubah kolom Tanggal ke format date
        if "Tanggal" in df.columns:
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce').dt.date

        return df

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Error: {e}")
        return pd.DataFrame()

# --- CSS Kustom untuk Gaya Tambahan (Opsional) ---
# Menggunakan Markdown dan HTML untuk tampilan yang lebih berwarna
st.markdown("""
<style>
    /* Mengganti warna primary button */
    div.stButton > button:first-child {
        background-color: #4CAF50; /* Hijau */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: 1px solid #4CAF50;
        transition: background-color 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #45a049;
        border: 1px solid #45a049;
    }
    
    /* Gaya untuk Subheader (Opsional) */
    h3 {
        color: #004d40; /* Hijau tua */
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 5px;
        margin-top: 15px;
    }
    
    /* Warna latar belakang untuk kolom input agar lebih menonjol */
    /* Ini hanya akan bekerja jika diletakkan di dalam container/kolom yang spesifik */
    .st-emotion-cache-1cypcdp { /* Ini adalah class yang mungkin berubah, gunakan dengan hati-hati */
        padding: 15px;
        border-radius: 10px;
        background-color: #f0f4f8; /* Abu-abu muda kebiruan */
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    
    /* Gaya untuk st.radio agar lebih menonjol */
    div[data-testid="stRadio"] label {
        background-color: #e8f5e9; /* Hijau sangat muda */
        padding: 5px 10px;
        border-radius: 5px;
        margin-right: 5px;
        border: 1px solid #c8e6c9;
    }
    
</style>
""", unsafe_allow_html=True)


# --- UI ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Sistem Pencatatan Bantuan **CSR itp p-12 tarjun** 📝")
st.markdown("---") # Penuh

col_input, col_view = st.columns([1, 1.5])

# --------------------------
# FORM INPUT
# --------------------------
# Definisikan jenis_bantuan_manual dan jenis_bantuan_final di global scope col_input
jenis_bantuan_manual = "" 
jenis_bantuan_final = ""

with col_input:
    # Menggunakan container untuk menerapkan warna latar belakang kolom input (Gaya kustom di atas)
    with st.container():
        st.subheader("🟢 Input Data Baru") # Menambahkan ikon

        with st.form("form_csr", clear_on_submit=False):
            st.markdown("---") # Peningkat visual

            tanggal = st.date_input("🗓️ **Tanggal Kegiatan**", datetime.now().date())

            opsi_pilar = [
                "Pendidikan", "Kesehatan", "Ekonomi", "Sos Bud Ag",
                "Keamanan", "Sustainable Development Project", "Donation Cash", "Donation Goods",
                "Public Relation Business", "Entertainment Business"
            ]
            pilar = st.selectbox("🎯 **Pilih Pilar**", opsi_pilar)
            
            # REVISI 2.1: Tambahkan KEY pada st.radio agar nilainya tersedia di Session State
            # Menggunakan Markdown untuk judul agar lebih bold
            st.markdown("⭐ **Jenis Bantuan**") 
            jenis_bantuan = st.radio(
                "Pilihan Bantuan", 
                ["💰 Uang", "🧱 Semen / Material", "📦 Lainnya"], 
                horizontal=True,
                key="jenis_bantuan_key",
                label_visibility="collapsed" # Menyembunyikan label bawaan st.radio
            )

            # REVISI 2.2: Logika input manual DIKEMBALIKAN KE DALAM FORM
            # Namun, karena st.radio (dengan key) memicu rerun, ini seharusnya bekerja
            if st.session_state.jenis_bantuan_key == "📦 Lainnya":
                jenis_bantuan_manual = st.text_input(
                    "Ketik Jenis Bantuan Lainnya", 
                    placeholder="Contoh: Beras, Kursi, Peralatan Kebersihan"
                )
            
            # Menentukan nilai final untuk Jenis Bantuan (berdasarkan session state)
            # Menghapus emoji untuk nilai final yang disimpan agar data tetap bersih di Sheets
            if st.session_state.jenis_bantuan_key.split(" ")[-1] == "Lainnya":
                jenis_bantuan_final = jenis_bantuan_manual  
            else:
                # Mengambil teks tanpa emoji
                jenis_bantuan_final = st.session_state.jenis_bantuan_key.split(" ")[-1]


            uraian = st.text_area("✍️ **Uraian Kegiatan**", placeholder="Jelaskan...")

            c1, c2 = st.columns([2, 1])
            with c1:
                # REVISI 1: Menerima Bilangan Desimal (Float)
                jumlah = st.number_input(
                    "💵 **Jumlah yang diterima / Nilai**", 
                    min_value=0.0, 
                    value=0.0,      
                    step=0.01,      
                    format="%.2f"       
                )
            with c2:
                satuan = st.selectbox("📏 **Satuan**", ["-", "Ton", "Sak", "Paket", "Unit", "liter", "buah", "juta"])

            opsi_lokasi = [
                "Tarjun", "Langadai", "Serongga", "Tegal Rejo",
                "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang",
                "Sidomulyo", "Dusun Simpang 3 Quary", "Lainnya (Input Manual)"
            ]

            lokasi_select = st.selectbox("📍 **Pilih Desa/Lokasi**", opsi_lokasi, key="lokasi_select_state")

            lokasi_manual = ""
            if lokasi_select == "Lainnya (Input Manual)":
                lokasi_manual = st.text_input("Ketik Nama Lokasi Baru", key="lokasi_manual_input")

            # Mengubah submit button menjadi warna yang lebih menarik menggunakan st.form_submit_button(..., type="primary")
            submitted = st.form_submit_button("✅ **Simpan Data**", type="primary")

    
    if submitted:
        lokasi_final = lokasi_manual if lokasi_select == "Lainnya (Input Manual)" else lokasi_select

        # Nilai jenis_bantuan_final sudah dihitung di atas form, kita hanya perlu memvalidasinya

        # Validasi Input
        if not uraian:
            st.error("⚠️ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠️ Lokasi manual belum diisi.")
        # REVISI 2.4: Validasi untuk input manual yang baru
        elif st.session_state.jenis_bantuan_key.split(" ")[-1] == "Lainnya" and not jenis_bantuan_final:
            st.error("⚠️ Jenis Bantuan Lainnya belum diisi.")
        elif jumlah <= 0:
            st.error("⚠️ Jumlah harus lebih dari nol.")
        else:
            try:
                with st.spinner("⏳ Menyimpan data..."):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)
                    
                    # Urutan kolom yang dikirim ke Google Sheets
                    new_row = [
                        tanggal.strftime("%Y-%m-%d"),
                        pilar,
                        jenis_bantuan_final,  # Menggunakan nilai final yang sudah dihitung (tanpa emoji)
                        uraian,
                        jumlah,             # Nilai ini sekarang bertipe float/desimal
                        satuan,
                        lokasi_final,
                    ]

                    worksheet.append_row(new_row)

                # Menggunakan st.success dengan ikon
                st.success(f"🎉 Data untuk lokasi **{lokasi_final}** berhasil disimpan!")

                # Clear cache dan refresh halaman untuk menampilkan data baru
                load_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Gagal menyimpan data ke Google Sheets. Error: {e}")

# --------------------------
# VIEW DATA (Tidak diubah fungsinya, hanya perlu ditampilkan)
# --------------------------

with col_view:
    st.subheader("📊 Data Kegiatan Tersimpan")
    st.markdown("---") # Peningkat visual

    df = load_data()

    if not df.empty:
        # Menampilkan data dalam tabel Streamlit yang lebih interaktif
        st.dataframe(df, use_container_width=True)

        # Statistik Sederhana
        st.markdown("#### Ringkasan Data")
        total_data = len(df)
        total_lokasi = df['Lokasi'].nunique()
        
        col_stats_1, col_stats_2 = st.columns(2)
        
        with col_stats_1:
            st.info(f"🔢 **Total Data:** {total_data} Baris")
        
        with col_stats_2:
            st.info(f"🏘️ **Jumlah Lokasi:** {total_lokasi} Desa/Lokasi")

    else:
        st.warning("Data belum tersedia atau gagal dimuat.")
