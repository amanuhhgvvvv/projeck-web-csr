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

        if "Tanggal" in df.columns:
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce').dt.date

        return df

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Error: {e}")
        return pd.DataFrame()


# --- UI ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Bantuan CSR")
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

        uraian = st.text_area("Uraian Kegiatan", placeholder="Jelaskan detail kegiatan...")

        c1, c2 = st.columns([2, 1])
        with c1:
            jumlah = st.number_input("Jumlah yang diterima / Nilai", min_value=0, step=1)
        with c2:
            satuan = st.selectbox("Satuan", ["0", "Rupiah", "Ton", "Sak", "Paket", "Unit"])

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

        if not uraian:
            st.error("⚠️ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠️ Lokasi manual belum diisi.")
        elif jumlah <= 0:
            st.error("⚠️ Jumlah harus lebih dari nol.")
        else:
            try:
                with st.spinner("⏳ Menyimpan data..."):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)

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

                st.success(f"✅ Data untuk lokasi **{lokasi_final}** berhasil disimpan!")

                st.session_state["lokasi_select_state"] = "Tarjun"
                load_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Error: {e}")

# --------------------------
# VIEW DATA
# --------------------------
with col_view:
    st.subheader("📊 Monitoring Data")

    df = load_data()

    if not df.empty:

        if "Jumlah" in df.columns and "Satuan" in df.columns:
            def format_jumlah(row):
                if row["Satuan"] == "Rupiah":
                    try:
                        return f"Rp {int(row['Jumlah']):,}".replace(",", ".")
                    except:
                        return f"{row['Jumlah']} Rupiah"
                else:
                    return f"{row['Jumlah']} {row['Satuan']}"

            df["Jumlah Manfaat"] = df.apply(format_jumlah, axis=1)
        else:
            df["Jumlah Manfaat"] = ""

        filter_pilar = st.multiselect("Filter berdasarkan Pilar:", df["Pilar"].unique())
        df_filtered = df[df["Pilar"].isin(filter_pilar)] if filter_pilar else df

        kolom_urut = [
            "Tanggal", "Pilar", "Jenis Bantuan", "Uraian Kegiatan",
            "Jumlah Manfaat", "Lokasi" ]

        kolom_ada = [k for k in kolom_urut if k in df_filtered.columns]

        st.dataframe(df_filtered[kolom_ada], use_container_width=True, hide_index=True)

        st.info(f"Total Transaksi: {len(df_filtered)} | Lokasi Terjangkau: {df_filtered['Lokasi'].nunique()}")

    else:
        st.info("Belum ada data tersimpan.")

# --- CSS ---
st.markdown("""
<style>
    div[data-testid="stForm"] {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    .stTextInput > label, .stSelectbox > label {
        font-size: 105%;
        font-weight: bold;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)













