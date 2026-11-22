# Struktur Matriks RKAB & Validasi Data Wajib

Format resmi ada di lampiran **Kepmen ESDM 341.K/MB.01/MEM.B/2025** (matriks tahap Eksplorasi dan
Operasi Produksi). Struktur di bawah adalah peta kerja untuk menyiapkan data dan memeriksa
konsistensi; nama kolom persis harus mengikuti formulir MinerbaOne/lampiran Kepmen yang berlaku.
RKAB mencakup tiga aspek: **pengusahaan, teknik, dan lingkungan** (definisi Pasal 1).

## Matriks dan isian minimum

| # | Matriks | Isian minimum | Validasi silang |
|---|---|---|---|
| 1 | Eksplorasi & Sumber Daya/Cadangan | Rencana & realisasi eksplorasi (metode, jumlah titik bor, meter bor, luas), SD terukur/tertunjuk/tereka, cadangan terbukti/terkira, kadar/kualitas, CP penanda tangan | Cadangan ≥ total produksi sisa umur tambang; tanggal laporan CP terbaru |
| 2 | Studi Kelayakan & Konstruksi/Infrastruktur | Nomor persetujuan FS, kapasitas maksimum, sarana (jalan, jetty/tersus, stockpile, smelter), jadwal | Kapasitas FS = batas atas produksi |
| 3 | Penambangan/Produksi & Pengolahan/Pemurnian | Lokasi pit/blok, luas bukaan, overburden (BCM), stripping ratio, produksi ROM, produk olahan, recovery, konservasi (low grade, sisa) | Produksi ≤ FS & dok. lingkungan; lokasi dalam WIUP & sesuai FS; SR × produksi ≈ OB |
| 4 | Pemasaran & Penjualan | Volume & nilai penjualan domestik/ekspor, pembeli, HPM/HBA acuan, stok awal/akhir, **DMO** (batubara) | Penjualan ≤ produksi + stok awal; DMO ≥ persentase wajib; kebutuhan pasar nasional (logam & batubara) |
| 5 | Keselamatan Pertambangan (K3 & KO) | Program SMKP, audit internal SMKP, statistik kecelakaan, anggaran K3, pengawas operasional bersertifikat | Anggaran K3 > 0 pada OP; KTT & pengawas sesuai jenjang |
| 6 | Perlindungan Lingkungan, Reklamasi & Pascatambang | Rencana & realisasi reklamasi (ha), revegetasi, pengelolaan air asam tambang/air larian, Jamrek & Jampas yang ditempatkan, RKL-RPL | Luas reklamasi realistis vs luas bukaan; bukti Jamrek 1 tahun sebelumnya |
| 7 | PPM | Program sesuai cetak biru/rencana induk PPM, anggaran, lokasi desa sasaran | Konsisten dengan RIPPM yang disetujui |
| 8 | Tenaga Kerja & Belanja Barang/Jasa (TKDN) | Jumlah TK lokal/nasional/asing, biaya pelatihan, belanja barang/jasa dalam negeri, IUJP subkontraktor | IUJP kontraktor aktif; komposisi TKA sesuai izin |
| 9 | Keuangan & Asumsi Ekonomi | Pendapatan, biaya produksi per pos, investasi/capex, penerimaan negara (iuran tetap, royalti, PNBP lain, pajak), asumsi harga & kurs | **Total biaya = jumlah anggaran matriks teknis**; royalti ≈ tarif × nilai penjualan; asumsi harga konsisten dengan matriks penjualan |

## Aturan validasi angka (dipakai `rkab_validator.py`)
1. `produksi_rencana_ton ≤ kapasitas_fs_ton` dan `≤ kapasitas_dokumen_lingkungan_ton` → KRITIS bila dilanggar.
2. `penjualan_domestik + penjualan_ekspor ≤ produksi + stok_awal` → KRITIS bila dilanggar.
3. DMO: `penjualan_domestik / produksi ≥ dmo_persen_wajib` (isi persentase dari Kepmen DMO yang berlaku; tidak di-hardcode).
4. `total_biaya_matriks_keuangan` vs Σ(biaya eksplorasi, konstruksi, penambangan, pengolahan, pengangkutan/penjualan, K3/KO, lingkungan/reklamasi, pascatambang, PPM, tenaga kerja, umum) → KRITIS bila selisih > toleransi (default 0,5%).
5. Tahap OP dengan anggaran lingkungan, K3, atau PPM nol → PERHATIAN.
6. Semua matriks harus "Sudah Diisi" sebelum Kirim.

## Cara memakai untuk file Excel/CSV pengguna
- Jika pengguna mengunggah matriks lengkap (banyak sheet), ringkas dulu ke format `kunci,nilai`
  (`templates/rkab_ringkasan_template.csv`) dengan pandas/openpyxl, lalu jalankan validator.
- Selalu tampilkan angka sumber (sheet/sel) untuk setiap temuan agar bisa ditelusuri.
- Jangan menebak tarif royalti/HPM/HBA/DMO dari ingatan; ambil Kepmen/PP tarif terbaru via `jdih_fetch.py`.
