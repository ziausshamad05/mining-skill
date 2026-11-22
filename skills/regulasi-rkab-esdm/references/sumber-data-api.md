# Sumber Data / "API" Peraturan ESDM

Tidak ada API publik terdokumentasi untuk JDIH ESDM maupun JDIH BPK. Yang tersedia adalah pola URL
yang stabil; `scripts/jdih_fetch.py` membungkusnya. Urutan prioritas sumber:

| Prioritas | Portal | Kekuatan | Kelemahan |
|---|---|---|---|
| 1 | **JDIH ESDM** `jdih.esdm.go.id` | Sumber primer (pemrakarsa), termasuk Kepmen & abstrak | Sering maintenance; nama file PDF tidak seragam; Kepmen teknis kadang tidak diunggah |
| 2 | **JDIH BPK** `peraturan.bpk.go.id` | Metadata rapi, **status peraturan** (mencabut/diubah), abstrak, PDF | Umumnya tanpa Kepmen/SE; bisa memblokir klien otomatis (HTTP 403) |
| 3 | **peraturan.go.id** (Kemenkum) | PDF dengan nama terprediksi `/files/<jenis>-no-<n>-tahun-<t>.pdf` | Hanya peraturan yang diundangkan; tanpa status |
| 4 | **jdihn.go.id** (BPHN) | Agregator nasional | Lambat |

## Pola URL

### JDIH BPK
- Pencarian: `https://peraturan.bpk.go.id/Search?keywords=<kata>&tentang=&nomor=<n>&tahun=<t>&jenis=<id>&entitas=<id>&p=<halaman>`
  (parameter `jenis`, `tahun`, `entitas`, `tema`, `p` terkonfirmasi dipakai situs; `keywords`/`tentang`/`nomor` mengikuti form pencarian – bila hasil kosong, pakai `--url` dengan URL dari browser).
- Detail: `https://peraturan.bpk.go.id/Details/<id>/<slug>` contoh `Details/350283/permen-esdm-no-17-tahun-2025`.
- PDF: `https://peraturan.bpk.go.id/Download/<fileId>/<nama-file>.pdf` (diambil dari halaman Detail).
- Struktur halaman Detail: label metadata (Tipe Dokumen, Judul, T.E.U., Nomor, Bentuk, Bentuk Singkat, Tahun, Tempat/Tanggal Penetapan, Tanggal Pengundangan, Tanggal Berlaku, Sumber, Subjek, Status, Bahasa, Lokasi, Bidang) lalu blok **STATUS PERATURAN** (Mencabut / Dicabut dengan / Mengubah / Diubah dengan).
- `jenis=147` menampilkan Permen ESDM (teramati dari hasil pencarian). Verifikasi ID jenis lain di browser sebelum dipakai.

### JDIH ESDM
- PDF: `https://jdih.esdm.go.id/storage/document/<Nama File>.pdf` (spasi di-encode `%20`; contoh `Permen ESDM Nomor 10 Tahun 2023.pdf`, `ABSTRAK PERMEN ESDM NO 10 THN 2023.pdf`).
- Detail (versi baru): `https://jdih.esdm.go.id/dokumen/view?id=<n>`; (versi lama): `https://jdih.esdm.go.id/index.php/web/result/<n>/detail`.
- Halaman maintenance berjudul "SISTEM SEDANG DALAM PERBAIKAN" – skrip mendeteksinya dan menyarankan BPK/peraturan.go.id.

### peraturan.go.id
- `https://www.peraturan.go.id/files/permen-esdm-no-17-tahun-2025.pdf` (terverifikasi). Format lama memakai nama Berita Negara, mis. `bn725-2017.pdf`, `pp7-2017bt.pdf`.

## Resep pemakaian

```bash
S=skills/regulasi-rkab-esdm/scripts
python3 $S/jdih_fetch.py catalog --topik rkab                 # peta regulasi yang sudah dikurasi
python3 $S/jdih_fetch.py detail 350283                         # metadata + status Permen 17/2025
python3 $S/jdih_fetch.py search "pertambangan mineral batubara" --tahun 2026 --jenis 147
python3 $S/jdih_fetch.py guess permen-esdm 6 2026              # URL kandidat lintas portal
python3 $S/jdih_fetch.py download 350280 --out regulasi/       # PDF + manifest SHA-256
python3 $S/jdih_fetch.py extract regulasi/<file>.pdf           # .txt + .pasal.json
python3 $S/jdih_fetch.py pasal regulasi/<file>.pasal.json 5 34A
python3 $S/jdih_fetch.py pasal regulasi/<file>.pasal.json --grep "jaminan reklamasi"
```

Variabel lingkungan: `JDIH_CACHE` (lokasi cache, default `~/.cache/jdih_fetch`). Proxy HTTP(S)
mengikuti `HTTPS_PROXY` otomatis.

## Bila jaringan/portal menolak
1. Coba sumber berikutnya di tabel prioritas (`guess`).
2. Gunakan browser (Claude in Chrome / built-in browser) untuk membuka halaman dan mengunduh PDF, lalu `extract` secara lokal.
3. Jangan menembus captcha/login, jangan memakai cermin tidak resmi sebagai dasar kutipan. Catat URL resmi & tanggal akses pada setiap kutipan.

## Etika & legal
- Peraturan perundang-undangan bukan objek hak cipta (UU 28/2014 Pasal 42), tetapi tampilan & metadata portal tetap milik pengelola: gunakan jeda permintaan, cache, dan atribusi sumber.
- Simpan manifest (URL, waktu akses, SHA-256) untuk jejak audit.
