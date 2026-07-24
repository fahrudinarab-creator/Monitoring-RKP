# Dashboard Monitoring Proyek RKP

Dashboard Streamlit untuk memonitor Rencana Kerja Perusahaan (RKP): target vs
realisasi biaya, progres fisik, dan rincian capaian per pekerjaan.

## Isi folder

```
streamlit_app/
├── app.py                  # aplikasi utama
├── requirements.txt        # dependensi Python
├── .streamlit/config.toml  # tema warna
└── data/rkp_data.csv       # data bawaan (dari Update_Rekap_RKP_1.xlsx)
```

## Menjalankan di komputer sendiri

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501` di browser.

## Membagikan secara online (gratis, via Streamlit Community Cloud)

1. **Buat repo GitHub baru** (boleh privat atau publik), lalu unggah seluruh isi
   folder `streamlit_app/` ini ke repo tersebut (pastikan struktur foldernya
   tetap sama, termasuk folder `data/` dan `.streamlit/`).
2. Buka **https://share.streamlit.io** dan login dengan akun GitHub Anda.
3. Klik **"New app"**, pilih repo & branch yang baru dibuat.
4. Isi **"Main file path"** dengan `app.py`.
5. Klik **Deploy**. Dalam 1–2 menit dashboard akan online dengan URL publik
   seperti `https://nama-app-anda.streamlit.app` yang bisa dibagikan ke siapa
   saja.

Setiap kali Anda push perubahan (misalnya data baru) ke repo GitHub tersebut,
aplikasi yang sudah online akan otomatis ter-update.

## Alternatif: perbarui data tanpa deploy ulang

Di sidebar aplikasi ada tombol **"Unggah pembaruan (.xlsx)"** — siapa pun yang
membuka dashboard bisa mengunggah file Excel bulan berikutnya (format kolom
sama seperti `Update_Rekap_RKP_1.xlsx`) langsung dari browser, tanpa perlu
mengubah kode atau deploy ulang. Kolom `Realisasi Biaya <Bulan>` dan
`Realisasi Fisik <Bulan>` terdeteksi otomatis apa pun nama bulannya.

## Menyalakan riwayat bulanan (opsional, langkah lanjutan)

Saat ini data hanya berisi satu periode realisasi (April). Jika ke depan Anda
menyimpan file per bulan, cara termudah membuat dashboard punya kurva-S
bulanan sungguhan adalah menggabungkan seluruh file bulanan menjadi satu tabel
dengan kolom tambahan `bulan`, lalu menambahkan filter/agregasi bulanan di
`app.py`. Beri tahu saya jika Anda ingin dibuatkan versi tersebut.
