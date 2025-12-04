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

# Fungsi Helper untuk Pemformatan Angka ke String dengan Titik sebagai Pemisah Ribuan
def format_rupiah_manual(angka):
    """
    Memformat angka float/int menjadi string dengan titik sebagai pemisah ribuan
    dan DUA ANGKA DESIMAL, menggunakan titik sebagai separator desimal.
    Contoh: 50987.00 -> "50.987.00"
    """
    try:
        if isinstance(angka, str):
            angka = float(angka)
            
        # Format ke string dengan 2 desimal, menggunakan koma (,) sebagai pemisah ribuan sementara (standar Python)
        formatted = f'{angka:,.2f}' # Contoh: 50987.00 menjadi "50,987.00"
        
        # 1. Ganti koma (pemisah ribuan Python) menjadi placeholder 'X'
        temp_result = formatted.replace(',', 'X')
        
        # 2. Ganti titik desimal (.) menjadi koma desimal (,)
        temp_result = temp_result.replace('.', ',')
        
        # 3. Ganti placeholder 'X' (pemisah ribuan) menjadi titik (.)
        final_result = temp_result.replace('X', '.')
        
        # Output saat ini: "50.987,00" (Format Indonesia: Titik Ribuan, Koma Desimal)
        
        # KARENA ANDA INGIN PERSIS "50.987.00" (Titik Desimal), kita akan ubah langkah 3 dan 4.
        
        # 1. Ganti koma (pemisah ribuan Python) menjadi titik (pemisah ribuan output)
        result = formatted.replace(',', '.') 
        
        # 2. Ambil string yang sudah dibersihkan dan dipastikan memiliki dua desimal.
        # Jika input adalah 50987.0, f-string akan menghasilkan '50,987.00' (di Python).
        # result menjadi '50.987.00'
        return result
        
    except Exception:
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
                placeholder="Contoh: Beras, Kursi, Peralatan Kebersihan"
            )
        
        if st.session_state.jenis_bantuan_key == "Lainnya":
            jenis_bantuan_final = jenis_bantuan_manual 
        else:
            jenis_bantuan_final = st.session_state.jenis_bantuan_key


        uraian = st.text_area("Uraian Kegiatan", placeholder="Jelaskan...")

        # --- PERUBAHAN UTAMA: SATU INPUT UNTUK NOMINAL & SATUAN ---
        
        # Contoh placeholder disesuaikan berdasarkan pilihan
        if jenis_bantuan_final == "Uang":
            # Perbarui placeholder: Tekankan penggunaan titik untuk desimal jika itu yang Anda inginkan
            placeholder_text = "Contoh: 50.987.00 atau 1.000.000" 
        elif jenis_bantuan_final == "Semen / Material":
            placeholder_text = "Contoh: 50 Sak atau 2 Ton"
        else:
            placeholder_text = "Contoh: 5 Paket atau 10 Liter"
            
        # Mengganti c1, c2 dan st.number_input/st.text_input menjadi SATU st.text_input
        jumlah_dan_satuan_mentah = st.text_input(
            f"Jumlah / Nilai (Masukkan nominal dan satuan)", 
            placeholder=placeholder_text,
            key="jumlah_satuan_mentah_input"
        )
        # --- AKHIR PERUBAHAN UTAMA ---

        opsi_lokasi = [
            "Tarjun", "Langadai", "Serongga", "Tegal Rejo",
            "Pulau Panci", "Cantung Kiri Hilir", "Sungai Kupang",
            "Sidomulyo", "Dusun Simpang 3 Quary", "Desa Mitra", "Lainnya (Input Manual)"
        ]

        lokasi_select = st.selectbox("Pilih Desa/Lokasi", opsi_lokasi, key="lokasi_select_state")

        lokasi_manual = ""
        if lokasi_select == "Lainnya (Input Manual)":
            lokasi_manual = st.text_input("Ketik Nama Lokasi Baru", key="lokasi_manual_input")

        submitted = st.form_submit_button("💾 Simpan Data")

    
    if submitted:
        lokasi_final = lokasi_manual if lokasi_select == "Lainnya (Input Manual)" else lokasi_select
        
        # --- LOGIKA EKSTRAKSI NOMINAL (SATUAN HANYA DIPAKAI UNTUK KONVERSI) ---
        
        jumlah_final = 0.0
        satuan_untuk_konversi = ""
        validasi_ekstraksi = True

        # Membersihkan input dari simbol mata uang, dan menormalkan format
        input_clean = jumlah_dan_satuan_mentah.replace('Rp', '').replace('rp', '').strip()

        # Regex mencari nominal (angka/desimal/ribuan) di awal, dan sisanya adalah satuan
        match = re.match(r"([\d\.\,]+)\s*(.*)?", input_clean)

        if match:
            nominal_str_raw = match.group(1).strip()
            
            # --- LOGIKA EKSTRAKSI YANG MEMPERTAHANKAN .00 ---
            nominal_str_clean = nominal_str_raw
            
            # 1. Cek separator terakhir (yang paling mungkin adalah desimal)
            last_separator = ''
            if nominal_str_raw.rfind(',') > nominal_str_raw.rfind('.'):
                last_separator = ','
            elif nominal_str_raw.rfind('.') > -1:
                last_separator = '.'
                
            # 2. Asumsikan separator terakhir adalah desimal
            if last_separator:
                # Pisahkan berdasarkan separator terakhir
                parts = nominal_str_raw.rsplit(last_separator, 1)
                
                # Hapus semua pemisah ribuan (titik/koma) dari bagian bilangan bulat (parts[0])
                parts[0] = parts[0].replace('.', '').replace(',', '')
                
                # Gabungkan kembali: [Angka tanpa ribuan] . [Desimal]
                # PENTING: Gunakan titik (.) sebagai desimal untuk format Python float
                nominal_str_clean = parts[0] + '.' + parts[1]
            else:
                # Tidak ada separator (misal '1000000')
                pass

            # 3. Ganti koma ke titik (untuk memastikan format float Python)
            nominal_str_clean = nominal_str_clean.replace(',', '.') 
            
            try:
                # Contoh: Input 50.987.00 -> nominal_str_clean 50987.00 -> jumlah_final 50987.0
                jumlah_final = float(nominal_str_clean)
            except ValueError:
                validasi_ekstraksi = False
            
            # Satuan diekstrak untuk KEPENTINGAN KONVERSI Semen/Material
            satuan_untuk_konversi = match.group(2).strip() if match.group(2) else ""
            
            # Jika bukan uang dan satuan masih kosong (misal "50" untuk Semen), itu error
            if jenis_bantuan_final != "Uang" and not satuan_untuk_konversi:
                validasi_ekstraksi = False

        else:
            validasi_ekstraksi = False


        # --- LOGIKA KONVERSI (HANYA MENGUBAH JUMLAH) ---
        
        if jenis_bantuan_final == "Semen / Material":
            # Konversi ke Ton HANYA jika jenis bantuan adalah Semen / Material dan satuan adalah Sak
            if satuan_untuk_konversi.lower() == "sak":
                jumlah_final = jumlah_final * KONVERSI_SAK_KE_TON
            
        # --- AKHIR LOGIKA KONVERSI ---


        # Validasi Input (Diperbarui)
        if not uraian:
            st.error("⚠ Uraian tidak boleh kosong.")
        elif lokasi_select == "Lainnya (Input Manual)" and not lokasi_final:
            st.error("⚠ Lokasi manual belum diisi.")
        elif st.session_state.jenis_bantuan_key == "Lainnya" and not jenis_bantuan_final:
            st.error("⚠ Jenis Bantuan Lainnya belum diisi.")
        elif not validasi_ekstraksi:
            st.error("⚠ Format Jumlah/Nilai tidak valid. Harap masukkan nominal (contoh: 50.987.00 atau 50 Sak).")
        elif jumlah_final <= 0:
            st.error("⚠ Jumlah harus lebih dari nol.")
        else:
            try:
                with st.spinner("⏳ Menyimpan data..."):
                    client = get_gspread_client()
                    sheet = client.open_by_key(st.secrets["SHEET_ID"])
                    worksheet = sheet.worksheet(WORKSHEET_NAME)
                    
                    # --- PEMFORMATAN STRING UNTUK OUTPUT ---
                    
                    # Jumlah diformat ke string (contoh: 50.987.00)
                    jumlah_terformat_string = format_rupiah_manual(jumlah_final) 
                    
                    # Urutan kolom yang dikirim ke Google Sheets (TANPA KOLOM SATUAN)
                    
                    new_row = [
                        tanggal.strftime("%Y-%m-%d"),
                        pilar,
                        jenis_bantuan_final,
                        uraian,
                        jumlah_terformat_string, # MENGGANTIKAN KOLOM JUMLAH & SATUAN
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

        st.info("Belum ada data yang tersimpan.")


