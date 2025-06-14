import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error

st.set_page_config(page_title="Prediksi BPJS PBI - Fuzzy Sugeno & Mamdani", layout="wide")

# --- Background Cyberpunk ---
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

# --- Sugeno ---
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

# --- Mamdani (simulasi: ambil rata-rata dari 2 nilai berdasarkan fuzzy max) ---
def mamdani_output(bpbi, jamkesda):
    turun, naik = fuzzify_bpbi(bpbi)
    sedikit, banyak = fuzzify_jamkesda(jamkesda)
    rules = [min(turun, sedikit), min(turun, banyak), min(naik, sedikit), min(naik, banyak)]
    outputs = [148805, 148805, 149840, 149840]
    max_val = max(rules)
    return np.mean([out for r, out in zip(rules, outputs) if r == max_val])

# --- Load Data ---
@st.cache_data
def get_default_data():
    return pd.DataFrame({
        "Bulan": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
        "PBI Asli": [148947, 148907, 148868, 148823, 148827, 148805, 149097, 149150, 149361, 149345, 149733, 149840],
        "BPBI": [341886, 340532, 342814, 347362, 349364, 349993, 350033, 349978, 352938, 357049, 359199, 360936],
        "Jamkesda": [42747, 42719, 42715, 42708, 42652, 42609, 42644, 42610, 42558, 42201, 41924, 42701],
    })

# --- Sidebar ---
st.sidebar.title("⚙️ Pengaturan")
metode = st.sidebar.radio("Metode Fuzzy", ["Sugeno", "Mamdani"])
d_sedikit = st.sidebar.number_input("Nilai PBI Sedikit", value=148805)
d_banyak = st.sidebar.number_input("Nilai PBI Banyak", value=149840)
uploaded = st.sidebar.file_uploader("📥 Upload Data CSV/Excel", type=["csv", "xlsx"])

if uploaded:
    df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
else:
    df = get_default_data()

st.title("📊 Prediksi Jumlah Peserta BPJS PBI")
st.markdown("""Menggunakan metode **Fuzzy Inference System** dan **Regresi Linier** sebagai pembanding.""")

# --- Proses Prediksi ---
results = []
for i, row in df.iterrows():
    bulan = row["Bulan"]
    try:
        pbi_asli = float(row["PBI Asli"])
        bpbi = float(row["BPBI"])
        jamkesda = float(row["Jamkesda"])
        pred_fuzzy = sugeno_output(bpbi, jamkesda, d_sedikit, d_banyak) if metode == "Sugeno" else mamdani_output(bpbi, jamkesda)
        results.append([bulan, pbi_asli, pred_fuzzy, bpbi, jamkesda])
    except:
        continue

res_df = pd.DataFrame(results, columns=["Bulan", "PBI Asli", "Prediksi Fuzzy", "BPBI", "Jamkesda"])

# --- Regresi Linier ---
X = res_df[["BPBI", "Jamkesda"]]
y = res_df["PBI Asli"]
reg = LinearRegression().fit(X, y)
res_df["Prediksi Regresi"] = reg.predict(X)

# --- Evaluasi ---
res_df["MAPE"] = abs(res_df["PBI Asli"] - res_df["Prediksi Fuzzy"]) / res_df["PBI Asli"] * 100
rmse = mean_squared_error(res_df["PBI Asli"], res_df["Prediksi Fuzzy"], squared=False)
mae = mean_absolute_error(res_df["PBI Asli"], res_df["Prediksi Fuzzy"])

# --- Tampilkan Data ---
st.subheader("📋 Hasil Prediksi")
st.dataframe(res_df, use_container_width=True)

# --- Grafik ---
st.subheader("📈 Grafik Perbandingan Model")
fig, ax = plt.subplots()
ax.plot(res_df["Bulan"], res_df["PBI Asli"], marker='o', label="Asli")
ax.plot(res_df["Bulan"], res_df["Prediksi Fuzzy"], marker='x', label="Fuzzy")
ax.plot(res_df["Bulan"], res_df["Prediksi Regresi"], marker='s', label="Regresi")
ax.legend()
ax.grid()
ax.set_ylabel("Jumlah Peserta")
st.pyplot(fig)

# --- Histogram Error ---
st.subheader("📊 Sebaran Error (Fuzzy vs Asli)")
fig2, ax2 = plt.subplots()
errors = res_df["PBI Asli"] - res_df["Prediksi Fuzzy"]
ax2.hist(errors, bins=10, color='skyblue', edgecolor='black')
ax2.set_title("Distribusi Error")
ax2.set_xlabel("Error")
ax2.set_ylabel("Frekuensi")
st.pyplot(fig2)

# --- Rangkuman Evaluasi ---
st.subheader("📏 Evaluasi Model")
st.markdown(f"- RMSE (Fuzzy): **{rmse:.2f}**")
st.markdown(f"- MAE (Fuzzy): **{mae:.2f}**")
st.markdown(f"- Rata-rata MAPE: **{res_df['MAPE'].mean():.2f}%**")

# --- Aturan Fuzzy ---
st.subheader("📘 Aturan Fuzzy")
st.markdown("""
**Jika:**
- BPBI *Turun* & Jamkesda *Sedikit* → PBI *Sedikit*  
- BPBI *Turun* & Jamkesda *Banyak* → PBI *Sedikit*  
- BPBI *Naik* & Jamkesda *Sedikit* → PBI *Banyak*  
- BPBI *Naik* & Jamkesda *Banyak* → PBI *Banyak*
""")

# --- Unduh Hasil ---
st.subheader("📥 Unduh Data")
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    res_df.to_excel(writer, index=False, sheet_name="Prediksi")
    writer.save()
st.download_button("📄 Unduh sebagai Excel", data=buffer.getvalue(), file_name="hasil_prediksi.xlsx")
