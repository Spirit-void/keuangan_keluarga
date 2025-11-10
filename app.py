import streamlit as st
import pandas as pd

st.title("Dashboard Keuangan Keluarga")

# Form input
with st.form("input_form"):
    tanggal = st.date_input("Tanggal")
    kategori = st.selectbox("Kategori", ["Pemasukan", "Pengeluaran"])
    jumlah = st.number_input("Jumlah (Rp)", min_value=0)
    submit = st.form_submit_button("Simpan")

# Tampilkan data dummy
data = pd.DataFrame({
    "Tanggal": ["2025-11-01", "2025-11-03"],
    "Kategori": ["Pemasukan", "Pengeluaran"],
    "Jumlah": [5000000, 1500000]
})
st.dataframe(data)

# Grafik
st.bar_chart(data.groupby("Kategori")["Jumlah"].sum())
