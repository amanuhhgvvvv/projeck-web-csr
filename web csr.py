import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time
from google.oauth2.service_account import Credentials

# --- KONFIGURASI TAMBAHAN ---
WORKSHEET_NAME = "CSR"
# Definisikan konversi: Misal, 1 Sak Semen = 0.05 Ton (50 kg)
KONVERSI_SAK_KE_TON = 0.05 

# --- SESSION STATE ---
if 'lokasi_manual_input' not in st.session_state:
    st.session_state['lokasi_manual_input'] = ""
if 'lokasi_select_state' not in st.session_state:
    st.session_state['lokasi_select_state'] = "Tarjun"
# Inisialisasi tambahan untuk memastikan key jenis bantuan ada
if 'jenis_bantuan_key' not in st.session_state:
    st.session_state['jenis_bantuan_key'] = "Uang" 

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

# --- UI ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Bantuan CSR itp p-12 tarjun")
st.markdown("---")

col_input, col_view = st.columns([1, 1.5])

# --------------------------
# FORM INPUT
# --------------------------
# Definisikan jenis_bantuan_manual dan jenis_bantuan_final di global scope col_input
jenis_bantuan_manual = "" 
jenis_bantuan_final = ""

with col_input:
    st.subheader("📝 Input Data Baru")

    with st.form("form_csr", clear_on_submit=False):
        tanggal = st.date_input("Tanggal Kegiatan", datetime.now().date())

        opsi_pilar = [
            "Pendidikan", "Kesehatan", "Ekonomi", "Sos Bud Ag",
            "Keamanan", "Sustainable Development Project", "Donation Cash", "Donation Goods",
            "Public Relation Business", "Entertainment Business"
        ]
        pilar = st.selectbox("Pilih Pilar", opsi_pilar)
        
        # REVISI 2.1: Tambahkan KEY pada st.radio agar nilainya tersedia di Session State
        jenis_bantuan = st.radio(
            "Jenis Bantuan", 
            ["Uang", "Semen / Material", "Lainnya"], 
            horizontal=True,
            key="jenis_bantuan_key" 
        )

        # REVISI 2.2: Logika input manual DIKEMBALIKAN KE DALAM FORM
        if st.session_state.jenis_bantuan_key == "Lainnya":
            jenis_bantuan_manual = st.text_input(
                "Ketik Jenis Bantuan Lainnya", 
                placeholder="Contoh: Beras, Kursi, Peralatan Kebersihan"
            )
        
        # Menentukan nilai final untuk Jenis Bantuan (berdasarkan session state)
        if st.session_state.jenis_bantuan_key == "Lainnya":
            jenis_bantuan_final = jenis_bantuan_manual 
        else:
            jenis_bantuan_final = st.session_state.jenis_bantuan_key


        uraian = st.text_area("Uraian Kegiatan", placeholder="Jelaskan...")

        c1, c2 = st.columns([2, 1])
        
        # Penyesuaian label berdasarkan pilihan Bantuan
        input_label = "Jumlah yang diterima / Nilai (Rp.)" if jenis_bantuan_final == "Uang" else "Jumlah yang diterima / Nilai"
        
        with c1:
            # REVISI 1: Menerima Bilangan Desimal (Float)
            jumlah = st.number_input(
                input_label, 
                min_value=0.0, 
                value=0.0,      
                step=0.01,      
                format="%.2f"       
            )
        
        # --- PERUBAHAN LOGIKA SATUAN ---
        # Opsi Satuan: HILANGKAN 'juta'
        opsi_satuan = ["-", "Ton", "Sak", "Paket", "Unit", "liter", "buah"]
        
        satuan = "-" # Nilai default
        
        if jenis_bantuan_final == "Uang":
            # Jika Uang, tampilkan Satuan sebagai 'Rupiah' (non-interaktif)
            with c2:
                 st.markdown(f"**Satuan**")
                 st.info("Rupiah (Otomatis)")
                 satuan = "Rupiah" # Nilai yang akan dikirim jika Uang
        elif jenis_bantuan_final == "Semen / Material":
            # Untuk Semen/Material, kita berikan opsi Ton/Sak dan konversi ke Ton saat disimpan
            with c2:
                satuan = st.selectbox("Satuan", ["Ton", "Sak"])
        else:
            # Untuk Lainnya/Default, gunakan opsi standar
            with c2:
                satuan = st.selectbox("Satuan", opsi_satuan)
        # --- AKHIR PERUBAHAN LOGIKA SATUAN ---

        opsi_lokasi = [
            "Tarjun", "Langadai", "Serongga", "Tegal Rejo",
            "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang",
            "Sidomulyo", "Dusun Simpang 3 Quary", "Lainnya (Input Manual)"
        ]

        lokasi_select = st.selectbox("Pilih Desa/Lokasi", opsi_lokasi, key="lokasi_select_state")

        lokasi_manual = ""
        if lokasi_select == "Lainnya (Input Manual)":
            lokasi_manual = st.text_input("Ketik Nama Lokasi Baru", key="lokasi_manual_input")

        submitted = st.form_submit_button("💾 Simpan Data")

    
    if submitted:
        lokasi_final = lokasi_manual if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        # --- LOGIKA KONVERSI DAN PENYESUAIAN NILAI FINAL ---
        jumlah_final = jumlah
        satuan_final = satuan
        
        if jenis_bantuan_final == "Uang":
            # 1. Konversi Rupiah: Satuan sudah diset di atas menjadi "Rupiah"
            satuan_final = "Rupiah"
        
        elif jenis_bantuan_final == "Semen / Material":
            # 2. Konversi Ton: Jika user memilih 'Sak', konversi ke Ton
            if satuan == "Sak":
                # Konversi jumlah dari Sak ke Ton (misal 1 Sak = 0.05 Ton)
                jumlah_final = jumlah * KONVERSI_SAK_KE_TON
                satuan_final = "Ton" # Nilai satuan di Sheets menjadi Ton
            else:
                satuan_final = satuan # Tetap Ton (jika user memilih Ton)
        # --- AKHIR LOGIKA KONVERSI ---

        # Nilai jenis_bantuan_final sudah dihitung di atas form, kita hanya perlu memvalidasinya

        # Validasi Input
        if not uraian:
            st.error("⚠ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠ Lokasi manual belum diisi.")
        # REVISI 2.4: Validasi untuk input manual yang baru
        elif st.session_state.jenis_bantuan_key == "Lainnya" and not jenis_bantuan_final:
            st.error("⚠ Jenis Bantuan Lainnya belum diisi.")
        elif jumlah <= 0:
            st.error("⚠ Jumlah harus lebih dari nol.")
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
                        jenis_bantuan_final,  # Menggunakan nilai final yang sudah dihitung
                        uraian,
                        jumlah_final,         # Menggunakan nilai yang sudah dikonversi
                        satuan_final,         # Menggunakan satuan yang sudah disesuaikan
                        lokasi_final,
                    ]

                    worksheet.append_row(new_row)

                st.success(f"✅ Data untuk lokasi *{lokasi_final}* berhasil disimpan!")

                # Clear cache dan refresh halaman untuk menampilkan data baru
                load_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Error: {e}")
