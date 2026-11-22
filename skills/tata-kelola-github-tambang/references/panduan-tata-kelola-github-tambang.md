# Panduan Penerapan Skill & Tata Kelola GitHub di Perusahaan Pertambangan

Versi 1.0 (November 2026) | Disusun untuk PT. Surya Saga Utama (nikel, Sultra) dan dapat diadaptasi untuk batubara & mineral lain.
Peran penyusun: Mining Technical Services + Data & DevOps Architecture.

> Status dokumen: pedoman internal. Nomor pasal yang bertanda **[verifikasi]** wajib dicocokkan ke teks resmi (JDIH ESDM /
> peraturan.bpk.go.id) dengan skill `regulasi-rkab-esdm` sebelum dikutip di dokumen yang diserahkan ke pemerintah.
> GitHub tidak menggantikan kewajiban pelaporan resmi (MinerbaOne, laporan CPI, laporan SMKP); GitHub adalah **sistem
> rekam jejak teknis** yang membuat setiap angka yang dilaporkan bisa ditelusuri ke data, kode, parameter, dan penyetujunya.

## Daftar isi
- Bagian 0. Prinsip dasar & peta regulasi
- Bagian 1. Regulasi, kepatuhan & keamanan data (governance)
  - 1.1 Pemetaan fitur GitHub ke kewajiban regulasi
  - 1.2 Draf Kebijakan Keamanan Git (Git Governance Policy)
- Bagian 2. Manajemen proyek & alur kerja tim (management)
  - 2.1 Arsitektur GitHub Organization, Teams, RBAC
  - 2.2 SOP alur kerja kolaborasi
- Bagian 3. Implementasi teknis & otomatisasi (technical)
  - 3.1 Geologi, 3.2 Mine Planning, 3.3 GIS & Geoteknik (Git LFS), 3.4 Operasional & Maintenance (ETL + CI/CD)
- Bagian 4. Roadmap implementasi 90 hari & KPI
- Lampiran: daftar templat siap pakai, glosarium, rujukan

---

## Bagian 0. Prinsip dasar

1. **Kode & parameter di Git, data mentah di sistem data.** Git menyimpan skrip, notebook (tanpa output), konfigurasi,
   parameter desain, laporan hasil, dan *hash/checksum* dataset — bukan basis data assay atau koordinat aktual.
2. **Setiap angka keputusan punya jejak:** commit (siapa, kapan, apa), Pull Request (alasan + review), tag/release
   (versi yang dipakai untuk laporan), dan artefak berchecksum.
3. **Pemisahan peran (four-eyes):** pembuat ≠ penyetuju. Untuk sumber daya/cadangan, penyetuju akhir adalah CPI; untuk
   sistem kritis keselamatan, penyetuju akhir adalah KTT/PJO melalui manajemen perubahan SMKP.
4. **Private by default, least privilege, secrets never in Git.**
5. **Reproducible:** dengan tag yang sama, data yang sama (dirujuk lewat checksum) dan lingkungan yang sama (lockfile/
   container), hasilnya harus identik.

### Peta regulasi yang dirujuk (status per November 2026)
| Regulasi / standar | Status & catatan |
|---|---|
| UU 4/2009 jo. UU 3/2020 jo. UU 2/2025 (Minerba) | UU 2/2025 = perubahan keempat, berlaku 19 Maret 2025; beberapa pasal sedang/sudah diuji di MK |
| Permen ESDM 26/2018 | Pelaksanaan kaidah pertambangan yang baik & pengawasan; status berlaku |
| Kepmen ESDM 1827 K/30/MEM/2018 | Pedoman kaidah teknik pertambangan yang baik; mengatur CP, PHE/ESD/EC mengacu SNI 4726:2019 / SNI 5015:2019 |
| Permen ESDM 17/2025 jo. Permen ESDM 6/2026 | RKAB tahunan, disampaikan melalui sistem informasi (MinerbaOne); pedoman teknis & matriks: Kepmen ESDM 341.K/MB.01/MEM.B/2025 |
| Permen ESDM 38/2014 + Kepdirjen Minerba 185.K/37.04/DJB/2019 | SMKP Minerba & juknis keselamatan pertambangan, penilaian, pelaporan SMKP |
| KCMI 2017, SNI 4726:2019 (mineral), SNI 5015:2019 (batubara) | KCMI 2017 wajib sejak 1 Nov 2019; CPI teregistrasi |
| JORC Code 2012 | Edisi berlaku; revisi JORC masih dalam proses (draf 2024–2025) |
| UU 27/2022 (PDP) | Berlaku penuh 17 Oktober 2024 (akhir masa transisi Pasal 74) |

---

## BAGIAN 1. REGULASI, KEPATUHAN & KEAMANAN DATA

### 1.1 Bagaimana fitur GitHub mendukung auditabilitas dan kepatuhan

#### Fitur inti dan nilai auditnya
| Fitur GitHub | Bukti audit yang dihasilkan |
|---|---|
| **Commit history** (+ commit bertanda tangan/verified) | Siapa mengubah apa, kapan, dan isi perubahan (diff). Tanda tangan GPG/SSH/S/MIME membuktikan identitas pembuat. |
| **Pull Request (PR)** | Alasan perubahan, diskusi, hasil uji otomatis, reviewer, persetujuan, dan waktu merge — catatan *management of change* digital. |
| **Branch protection / Rulesets** | Memaksa: wajib PR, jumlah approval, approval CODEOWNERS, status check lulus, commit bertanda tangan, larangan force-push/hapus. Ruleset dapat dilihat siapa pun yang punya akses baca → transparan bagi auditor. |
| **CODEOWNERS** | Menetapkan penanggung jawab teknis per folder (mis. folder `cadangan/` wajib disetujui CPI). |
| **Tag & Release (immutable)** | Mengunci versi yang dipakai untuk laporan resmi. Dengan *immutable releases*, tag dan aset rilis tidak bisa dipindah/dihapus/diganti setelah dipublikasikan, dan rilis mendapat *attestation* yang bisa diverifikasi. |
| **GitHub Actions** | Uji otomatis, QA/QC data, perhitungan ulang, pembuatan laporan & checksum yang dapat diulang. Log job tersimpan per run. |
| **Audit log organisasi** | Peristiwa admin/akses (perubahan izin, ruleset, anggota). Retensi di UI terbatas (umumnya ±6 bulan; event Git ±7 hari) → **wajib ekspor/streaming** ke penyimpanan perusahaan untuk retensi jangka panjang. |
| **Secret scanning & push protection** | Mencegah API key/kata sandi masuk repo. Untuk repo privat butuh add-on *GitHub Secret Protection* (Team/Enterprise). |
| **Push rulesets** (repo privat, plan Team ke atas) | Memblokir push yang memuat path terlarang (mis. `data/raw/**`, `*.assay.csv`) atau file melebihi ukuran tertentu di seluruh jaringan fork. |

#### a. UU Minerba, Permen ESDM 26/2018, Kepmen ESDM 1827 K/30/MEM/2018 (kaidah teknik pertambangan yang baik)
Kewajiban inti yang didukung: perencanaan & pelaksanaan teknis sesuai kaidah, keterlusuran dokumen teknis, tanggung jawab
KTT, dan dokumen yang siap diperiksa Inspektur Tambang.

| Kewajiban (ringkas) | Penerapan GitHub |
|---|---|
| Desain teknis (lereng, jalan, disposal, penyaliran) memenuhi kriteria Kepmen 1827 (mis. Tabel 1 FK/PoF hal. 57; jalan hal. 99–100) | Desain dibuat dengan skill `desain-pit-geoteknik` / `desain-jalan-tambang`; tabel kepatuhan otomatis menjadi **status check wajib** di PR. PR tidak bisa di-merge bila ada butir "TIDAK MEMENUHI" tanpa label `pengecualian-kajian-teknis` + persetujuan KTT. |
| Pengesahan oleh KTT | CODEOWNERS folder `desain/final/` = tim `ktt-pjo`; rilis desain final (`desain-2026.11-v1`) hanya dibuat oleh peran Maintain tim KTT. |
| Dokumen siap diperiksa Inspektur Tambang | Release berisi PDF gambar + laporan + LandXML/DXF + `MANIFEST.sha256`; tautan release dicantumkan di dokumen fisik. |
| Perubahan desain di lapangan | Setiap revisi = PR baru dengan referensi issue MOC; riwayat revisi gambar (Rev 0, 1, 2) = tag berurutan. |

#### b. RKAB (Permen ESDM 17/2025 jo. 6/2026; Kepmen ESDM 341.K/MB.01/MEM.B/2025)
RKAB kini tahunan dan disampaikan lewat sistem informasi; matriks RKAB berisi angka produksi, cadangan, rencana tambang,
dan biaya. Risiko utama: angka di matriks tidak bisa ditelusuri ke model yang menghasilkannya.

Penerapan:
1. Repo `rkab-<tahun>` berisi skrip perhitungan matriks (produksi, SR, kualitas, neraca cadangan), parameter, dan
   *referensi* ke versi block model/pit desain (tag repo lain + checksum file data).
2. Saat matriks final siap diunggah ke MinerbaOne: buat **release immutable** `rkab-2027-v1` (draft → lampirkan aset →
   publish). Aset: matriks XLSX hasil skrip, PDF lampiran teknis, `MANIFEST.sha256`, `environment.lock`.
3. Revisi RKAB (evaluasi/penyesuaian) = `rkab-2027-v2` dengan PR yang menjelaskan perubahan angka (tabel delta otomatis
   dari Actions).
4. Cocokkan nomor versi release dengan nomor/tanggal pengajuan di MinerbaOne dalam catatan release.

#### c. KCMI 2017, JORC 2012, SNI 4726:2019 & SNI 5015:2019 — validasi Competent Person Indonesia (CPI)
Kode pelaporan menuntut **transparansi, materialitas, kompetensi**: CP harus bisa menjelaskan data, metode, asumsi, dan
faktor pengubah. Kepmen 1827 mensyaratkan PHE/ESD/EC dilakukan CP dengan acuan SNI 4726:2019/5015:2019.

| Kebutuhan kode pelaporan | Penerapan GitHub |
|---|---|
| Keterlusuran data (sampling, QA/QC, database) | Repo `geologi-qaqc`: skrip QA/QC (blank, CRM, duplikat) + laporan bulanan sebagai artefak; dataset dirujuk lewat checksum, bukan diunggah. |
| Metode estimasi & parameter (variogram, search, domain) | Notebook geostatistik (output dibersihkan) + file parameter YAML; setiap perubahan parameter = PR. |
| Tanggung jawab CP | CODEOWNERS: `estimasi/**` & `cadangan/**` → tim `cpi`; ruleset mewajibkan approval CODEOWNERS; CPI menyetujui PR dengan akun pribadi terverifikasi (2FA + commit/approval tercatat). |
| Pernyataan sumber daya/cadangan per tanggal efektif | Release `sdc-2026-06-30` (immutable) berisi tabel klasifikasi + JORC/KCMI Table 1 (checklist) + laporan CP. |
| Audit/review independen | Reviewer eksternal diberi akses **Read** sementara (outside collaborator) ke repo/tag tertentu; akses dicabut otomatis setelah tanggal berakhir. |

#### d. SMKP Minerba (Permen ESDM 38/2014; Kepdirjen 185.K/37.04/DJB/2019) — manajemen perubahan sistem kritis
Sistem kritis: radar/prism pemantauan lereng, piezometer, alarm ambang geoteknik, *fleet management system* (FMS),
proximity/collision avoidance, dispatch, konfigurasi peledakan. Perubahan konfigurasi/kode di sini harus melalui
pengelolaan perubahan SMKP (identifikasi bahaya, penilaian risiko, persetujuan, komunikasi, verifikasi) **[verifikasi
sub-elemen dan formulir MOC sesuai juknis 185/2019 dan prosedur internal SMKP]**.

Penerapan GitHub sebagai MOC digital:
1. **Issue form "Permintaan Perubahan (MOC)"** wajib diisi: sistem terdampak, alasan, penilaian risiko (5x5), rencana
   uji, rencana rollback, waktu henti, pihak yang diberitahu.
2. Branch `feature/MOC-<no>-...` → PR yang menautkan issue MOC.
3. Ruleset repo `sistem-kritis-*`: 2 approval (teknis + K3), approval CODEOWNERS `ktt-pjo`, status check uji simulasi
   lulus, commit bertanda tangan, larangan force-push.
4. **GitHub Environments** `produksi` dengan *required reviewers* (KTT/PJO) dan jendela deploy; deploy tercatat per run.
5. Setelah go-live: release + verifikasi lapangan dicatat di issue; issue ditutup = MOC selesai.
6. Ambang alarm geoteknik (mis. kecepatan deformasi) disimpan sebagai file konfigurasi bertipe (YAML) dengan uji
   otomatis rentang wajar — mencegah salah ketik satuan.

#### e. UU 27/2022 (PDP) dan kerahasiaan data WIUP
- Data pribadi di lingkungan tambang: identitas karyawan/operator di FMS, data fatigue/kesehatan, NIK, nomor HP, data
  pemilik lahan/PPM, foto wajah. Pemrosesan wajib punya dasar, dibatasi tujuan, diamankan, dan tercatat.
- Data rahasia perusahaan/negara: koordinat aktual batas & titik bor WIUP, assay mentah, model sumber daya, kontrak,
  harga. Data eksplorasi juga merupakan data yang wajib dilaporkan ke pemerintah — perlakukan sebagai **RAHASIA**.
- Kontrol GitHub: repo privat/internal saja, klasifikasi data di README, `guard_data_sensitif.py` (pre-commit + CI)
  memblokir NIK/telepon/email/koordinat dalam batas WIUP/kolom assay, push ruleset memblokir path data mentah,
  anonimisasi untuk berbagi, ekspor audit log, prosedur insiden (rotasi kredensial, penghapusan riwayat, notifikasi).

### 1.2 Draf Kebijakan Keamanan Git (Git Governance Policy)
Teks kebijakan lengkap siap tanda tangan: `templates/kebijakan/KEBIJAKAN-TATA-KELOLA-GIT.md`. Ringkasan aturan wajib:

**A. Klasifikasi data**
| Kelas | Contoh | Boleh di GitHub? |
|---|---|---|
| PUBLIK | materi presentasi publik, kode open-source tanpa data | Ya (repo publik hanya dengan persetujuan Manajemen) |
| INTERNAL | skrip, SOP, templat, parameter generik | Ya, repo privat/internal |
| RAHASIA | assay mentah, collar/survey bor, koordinat aktual WIUP, block model, cadangan sebelum rilis, data FMS beridentitas | **Tidak** (kecuali checksum/metadata, atau versi teranonimisasi yang disetujui) |
| SANGAT RAHASIA | kredensial, kunci API, data pribadi sensitif (kesehatan), kontrak & harga | **Tidak pernah** |

**B. Larangan**
1. Dilarang mengunggah data mentah assay, collar, survey, downhole, sampel QA/QC asli, koordinat aktual titik bor/batas
   WIUP, block model produksi, dan ekspor FMS beridentitas operator.
2. Dilarang menyimpan kata sandi, token, API key, string koneksi, sertifikat, file `.env` di repo (termasuk riwayat).
3. Dilarang membuat repo **publik** atau menjadikan repo publik tanpa persetujuan tertulis Manajemen + Data Owner.
4. Dilarang memakai akun GitHub pribadi tanpa keanggotaan organisasi untuk pekerjaan perusahaan; dilarang fork ke akun
   pribadi (setting organisasi: forking repo privat dimatikan).
5. Dilarang force-push/rewrite riwayat branch terlindungi; dilarang bypass ruleset kecuali prosedur darurat tercatat.
6. Dilarang menempel data rahasia ke issue/PR/discussion/AI assistant eksternal.

**C. Kewajiban**
1. 2FA wajib; SSO perusahaan bila tersedia; commit signing wajib di branch `main`/`staging`.
2. Pre-commit hook wajib (gitleaks/secret scan, guard data sensitif, nbstripout, batas ukuran file).
3. Secrets hanya di GitHub Actions Secrets/Environments atau vault perusahaan; rotasi ≤ 90 hari dan segera bila bocor.
4. Data untuk uji/CI memakai **data sintetis atau teranonimisasi** (`anonimisasi.py`: geser+rotasi koordinat dengan kunci
   rahasia, hash ID lubang bor, pembulatan/derau kadar terkontrol); kunci anonimisasi tidak disimpan di repo.
5. Setiap repo memiliki README berisi: pemilik data, klasifikasi, sumber data (sistem & checksum), cara reproduksi.
6. Kontraktor: akses waktu terbatas (outside collaborator), NDA, hanya repo terkait, review akses tiap bulan.
7. Insiden (kebocoran secret/data): lapor ≤ 1 jam ke Security Lead; rotasi kredensial; hapus dari riwayat
   (`git filter-repo`) dan minta GitHub Support membersihkan cache; catat di register insiden; evaluasi kewajiban
   notifikasi berdasarkan UU PDP.
8. Offboarding: hapus dari organisasi pada hari terakhir; audit PAT/SSH key/OAuth app.
9. Audit log diekspor/streaming ke penyimpanan perusahaan dengan retensi minimal sesuai kebijakan arsip (disarankan ≥ 5
   tahun untuk dokumen teknis & cadangan) **[sesuaikan kebijakan retensi arsip perusahaan]**.

---

## BAGIAN 2. MANAJEMEN PROYEK & ALUR KERJA TIM

### 2.1 Arsitektur GitHub Organization
**Plan yang disarankan:** GitHub Team (minimum: rulesets repo privat, push rulesets, CODEOWNERS wajib, Secret
Protection dapat dibeli). GitHub Enterprise Cloud bila perlu: SAML SSO/EMU, audit log streaming, ruleset tingkat
enterprise, artifact attestation untuk repo privat, IP allow list.

**Struktur organisasi** `ssu-mining` (satu organisasi, repo dinamai `<domain>-<topik>`):
```
ssu-mining/
├── .github                    # profil org, templat issue/PR default, workflow reusable
├── tatakelola-kebijakan       # kebijakan, SOP, register risiko, register akses
├── geologi-qaqc               # QA/QC assay, laporan bulanan
├── geologi-estimasi           # notebook geostatistik, parameter domain/variogram
├── sdc-pelaporan              # pernyataan sumber daya & cadangan (KCMI/SNI) — CPI
├── perencanaan-pit            # optimasi pit, desain jenjang, jadwal produksi
├── perencanaan-jalan          # desain jalan & ramp
├── rkab-2027                  # matriks RKAB + lampiran teknis
├── geoteknik-lereng           # analisis FK/PoF, ambang alarm radar/prism
├── gis-spasial                # batas IUP (teranonimisasi), drone/LiDAR via LFS
├── operasi-fms-etl            # ETL telemetri FMS, KPI PA/MA/UA/EU
├── maintenance-analitik       # analitik keandalan alat
├── sistem-kritis-alarm        # konfigurasi alarm geoteknik & FMS (MOC ketat)
└── mining-skill               # skill/alat bersama (repo ini)
```

**Teams (bersarang):**
```
@ssu-mining/semua-karyawan
 ├── eksplorasi-geologi     (anak: geologi-qaqc-officer, geostat)
 ├── mine-planning          (anak: planner-jangka-pendek, planner-jangka-panjang)
 ├── geoteknik-survei
 ├── gis
 ├── produksi-maintenance
 ├── data-devops            (platform engineering)
 ├── cpi                    (Competent Person Indonesia)
 ├── ktt-pjo                (KTT, PJO, pengawas operasional)
 ├── manajemen              (direksi, manajer teknik)
 └── auditor-eksternal      (sementara, read-only)
```

**Matriks RBAC (peran per repo)**
| Repo \ Team | Eksplorasi/Geologi | Mine Planning | Geoteknik/Survei | GIS | Produksi/Maint. | Data-DevOps | CPI | KTT/PJO | Manajemen | Auditor |
|---|---|---|---|---|---|---|---|---|---|---|
| geologi-qaqc | **Write** | Read | – | Read | – | Maintain | Read (approve) | Read | Read | Read* |
| geologi-estimasi | **Write** | Read | – | – | – | Maintain | **Maintain** | Read | Read | Read* |
| sdc-pelaporan | Write | Write | Read | – | – | Maintain | **Maintain** (CODEOWNER) | Read | Read | Read* |
| perencanaan-pit/jalan | Read | **Write** | Write | Read | Read | Maintain | Read | **Maintain** (CODEOWNER final) | Read | Read* |
| rkab-2027 | Write | **Write** | Write | Read | Write | Maintain | Read (approve cadangan) | **Maintain** | Read | Read* |
| geoteknik-lereng | – | Read | **Write** | Read | Read | Maintain | – | **Maintain** | Read | Read* |
| gis-spasial | Read | Read | Write | **Write** | Read | Maintain | – | Read | Read | – |
| operasi-fms-etl | – | Read | – | – | **Write** | **Maintain** | – | Read | Read | – |
| sistem-kritis-alarm | – | – | Write | – | Write | Write | – | **Maintain** (CODEOWNER, deploy reviewer) | Read | Read* |
| tatakelola-kebijakan | Read | Read | Read | Read | Read | Write | Read | Write | **Maintain** | Read |

Admin repo/organisasi: hanya 2–3 orang (Data-DevOps Lead + 1 cadangan dari Manajemen), bukan anggota harian.
`Read*` = akses sementara dengan tanggal berakhir. Peran Triage dipakai untuk koordinator proyek (kelola issue tanpa
menulis kode).

Prinsip: **Write** untuk pembuat, **Maintain** untuk pemilik domain/penyetuju, **Admin** sangat terbatas; persetujuan
final ditegakkan lewat **CODEOWNERS + ruleset**, bukan lewat peran Admin.

Templat siap pakai: `templates/scripts/buat_tim_dan_akses.sh` (gh api), `templates/.github/CODEOWNERS`.

### 2.2 SOP alur kerja kolaborasi (end-to-end)

**Strategi branch**
| Branch | Fungsi | Proteksi |
|---|---|---|
| `main` | versi yang **disetujui untuk keputusan operasional/pelaporan** | PR wajib, 2 approval (1 CODEOWNER), status check lulus, signed commit, linear history, larangan force-push/hapus |
| `staging` | integrasi & uji dengan data teranonimisasi/sintetis; review teknis | PR wajib, 1 approval, status check lulus |
| `feature/<issue>-<ringkas>` | pekerjaan harian | bebas, otomatis dihapus setelah merge |
| `hotfix/<issue>-<ringkas>` | perbaikan mendesak (mis. ambang alarm salah) | PR langsung ke `main` dengan approval KTT/PJO + backport ke `staging` |
| Tag `vYYYY.MM.patch`, `rkab-YYYY-vN`, `sdc-YYYY-MM-DD`, `desain-<nama>-revN` | versi terkunci | release immutable |

**Siklus kerja (10 langkah)**
1. **Inisiasi** — buat Issue dari templat (Permintaan Analisis / Permintaan Perubahan MOC / Bug). Wajib isi: tujuan,
   data yang dipakai (sistem sumber + checksum), klasifikasi data, risiko, tenggat, penyetuju.
2. **Triage** — koordinator memberi label (`disiplin:geologi`, `prioritas:tinggi`, `regulasi:rkab`, `smkp:moc`) dan
   memasukkan ke GitHub Projects (Kanban).
3. **Kanban kolom:** `Backlog → Siap Dikerjakan → Dikerjakan → Review Teknis → Persetujuan (CPI/KTT) → Siap Rilis →
   Selesai`. Field kustom: Disiplin, Tenggat regulasi, Penyetuju, Klasifikasi data, Nomor MOC.
4. **Pengerjaan** — buat branch `feature/123-qaqc-crm-oreas` dari `staging`; commit kecil, pesan jelas
   (`qaqc: tambah aturan 3SD untuk CRM OREAS-xxx (#123)`); pre-commit hook berjalan lokal.
5. **PR ke `staging`** — isi templat PR (ringkasan, dampak angka, checklist data & regulasi). Actions menjalankan lint,
   uji, guard data, QA/QC, dan memposting ringkasan hasil ke PR.
6. **Review teknis** — reviewer sejawat memeriksa logika, asumsi, unit, dan hasil uji; diskusi diselesaikan sebelum
   merge.
7. **PR `staging` → `main`** — wajib approval CODEOWNERS (CPI untuk estimasi/cadangan, KTT/PJO untuk desain & sistem
   kritis); untuk sistem kritis, tautkan issue MOC yang sudah disetujui.
8. **Rilis** — Maintainer membuat draft release dari tag, Actions melampirkan aset (laporan PDF, CSV, LandXML/DXF,
   `MANIFEST.sha256`), lalu publish (immutable).
9. **Pemakaian operasional** — dokumen/angka yang dipakai di lapangan atau dilaporkan wajib mencantumkan tag release.
   Deploy sistem kritis melalui Environment `produksi` dengan reviewer KTT/PJO.
10. **Penutupan & evaluasi** — issue ditutup dengan tautan release; retro bulanan memakai metrik (lead time, % PR lulus
   check pertama kali, insiden).

**Aturan code review (minimum)**
- Reviewer menjalankan ulang (atau melihat hasil Actions) dan memeriksa: satuan & datum koordinat (UTM 51S), konsistensi
  densitas/tonase, cut-off, faktor pengubah, ambang regulasi + halaman, kebocoran data.
- PR > 400 baris perubahan kode dipecah; notebook di-review sebagai file `.py` (jupytext) atau diff yang dibersihkan.
- Approval CPI/KTT dilakukan dengan akun pribadi bertanda tangan 2FA; approval atas nama orang lain dilarang.

---

## BAGIAN 3. IMPLEMENTASI TEKNIS & OTOMATISASI

### 3.1 Geologi — QA/QC assay & notebook geostatistik
**Struktur repo `geologi-qaqc`:**
```
geologi-qaqc/
├── config/qaqc.yml                # daftar CRM (nilai sertifikat, SD), batas blank, batas duplikat
├── scripts/qaqc_assay.py          # (templat tersedia)
├── data/README.md                 # sumber data + checksum; data asli TIDAK di-commit
├── data/sintetis/assay_qaqc.csv   # data uji sintetis untuk CI
├── reports/                       # diabaikan git; dibuat Actions sebagai artefak
└── .github/workflows/qaqc.yml
```
**Aturan QA/QC yang diotomatisasi (`templates/scripts/qaqc_assay.py`):**
| Kontrol | Aturan | Status |
|---|---|---|
| Blank | hasil ≤ batas (mis. 5–10 × batas deteksi) | GAGAL bila melewati |
| CRM/standar | Shewhart: dalam ±2SD = lulus; 2–3SD = peringatan; > 3SD atau 2 berturut-turut > 2SD di sisi sama = gagal batch | per batch |
| Bias CRM | rata-rata (hasil/sertifikat − 1) per CRM, peringatan bila > ±5% | tren |
| Duplikat (field/coarse/pulp) | HARD (half absolute relative difference); ≥ 90% pasangan HARD ≤ ambang (field 20–30%, coarse 10–20%, pulp ≤ 10%) | per tipe |
| Insersi | proporsi sampel QC ≥ target (mis. 5% blank, 5% CRM, 5% duplikat) | ringkasan |
Ambang adalah praktik industri (mengacu praktik KCMI/JORC Table 1 Section 1 tentang QA/QC) dan **harus ditetapkan CPI**
di `config/qaqc.yml`. Skrip menghasilkan `laporan_qaqc.md`, `ringkasan.json`, dan grafik kontrol; *exit code* ≠ 0 bila
ada batch gagal → status check PR merah.

**Notebook geostatistik (GeostatsPy):**
- Simpan notebook tanpa output (`nbstripout`), pasangkan dengan `.py` via jupytext untuk review diff.
- Parameter (domain, top-cut, variogram, search ellipse) di YAML; notebook membaca YAML.
- Data input via path lingkungan (`DATA_DIR`) dan checksum dicek di sel pertama.
- Action `nbmake` menjalankan notebook dengan data sintetis untuk memastikan masih bisa dieksekusi.
- Tag `estimasi-YYYY-MM-vN` saat model diserahkan ke CPI; release berisi parameter + laporan validasi (swath plot,
  cross-validation) — bukan block model mentah.

### 3.2 Mine Planning — optimasi pit, SR, integrasi software tambang
- Skrip optimasi pit (`desain-pit-geoteknik/pit_design.py`; min-cut) dan jalan (`desain-jalan-tambang`) di-version;
  parameter ekonomi & geoteknik di JSON/YAML yang di-review.
- **Skenario sebagai branch/tag**: `scenario/harga-nikel-15k`, `scenario/kh-0.15`; hasil dibandingkan otomatis
  (Actions memposting tabel delta: tonase bijih, kadar, SR, nilai) di PR.
- **Perhitungan SR & tonase** diuji unit (pytest) dengan model kecil yang hasilnya diketahui.
- **Integrasi software tambang (pertukaran via format terbuka):**
  | Software | Impor dari skrip | Ekspor ke skrip |
  |---|---|---|
  | Surpac | string `.str` (templat `format_tambang.py`), DTM via DXF 3DFACE | `.str`/CSV → parser |
  | Datamine | CSV block model / string, DXF | CSV |
  | Vulcan | CSV/BDF block model (miningpy `vulcan_csv`), DXF | CSV |
  | Deswik | DXF, CSV, LandXML surface | CSV/DXF |
  | Civil 3D / Minescape | LandXML (alignment, surface), DXF | LandXML |
  File proprietary biner (mis. `.dm`, `.bmf`, `.dwg`) tidak dimasukkan ke Git biasa; bila memang perlu, lewat LFS dan
  hanya hasil final yang dirilis.
- Jadwal produksi (Pyomo + HiGHS): model MILP di repo, input diringkas per blok/periode, hasil diringkas ke matriks RKAB.

### 3.3 GIS & Geoteknik — data spasial besar dengan Git LFS
- Batas ukuran per file Git LFS bergantung plan (Free/Pro 2 GB, Team 4 GB, Enterprise Cloud 5 GB); Git biasa menolak
  file > 100 MB. Kuota storage/bandwidth LFS berbayar — **pantau penggunaan**.
- Simpan di LFS: ortofoto/DSM GeoTIFF terkompresi (COG), LAZ (bukan LAS), shapefile hasil (`*.shp/.shx/.dbf/.prj`),
  GeoPackage, laporan PDF besar. Data mentah drone (foto JPG ribuan) **tidak** ke Git — simpan di object storage
  (S3/MinIO/NAS) dan catat manifest + checksum di Git.
- Konvensi: `gis/<tahun>/<tanggal-akuisisi>_<area>_<jenis>.<ext>` + file `*.meta.yml` (CRS EPSG:32751, alat, akurasi,
  GCP, operator, klasifikasi).
- GeoJSON kecil (< 10 MB) disimpan sebagai teks biasa (diff terbaca), dengan koordinat dibulatkan bila bukan data rahasia.
- Batas WIUP aktual: RAHASIA → hanya versi teranonimisasi/digeneralisasi di repo; versi resmi di sistem GIS perusahaan.
- Geoteknik: data radar/prism → database time-series; repo menyimpan skrip analisis kecepatan deformasi (inverse
  velocity), ambang alarm (YAML, MOC), dan laporan.
- Templat: `templates/.gitattributes` (pola LFS), `templates/.gitignore`.

### 3.4 Operasional & Maintenance — ETL telemetri dan CI/CD
**Pipeline ETL FMS (templat `etl_telemetri.py`):**
```
FMS/dispatch export (CSV/JSON/API) → validasi skema → normalisasi (zona waktu WITA, satuan) → status alat per jam
→ KPI PA/MA/UA/EU per unit & shift → pseudonimisasi ID operator → Parquet/CSV → data warehouse
(skema bintang, lihat skill desain-sistem-tambang-dan-dwh) → dashboard
```
- KPI mengikuti definisi dan ambang Kepmen 1827 hal. 118 (PA ≥ 90%, MA ≥ 85%, UA ≥ 75%, EU ≥ 65%).
- ID operator di-hash dengan *salt* rahasia (Secrets) sebelum keluar dari zona operasional (UU PDP: minimisasi data).
- Dijalankan terjadwal oleh GitHub Actions pada *self-hosted runner* di jaringan site (data tidak keluar jaringan),
  kredensial dari Environments/Secrets.

**CI/CD (GitHub Actions) — workflow templat:**
| Workflow | Pemicu | Isi |
|---|---|---|
| `ci-kualitas.yml` | PR & push | ruff (lint), pytest + coverage, nbstripout check, gitleaks, guard data sensitif, batas ukuran file |
| `qaqc-assay.yml` | PR yang mengubah `config/`/`scripts/`, jadwal mingguan (self-hosted) | QA/QC + unggah laporan sebagai artefak + komentar ringkasan ke PR |
| `rilis-laporan.yml` | push tag `rkab-*`, `sdc-*`, `desain-*`, `v*` | bangun ulang laporan secara reproducible, `MANIFEST.sha256`, draft release + lampirkan aset (publish manual oleh Maintainer) |
| `etl-telemetri.yml` | jadwal tiap jam (self-hosted) + manual | ETL FMS → KPI → gudang data; gagal = notifikasi |
Prinsip keamanan Actions: `permissions:` minimal per job, pin action ke SHA commit, `pull_request` (bukan
`pull_request_target`) untuk kode dari fork, secrets hanya di Environment dengan reviewer untuk produksi, runner
self-hosted hanya untuk repo privat.

---

## Bagian 4. Roadmap implementasi 90 hari & KPI
| Fase | Minggu | Kegiatan | Keluaran |
|---|---|---|---|
| 1. Fondasi | 1–3 | Plan GitHub, organisasi, SSO/2FA, Teams, kebijakan ditandatangani, templat `.github` org | Kebijakan berlaku, 100% anggota 2FA |
| 2. Pilot | 4–7 | Repo `geologi-qaqc` & `perencanaan-jalan`: ruleset, CODEOWNERS, CI, LFS | 2 repo pilot hijau; laporan QA/QC otomatis |
| 3. Regulasi | 8–10 | Repo `rkab-<tahun>` & `sdc-pelaporan` dengan release immutable; MOC digital untuk `sistem-kritis-alarm` | RKAB & pernyataan SDC tertelusur |
| 4. Skala | 11–13 | ETL FMS self-hosted, dashboard KPI, audit log streaming, pelatihan semua disiplin | KPI otomatis; audit internal pertama |

KPI tata kelola: 0 secret/data rahasia bocor; ≥ 95% merge ke `main` lewat PR teraprov; 100% angka RKAB/SDC punya tag
release; median lead time issue → release; % PR lulus check pada percobaan pertama; waktu rotasi kredensial setelah
insiden < 4 jam; review akses bulanan 100%.

---

## Lampiran A. Templat siap pakai (folder `templates/`)
| Berkas | Fungsi |
|---|---|
| `kebijakan/KEBIJAKAN-TATA-KELOLA-GIT.md` | Teks kebijakan resmi + lembar pernyataan karyawan/kontraktor |
| `.github/CODEOWNERS` | Penyetuju per folder (CPI, KTT/PJO, disiplin) |
| `.github/pull_request_template.md` | Checklist teknis, data, regulasi |
| `.github/ISSUE_TEMPLATE/*.yml` | Permintaan analisis, MOC SMKP, laporan masalah |
| `.github/workflows/*.yml` | CI kualitas, QA/QC, rilis laporan, ETL telemetri |
| `rulesets/*.json` | Ruleset `main`, `staging`, tag rilis, push ruleset data mentah |
| `scripts/terapkan_ruleset.sh`, `scripts/buat_tim_dan_akses.sh` | Penerapan via `gh api` |
| `.gitattributes`, `.gitignore`, `.pre-commit-config.yaml` | LFS, pengecualian data, hook lokal |
| `../scripts/qaqc_assay.py` | QA/QC blank, CRM, duplikat |
| `../scripts/guard_data_sensitif.py` | Pemblokir data pribadi/koordinat WIUP/kolom assay |
| `../scripts/anonimisasi.py` | Anonimisasi koordinat, ID, kadar untuk berbagi/CI |
| `../scripts/etl_telemetri.py` | ETL FMS → KPI PA/MA/UA/EU + pseudonimisasi |
| `../scripts/format_tambang.py` | Tulis/baca string Surpac `.str`, CSV block model |

## Lampiran B. Glosarium singkat
CPI: Competent Person Indonesia; CRM: certified reference material; HARD: half absolute relative difference; MOC:
management of change; PA/MA/UA/EU: physical/mechanical availability, use of availability, effective utilization;
LFS: Large File Storage; RBAC: role-based access control.

## Lampiran C. Rujukan
- UU 2/2025: https://peraturan.bpk.go.id/Details/316682/uu-no-2-tahun-2025
- Permen ESDM 26/2018: https://peraturan.bpk.go.id/Details/142457/permen-esdm-no-26-tahun-2018
- Kepmen ESDM 1827 K/30/MEM/2018: https://jdih.esdm.go.id/storage/document/Keputusan%20Menteri%20ESDM%20Nomor%201827%20K%2030%20MEM%202018.pdf
- Ketentuan CP (Ditjen Minerba): https://www.minerba.esdm.go.id/upload/file_menu/20240109114206.pdf
- Permen ESDM 17/2025: https://peraturan.bpk.go.id/Details/350283/permen-esdm-no-17-tahun-2025 ; perubahan: Permen ESDM 6/2026
- Kepdirjen 185.K/37.04/DJB/2019 (SMKP): dirujuk dalam https://www.minerba.esdm.go.id/upload/file_menu/20220518125238.pdf
- KCMI 2017 (CRIRSCO): https://crirsco.com/wp-content/uploads/2024/04/1_Indonesia.pdf
- JORC: https://jorc.org/ dan https://jorc.org/code-update
- UU 27/2022 (PDP): https://pasal.id/akn/id/act/uu/2022/27
- GitHub immutable releases: https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- GitHub rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- GitHub Git LFS: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
- GitHub Secret Protection: https://docs.github.com/en/enterprise-cloud@latest/code-security/securing-your-organization/understanding-your-organizations-exposure-to-leaked-secrets/choosing-github-secret-protection
- GitHub audit log: https://resources.github.com/learn/pathways/administration-governance/essentials/access-capture-consume-audit-logs
