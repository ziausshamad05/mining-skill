## Ringkasan perubahan
<!-- Apa yang berubah dan mengapa. Tautkan issue: Closes #123 / MOC #45 -->

## Dampak angka / desain
<!-- Tabel delta otomatis dari Actions akan diposting; jelaskan perubahan material (tonase, kadar, SR, FK, grade, dsb.) -->

## Checklist teknis
- [ ] Uji otomatis lulus (lint, pytest, QA/QC) dan saya sudah membaca hasilnya
- [ ] Satuan, datum & CRS (UTM 51S / EPSG:32751) diperiksa
- [ ] Parameter berubah tercatat di file konfigurasi (bukan hard-coded)
- [ ] Ambang regulasi yang dipakai mencantumkan pasal/halaman; nilai praktik rekayasa ditandai

## Checklist data & keamanan
- [ ] Tidak ada data mentah (assay, collar, koordinat aktual WIUP, block model produksi) di PR ini
- [ ] Tidak ada secrets / data pribadi; guard data sensitif lulus
- [ ] Data uji = sintetis/teranonimisasi; sumber data asli dirujuk lewat checksum
- [ ] File besar (> 50 MB) memakai Git LFS

## Persetujuan yang dibutuhkan
- [ ] Review teknis sejawat
- [ ] CPI (estimasi / sumber daya / cadangan)
- [ ] KTT/PJO (desain final, RKAB, sistem kritis — sertakan nomor MOC)

## Rencana rilis / rollback
<!-- Tag yang akan dibuat (mis. rkab-2027-v2) dan cara kembali ke versi sebelumnya -->
