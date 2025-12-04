import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time
from google.oauth2.service_account import Credentials
import re

# --- KONFIGURASI TAMBAHAN ---
WORKSHEET_NAME = "CSR"
# Definisikan konversi: Misal, 1 Sak Semen = 0.05 Ton (50 kg)
KONVERSI_SAK_KE_TON = 0.05

# Fungsi Helper 1: Untuk UANG (Selalu tampil dua desimal)
def format_rupiah_uang(angka):
    """Memformat angka float/int menjadi string dengan titik sebagai pemisah ribuan dan SELALU dua desimal."""
    try:
        if isinstance(angka, str):
            angka = float(angka)
            
        # Selalu format ke string dengan 2 desimal
        formatted = f'{angka:,.2f}' 
        
        # Ganti koma (pemisah ribuan Python) menjadi titik (pemisah ribuan output)
        result = formatted.replace(',', '.') 
        
        # Output: "59.000.00"
        return result
        
    except Exception:
        return str(angka) 

# Fungsi Helper 2: Untuk MATERIAL/SATUAN (Tampilkan desimal hanya jika ada)
def format_satuan_material(angka):
    """Memformat angka float/int, menampilkan desimal HANYA jika nilainya bukan bilangan bulat."""
    try:
        if isinstance(angka, str):
            angka = float(angka)
        
        if angka.is_integer():
            angka_int = int(angka)
            # Format tanpa desimal (Contoh: 5.0 -> "5")
            return f'{angka_int:,}'.replace(',', '.')
        else:
            # Format dengan dua desimal jika ada desimal (Contoh: 5.5 -> "5.50")
            return f'{angka:,.2f}'.replace(',', '.') 

    except Exception:
        return str(angka)

# --- SESSION STATE ---
# Kita perlu menginisialisasi semua input yang akan kita reset secara manual di session_state
if 'lokasi_manual_input' not in st.session_state:
    st.session_state['lokasi_manual_input'] = ""
if 'lokasi_select_state' not in st.session_state:
    st.session_state['lokasi_select_state'] = "Tarjun"
if 'jenis_bantuan_key' not in st.session_state:
    st.session_state['jenis_bantuan_key'] = "Uang" 
if 'uraian_key' not in st.session_state:
    st.session_state['uraian_key'] = ""
if 'jumlah_satuan_mentah_input' not in st.session_state:
    st.session_state['jumlah_satuan_mentah_input'] = ""
if 'jenis_bantuan_manual_key' not in st.session_state:
    st.session_state['jenis_bantuan_manual_key'] = ""


# --- GOOGLE SHEETS CLIENT ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    # ... (Kode koneksi GSpread tetap sama)
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

# --- LOAD DATA (tetap sama) ---
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

# --- FUNGSI RESET INPUT MANUAL ---
def reset_form_inputs():
    """Mengatur ulang semua input form ke nilai default."""
    st.session_state['uraian_key'] = ""
    st.session_state['jumlah_satuan_mentah_input'] = ""
    st.session_state['lokasi_select_state'] = "Tarjun"
    st.session_state['lokasi_manual_input'] = ""
    st.session_state['jenis_bantuan_manual_key'] = ""
    st.session_state['jenis_bantuan_key'] = "Uang" # Reset radio button

# --- UI ---
st.set_page_config(page_title="Sistem Pencatatan CSR", layout="wide")
st.title("🏭 Bantuan CSR itp p-12 tarjun")
st.markdown("---")

col_input, col_view = st.columns([1, 1.5])

# --------------------------
# FORM INPUT
# --------------------------
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
        
        jenis_bantuan = st.radio(
            "Jenis Bantuan", 
            ["Uang", "Semen / Material", "Lainnya"], 
            horizontal=True,
            key="jenis_bantuan_key" 
        )

        if st.session_state.jenis_bantuan_key == "Lainnya":
            jenis_bantuan_manual = st.text_input(
                "Ketik Jenis Bantuan Lainnya", 
                placeholder="Contoh: Beras, Kursi, Peralatan Kebersihan",
                key="jenis_bantuan_manual_key",
                value=st.session_state['jenis_bantuan_manual_key']
            )
        
        if st.session_state.jenis_bantuan_key == "Lainnya":
            jenis_bantuan_final = jenis_bantuan_manual 
        else:
            jenis_bantuan_final = st.session_state.jenis_bantuan_key


        uraian = st.text_area(
            "Uraian Kegiatan", 
            placeholder="Jelaskan...",
            key="uraian_key",
            value=st.session_state['uraian_key']
        )

        # Contoh placeholder disesuaikan berdasarkan pilihan
        if jenis_bantuan_final == "Uang":
            placeholder_text = "Contoh: Rp50.987.00 atau Rp1.000.000" 
        elif jenis_bantuan_final == "Semen / Material":
            placeholder_text = "Contoh: 50 Sak atau 2 Ton"
        else:
            placeholder_text = "Contoh: 5 Paket atau 10 Liter"
            
        jumlah_dan_satuan_mentah = st.text_input(
            f"Jumlah / Nilai (Masukkan nominal dan satuan)", 
            placeholder=placeholder_text,
            key="jumlah_satuan_mentah_input",
            value=st.session_state['jumlah_satuan_mentah_input']
        )

        opsi_lokasi = [
            "Tarjun", "Langadai", "Serongga", "Tegal Rejo",
            "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang",
            "Sidomulyo", "Dusun Simpang 3 Quary", "Lainnya (Input Manual)"
        ]

        lokasi_select = st.selectbox(
            "Pilih Desa/Lokasi", 
            opsi_lokasi, 
            key="lokasi_select_state",
            index=opsi_lokasi.index(st.session_state['lokasi_select_state'])
        )

        lokasi_manual = ""
        if lokasi_select == "Lainnya (Input Manual)":
            lokasi_manual = st.text_input(
                "Ketik Nama Lokasi Baru", 
                key="lokasi_manual_input",
                value=st.session_state['lokasi_manual_input']
            )

        # Tombol Simpan Data
        submitted = st.form_submit_button("💾 Simpan Data")
        
        # --- WADAH KOSONG UNTUK PESAN NOTIFIKASI 2 DETIK ---
        notification_placeholder = st.empty()
        # --------------------------------------------------
    
    if submitted:
        lokasi_final = lokasi_manual if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        # --- LOGIKA EKSTRAKSI NOMINAL & SATUAN (tetap sama) ---
        jumlah_final = 0.0
        satuan_terekstrak = "" 
        validasi_ekstraksi = True

        prefix_rp = ""
        if jumlah_dan_satuan_mentah.strip().lower().startswith('rp'):
            prefix_rp = "Rp"
            input_untuk_match = re.sub(r'^[rR][pP]\s*', '', jumlah_dan_satuan_mentah.strip())
        else:
            input_untuk_match = jumlah_dan_satuan_mentah.strip()

        match = re.match(r"([\d\.\,]+)\s*(.*)?", input_untuk_match)
        
        if match:
            nominal_str_raw = match.group(1).strip()
            
            nominal_str_clean = nominal_str_raw
            
            last_separator = ''
            if nominal_str_raw.rfind(',') > nominal_str_raw.rfind('.'):
                last_separator = ','
            elif nominal_str_raw.rfind('.') > -1:
                last_separator = '.'
                
            if last_separator:
                parts = nominal_str_raw.rsplit(last_separator, 1)
                parts[0] = parts[0].replace('.', '').replace(',', '')
                nominal_str_clean = parts[0] + '.' + parts[1]
            
            nominal_str_clean = nominal_str_clean.replace(',', '.') 
            
            try:
                jumlah_final = float(nominal_str_clean)
            except ValueError:
                validasi_ekstraksi = False
            
            satuan_terekstrak = match.group(2).strip() if match.group(2) else ""
            
            if jenis_bantuan_final != "Uang" and not satuan_terekstrak:
                validasi_ekstraksi = False
        else:
            validasi_ekstraksi = False

        if jenis_bantuan_final == "Semen / Material":
            if satuan_terekstrak.lower() == "sak":
                jumlah_final = jumlah_final * KONVERSI_SAK_KE_TON
                satuan_terekstrak = "Ton"

        # Validasi Input (Diperbarui)
        if not uraian:
            st.error("⚠ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠ Lokasi manual belum diisi.")
        elif st.session_state.jenis_bantuan_key == "Lainnya" and not jenis_bantuan_final:
            st.error("⚠ Jenis Bantuan Lainnya belum diisi.")
        elif not validasi_ekstraksi:
            st.error("⚠ Format Jumlah/Nilai tidak valid. Harap masukkan nominal (contoh: Rp50.987.00 atau 50 Sak).")
        elif jumlah_final <= 0:
            st.error("⚠ Jumlah harus lebih dari nol.")
        else:
            try:
                # 1. Simpan Data ke Google Sheets
                with st.spinner("⏳ Menyimpan data..."):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)
                    
                    if jenis_bantuan_final == "Uang":
                        jumlah_terformat_string = format_rupiah_uang(jumlah_final) 
                        final_output = prefix_rp + jumlah_terformat_string
                    else: 
                        jumlah_terformat_string = format_satuan_material(jumlah_final) 
                        if satuan_terekstrak:
                             final_output = f"{jumlah_terformat_string} {satuan_terekstrak}"
                        else:
                             final_output = jumlah_terformat_string
                    
                    new_row = [
                        tanggal.strftime("%Y-%m-%d"),
                        pilar,
                        jenis_bantuan_final,
                        uraian,
                        final_output,
                        lokasi_final,
                    ]

                    worksheet.append_row(new_row)

                # 2. Tampilkan Notifikasi 2 Detik di bawah tombol
                notification_placeholder.success("BERHASIL")
                time.sleep(2) # Tunggu 2 detik
                notification_placeholder.empty() # Hapus pesan

                # 3. Reset Form Input secara manual
                reset_form_inputs()
                
                # 4. Clear cache data dan panggil rerun untuk refresh data view di kolom samping
                load_data.clear()
                st.rerun() 

            except Exception as e:
                st.error(f"Gagal menyimpan data ke Google Sheets. Error: {e}") 

