import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

st.set_page_config(page_title="Prediksi BPJS PBI - FIS Sugeno", layout="wide")

# --- Tambahkan background anime cyberpunk ---
def add_bg_from_url():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("https://i.ibb.co/YLQTy8C/cyberpunk-anime-bg.jpg");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .block-container {{
            background-color: rgba(255, 255, 255, 0.88);
            padding: 2rem;
            border-radius: 12px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #222;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

add_bg_from_url()

# --- Fuzzifikasi ---
def fuzzify_bpbi(x):
    if x <= 340_532:
        return 1, 0
    elif 340_532 < x < 360_936:
        turun = (360_936 - x) / (360_936 - 340_532)
        naik = (x - 340_532) / (360_936 - 340_532)
        return turun, naik
    else:
        return 0, 1

def fuzzify_jamkesda(y):
    if y <= 41_924:
        return 1, 0
    elif 41_924 < y < 42_747:
        sedikit = (42_747 - y) / (42_747 - 41_924)
        banyak = (y - 41_924) / (42_747 - 41_924)
        return sedikit, banyak
    else:
        return 0, 1

# --- FIS Sugeno ---
def sugeno_output(bpbi, jamkesda, d_sedikit=148805, d_banyak=149840):
    turun, naik = fuzzify_bpbi(bpbi)
    sedikit, banyak = fuzzify_jamkesda(jamkesda)

    alpha1 = min(turun, sedikit)
    alpha2 = min(turun, banyak)
    alpha3 = min(naik, sedikit)
    alpha4 = min(naik, banyak)

    numerator = (alpha1 * d_sedikit + alpha2 * d_sedikit + alpha3 * d_banyak + alpha4 * d_banyak)
    denominator = alpha1 + alpha2 + alpha3 + alpha4

    return numerator / denominator if denominator != 0 else 0

# --- Sidebar Parameter ---
st.sidebar.header("⚙️ Pengaturan Fuzzy")
d_sedikit = st.sidebar.number_input("Nilai PBI Sedikit (konsekuen)", value=148805)
d_banyak = st.sidebar.number_input("Nilai PBI Banyak (konsekuen)", value=149840)

# --- Upload File ---
st.sidebar.subheader("📥 Upload File")
uploaded_file = st.sidebar.file_uploader("Upload CSV atau Excel", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
    st.sidebar.success("File berhasil diunggah!")
else:
    df_input = pd.DataFrame({
        "Bulan": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
        "PBI Asli": [148947, 148907, 148868, 148823, 148827, 148805, 149097, 149150, 149361, 149345, 149733, 149840],
        "BPBI": [341886, 340532, 342814, 347362, 349364, 349993, 350033, 349978, 352938, 357049, 359199, 360936],
        "Jamkesda": [42747, 42719, 42715, 42708, 42652, 42609, 42644, 42610, 42558, 42201, 41924, 42701],
    })

# --- Input Manual Satuan ---
st.subheader("📝 Input Data Bulan Satuan")
with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        bulan_manual = st.text_input("Bulan", "Bulan Baru")
    with col2:
        bpbi_manual = st.number_input("BPBI", value=340000)
    with col3:
        jamkesda_manual = st.number_input("Jamkesda", value=42000)
    submitted = st.form_submit_button("Prediksi")

    if submitted:
        hasil_manual = sugeno_output(bpbi_manual, jamkesda_manual, d_sedikit, d_banyak)
        st.success(f"Hasil Prediksi PBI untuk {bulan_manual}: {hasil_manual:.2f}")

# --- Input Data Bulanan Tabel ---
st.subheader("📋 Input atau Edit Data Bulanan")
edited_df = st.data_editor(df_input, num_rows="dynamic", use_container_width=True)

# --- Proses Prediksi ---
results = []
for i, row in edited_df.iterrows():
    bulan = row.get("Bulan", f"Bulan-{i+1}")
    try:
        pbi_asli = float(row["PBI Asli"])
        bpbi = float(row["BPBI"])
        jamkesda = float(row["Jamkesda"])
        pred = sugeno_output(bpbi, jamkesda, d_sedikit, d_banyak)
        error = abs(pbi_asli - pred)
        mape = (error / pbi_asli) * 100
        results.append([bulan, pbi_asli, round(pred, 2), round(mape, 2), error])
    except:
        continue

df_result = pd.DataFrame(results, columns=["Bulan", "PBI Asli", "PBI Prediksi", "MAPE", "Error"])
st.subheader("📄 Hasil Prediksi")
st.dataframe(df_result, use_container_width=True)

# --- Visualisasi ---
if not df_result.empty:
    st.subheader("📈 Grafik Prediksi vs Aktual")
    fig1, ax1 = plt.subplots()
    ax1.plot(df_result["Bulan"], df_result["PBI Asli"], marker='o', label="PBI Asli")
    ax1.plot(df_result["Bulan"], df_result["PBI Prediksi"], marker='x', label="PBI Prediksi")
    ax1.set_title("Prediksi vs Realisasi")
    ax1.set_xlabel("Bulan")
    ax1.set_ylabel("Jumlah Peserta")
    ax1.legend()
    ax1.grid(True)
    st.pyplot(fig1)

    st.subheader("📊 Grafik MAPE per Bulan")
    fig2, ax2 = plt.subplots()
    ax2.bar(df_result["Bulan"], df_result["MAPE"], color='skyblue')
    avg_mape = df_result["MAPE"].mean()
    ax2.axhline(y=avg_mape, color='red', linestyle='--', label=f"Rata-rata: {avg_mape:.2f}%")
    ax2.legend()
    ax2.set_ylabel("MAPE (%)")
    ax2.set_title("Tingkat Kesalahan (MAPE)")
    st.pyplot(fig2)

    st.subheader("📉 Grafik Error Absolut")
    fig3, ax3 = plt.subplots()
    ax3.plot(df_result["Bulan"], df_result["Error"], color='orange', marker='s', label="Error Absolut")
    ax3.set_title("Error Absolut per Bulan")
    ax3.set_ylabel("|Error|")
    ax3.grid(True)
    st.pyplot(fig3)

    st.success(f"🎯 Rata-rata MAPE: {avg_mape:.2f}% → Akurasi: {100 - avg_mape:.2f}%")

    # --- Download Excel ---
    st.subheader("📤 Unduh Hasil Prediksi")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name="Hasil Prediksi")
    st.download_button(
        label="📥 Unduh sebagai Excel",
        data=output.getvalue(),
        file_name="hasil_prediksi_bpjs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
