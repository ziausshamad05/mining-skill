# KEBIJAKAN TATA KELOLA GIT & GITHUB
**[NAMA PERUSAHAAN]** — Nomor: KBJ-IT-GIT-001 | Revisi: 0 | Tanggal berlaku: [tanggal]
Pemilik kebijakan: [Kepala Data & DevOps] | Disetujui: [Direktur Utama] dan [Kepala Teknik Tambang]

## 1. Tujuan
Menjamin bahwa kode, model, parameter, dan dokumen teknis pertambangan yang dikelola di Git/GitHub (a) dapat ditelusuri
dan diaudit untuk kepatuhan kaidah teknik pertambangan yang baik, RKAB, pelaporan sumber daya & cadangan, dan SMKP;
(b) melindungi data rahasia perusahaan/WIUP dan data pribadi sesuai UU 27/2022; (c) mencegah kebocoran kredensial.

## 2. Ruang lingkup
Seluruh karyawan, kontraktor, konsultan, dan pihak ketiga yang mengakses organisasi GitHub `[nama-org]`, repositori
Git perusahaan, atau perangkat/akun yang digunakan untuk pekerjaan perusahaan.

## 3. Definisi
- **Data mentah**: assay, collar, survey, downhole, sampel QA/QC asli, koordinat aktual titik bor & batas WIUP, block
  model produksi, ekspor FMS/dispatch beridentitas, data sensor sistem kritis.
- **Secrets**: kata sandi, token, API key, kunci SSH/GPG privat, sertifikat, string koneksi, file `.env`.
- **Data pribadi**: sebagaimana UU 27/2022 (mis. nama + NIK, nomor telepon, email pribadi, data kesehatan/fatigue, foto
  wajah, ID operator yang dapat dikaitkan ke orang).

## 4. Klasifikasi data
| Kelas | Contoh | Ketentuan di GitHub |
|---|---|---|
| PUBLIK | materi publik, kode open-source tanpa data | Boleh di repo publik dengan persetujuan tertulis Manajemen |
| INTERNAL | skrip, SOP, templat, parameter generik, data sintetis | Repo privat/internal |
| RAHASIA | data mentah, model sumber daya, cadangan sebelum rilis, kontrak, harga | **Dilarang**; hanya checksum/metadata atau versi teranonimisasi yang disetujui Data Owner |
| SANGAT RAHASIA | secrets, data pribadi sensitif | **Dilarang mutlak** |

## 5. Larangan
5.1 Mengunggah data mentah dan data pribadi ke repositori, issue, PR, wiki, discussion, gist, atau release.
5.2 Menyimpan secrets di kode, notebook, konfigurasi, riwayat commit, atau log Actions.
5.3 Membuat repo publik, mengubah visibilitas menjadi publik, atau mem-fork repo perusahaan ke akun pribadi.
5.4 Melakukan force-push, menghapus branch terlindungi, atau melewati (bypass) ruleset di luar prosedur darurat §9.
5.5 Menyetujui PR atas nama orang lain atau memakai akun bersama.
5.6 Menempelkan data RAHASIA/SANGAT RAHASIA ke layanan AI atau pihak eksternal tanpa persetujuan Data Owner.

## 6. Kewajiban
6.1 Akun: keanggotaan organisasi dengan identitas asli, 2FA wajib, SSO perusahaan bila tersedia.
6.2 Commit ke `main`/`staging` wajib bertanda tangan (signed/verified).
6.3 Pre-commit hook perusahaan wajib terpasang (secret scan, guard data sensitif, nbstripout, batas ukuran file).
6.4 Secrets hanya disimpan di GitHub Actions Secrets/Environments atau vault perusahaan; rotasi ≤ 90 hari dan segera
    setelah dugaan kebocoran.
6.5 Data uji/CI hanya data sintetis atau teranonimisasi; kunci anonimisasi disimpan di vault, bukan di repo.
6.6 Setiap repo wajib memiliki README dengan pemilik data, klasifikasi, sumber data + checksum, dan cara reproduksi.
6.7 Angka yang dipakai untuk keputusan operasional atau pelaporan (RKAB, sumber daya/cadangan, desain final) wajib
    berasal dari **release bertag** yang disetujui CODEOWNERS (CPI/KTT/PJO sesuai domain).
6.8 Perubahan pada sistem kritis keselamatan (pemantauan lereng, alarm, FMS, collision avoidance, konfigurasi
    peledakan) wajib melalui issue MOC dan persetujuan KTT/PJO sesuai SMKP sebelum deploy.

## 7. Akses
7.1 Akses diberikan per tim dengan prinsip *least privilege* sesuai matriks RBAC (Lampiran 1 panduan).
7.2 Peran Admin organisasi maksimal 3 orang; penggunaan dicatat.
7.3 Kontraktor/auditor: outside collaborator, akses ke repo terkait saja, berbatas waktu, NDA wajib.
7.4 Review akses bulanan oleh pemilik repo; offboarding dicabut pada hari terakhir kerja.

## 8. Rekam jejak & retensi
8.1 Riwayat Git pada branch terlindungi tidak boleh ditulis ulang kecuali untuk menghapus data terlarang (§9).
8.2 Audit log organisasi diekspor/di-stream ke penyimpanan perusahaan; retensi minimal [5] tahun atau sesuai kebijakan
    arsip perusahaan, mana yang lebih lama.
8.3 Release untuk RKAB, sumber daya/cadangan, dan desain final diaktifkan sebagai **immutable**.

## 9. Penanganan insiden
9.1 Laporkan dugaan kebocoran secret/data ke Security Lead ≤ 1 jam ([email/WA]).
9.2 Langkah: cabut/rotasi kredensial → hapus dari riwayat (`git filter-repo`) dan minta pembersihan cache GitHub →
    periksa audit log & akses → catat di register insiden → evaluasi kewajiban pemberitahuan berdasarkan UU 27/2022.
9.3 Bypass ruleset darurat (mis. ambang alarm salah membahayakan) hanya oleh KTT/PJO atau delegasinya, dicatat dalam
    issue insiden, dan dilanjutkan PR retroaktif ≤ 1×24 jam.

## 10. Sanksi
Pelanggaran ditindak sesuai Peraturan Perusahaan/kontrak, tanpa mengurangi tanggung jawab hukum berdasarkan peraturan
perundang-undangan.

## 11. Rujukan
UU 4/2009 jo. UU 3/2020 jo. UU 2/2025; Permen ESDM 26/2018; Kepmen ESDM 1827 K/30/MEM/2018; Permen ESDM 17/2025 jo.
Permen ESDM 6/2026; Permen ESDM 38/2014 & Kepdirjen Minerba 185.K/37.04/DJB/2019; KCMI 2017, SNI 4726:2019,
SNI 5015:2019, JORC 2012; UU 27/2022.

---
### Lembar Pernyataan
Saya yang bertanda tangan di bawah ini telah membaca, memahami, dan akan mematuhi Kebijakan Tata Kelola Git & GitHub.

Nama: ____________________ Jabatan/Perusahaan: ____________________ Akun GitHub: @____________

Tanda tangan: ____________ Tanggal: ____________
