---
name: desain-jalan-tambang
description: "Desain jalan tambang/haul road sesuai Kepmen ESDM 1827 K/30/MEM/2018 (hal. 99-100): alinyemen horizontal & tikungan, profil memanjang teroptimasi (grade <= 12%), penampang melintang (lebar 3,5x unit, tanggul 3/4 roda, cross fall 2%, saluran, galian/timbunan berjenjang), koridor 3D, volume & mass-haul, FK/PoF lereng galian-timbunan. Keluaran format baku: paket gambar (peta situasi, plan & profile berskala, penampang tipikal, penampang melintang + Material(s) at Station, Total Volume Table) dengan informasi tepi & pengesahan KTT, laporan perencanaan (PDF/DOCX/MD), LandXML, DXF 2D/3D, OBJ/STL. Gunakan untuk merancang, mengevaluasi, atau mengaudit jalan angkut, ramp, jalan akses tambang."
---

# Desain Jalan Tambang (Kepmen ESDM 1827 + AASHTO)

Skrip `scripts/haul_road.py` menghasilkan desain jalan angkut lengkap dari titik PI + topografi, lalu memeriksa
kepatuhan Kepmen ESDM 1827 K/30/MEM/2018 butir jalan pertambangan (hal. 99-100) dan kapasitas (hal. 67).

## Kapan dipakai
- Merancang jalan angkut pit -> ROM/stockpile/disposal, ramp keluar pit, jalan akses.
- Mengaudit jalan eksisting (lebar, grade, tanggul, cross fall, tikungan) terhadap Kepmen.
- Butuh keluaran yang bisa langsung dibuka di Civil 3D / AutoCAD / Minescape / Surpac / QGIS.

## Input (JSON, lihat `templates/contoh_jalan.json`)
| Kunci | Isi |
|---|---|
| `alinyemen.pi` | daftar [E, N] titik PI (awal, PI tikungan, akhir), koordinat UTM |
| `alinyemen.radius` | radius tiap PI tikungan (m) |
| `unit_terbesar` | lebar, diameter & lebar roda, jejak roda, wheelbase, juntai, GVW, tinggi mata pengemudi |
| `topografi.sumber` | `demo`, CSV `x,y,z` (atau `E,N,Z`), atau LandXML surface (ekspor Civil 3D/Global Mapper) |
| `jumlah_jalur`, `kecepatan_rencana_kmh`, `grade_maks_desain`, `superelevasi_maks`, `gesekan_samping_f` | parameter geometri |
| `tanggul`, `saluran`, `galian`, `timbunan`, `lapis_perkerasan` | dimensi penampang & lereng |
| `profil.mode` | `otomatis` (optimasi LP HiGHS: minimalkan beda dengan tanah asli dengan batas grade & perubahan grade) atau `manual` + `profil.pvi` [[sta, elev], ...] |
| `produksi_tph`, `kapasitas_jalan_tph`, `persimpangan_deg` | cek opsional kapasitas (+25%) & sudut pertigaan (>= 70 derajat) |
| `penampang.tipe` | `adaptif` (galian: saluran tanpa tanggul; timbunan: tanggul) atau `saluran_tanggul_dua_sisi` (saluran + tanggul di kedua sisi, lereng dari puncak tanggul) |
| `tanggul.bentuk`, `tanggul.tinggi_m` | `trapesium` atau `blok`; tinggi dipakai bila > 3/4 D roda |
| `geoteknik` | `aktif`, `keparahan_longsor` (CoF), `ru`, `kh`, `material_galian`, `material_timbunan` (c, phi, gamma + simpangan baku), `status_parameter` |
| `lembar` | tata letak gambar: `kertas` (A0-A4), `skala_horizontal`, `skala_vertikal`, `skala_penampang`, `interval_label_sta_m`, `interval_data_profil_m`, `interval_penampang_lembar_m`, `penampang_per_lembar`, `overlap_m`, `ortofoto` {path, extent / world file}, `sistem_koordinat`, `sumber_topografi`, `nomor_gambar`, `revisi`, `nomor_iup`, `lokasi`, `logo`, `pengesahan`, `label_baris_profil` |

Panjang tiap lembar plan & profile **dihitung dari parameter**: (lebar area gambar − 34 mm) × skala_horizontal / 1000
(A3 @ 1:2.000 ≈ 530 m, A3 @ 1:1.000 ≈ 265 m, A1 @ 1:2.000 ≈ 1.150 m). Skala vertikal & penampang naik otomatis ke skala
standar berikutnya bila tidak muat. Detail format: `references/format-gambar-dan-laporan.md`.

Bila data unit belum ada, tanyakan model unit angkut terbesar; jangan menebak spesifikasi pabrikan.

## Menjalankan
```bash
pip install numpy scipy shapely matplotlib ezdxf pandas
python3 scripts/haul_road.py --demo --out hasil_demo/                 # contoh topografi sintetis
python3 scripts/haul_road.py --config templates/contoh_jalan_saluran_tanggul.json --out hasil/   # tipe saluran+tanggul dua sisi
python3 scripts/haul_road.py --config proyek.json --out hasil/
```

## Keluaran
| Berkas | Setara Civil 3D |
|---|---|
| `jalan.xml` | LandXML 1.2: Alignment (Line/Curve), Profile EG (ProfSurf) & FG (ProfAlign PVI + ParaCurve), CrossSects (EG/FG per stasiun), Surface EG, FG_Koridor_Jalan (dengan breakline CL/ETW/SHLD/DAYL), FG_Komposit |
| `jalan_plan.dxf` | denah: CL + stasiun, tepi jalur, bahu, tanggul, saluran, daylight, kontur EG 1/5 m & FG, label tikungan, garis potong |
| `jalan_3d.dxf` | feature line 3D (POLYLINE), string penampang, TIN koridor (3DFACE + MESH) |
| `jalan_profil.dxf` | profile view (skala vertikal x5), grid, label PVI, grade, elevasi EG/FG |
| `jalan_penampang.dxf` | section view tersusun grid + luas galian/timbunan |
| `koridor.obj/.stl`, `komposit.obj` | mesh 3D (origin digeser; offset ditulis di header OBJ) |
| `volume.csv`, `titik_koridor.csv` | luas & volume average end area + mass-haul kumulatif; titik PENZD berkode |
| `gambar_perencanaan_jalan.pdf` + `pratinjau/*.png` | paket gambar: peta situasi & indeks lembar, plan & profile per segmen, penampang jalan tipikal, penampang melintang (tabel Material(s) at Station, OFF/ELEV, pita data), Total Volume Table; tiap lembar dengan kop, peta indeks, legenda, sistem koordinat, skala numerik+grafis, utara, catatan Kepmen, pengesahan KTT, nomor gambar |
| `laporan_perencanaan_jalan.pdf/.docx/.md` | laporan baku: judul, pengesahan, daftar isi, BAB 1-6 (pendahuluan, data & asumsi, kriteria, hasil, kepatuhan, rekomendasi + K3), lampiran daftar gambar & berkas |
| `laporan.json` | seluruh data perhitungan |

Layer DXF memakai pola NCS (`C-ROAD-CNTR`, `C-ROAD-EDGE`, `C-ROAD-BERM`, `C-ROAD-DTCH`, `C-ROAD-DAYL`, `C-TOPO-MAJR`, ...).
Impor ke Civil 3D: Insert > LandXML (pilih alignment, profil, surface). DXF berelevasi bisa dijadikan breakline.

## Aturan yang diterapkan
Ambang ada di `references/kriteria_jalan_kepmen1827.json` (sitasi halaman). Ringkas:
- Lebar lurus: max(Kepmen 3,5 x lebar unit untuk 2 jalur / 2 x untuk 1 jalur, AASHTO L = n.Wt + (n+1).0,5Wt).
- Tikungan: lebar = max(W = n(U+Fa+Fb+Z)+C, lebar lurus + off-tracking); R_min = V^2/(127(e+f)); superelevasi e = V^2/(127R) - f (dibatasi e_maks), transisi (runoff) linear.
- Grade <= 12% (target desain default 10%); > 12% ditandai wajib kajian teknis.
- Cross fall >= 2% (crown), tanggul >= 3/4 diameter roda pada sisi timbunan/terbuka; sisi boxcut tanpa tanggul.
- Saluran di sisi galian; kapasitas Manning vs debit rasional (intensitas hujan dapat diatur).
- Lengkung vertikal & jarak pandang henti (AASHTO, tinggi mata pengemudi truk), tebal perkerasan metode CBR Kaufman & Ault (USBM IC 8758).
- Lereng galian/timbunan berjenjang; FK statis/dinamis & PoF lereng galian dan timbunan tertinggi dihitung otomatis dengan `../desain-pit-geoteknik/scripts/geotek.py` terhadap Tabel 1 hal. 57 (timbunan: parameter residual, hal. 58).

## Batasan (sampaikan ke pengguna)
- Kepmen tidak memberi angka radius, superelevasi, jarak pandang, dimensi saluran: dihitung dengan metode rekayasa dan ditandai demikian.
- Volume average end area belum dikoreksi eksentrisitas di tikungan; bandingkan dengan volume TIN (keduanya dilaporkan).
- Hasil = desain teknis awal. Wajib verifikasi topografi aktual, uji CBR/DCP, kajian geoteknik & hidrologi, dan pengesahan KTT.
- Persimpangan dirancang manual; skrip hanya memeriksa sudut yang diberikan.
- Tata letak peta resmi WIUP (Kepmen 1798 Lampiran IV) tidak terbaca otomatis; elemen informasi tepi dapat disesuaikan lewat `lembar.*` bila instansi meminta format tertentu.
- Parameter geoteknik default adalah ASUMSI; ganti dengan hasil uji sebelum laporan diajukan.

## Uji
```bash
python3 -m pytest skills/desain-jalan-tambang/tests -q
```
