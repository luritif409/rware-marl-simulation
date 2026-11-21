# Simulasi Penugasan Robot Gudang

Aplikasi Streamlit untuk membandingkan dua kebijakan penugasan robot tanpa proses training:

1. **Baseline** menggunakan heuristik jarak lintasan minimum.
2. **Kontribusi usulan** menggunakan skor `jarak + α × kepadatan jalur`.

Simulator ini mengikuti konsep umum Multi-Robot Warehouse (RWARE), tetapi merupakan simulator grid mandiri agar parameter penugasan dan evaluasi dapat dikustomisasi. Aplikasi ini bukan implementasi resmi atau reproduksi penuh RWARE/MAPPO.

## Menjalankan aplikasi

Disarankan menggunakan Python 3.10 atau 3.11.

### Windows

Klik dua kali `run.bat`, atau jalankan:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Linux/macOS

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Browser akan membuka alamat `http://localhost:8501`.

## Deployment publik

Proyek siap dipasang pada Streamlit Community Cloud. Unggah seluruh isi folder proyek ke root repositori GitHub, kemudian gunakan:

- Branch: `main`
- Main file path: `app.py`
- Python: `3.12`
- Secrets: tidak diperlukan

Petunjuk lengkap tersedia di [`DEPLOY_STREAMLIT_CLOUD.md`](DEPLOY_STREAMLIT_CLOUD.md).

## Parameter input

- Lebar dan tinggi gudang
- Jumlah rak, robot, dan pesanan
- Maksimum langkah simulasi
- Bobot kepadatan α
- Radius pengamatan kepadatan
- Jumlah pengulangan
- Seed awal

Kedua kebijakan selalu dijalankan menggunakan seed dan urutan pesanan yang sama sehingga perbandingannya berpasangan dan lebih adil.

Setelah menekan **Jalankan simulasi**, aplikasi menghitung hasil seluruh pengulangan terlebih dahulu. Di bagian **Visualisasi kasus pertama**, pilih kebijakan **Baseline** atau **Kontribusi usulan**. Plotly menerima riwayat pengulangan pertama sebagai satu Figure berisi `frames`; setelah grafik tampil, tombol **Play**, **Pause**, dan slider timeline bekerja di browser tanpa menjalankan ulang Streamlit pada setiap langkah. Menu kecepatan **Lambat**, **Normal**, atau **Cepat** langsung memutar animasi pada kecepatan yang dipilih. Tombol Play memakai kecepatan Normal.

Judul grafik menampilkan langkah saat ini dan jumlah pesanan selesai. Robot berlabel R1, R2, dan seterusnya; warna abu-abu berarti `idle`, hijau `menuju_rak`, dan biru `menuju_pengantaran`. Arahkan kursor ke robot untuk melihat status dan ID pesanan. Kotak oranye di samping robot menunjukkan barang yang sedang dibawa.

Untuk riwayat panjang, visualisasi mengambil maksimal 300 frame, selalu termasuk langkah 0 dan langkah terakhir. Aplikasi menampilkan interval sampling di atas grafik. Sampling hanya berlaku untuk animasi; tabel, grafik evaluasi, dan unduhan CSV tetap memakai hasil simulasi lengkap.

## Metrik evaluasi

- **Rata-rata waktu penyelesaian pesanan:** langkah dari awal simulasi sampai pesanan diantar.
- **Langkah terhambat:** gerakan yang ditolak akibat konflik antarro­bot.
- **Jarak tempuh:** jumlah perpindahan sel yang berhasil.
- **Pesanan selesai:** jumlah pesanan yang sampai ke titik pengantaran.
- **Throughput:** pesanan selesai dibagi jumlah langkah simulasi.

## Menjalankan pengujian

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Interpretasi hasil

Nilai waktu selesai, langkah terhambat, dan jarak tempuh yang lebih kecil menunjukkan penggunaan sumber daya yang lebih efisien. Namun, jarak tempuh hanya boleh dibandingkan bersama jumlah pesanan selesai. Kebijakan dengan jarak rendah tetapi banyak pesanan gagal belum tentu lebih baik.
