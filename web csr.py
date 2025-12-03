import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time
from google.oauth2.service_account import Credentials
import re 
# import locale # Dihapus karena format manual lebih stabil di Streamlit cloud

# --- KONFIGURASI TAMBAHAN ---
WORKSHEET_NAME = "CSR"
# Definisikan konversi: Misal, 1 Sak Semen = 0.05 Ton (50 kg)
KONVERSI_SAK_KE_TON = 0.05 

# Fungsi Helper untuk Pemformatan Angka ke String dengan Titik sebagai Pemisah Ribuan
def format_rupiah_manual(angka):
    """Memformat angka float/int menjadi string dengan titik sebagai pemisah ribuan."""
    try:
        if isinstance(angka, str):
            # Coba konversi string ke float jika diperlukan
            angka = float(angka)
        
        # Jika nilai adalah bilangan bulat (misal 100000.0), tampilkan tanpa desimal
        if angka.is_integer():
            angka_int = int(angka)
            # Menggunakan f-string formatting dengan koma sebagai pemisah ribuan, lalu ganti koma menjadi titik
            return f'{angka_int:,}'.replace(',', '.')
        else:
            # Jika ada desimal, format dengan dua angka desimal dan titik sebagai pemisah ribuan
            # Metode penggantian X diperlukan untuk lingkungan non-default locale
            return f'{angka:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return str(angka) # Kembalikan sebagai string biasa jika gagal diformat

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

        # --- PERUBAHAN UTAMA: SATU INPUT UNTUK NOMINAL & SATUAN ---
        
        # Contoh placeholder disesuaikan berdasarkan pilihan
        if jenis_bantuan_final == "Uang":
            placeholder_text = "Contoh: Rp1000000 atau 1.500.000"
        elif jenis_bantuan_final == "Semen / Material":
            placeholder_text = "Contoh: 50 Sak atau 2 Ton"
        else:
            placeholder_text = "Contoh: 5 Paket atau 10 Liter"
            
        # Mengganti c1, c2 dan st.number_input/st.text_input menjadi SATU st.text_input
        jumlah_dan_satuan_mentah = st.text_input(
            f"Jumlah yang diterima / Nilai (Masukkan nominal dan satuan)", 
            placeholder=placeholder_text,
            key="jumlah_satuan_mentah_input"
        )
        # --- AKHIR PERUBAHAN UTAMA ---

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
        
        # --- LOGIKA EKSTRAKSI NOMINAL DAN SATUAN DARI INPUT TUNGGAL ---
        
        # Membersihkan input dari pemisah ribuan dan simbol Rupiah yang mungkin
        input_clean = jumlah_dan_satuan_mentah.replace('.', '').replace('Rp', '').replace('rp', '').strip()
        
        # Regex untuk memisahkan angka di awal string dari teks/satuan di belakangnya.
        match = re.match(r"(\d+[\.\,]?\d*)\s*([a-zA-Z\/]+.*)?", input_clean)
        
        jumlah_final = 0.0
        satuan_final = ""
        validasi_ekstraksi = True

        if match:
            # Grup 1 adalah Angka (nominal)
            nominal_str = match.group(1).replace(',', '.') # Ganti koma desimal ke titik
            try:
                jumlah_final = float(nominal_str)
            except ValueError:
                validasi_ekstraksi = False
                
            # Grup 2 adalah Satuan (teks)
            satuan_final = match.group(2).strip() if match.group(2) else ""
            
            # Khusus untuk UANG: Jika satuan kosong, isi otomatis Rupiah
            if jenis_bantuan_final == "Uang" and not satuan_final:
                 satuan_final = "Rupiah"
            
            # Jika bukan uang dan satuan masih kosong, itu error
            if jenis_bantuan_final != "Uang" and not satuan_final:
                 validasi_ekstraksi = False
        else:
             validasi_ekstraksi = False


        # --- LOGIKA KONVERSI ---
        
        if jenis_bantuan_final == "Semen / Material":
            # Konversi ke Ton HANYA jika jenis bantuan adalah Semen / Material
            if satuan_final.lower() == "sak":
                jumlah_final = jumlah_final * KONVERSI_SAK_KE_TON
                satuan_final = "Ton" # Nilai satuan di Sheets menjadi Ton (Otomatis)
            elif satuan_final.lower() == "ton":
                satuan_final = "Ton" # Pastikan konsisten
            
        elif jenis_bantuan_final == "Uang":
            # JIKA JENIS BANTUAN ADALAH UANG, SELALU PAKSA SATUAN MENJADI RUPIAH
            satuan_final = "Rupiah"
        
        # --- AKHIR LOGIKA KONVERSI ---


        # Validasi Input (Diperbarui)
        if not uraian:
            st.error("⚠ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠ Lokasi manual belum diisi.")
        elif st.session_state.jenis_bantuan_key == "Lainnya" and not jenis_bantuan_final:
            st.error("⚠ Jenis Bantuan Lainnya belum diisi.")
        elif not validasi_ekstraksi:
            st.error("⚠ Format Jumlah/Nilai tidak valid. Harap masukkan angka diikuti satuan (contoh: 5 Ton).")
        elif jumlah_final <= 0:
            st.error("⚠ Jumlah harus lebih dari nol.")
        else:
            try:
                with st.spinner("⏳ Menyimpan data..."):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)
                    
                    # --- PERUBAHAN UTAMA: PEMFORMATAN STRING UNTUK OUTPUT ---
                    
                    jumlah_terformat_string = format_rupiah_manual(jumlah_final) 
                    # Memformat semua angka yang dikirim (uang atau material) ke string berformat titik.
                        
                    # Urutan kolom yang dikirim ke Google Sheets
                    new_row = [
                        tanggal.strftime("%Y-%m-%d"),
                        pilar,
                        jenis_bantuan_final,
                        uraian,
                        jumlah_terformat_string, # Menggunakan nilai STRING terformat dengan titik
                        satuan_final,           # Nilai satuan yang sudah diekstrak/dikonversi
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
