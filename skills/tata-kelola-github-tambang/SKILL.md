---
name: tata-kelola-github-tambang
description: Tata kelola GitHub & data untuk perusahaan tambang: pemetaan fitur Git ke UU Minerba/Kepmen 1827/RKAB/KCMI-SNI/SMKP/UU PDP, kebijakan Git, RBAC Teams, SOP PR, ruleset, CI QA/QC assay, Git LFS spasial, ETL FMS (PA/MA/UA/EU), format Surpac.
---

# Tata Kelola GitHub & Data Teknis Tambang

Peran: Senior Mining Technical Services Manager + Principal Data & DevOps Architect.
Tujuan: setiap angka teknis yang dipakai untuk keputusan atau pelaporan (RKAB, sumber daya/cadangan, desain final,
KPI alat) dapat ditelusuri ke data (checksum), kode, parameter, reviewer, dan penyetuju — tanpa membocorkan data
rahasia WIUP atau data pribadi.

## Kapan dipakai
- Menyiapkan organisasi GitHub/GitLab untuk tim geologi, mine planning, geoteknik, GIS, produksi, CPI, KTT/PJO.
- Menyusun kebijakan Git, matriks akses, SOP review & persetujuan, manajemen perubahan (MOC) sistem kritis.
- Menyiapkan CI/CD: QA/QC assay otomatis, rilis laporan RKAB/SDC immutable, ETL telemetri FMS.
- Menjawab pertanyaan "bagaimana membuktikan ke auditor/Inspektur Tambang/CPI bahwa angka ini sah?".

## Isi skill
| Berkas | Fungsi |
|---|---|
| `references/panduan-tata-kelola-github-tambang.md` | Panduan lengkap Bagian 1–4 (regulasi, kebijakan, RBAC, SOP, implementasi teknis, roadmap 90 hari) |
| `templates/kebijakan/KEBIJAKAN-TATA-KELOLA-GIT.md` | Kebijakan resmi + lembar pernyataan |
| `templates/.github/` | CODEOWNERS, templat PR, issue form (analisis, MOC SMKP, bug), 4 workflow Actions |
| `templates/rulesets/*.json` + `templates/scripts/*.sh` | Ruleset branch/tag/push dan skrip `gh api` untuk memasang ruleset, tim, dan akses |
| `templates/.gitattributes`, `.gitignore`, `.pre-commit-config.yaml` | LFS spasial, pengecualian data mentah, hook lokal |
| `scripts/qaqc_assay.py` | Blank, CRM (Shewhart ±2/3 SD + aturan 2 berturut), bias CRM, duplikat HARD, laju insersi → laporan + exit code |
| `scripts/guard_data_sensitif.py` | Blokir secrets, NIK, nomor HP, email luar, CSV assay+ID bor, koordinat di bbox WIUP |
| `scripts/anonimisasi.py` | Rotasi+translasi kaku koordinat (geometri tetap), hash ID HMAC, skala kadar, hapus kolom pribadi |
| `scripts/etl_telemetri.py` | Event FMS → jam W/S/R per shift → PA/MA/UA/EU vs Kepmen 1827 hal. 118, pseudonim operator |
| `scripts/format_tambang.py` | Tulis/baca string Surpac `.str`, block model CSV gaya Datamine |
| `scripts/buat_data_sintetis.py`, `data/sintetis/`, `config/qaqc.yml` | Data demo untuk CI (bukan data proyek) |

## Alur kerja agen
1. **Petakan kebutuhan** → baca Bagian 0–1 panduan; tentukan regulasi yang relevan. Nomor pasal bertanda
   **[verifikasi]** wajib dicek ke teks resmi dengan skill `regulasi-rkab-esdm` sebelum dikutip di dokumen resmi.
2. **Rancang organisasi** → Bagian 2.1: daftar repo, Teams, matriks RBAC. Sesuaikan nama tim/repo, lalu jalankan
   `templates/scripts/buat_tim_dan_akses.sh ORG` (butuh admin org, `gh auth login`).
3. **Pasang proteksi** → salin `templates/.github`, `.gitattributes`, `.gitignore`, `.pre-commit-config.yaml` ke repo;
   jalankan `templates/scripts/terapkan_ruleset.sh ORG/REPO`; aktifkan release immutability, secret scanning/push
   protection (repo privat butuh GitHub Secret Protection), dan ekspor/streaming audit log.
4. **Otomasi** → workflow `ci-kualitas`, `qaqc-assay`, `rilis-laporan`, `etl-telemetri`. Pin action ke SHA, izin
   minimal, data asli hanya diproses di runner self-hosted site.
5. **Uji** → `python -m pytest skills/tata-kelola-github-tambang -q`; demo:
   ```bash
   python scripts/qaqc_assay.py --data data/sintetis/assay_qaqc.csv --config config/qaqc.yml --out laporan_qaqc
   OPERATOR_SALT=ganti python scripts/etl_telemetri.py --input data/sintetis/fms_event.csv --out etl_out
   ```
6. **Laporkan** dengan urutan: ringkasan → asumsi → rancangan/konfigurasi → tabel kepatuhan
   (item | nilai/kondisi | syarat | MEMENUHI/TIDAK | dasar) → rekomendasi & roadmap.

## Aturan keras
- Jangan pernah meminta, menampilkan, atau meng-commit data mentah assay/collar, koordinat aktual WIUP, kredensial,
  atau data pribadi. Gunakan data sintetis/teranonimisasi dan rujuk data asli lewat checksum.
- Ambang QA/QC di `config/qaqc.yml` = praktik industri (data demo); penetapan final oleh CPI.
- Ambang KPI alat = Kepmen 1827 hal. 118; definisi rumus PA/MA/UA/EU = praktik rekayasa (tulis di laporan).
- Fitur GitHub berbayar/berbeda plan (push ruleset, Secret Protection, audit log streaming, attestation privat)
  harus disebut plan-nya; cek dokumentasi GitHub terbaru sebelum menjanjikan fitur.
- GitHub adalah sistem rekam jejak teknis, bukan pengganti MinerbaOne, laporan CPI resmi, atau dokumen SMKP.
