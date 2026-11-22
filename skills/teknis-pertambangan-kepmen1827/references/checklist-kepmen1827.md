# Checklist kaidah teknik pertambangan yang baik (Kepmen ESDM 1827 K/30/MEM/2018)

Sumber teks resmi: https://jdih.esdm.go.id/storage/document/Keputusan%20Menteri%20ESDM%20Nomor%201827%20K%2030%20MEM%202018.pdf
Dasar: Permen ESDM 26/2018 (kaidah pertambangan yang baik & pengawasan). Nomor halaman = penanda halaman cetak di PDF.
Angka di bawah diekstrak otomatis dari PDF (November 2026). Sebelum dikutip dalam dokumen resmi, cocokkan ke teks asli
(pakai `skills/regulasi-rkab-esdm/scripts/jdih_fetch.py`). Butir bertanda **[verifikasi]** ekstraksinya meragukan.

Status regulasi: 1827 K/30/MEM/2018 masih dirujuk sebagai pedoman kaidah teknik oleh Kepmen ESDM 174.K/MB.01/MEM.B/2024
(IPR) dan Kepmen ESDM 344.K/MB.01/MEM.B/2025 (pedoman reklamasi & pascatambang, berlaku 23 Okt 2025). Untuk reklamasi
dan pascatambang, **utamakan Kepmen 344/2025**; Lampiran VI Kepmen 1827 dipakai bila tidak diatur lain. Untuk K3 dan
SMKP rujuk juga Kepdirjen Minerba tentang petunjuk teknis keselamatan pertambangan & SMKP **[verifikasi nomor terbaru]**.

## Struktur lampiran
| Lampiran | Isi | Hal. |
|---|---|---|
| I | Pengesahan KTT/PTL/KTBT, pengawas operasional & teknis, PJO | 5 |
| II | Pengelolaan teknis pertambangan: E.1 eksplorasi (39), E.2 studi kelayakan: geoteknik, hidrologi, perencanaan, pengolahan, pengangkutan (54), E.3 konstruksi & uji alat (70), penambangan, pengangkutan, penyaliran, pengolahan | 27-140 |
| III | Keselamatan pertambangan / pengolahan & pemurnian | - |
| VI | Reklamasi & pascatambang (format rencana, jaminan, penilaian) | 217-343 |
| VII | Konservasi mineral & batubara | 344 |

## 1. Eksplorasi (Lampiran II E.1)
- Penginderaan jauh resolusi 7 m, 5 saluran, data <= 5 tahun (hal. 40); survei tinjau peta 1:50.000, prospeksi 1:25.000 (hal. 41).
- Parit uji: kedalaman maks 3 m, panjang 10 m (hal. 42-43) **[verifikasi]**; sumur uji diameter 1 m (hal. 43).
- Geokimia: BLEG 5-10 km2/conto, sedimen sungai 1-3 km2, tanah 30-50 cm (hal. 45); QA/QC analisis 10% (hal. 49).
- Peta topografi skala 1:2.000 akurasi 1 m (hal. 50); peta titik bor dimutakhirkan tiap 3 bulan (hal. 51).
- Coal core recovery 95% (hal. 44).

## 2. Studi kelayakan & geoteknik (E.2)
- Eksplorasi minimal 70% WIUP sebelum studi kelayakan (hal. 54).
- **Tabel 1 FK & PoF lereng (hal. 57)**: tunggal FK 1,1 PoF 25-50%; inter-ramp FK 1,15-1,3 FKd 1,0-1,1 PoF 25/20/10%; keseluruhan FK 1,2-1,5 FKd 1,0-1,1 PoF 15-20/10/5% (rendah/menengah/tinggi). Detail: `skills/desain-pit-geoteknik/references/kriteria_geoteknik_kepmen1827.json`.
- Keparahan longsor (hal. 57-58): tinggi = korban > 3 orang / > 50% produksi / henti > 24 jam; menengah = 25-50% / 12-24 jam; rendah = < 25% / < 12 jam **[verifikasi rincian]**.
- Lereng timbunan: FK dengan c & phi residual (hal. 58). Bukaan bawah tanah FK >= 2,0 (tetap) / 1,5 (tidak tetap) (hal. 58).
- Beban gempa mengacu SNI 1726 (hal. 59); curah hujan rencana periode ulang 10 tahun (hal. 59).
- Pemberaian (hal. 62): gali bebas UCS < 1,5 MPa / GSI < 50 / Vp < 450 m/s; garu 1,5-40 MPa / 50-70 / 450-1.650 m/s; peledakan > 40 MPa / > 70 / > 1.650 m/s.
- Kapasitas jalan angkut >= laju produksi + 25% (hal. 67).

## 3. Konstruksi & kelaikan alat (E.3)
- Alat/konstruksi laik bila mampu beroperasi >= 70% kapasitas terpasang (hal. 72).

## 4. Penambangan terbuka
- Lebar front kerja cukup untuk >= 7 hari produksi (hal. 82, 91).
- Tinggi jenjang <= jangkauan efektif alat gali-muat terbesar (hal. 91-92).
- Akses kendaraan dalam bukaan lebar >= 1,5 x alat, tanggul >= 3/4 roda (hal. 93-94) **[verifikasi]**.
- Tanggul/jarak aman di crest lereng akhir >= 1 m + 4% tinggi lereng (hal. 94); lebar bukaan dihitung dari tebal lapisan + kedalaman/tan(sudut) (hal. 94).
- Kedalaman akhir > 45 m: wajib dua akses (hal. 95).

## 5. Peledakan
- Stiffness ratio (H/B) 2-4; lubang ke lapisan batubara >= 0,5 m; tanggul area ledak >= 1/3 roda, berjarak 1 burden (hal. 80).
- Jarak aman: 300 m alat/fasilitas, 500 m manusia (horizontal) (hal. 80); < 500 m dari rel/listrik/bendungan wajib kajian (hal. 81).
- Batuan panas > 55 C atau metana > 50% LEL wajib kajian (hal. 81); oxygen balance ANFO 5,5-6,5% solar (hal. 82) **[verifikasi]**.
- Dilarang menggali < 5 x burden dari bahan peledak/lubang gagal ledak (hal. 82).
- Baris terakhir >= 2 x tinggi jenjang dari lereng akhir (hal. 93).

## 6. Timbunan, disposal, stockpile
- Lereng tunggal timbunan 1V:2H (50%) kecuali kajian teknis (hal. 84); tebal lapisan bottom-up <= 1/3 tinggi alat angkut (hal. 85) **[verifikasi]**.
- Timbunan in-pit: kaki timbunan ke area kerja aktif >= 3 x tinggi total timbunan (hal. 86).
- Lumpur: beda tinggi dengan landasan <= diameter roda (hal. 87).
- Stockpile: tanggul keliling >= 1 m, kapasitas >= 3 hari produksi (hal. 97).

## 7. Penyaliran
- Kapasitas penampungan/pengendapan >= 1,25 x volume air tambang pada curah hujan tertinggi (hal. 96) **[verifikasi durasi]**.
- Tindakan pengendalian saat terisi >= 80%; kolam pengendapan >= 500 m dari tepi terluar penambangan atau sesuai kajian (hal. 96) **[verifikasi]**.
- Bawah tanah: pompa utama+cadangan = debit maks + 15% (hal. 106).

## 8. Jalan pertambangan (hal. 99-100)
- Lebar 2 jalur >= 3,5 x unit terbesar, 1 jalur >= 2 x; tanggul >= 3/4 D roda; cross fall >= 2%; grade <= 12% (lebih wajib kajian);
  separator >= 1/2 D roda, lebar atas >= lebar roda; sudut pertigaan >= 70 derajat. Kalkulator lengkap: `skills/desain-jalan-tambang`.

## 9. Alat gali-muat-angkut (hal. 118-120)
- PA >= 90%, MA >= 85%, UA >= 75%, EU >= 65%, produktivitas >= 85% target; match factor mendekati 1.
- Bucket fill factor >= 80%; pemuatan 3-5 kali per truk; muatan 90-100% kapasitas.
- Surface miner: UCS 10-50 MPa, kejenuhan air <= 15%, kemiringan <= 25% (hal. 123).

## 10. Pengolahan & konservasi
- Recovery pengolahan >= studi kelayakan (hal. 125); kapasitas pengolahan batubara >= produksi + 10% (hal. 127).
- Peremuk batubara: rasio reduksi 4-5, kapasitas operasi <= 95% (hal. 128); mineral logam: kapasitas <= 95%, undersize <= 15%, rasio reduksi 4-10 (hal. 132-133).
- Unjuk kerja alat pengolahan: PA/MA/UA >= 90%, EU >= 80% (hal. 127).
- Konservasi: recovery penambangan terbuka >= 90%; cut-off thickness batubara >= 30 cm; recovery peremukan batubara >= 90% (hal. 348-350).

## 11. Reklamasi & pascatambang (Lampiran VI; utamakan Kepmen 344/2025)
- Rencana reklamasi eksplorasi diajukan <= 45 hari sebelum kegiatan; rencana reklamasi OP per 5 tahun (hal. 222-223).
- Pemeliharaan revegetasi >= 3 tahun (hal. 224); pencairan jaminan reklamasi bertahap maks 60% / 80% / 100% (hal. 250).
- Kriteria keberhasilan: pH tanah baik 5-6, rasio tumbuh baik > 80%, penebaran tanah pucuk baik > 75% luas (hal. 302-314).
- Biaya tidak langsung: mobilisasi 2,5%, perencanaan 2-10%, administrasi 3-14%, supervisi 2-7% biaya langsung (hal. 260).

## 12. Sumber daya manusia (Lampiran I)
- Orang berkompeten berpengalaman >= 5 tahun, tenaga teknis >= 3 tahun (hal. 35-36). Kompetensi KTT/pengawas: lihat skill `regulasi-rkab-esdm`.
