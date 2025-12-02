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

# --- UI ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Bantuan CSR itp p-12 tarjun")
st.markdown("---")

col_input, col_view = st.columns([1, 1.5])

# --------------------------
# FORM INPUT
# --------------------------
with col_input:
    st.subheader("📝 Input Data Baru")

    with st.form("form_csr", clear_on_submit=False):
        tanggal = st.date_input("Tanggal Kegiatan", datetime.now().date())

        opsi_pilar = [
            "Pendidikan", "Kesehatan", "Ekonomi", "Sosial Budaya Agama",
            "Keamanan", "SDP", "Donation Cash", "Donation Goods",
            "Public Relation Business", "Entertainment Business"
        ]
        pilar = st.selectbox("Pilih Pilar CSR", opsi_pilar)

        jenis_bantuan = st.radio("Jenis Bantuan", ["Uang", "Semen / Material", "Lainnya"], horizontal=True)

        # Logika input manual untuk Jenis Bantuan
        jenis_bantuan_manual = ""
        if jenis_bantuan == "Lainnya":
            jenis_bantuan_manual = st.text_input("Ketik Jenis Bantuan Lainnya", placeholder="Contoh: Beras, Kursi, Peralatan Kebersihan")

        # Menentukan nilai final untuk Jenis Bantuan
        jenis_bantuan_final = jenis_bantuan_manual if jenis_bantuan == "Lainnya" else jenis_bantuan


        uraian = st.text_area("Uraian Kegiatan", placeholder="Jelaskan detail kegiatan...")

        c1, c2 = st.columns([2, 1])
        with c1:
            # --- BAGIAN YANG DIREVISI UNTUK DESIMAL ---
            jumlah = st.number_input(
                "Jumlah yang diterima / Nilai", 
                min_value=0.0, 
                value=0.0,          # Mengatur nilai awal menjadi float
                step=0.01,          # Mengatur step menjadi desimal
                format="%.2f"       # Format tampilan dua desimal
            )
            # ------------------------------------------
        with c2:
            satuan = st.selectbox("Satuan", ["-", "Ton", "Sak", "Paket", "Unit", "liter", "buah", "juta"])

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

        # Validasi Input
        if not uraian:
            st.error("⚠️ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠️ Lokasi manual belum diisi.")
        elif jenis_bantuan == "Lainnya" and not jenis_bantuan_manual:
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
                        jenis_bantuan_final,  # Menggunakan nilai final
                        uraian,
                        jumlah,               # Nilai ini sekarang bertipe float/desimal
                        satuan,
                        lokasi_final,
                    ]

                    worksheet.append_row(new_row)

                st.success(f"✅ Data untuk lokasi **{lokasi_final}** berhasil disimpan!")

                # Clear cache dan refresh halaman untuk menampilkan data baru
                load_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Error: {e}")
        
# --------------------------
# DATA VIEW (VIEW HANYA JIKA ADA DATA)
# --------------------------
df_data = load_data()

with col_view:
    st.subheader("📊 Data Kegiatan CSR Terakhir")
    if not df_data.empty:
        st.dataframe(df_data, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data untuk ditampilkan.")
