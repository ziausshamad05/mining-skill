---
name: regulasi-rkab-esdm
description: "Ambil teks peraturan resmi langsung dari JDIH ESDM, JDIH BPK, atau peraturan.go.id lalu olah per Pasal, dan pakai untuk kepatuhan RKAB Minerba (Permen ESDM 17/2025 jo. 6/2026, Kepmen 341.K/2025) maupun RKAB panas bumi. Gunakan saat diminta mencari/mengunduh/mengutip peraturan ESDM, mengecek status berlaku/dicabut, menyusun checklist prasyarat RKAB, memvalidasi matriks RKAB (produksi vs FS, keuangan, DMO), menjelaskan alur MinerbaOne, laporan triwulan, pencampuran batubara, atau kompetensi KTT/pengawas BPSDM ESDM."
---

# Regulasi & Kepatuhan RKAB ESDM (Minerba + Panas Bumi)

Skill ini punya dua kemampuan yang saling mengunci:

1. **Pengambil regulasi resmi** (`scripts/jdih_fetch.py`): cari, baca metadata & status, unduh PDF
   dengan manifest SHA-256, ubah ke teks, dan pecah per Pasal agar bisa dikutip/diolah sendiri.
2. **Penilai kepatuhan RKAB** (`scripts/rkab_validator.py` + `references/`): checklist prasyarat,
   tata waktu, struktur matriks, dan validasi angka, dengan dasar Pasal yang bisa ditelusuri.

Prinsip: **kutip dari teks resmi yang diambil hari ini, bukan dari ingatan.** Bila belum bisa
mengambil teks, tandai butir sebagai `[verifikasi]`.

## Peta file
| File | Isi | Kapan dibaca |
|---|---|---|
| `references/dasar-hukum-dan-alur.md` | Hierarki regulasi, perubahan kunci, tata waktu, prasyarat Pasal 5, alur MinerbaOne, Permen 6/2026 | Setiap pertanyaan RKAB Minerba |
| `references/struktur-matriks.md` | 9 matriks, isian minimum, aturan validasi silang | Meninjau draf matriks/Excel |
| `references/panas-bumi-dan-kompetensi.md` | RKAB panas bumi (EBTKE), KTT/POP/POM/POU, CPI, praktik GitHub | Panas bumi, SDM, otomasi |
| `references/sumber-data-api.md` | Pola URL JDIH ESDM/BPK/peraturan.go.id, resep CLI, fallback | Sebelum mengambil regulasi |
| `references/katalog_regulasi.json` | Katalog regulasi RKAB terkurasi + ID BPK | Titik awal pencarian |
| `templates/rkab_ringkasan_template.csv` | Format input validator | Saat memvalidasi angka |

## Alur kerja

### 1. Ambil & verifikasi regulasi (selalu lebih dulu untuk klaim hukum)
```bash
S=<path skill>/scripts
python3 $S/jdih_fetch.py catalog --topik rkab
python3 $S/jdih_fetch.py detail 350283            # status Permen 17/2025 (Diubah dengan …)
python3 $S/jdih_fetch.py download 350280 --out regulasi/
python3 $S/jdih_fetch.py extract regulasi/<file>.pdf
python3 $S/jdih_fetch.py pasal regulasi/<file>.pasal.json 5 6 19 34A
```
- Jika portal menolak (403/maintenance/jaringan dibatasi): jalankan `guess <jenis> <nomor> <tahun>`
  untuk sumber cermin, atau buka halaman lewat browser dan unduh manual, lalu `extract`.
- Jika sandbox tidak punya akses jaringan ke `.go.id`, katakan itu terus terang, gunakan
  WebFetch/WebSearch untuk metadata, dan minta pengguna melampirkan PDF bila perlu teks penuh.
- Selalu cek blok **STATUS PERATURAN** (Mencabut / Diubah dengan / Dicabut dengan) sebelum
  menyatakan suatu aturan berlaku. Contoh: Permen 10/2023 & 15/2024 sudah dicabut Permen 17/2025.

### 2. Jawab pertanyaan regulasi
- Rujuk Pasal & ayat dari `.pasal.json`; sertakan URL sumber dan tanggal akses dari manifest.
- Bedakan: **syarat tertulis** (Pasal 5) vs **praktik evaluator** vs **wacana** (mis. KSWP pajak).
- Minerba → Permen 17/2025 jo. 6/2026 + Kepmen 341.K/MB.01/MEM.B/2025. Panas bumi → rezim EBTKE
  (PP 7/2017 dst.), bukan MinerbaOne.

### 3. Checklist prasyarat sebelum submit (Minerba)
Gunakan daftar Pasal 5 di `dasar-hukum-dan-alur.md` §4 sesuai tahap (Eksplorasi: 5 syarat; OP:
administratif OSS, laporan SDC oleh competent person, PNBP lunas, peta digital termasuk tumpang
tindih kawasan hutan, KTT, Jamrek OP 1 tahun sebelumnya, produksi & lokasi ≤ FS dan dokumen
lingkungan, kesesuaian dengan kebutuhan pasar nasional untuk logam & batubara).

Selalu ingatkan risiko penolakan utama: **tunggakan PNBP, Jamrek tahun sebelumnya belum
ditempatkan, KTT belum disahkan, produksi melebihi FS, bukaan di kawasan hutan tanpa PPKH**, dan
tenggat **1 Okt – 15 Nov**.

### 4. Validasi matriks / Excel pengguna
1. Petakan file pengguna ke `templates/rkab_ringkasan_template.csv` (pandas/openpyxl). Catat
   sheet/sel asal setiap angka.
2. `python3 $S/rkab_validator.py ringkasan.csv --tanggal YYYY-MM-DD` (atau `--json`).
3. Kode keluar 1 = ada temuan KRITIS. Laporkan temuan berikut asal selnya.
4. Persentase DMO, tarif royalti, HBA/HPM: ambil dari Kepmen yang berlaku via `jdih_fetch.py`;
   jangan mengisi dari ingatan.

### 5. Laporan berkala & pencampuran batubara
- Laporan triwulanan (Pasal 19 jo. Permen 6/2026) mencakup juga pelaksanaan pencampuran batubara
  bagi pemegang persetujuan. Tenggat hari setelah triwulan → kutip dari teks Pasal yang diunduh.
- Pencampuran butuh persetujuan Menteri (Pasal 34A) dengan lampiran kontrak & uji kualitas
  surveyor; pedoman teknis lewat Kepmen (Pasal 34B) – cari Kepmen terbitannya.

## Format output
Tinjauan kepatuhan selalu berbentuk tabel:

| No | Status (KRITIS/PERHATIAN/OK/INFO) | Temuan | Dasar Regulasi (Pasal) | Rekomendasi Perbaikan |

Lalu: ringkasan 1–2 kalimat, daftar butir `[verifikasi]`, dan **Sumber** (URL resmi + tanggal akses).

## Anti-pola
- Mengutip Permen 10/2023 / RKAB 3 tahunan sebagai aturan berlaku.
- Menyatakan angka tenggat/tarif/persentase tanpa teks Pasal atau Kepmen yang diambil.
- Memakai MinerbaOne/Permen 17/2025 untuk panas bumi.
- Menyamakan "persetujuan otomatis" dengan jaminan: hanya berlaku bila permohonan **lengkap**.
- Menembus captcha/login portal atau memakai cermin tidak resmi sebagai dasar kutipan.

> Skill ini alat bantu kepatuhan, bukan nasihat hukum dan bukan keputusan evaluator Ditjen
> Minerba/EBTKE. Teks resmi yang diundangkan dan surat persetujuan adalah otoritas.
