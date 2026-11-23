from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from warehouse_sim import SimulationConfig, compare_policies
from warehouse_sim.config import WAREHOUSE_SIZES
from warehouse_sim.simulation import demo_results
from warehouse_sim.visualization import aggregate_results, comparison_chart, warehouse_animation

st.set_page_config(page_title="Simulasi Robot Gudang", page_icon="🤖", layout="wide")

st.title("Simulasi Penugasan Robot Gudang")
st.caption(
    "Perbandingan kebijakan baseline dan kontribusi usulan pada lingkungan RWARE "
    "tanpa proses training."
)

with st.sidebar:
    st.header("Parameter simulasi")
    warehouse_size = st.selectbox(
        "Ukuran gudang",
        list(WAREHOUSE_SIZES),
        format_func=lambda name: f"{name} ({WAREHOUSE_SIZES[name][0]} × {WAREHOUSE_SIZES[name][1]})",
    )
    width, height = WAREHOUSE_SIZES[warehouse_size]
    delivery_start, delivery_end = st.slider(
        "Rentang kolom peletakan barang/pengantaran (baris bawah)",
        min_value=0,
        max_value=int(width) - 1,
        value=(0, int(width) - 1),
        help="Pilih satu kolom atau rentang kolom pada baris paling bawah gudang.",
    )
    max_shelves = sum(x % 3 != 0 for x in range(1, int(width) - 1)) * len(range(1, int(height) - 3))
    n_shelves = st.number_input(
        "Jumlah seluruh rak", 2, max_shelves, min(18, max_shelves),
        help="Jumlah seluruh rak yang tersedia; batasnya mengikuti ukuran gudang terpilih.",
    )
    n_robots = st.number_input("Jumlah robot", 1, int(width), min(4, int(width)))
    request_queue_size = st.number_input(
        "Rak diminta serentak (R)", 1, int(n_shelves) - 1,
        min(int(n_robots), int(n_shelves) - 1),
        help="R berbeda dari jumlah seluruh rak. Normal: R=N; mudah: R=2N; sulit: R≈N/2.",
    )
    n_orders = st.number_input("Target pengantaran", 1, 500, 20)
    max_steps = st.number_input("Maksimum langkah", 10, 20_000, 1000, step=100)
    st.divider()
    congestion_weight = st.number_input("Bobot kepadatan (α)", 0.0, 20.0, 2.0, 0.5)
    congestion_radius = st.number_input("Radius kepadatan", 1, 10, 2)
    repetitions = st.number_input("Jumlah pengulangan", 1, 100, 10)
    seed = st.number_input("Seed awal", 0, 1_000_000, 42)
    run = st.button("Jalankan simulasi", type="primary", width="stretch")

config = SimulationConfig(
    width=int(width),
    height=int(height),
    delivery_start=int(delivery_start),
    delivery_end=int(delivery_end),
    n_shelves=int(n_shelves),
    n_robots=int(n_robots),
    request_queue_size=int(request_queue_size),
    n_orders=int(n_orders),
    max_steps=int(max_steps),
    congestion_weight=float(congestion_weight),
    congestion_radius=int(congestion_radius),
    repetitions=int(repetitions),
    seed=int(seed),
)

with st.expander("Definisi kebijakan dan metrik"):
    st.markdown(
        """
        **Baseline:** robot idle memilih rak dengan jarak lintasan minimum.

        **Kontribusi usulan:** skor penugasan adalah
        $S_{ij}=D_{ij}+\\alpha H_{ij}$, dengan $D_{ij}$ sebagai jarak dan
        $H_{ij}$ sebagai estimasi robot lain di sekitar jalur.

        **Waktu selesai** dihitung sejak rak diminta hingga tiba di titik pengantaran.
        **Langkah terhambat** bertambah ketika gerak robot ditolak karena konflik.
        **Jarak tempuh** adalah jumlah perpindahan sel yang berhasil.
        """
    )

if run:
    try:
        with st.spinner("Menjalankan seluruh pengulangan..."):
            results, layout = compare_policies(config)
            demos = demo_results(config)
        st.session_state["results"] = results
        st.session_state["layout"] = layout
        st.session_state["demos"] = demos
        st.session_state["config"] = config.to_dict()
    except ValueError as exc:
        st.error(str(exc))

if "results" not in st.session_state:
    st.info("Atur parameter pada panel kiri, lalu tekan **Jalankan simulasi**.")
    st.stop()

results = st.session_state["results"]
layout = st.session_state["layout"]
demos = st.session_state["demos"]
summary = aggregate_results(results)

st.subheader("Ringkasan hasil")
st.dataframe(summary, width="stretch", hide_index=True)
if any(result.orders_completed < result.orders_total for result in results):
    st.warning(
        "Sebagian pengulangan mencapai batas langkah sebelum semua pesanan selesai. "
        "Kondisi ini dipertahankan sebagai indikasi kemacetan atau deadlock dan tercatat pada CSV."
    )

metric = st.selectbox(
    "Metrik grafik",
    ["Rata-rata waktu selesai", "Langkah terhambat", "Jarak tempuh", "Pesanan selesai", "Throughput"],
)
st.plotly_chart(comparison_chart(summary, metric), width="stretch")

st.subheader("Visualisasi kasus pertama")
selected_policy = st.radio("Kebijakan animasi", list(demos.keys()), horizontal=True)
history = demos[selected_policy].history
animation, stride = warehouse_animation(layout, history, selected_policy)
st.caption(
    "Tekan Play untuk kecepatan normal. Pilih Lambat, Normal, atau Cepat pada menu "
    "di grafik untuk langsung memutar pada kecepatan itu; Pause menghentikan animasi. "
    "Geser timeline untuk melihat langkah tertentu. "
    "Warna robot: abu-abu = idle, hijau = menuju_rak, biru = menuju_pengantaran, "
    "ungu = mengembalikan_rak. Rak merah sedang diminta; rak oranye sedang dibawa."
)
if stride > 1:
    st.info(
        f"Visualisasi menampilkan setiap {stride} langkah dan langkah terakhir "
        f"({len(animation.frames)} dari {len(history)} frame). "
        "Hasil evaluasi tetap dihitung dari seluruh langkah."
    )
st.plotly_chart(animation, width="stretch")

raw = pd.DataFrame([result.to_summary() for result in results])
config_json = json.dumps(st.session_state["config"], indent=2, ensure_ascii=False)
download_a, download_b = st.columns(2)
with download_a:
    st.download_button(
        "Unduh hasil CSV",
        raw.to_csv(index=False).encode("utf-8"),
        "hasil_simulasi_robot.csv",
        "text/csv",
        width="stretch",
    )
with download_b:
    st.download_button(
        "Unduh konfigurasi JSON",
        config_json,
        "konfigurasi_simulasi.json",
        "application/json",
        width="stretch",
    )
