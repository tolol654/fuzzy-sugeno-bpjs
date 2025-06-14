import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Prediksi BPJS PBI - FIS Sugeno", layout="wide")

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
def sugeno_output(bpbi, jamkesda):
    turun, naik = fuzzify_bpbi(bpbi)
    sedikit, banyak = fuzzify_jamkesda(jamkesda)

    alpha1 = min(turun, sedikit)
    alpha2 = min(turun, banyak)
    alpha3 = min(naik, sedikit)
    alpha4 = min(naik, banyak)

    d_sedikit = 148805
    d_banyak = 149840

    numerator = (alpha1 * d_sedikit + alpha2 * d_sedikit + alpha3 * d_banyak + alpha4 * d_banyak)
    denominator = alpha1 + alpha2 + alpha3 + alpha4

    return numerator / denominator if denominator != 0 else 0

# --- Data Input Default ---
data_default = {
    "Bulan": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
    "PBI Asli": [148947, 148907, 148868, 148823, 148827, 148805, 149097, 149150, 149361, 149345, 149733, 149840],
    "BPBI": [341886, 340532, 342814, 347362, 349364, 349993, 350033, 349978, 352938, 357049, 359199, 360936],
    "Jamkesda": [42747, 42719, 42715, 42708, 42652, 42609, 42644, 42610, 42558, 42201, 41924, 42701],
}

st.title("\U0001F4CA Prediksi Jumlah Peserta BPJS PBI - FIS Sugeno")
st.markdown("""
Aplikasi ini menggunakan metode **Fuzzy Inference System Sugeno** untuk memprediksi jumlah peserta BPJS kategori PBI berdasarkan jumlah peserta BPBI dan Jamkesda/PJKMU.
""")

# --- Upload CSV (opsional) ---
st.sidebar.subheader("Upload Data CSV (opsional)")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV", type="csv")

if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    st.sidebar.success("File berhasil diunggah!")
else:
    df_input = pd.DataFrame(data_default)

# --- Input Tabel ---
with st.expander("\U0001F4C5 Input atau Edit Data Bulanan"):
    edited_df = st.data_editor(df_input, num_rows="dynamic", use_container_width=True)

# --- Proses Prediksi ---
results = []
for i, row in edited_df.iterrows():
    bulan = row.get("Bulan", f"Bulan-{i+1}")
    try:
        pbi_asli = float(row["PBI Asli"])
        bpbi = float(row["BPBI"])
        jamkesda = float(row["Jamkesda"])
        pred = sugeno_output(bpbi, jamkesda)
        error = abs(pbi_asli - pred)
        mape = (error / pbi_asli) * 100
        results.append([bulan, pbi_asli, round(pred, 2), round(mape, 2)])
    except:
        continue

df_result = pd.DataFrame(results, columns=["Bulan", "PBI Asli", "PBI Prediksi", "MAPE"])

st.subheader("\U0001F4C4 Hasil Prediksi")
st.dataframe(df_result, use_container_width=True)

# --- Grafik Prediksi vs Asli ---
if not df_result.empty:
    st.subheader("\U0001F4C8 Grafik Prediksi vs Realisasi")
    fig1, ax1 = plt.subplots()
    ax1.plot(df_result["Bulan"], df_result["PBI Asli"], marker='o', label="PBI Asli")
    ax1.plot(df_result["Bulan"], df_result["PBI Prediksi"], marker='x', label="PBI Prediksi (Sugeno)")
    ax1.set_xlabel("Bulan")
    ax1.set_ylabel("Jumlah Peserta")
    ax1.set_title("Prediksi vs PBI Aktual")
    ax1.legend()
    ax1.grid(True)
    st.pyplot(fig1)

    st.subheader("\U0001F4CA Grafik MAPE per Bulan")
    fig2, ax2 = plt.subplots()
    ax2.bar(df_result["Bulan"], df_result["MAPE"], color='green')
    avg_mape = df_result["MAPE"].mean()
    ax2.axhline(y=avg_mape, color='red', linestyle='--', label=f"Rata-rata: {avg_mape:.2f}%")
    ax2.set_title("MAPE per Bulan")
    ax2.set_xlabel("Bulan")
    ax2.set_ylabel("MAPE (%)")
    ax2.legend()
    st.pyplot(fig2)

    st.success(f"\U0001F3AF Rata-rata MAPE: {avg_mape:.2f}% → Akurasi: {100 - avg_mape:.2f}%")

    # --- Download Excel ---
    st.subheader("\U0001F4E5 Unduh Hasil")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name="Hasil Prediksi")
    st.download_button(
        label="📥 Unduh sebagai Excel",
        data=output.getvalue(),
        file_name="hasil_prediksi_bpjs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Tidak ada data valid untuk diproses.")
