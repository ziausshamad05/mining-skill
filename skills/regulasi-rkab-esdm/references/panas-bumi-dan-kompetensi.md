# RKAB Panas Bumi & Kompetensi SDM (BPSDM ESDM)

## A. RKAB Panas Bumi (Ditjen EBTKE)

Rezim RKAB panas bumi **terpisah** dari Minerba: tidak memakai Permen 17/2025 maupun MinerbaOne.

| Instrumen | Relevansi RKAB |
|---|---|
| UU 21/2014 tentang Panas Bumi | Payung pengusahaan |
| **PP 7/2017** Panas Bumi untuk Pemanfaatan Tidak Langsung | Mendefinisikan RKAB sebagai rencana kerja & anggaran yang disampaikan **berkala** oleh Pihak Lain dan/atau **pemegang IPB** |
| Standar usaha perizinan berbasis risiko (dulu Lampiran IV Permen ESDM 5/2021; **Permen 5/2021 dicabut oleh Permen ESDM 7/2026**) | Kewajiban pemegang IPB menyampaikan RKAB dan realisasi RKAB secara berkala, serta rencana jangka panjang eksplorasi–eksploitasi–pemanfaatan |
| Permen ESDM 23/2017 | Rencana tahunan produksi uap/listrik PLTP & rencana besaran Bonus Produksi |
| Permen ESDM 37/2017 | Wilayah Kerja Panas Bumi |
| Permen ESDM 5/2023 | PNBP EBTKE: iuran tetap eksplorasi/eksploitasi sebelum COD, komitmen eksplorasi |
| Permen ESDM 44/2016 | Pencairan komitmen eksplorasi mengacu RKAB tahunan yang dievaluasi Dirjen |

Langkah wajib sebelum menyusun checklist panas bumi: jalankan
`jdih_fetch.py search "panas bumi rencana kerja" --tahun 2026` dan cek apakah Permen 7/2026 atau
regulasi lain sudah mengganti ketentuan di atas. Tandai setiap butir dengan status verifikasinya.

Checklist ringkas RKAB panas bumi (untuk divalidasi ke regulasi terbaru):
1. IPB/izin aktif & wilayah kerja sesuai penetapan.
2. Rencana pengeboran (sumur eksplorasi/produksi/injeksi), rencana biaya, kapasitas pengembangan, tahapan PLTP.
3. Status komitmen eksplorasi & iuran tetap (PNBP).
4. Rencana produksi uap/listrik tahunan & Bonus Produksi.
5. Rencana pengelolaan lumpur bor & serbuk bor (disampaikan sebelum pengeboran).
6. Persetujuan lingkungan & PPKH (bila di kawasan hutan/konservasi).

## B. Kompetensi & Sertifikasi (BPSDM ESDM)

| Peran | Dasar & lembaga | Relevansi RKAB |
|---|---|---|
| **Kepala Teknik Tambang (KTT)** | Permen ESDM 26/2018 (kaidah pertambangan yang baik); diklat penyiapan oleh **PPSDM Geominerba** (BPSDM ESDM) | KTT wajib ada untuk tahap eksplorasi dan OP (Pasal 5 Permen 17/2025) |
| **Pengawas Operasional** – Pertama (POP), Madya (POM), Utama (POU) | Diklat & uji kompetensi PPSDM Geominerba; sertifikasi melalui LSP ESDM berlisensi BNSP | Matriks K3/KO: jumlah & jenjang pengawas bersertifikat |
| **Competent Person Indonesia (CPI)** | Organisasi profesi (mis. PERHAPI/IAGI, KCMI) – bukan BPSDM | Penanda tangan laporan sumber daya & cadangan (syarat OP) |
| Juru ukur, juru ledak, ventilasi tambang, dll. | Skema sertifikasi Geominerba BPSDM | Pendukung matriks K3 & penambangan |

Catatan: sebutkan skema/lembaga persis dari situs BPSDM/PPSDM Geominerba terbaru; jangan menebak
nomor Kepmen standar kompetensi.

## C. Kompetensi teknis data & GitHub (untuk tim kepatuhan)
- Simpan regulasi hasil `download` + manifest di repo terpisah (atau Git LFS bila besar); commit mencatat tanggal akses.
- Jadikan `.pasal.json` sebagai dataset: diff antar versi peraturan (mis. Permen 17/2025 vs 6/2026) dengan `git diff --word-diff`.
- Jalankan `rkab_validator.py` di CI (GitHub Actions) setiap kali draf matriks CSV diperbarui; kode keluar 1 = ada temuan KRITIS.

## Sumber
- PP 7/2017 (definisi RKAB): https://peraturan.go.id/files/pp7-2017bt.pdf
- Permen ESDM 23/2017: https://jdih.esdm.go.id/storage/document/Permen%20ESDM%20Nomor%2023%20Thn%202017.pdf
- Lampiran IV Permen ESDM 5/2021 (EBTKE): https://jdih.esdm.go.id/storage/document/4_Lampiran%20IV%20Permen%205%202021_EBTKE_Pengundangan_net.pdf
- BPSDM ESDM – sertifikasi pengawas operasional & KTT: https://www.esdm.go.id/id/berita-unit/badan-pengembangan-sumber-daya-manusia/sertifikasi-pengawas-operasional-sebagai-upaya-ppsdm-geominerba-
