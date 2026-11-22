# Format baku gambar & laporan perencanaan jalan tambang

Format ini dipakai `haul_road.py` (paket gambar: `sheets_jalan.py`; laporan: `laporan_jalan.py`). Susunannya mengikuti
paket gambar perencanaan jalan yang lazim (gaya plan production Civil 3D) dan ketentuan Kepmen ESDM 1827 K/30/MEM/2018.

## A. Paket gambar `gambar_perencanaan_jalan.pdf`
| Urutan | Lembar | Isi |
|---|---|---|
| 1 | Peta situasi trase & indeks lembar | Seluruh trase, patok tiap 100 m, label tiap 500 m, kontur, batas galian/timbunan, kotak cakupan tiap lembar plan & profile (bernomor), DESIGN SPEED |
| 2..n | Plan & profile | Atas: denah diputar agar trase mendatar (viewport), label STA dalam kotak putih tiap `interval_label_sta_m`, ticks tiap `interval_data_profil_m`, garis penampang, tepi jalur, saluran, tanggul, daylight, kontur, grid UTM, data tikungan (PI, R, Δ, L, e, W), MATCH LINE. Bawah: profil (EG merah, FG biru putus), arsir galian merah/timbunan hijau, label GRADE BREAK STA/ELEV (atau PVI + L lengkung), label grade %, pita data 3 baris (EXISTING ELEVATIONS / PROPOSED ELEVATIONS / STATION) |
| n+1 | Penampang jalan (tipikal) | Template dengan dimensi: lebar jalur, crown %, saluran, tanggul (tinggi), lereng galian (merah) & timbunan (hijau) beserta jenjang & rasio H:V |
| ... | Penampang melintang | `penampang_per_lembar` penampang tiap lembar pada interval `interval_penampang_lembar_m`: kotak STA, tabel *Material(s) at Station* (Ground Cut/Fill: Area, Volume, Cumulative Volume), label OFF/ELEV di daylight & CL, pita data EXISTING / PROPOSED ELEVATIONS / OFFSET, skala per penampang |
| akhir | Total Volume Table | Station, Fill Area, Cut Area, Fill Volume, Cut Volume, Cumulative Fill/Cut Vol |

### Panjang lembar plan & profile (berparameter)
`panjang per lembar (m) = (lebar area gambar mm − 34 mm kolom label) × skala_horizontal / 1000`.
Contoh A3 @ 1:2.000 ≈ 530 m; A3 @ 1:1.000 ≈ 265 m; A1 @ 1:2.000 ≈ 1.150 m. Lembar berurutan tumpang tindih `overlap_m`.
Skala vertikal profil dimulai dari `skala_vertikal` dan otomatis dinaikkan ke skala standar berikutnya bila beda tinggi
tidak muat; skala aktual dicetak di lembar. Skala penampang dimulai dari `skala_penampang` dengan aturan yang sama.

### Informasi tepi (kolom kanan setiap lembar)
1. Kop: nama perusahaan, nomor IUP, lokasi, nama proyek (opsional logo).
2. Judul gambar.
3. Peta indeks/lokasi: seluruh trase dengan segmen lembar disorot.
4. Legenda.
5. Informasi teknis: sistem koordinat (default UTM Zona 51S WGS 84 / EPSG:32751), sumber topografi, kecepatan rencana,
   unit terbesar, skala numerik + skala batang, arah utara (ikut rotasi viewport).
6. Catatan kriteria Kepmen ESDM 1827 (lebar, tanggul, cross fall, grade, tikungan) dengan nomor halaman.
7. Kolom pengesahan: Digambar / Diperiksa / Disetujui (KTT), nama dan tanggal.
8. Nomor gambar, lembar x/y, revisi, tanggal.

Dasar yang dapat dikutip:
- Kepmen 1827 hal. 50: peta topografi skala 1:2.000, akurasi 1 m → default `skala_horizontal` = 2000.
- Kepmen 1827 hal. 99-100: kriteria jalan yang dicetak di catatan setiap lembar.
- Pengesahan oleh KTT: Permen ESDM 26/2018 dan Kepmen 1827 Lampiran I (tanggung jawab KTT atas kaidah teknik).
- Format peta resmi WIUP/WIUPK ada di Kepmen ESDM 1798 K/30/MEM/2018 Lampiran IV (berupa halaman pindaian). Bila
  instansi meminta tata letak itu persis, cocokkan elemen di atas dengan lampiran asli; semua teks/urutan informasi tepi
  dapat diubah lewat `lembar.*` **[verifikasi terhadap Lampiran IV asli]**.

## B. Laporan `laporan_perencanaan_jalan.(pdf|docx|md)`
Halaman judul → Lembar pengesahan (KTT) → Daftar isi →
BAB 1 Pendahuluan (latar belakang, maksud & tujuan, lokasi & lingkup + gambar situasi, dasar acuan) →
BAB 2 Data & asumsi (topografi, unit angkut terbesar, parameter desain, asumsi; data demo ditandai) →
BAB 3 Kriteria desain (tabel Kepmen dengan halaman + praktik rekayasa) →
BAB 4 Hasil perencanaan (alinyemen horizontal, vertikal + JPH + lengkung vertikal, penampang, drainase, perkerasan,
kestabilan lereng FK/PoF, volume + mass-haul + 3D) →
BAB 5 Pemeriksaan kepatuhan (tabel item | nilai | syarat | status | dasar) →
BAB 6 Kesimpulan & rekomendasi (perbaikan otomatis untuk butir TIDAK MEMENUHI + pengendalian K3 & pemantauan) →
Lampiran (daftar gambar bernomor, daftar berkas digital).
