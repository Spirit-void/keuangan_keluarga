import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import date, timedelta
import altair as alt # Untuk visualisasi

# --- Pengaturan Halaman & Judul Utama ---
st.set_page_config(
    page_title="Dashboard Keuangan Keluarga",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("💸 Dashboard Keuangan Keluarga")
st.markdown("---")

# 🔐 Setup koneksi ke Google Sheets (TIDAK DIUBAH sesuai permintaan)
try:
    sscope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("KeuanganKeluarga").sheet1

    connection_status = True
except Exception as e:
    st.error(f"❌ Kesalahan koneksi Google Sheets. Pastikan 'credentials.json' sudah benar dan terotorisasi. Error: {e}")
    connection_status = False

# Fungsi untuk memformat Rupiah
def format_rupiah(amount):
    """Format angka ke format Rupiah."""
    return f"Rp {amount:,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")

# --- Pelacakan Aset/Tabungan (Simulasi Manual) ---
# Aset tidak dilacak otomatis dari transaksi karena keterbatasan 1 sheet.
# Pengguna harus mengupdate ini secara manual.
st.header("💰 Saldo Aset Saat Ini")
if 'aset_saldo' not in st.session_state:
    st.session_state['aset_saldo'] = {
        'Bank': 5000000,
        'Saham': 10000000,
        'Emas': 2500000
    }

aset_cols = st.columns(3)
with aset_cols[0]:
    st.session_state['aset_saldo']['Bank'] = st.number_input(
        "Saldo di Bank (Rp)",
        value=st.session_state['aset_saldo']['Bank'],
        min_value=0,
        step=100000,
        key='bank_input',
        help="Update saldo uang di rekening bank Anda."
    )
    st.metric("Total Bank", format_rupiah(st.session_state['aset_saldo']['Bank']))

with aset_cols[1]:
    st.session_state['aset_saldo']['Saham'] = st.number_input(
        "Nilai Investasi Saham (Rp)",
        value=st.session_state['aset_saldo']['Saham'],
        min_value=0,
        step=100000,
        key='saham_input',
        help="Update total nilai portofolio saham Anda."
    )
    st.metric("Total Saham", format_rupiah(st.session_state['aset_saldo']['Saham']))

with aset_cols[2]:
    st.session_state['aset_saldo']['Emas'] = st.number_input(
        "Nilai Kepemilikan Emas (Rp)",
        value=st.session_state['aset_saldo']['Emas'],
        min_value=0,
        step=100000,
        key='emas_input',
        help="Update nilai terkini dari emas yang Anda miliki."
    )
    st.metric("Total Emas", format_rupiah(st.session_state['aset_saldo']['Emas']))

total_aset = sum(st.session_state['aset_saldo'].values())
st.markdown(f"### Total Kekayaan Bersih: **{format_rupiah(total_aset)}**")
st.markdown("---")

# --- Fungsi Ambil Data & Pemrosesan ---
@st.cache_data(ttl=600)
def load_data():
    """Mengambil data dari Google Sheets dan memprosesnya."""
    if not connection_status:
        # Jika koneksi gagal, kembalikan DataFrame kosong
        return pd.DataFrame({'Tanggal': [], 'Deskripsi': [], 'Kategori': [], 'Jumlah': []})
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Memastikan kolom ada dan mengkonversi tipe data
    required_cols = ['Tanggal', 'Deskripsi', 'Kategori', 'Jumlah']
    if not all(col in df.columns for col in required_cols):
        st.warning(f"Header Google Sheet TIDAK sesuai. Harap pastikan header: {required_cols}. Kolom yang ditemukan: {df.columns.tolist()}")
        return pd.DataFrame({'Tanggal': [], 'Deskripsi': [], 'Kategori': [], 'Jumlah': []})

    # Pembersihan Data
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Jumlah'] = pd.to_numeric(df['Jumlah'], errors='coerce').fillna(0)
    df = df.dropna(subset=['Tanggal', 'Kategori']) # Hapus baris tanpa Tanggal/Kategori
    df = df[df['Jumlah'] >= 0] # Hanya jumlah positif

    return df

df_transactions = load_data()


# --- Sidebar: Form Input Transaksi Baru ---
with st.sidebar:
    st.header("➕ Masukkan Transaksi Baru")
    if connection_status:
        with st.form("input_form"):
            new_tanggal = st.date_input("Tanggal Transaksi", value=date.today())
            new_kategori = st.selectbox("Jenis Transaksi", ["Pemasukan", "Pengeluaran"])
            new_deskripsi = st.text_input("Deskripsi/Keterangan", placeholder="Contoh: Gaji, Belanja Bulanan, Pulsa")
            new_jumlah = st.number_input("Jumlah (Rp)", min_value=0, value=0, step=1000)
            submit = st.form_submit_button("Simpan Transaksi")

        if submit and new_jumlah > 0 and new_deskripsi:
            # Baris di Google Sheets: Tanggal | Deskripsi | Kategori | Jumlah
            try:
                sheet.append_row([str(new_tanggal), new_deskripsi, new_kategori, new_jumlah])
                st.success(f"✅ {new_kategori} sebesar {format_rupiah(new_jumlah)} telah disimpan!")
                st.cache_data.clear() # Hapus cache agar data di dashboard terupdate
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan ke Google Sheets: {e}")
        elif submit:
             st.warning("Pastikan Jumlah > 0 dan Deskripsi diisi.")
    else:
        st.info("Form input dinonaktifkan karena koneksi Google Sheets gagal.")

# --- Dashboard Utama ---
if not df_transactions.empty:
    # 1. Penghitungan KPI
    df_income = df_transactions[df_transactions['Kategori'] == 'Pemasukan']
    df_expense = df_transactions[df_transactions['Kategori'] == 'Pengeluaran']

    total_income = df_income['Jumlah'].sum()
    total_expense = df_expense['Jumlah'].sum()
    net_saldo = total_income - total_expense
    
    # Menentukan warna metric berdasarkan nilai saldo
    saldo_color = "inverse" if net_saldo < 0 else "off"

    st.header("🔑 Ikhtisar Keuangan")
    kpi_cols = st.columns(3)

    with kpi_cols[0]:
        st.metric(
            label="Total Pemasukan",
            value=format_rupiah(total_income),
            delta="Sejak awal pencatatan"
        )
    with kpi_cols[1]:
        st.metric(
            label="Total Pengeluaran",
            value=format_rupiah(total_expense),
            delta_color="off"
        )
    with kpi_cols[2]:
        st.metric(
            label="Saldo Bersih (Pemasukan - Pengeluaran)",
            value=format_rupiah(net_saldo),
            delta_color=saldo_color,
            help="Ini adalah selisih Pemasukan dan Pengeluaran, BUKAN Saldo Aset."
        )

    # 2. Grafik Pemasukan vs Pengeluaran
    st.header("📈 Visualisasi Keuangan")
    col_chart_1, col_chart_2 = st.columns([1, 1.5])

    # Chart 1: Donut Chart Pemasukan vs Pengeluaran
    kategori_summary = df_transactions.groupby('Kategori')['Jumlah'].sum().reset_index()
    
    pie_chart = alt.Chart(kategori_summary).mark_arc(outerRadius=120).encode(
        theta=alt.Theta("Jumlah", stack=True),
        color=alt.Color("Kategori", scale=alt.Scale(domain=['Pemasukan', 'Pengeluaran'], range=['#4CAF50', '#F44336'])),
        order=alt.Order("Jumlah", sort="descending"),
        tooltip=['Kategori', alt.Tooltip("Jumlah", format=",")]
    ).properties(
        title="Total Pemasukan vs Pengeluaran"
    )
    
    with col_chart_1:
        st.altair_chart(pie_chart, use_container_width=True)

    # Chart 2: Tren Pengeluaran Harian/Mingguan
    df_expense_only = df_expense[['Tanggal', 'Jumlah']].copy()
    
    # Tren Harian
    df_daily = df_expense_only.groupby(df_expense_only['Tanggal'].dt.normalize())['Jumlah'].sum().reset_index()
    df_daily.rename(columns={'Tanggal': 'Tanggal', 'Jumlah': 'Pengeluaran'}, inplace=True)
    
    # Tren Mingguan (Menggunakan start of week)
    df_expense_only['Minggu'] = df_expense_only['Tanggal'].dt.to_period('W').apply(lambda r: r.start_time)
    df_weekly = df_expense_only.groupby('Minggu')['Jumlah'].sum().reset_index()
    df_weekly.rename(columns={'Minggu': 'Tanggal', 'Jumlah': 'Pengeluaran'}, inplace=True)

    # Tampilkan tren dalam satu tab
    with col_chart_2:
        tab_harian, tab_mingguan = st.tabs(["Pengeluaran Harian", "Pengeluaran Mingguan"])
        
        # Grafik Harian
        with tab_harian:
            # FIX: GradientStop hanya menerima 2 argumen posisi (color, offset)
            daily_chart = alt.Chart(df_daily).mark_area(line={'color':'#F44336'}, color=alt.Gradient(
                gradient='linear',
                # Memperbaiki TypeError: GradientStop hanya menerima 2 argumen posisi (color, offset).
                # Opacity diatur melalui kanal alpha pada kode hex (#1A) di stop kedua.
                stops=[alt.GradientStop('#F44336', 0.1), alt.GradientStop('#F443361A', 1)],
                x1=1,
                y1=1,
                x2=1,
                y2=0
            )).encode(
                x=alt.X('Tanggal', title='Tanggal'),
                y=alt.Y('Pengeluaran', title='Jumlah Pengeluaran (Rp)'),
                tooltip=['Tanggal', alt.Tooltip("Pengeluaran", format=",")]
            ).properties(title="Tren Pengeluaran Harian")
            st.altair_chart(daily_chart, use_container_width=True)

        # Grafik Mingguan
        with tab_mingguan:
            weekly_chart = alt.Chart(df_weekly).mark_bar(color='#F44336').encode(
                x=alt.X('Tanggal', title='Awal Minggu'),
                y=alt.Y('Pengeluaran', title='Jumlah Pengeluaran (Rp)'),
                tooltip=['Tanggal', alt.Tooltip("Pengeluaran", format=",")]
            ).properties(title="Tren Pengeluaran Mingguan")
            st.altair_chart(weekly_chart, use_container_width=True)

    # 3. Data Editor (Editable Table)
    st.header("📝 Data Transaksi & Editor Cepat")
    st.info("Anda dapat mengedit data langsung di tabel ini. Tekan tombol 'Simpan Perubahan' di bawah untuk update ke Google Sheets.")

    # Tampilkan DataFrame dengan st.data_editor
    # Tampilkan 10 kolom pertama untuk menghindari terlalu panjang
    edited_df = st.data_editor(
        df_transactions,
        column_config={
            "Tanggal": st.column_config.DatetimeColumn("Tanggal", format="YYYY-MM-DD", required=True),
            "Deskripsi": st.column_config.TextColumn("Deskripsi", required=True),
            "Kategori": st.column_config.SelectboxColumn("Kategori", options=["Pemasukan", "Pengeluaran"], required=True),
            "Jumlah": st.column_config.NumberColumn("Jumlah (Rp)", min_value=0, format="%,.0f", required=True)
        },
        hide_index=False, # Tampilkan index agar mudah diacu
        num_rows="dynamic", # Memungkinkan penambahan baris baru
        use_container_width=True
    )

    if st.button("Simpan Perubahan ke Google Sheets"):
        # Logika penyimpanan: Hapus semua data lama dan tulis ulang dengan data yang sudah di edit
        try:
            # 1. Pastikan kolom sesuai
            output_df = edited_df[['Tanggal', 'Deskripsi', 'Kategori', 'Jumlah']]
            # 2. Konversi Tanggal kembali ke string
            output_df['Tanggal'] = output_df['Tanggal'].dt.strftime('%Y-%m-%d')
            
            # 3. Ambil data dalam format list of lists (termasuk header)
            data_to_save = [output_df.columns.tolist()] + output_df.values.tolist()
            
            # 4. Kosongkan sheet dan update
            sheet.clear()
            sheet.update(f"A1", data_to_save)
            st.success("🎉 Semua perubahan berhasil disimpan ke Google Sheets!")
            st.cache_data.clear()
            st.rerun()

        except Exception as e:
            st.error(f"Gagal menyimpan perubahan: {e}")

else:
    st.info("Data keuangan kosong. Silakan masukkan transaksi pertama Anda melalui sidebar.")

st.markdown("---")
st.caption("Aplikasi ini dibuat menggunakan Streamlit dan Google Sheets.")
