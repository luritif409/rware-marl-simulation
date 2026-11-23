# Simulasi Penugasan Robot Gudang

Aplikasi Streamlit untuk membandingkan dua pengendali heuristik pada lingkungan Multi-Robot Warehouse (RWARE) tanpa proses training:

1. **Baseline** menggunakan heuristik jarak lintasan minimum.
2. **Kontribusi usulan** menggunakan skor `jarak + α × kepadatan jalur`.

Mesin simulasi menggunakan paket [RWARE](https://github.com/uoe-agents/robotic-warehouse) pada commit yang dipatok di `requirements.txt`. Layout dibuat khusus: rak berada di area gudang dan semua titik pengantaran dipilih dari baris paling bawah. Pengendali Baseline memilih rak yang diminta berdasarkan jarak lintasan; Kontribusi usulan menambahkan estimasi kepadatan robot di sepanjang lintasan. Keduanya memakai aturan gerak, pengambilan, pengantaran, dan pengembalian rak milik RWARE. Aplikasi ini tidak melatih model MARL atau menjalankan MAPPO.

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

- Ukuran gudang: Tiny (10 × 11), Small (10 × 20), Medium (16 × 20), atau Large (16 × 29)
- Rentang kolom peletakan barang/pengantaran pada baris paling bawah. Satu kolom atau beberapa kolom berurutan dapat dipilih.
- Jumlah rak, robot (N), rak diminta serentak (R), dan target pengantaran
- Maksimum langkah simulasi
- Bobot kepadatan α
- Radius pengamatan kepadatan
- Jumlah pengulangan
- Seed awal

**Jumlah seluruh rak** dan **R** berbeda. Batas jumlah rak mengikuti ukuran gudang yang dipilih, sementara nilai awalnya 18. R menentukan berapa rak yang diminta secara bersamaan: normal `R=N`, mudah `R=2N`, dan sulit sekitar `R=N/2`, selama R lebih kecil daripada jumlah seluruh rak. Pilihan ukuran menetapkan dimensi grid; susunan rak dan titik pengantaran tetap dibuat oleh layout khusus aplikasi.

Kedua kebijakan dijalankan dengan seed, layout, posisi awal robot, dan antrean permintaan awal yang sama. Antrean setelah pengantaran dapat berbeda karena permintaan baru dipilih RWARE berdasarkan keadaan antrean pada saat itu.

RWARE mengisi ulang antrean rak yang diminta setelah setiap pengantaran. Simulasi berhenti saat target pengantaran tercapai atau batas langkah habis. Untuk setiap rak yang telah diantar, robot mengembalikannya ke posisi awal sebelum mengambil tugas berikutnya.

Target pengantaran adalah batas evaluasi aplikasi, bukan parameter bawaan RWARE. Kedua pengendali heuristik memakai keadaan lengkap lingkungan untuk memilih rak dan jalur; ini tidak menguji kebijakan MARL dengan observasi lokal terbatas.

Setelah menekan **Jalankan simulasi**, aplikasi menghitung hasil seluruh pengulangan terlebih dahulu. Di bagian **Visualisasi kasus pertama**, pilih kebijakan **Baseline** atau **Kontribusi usulan**. Plotly menerima riwayat pengulangan pertama sebagai satu Figure berisi `frames`; setelah grafik tampil, tombol **Play**, **Pause**, dan slider timeline bekerja di browser tanpa menjalankan ulang Streamlit pada setiap langkah. Menu kecepatan **Lambat**, **Normal**, atau **Cepat** langsung memutar animasi pada kecepatan yang dipilih. Tombol Play memakai kecepatan Normal.

Judul grafik menampilkan langkah saat ini dan jumlah pengantaran selesai. Robot berlabel R1, R2, dan seterusnya; warna abu-abu berarti `idle`, hijau `menuju_rak`, biru `menuju_pengantaran`, dan ungu `mengembalikan_rak`. Rak merah sedang diminta, sedangkan rak oranye sedang dibawa. Arahkan kursor ke robot untuk melihat status dan ID rak target.

Untuk riwayat panjang, visualisasi mengambil maksimal 300 frame, selalu termasuk langkah 0 dan langkah terakhir. Aplikasi menampilkan interval sampling di atas grafik. Sampling hanya berlaku untuk animasi; tabel, grafik evaluasi, dan unduhan CSV tetap memakai hasil simulasi lengkap.

## Metrik evaluasi

- **Rata-rata waktu penyelesaian pesanan:** langkah sejak rak masuk antrean permintaan hingga diantar.
- **Langkah terhambat:** aksi maju yang tidak menghasilkan perpindahan karena konflik atau halangan.
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
