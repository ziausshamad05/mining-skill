# Laporan Desain Pit - Contoh Desain Pit A (DEMO, data sintetis)

Dasar: Kepmen ESDM 1827 K/30/MEM/2018 (Tabel 1 FK/PoF hal. 57; tambang permukaan hal. 84, 91-94; jalan hal. 99-100).

## Geometri lereng & pit

- Tinggi jenjang 10.0 m, sudut muka 55 deg, lebar berm 8.0 m
- Sudut inter-ramp 33.7 deg; sudut keseluruhan 34.9 deg (optimasi pit memakai 31.9 deg untuk kelonggaran ramp)
- Ramp 17.45 m, grade 10.0%; dasar pit EL 80.0; tinggi dinding maks 98.4 m; 10 jenjang

## Tonase

| | Bijih (t) | Kadar rata | Waste (t) | Nisbah kupas | Nilai |
|---|---|---|---|---|---|
| Pit optimasi | 3,904,772 | 0.595 | 6,741,132 | 1.73 | 76,861,129 |
| Pit desain | 4,470,353 | 0.561 | 11,141,106 | 2.49 | 66,120,649 |

Cut-off kadar: 0.235 %. Volume galian (TIN): 6,705,570 m3.

## Pemeriksaan kepatuhan

| No | Item | Nilai | Syarat | Status | Dasar |
|---|---|---|---|---|---|
| 1 | Lereng tunggal (H 10 m, 55.0 deg) | FKs 1.87, FKd 1.66, PoF 0.0% | FKs >= 1.1, PoF <= 25% (CoF menengah) | MEMENUHI | Kepmen 1827 Tabel 1 hal. 57 |
| 2 | Lereng inter-ramp (H 40 m, 37.6 deg) | FKs 1.44, FKd 1.21, PoF 0.0% | FKs >= 1.3, FKd >= 1.0, PoF <= 20% (CoF menengah) | MEMENUHI | Kepmen 1827 Tabel 1 hal. 57 |
| 3 | Lereng keseluruhan (H 100 m, 35.2 deg) | FKs 1.48, FKd 1.23, PoF 0.0% | FKs >= 1.3, FKd >= 1.05, PoF <= 10% (CoF menengah) | MEMENUHI | Kepmen 1827 Tabel 1 hal. 57 |
| 4 | Tinggi jenjang vs jangkauan alat gali | 10.0 m | <= 10.5 m | MEMENUHI | Kepmen 1827 hal. 91 (xiv.xi) |
| 5 | Lebar ramp (2 jalur + tanggul + saluran) | 17.45 m | >= 3.5 x 3.5 m + tanggul | MEMENUHI | Kepmen 1827 hal. 99 (i) |
| 6 | Grade ramp | 10.0% | <= 12% | MEMENUHI | Kepmen 1827 hal. 99 (vii) |
| 7 | Tanggul pengaman ramp | 1.20 m | >= 3/4 x 1.6 m | MEMENUHI | Kepmen 1827 hal. 99 (ii) |
| 8 | Jarak aman bibir pit akhir | 4.9 m (tandai di lapangan) | 1 m + 4% tinggi lereng | MEMENUHI | Kepmen 1827 hal. 94 (xvi.viii) [verifikasi] |
| 9 | Peledakan dekat lereng akhir | baris terakhir >= 20 m dari lereng akhir | 2 x tinggi jenjang | MEMENUHI | Kepmen 1827 hal. 93 (xvi.iii) |
| 10 | Jumlah akses keluar pit | 1 akses (kedalaman 98 m) | 2 akses bila kedalaman akhir > 45 m | TIDAK MEMENUHI | Kepmen 1827 hal. 95 |
| 11 | Lebar dasar pit minimum | 30 m | cukup untuk manuver alat (praktik) | MEMENUHI | Praktik rekayasa |

## Iterasi optimasi geometri lereng

| Sudut muka | Berm (m) | Sudut keseluruhan | FK keseluruhan | PoF | Lolos |
|---|---|---|---|---|---|
| 70 | 6 | 47.6 | 1.01 | nan% | tidak |
| 70 | 7 | 44.8 | 1.06 | nan% | tidak |
| 65 | 6 | 44.5 | 1.06 | nan% | tidak |
| 70 | 8 | 42.3 | 1.12 | nan% | tidak |
| 65 | 7 | 42.1 | 1.13 | nan% | tidak |
| 60 | 6 | 41.6 | 1.14 | nan% | tidak |
| 65 | 8 | 39.8 | 1.21 | nan% | tidak |
| 60 | 7 | 39.4 | 1.22 | nan% | tidak |
| 55 | 6 | 38.7 | 1.21 | 3.0% | tidak |
| 70 | 10 | 38.0 | 1.25 | nan% | tidak |
| 60 | 8 | 37.3 | 1.25 | 0.5% | tidak |
| 55 | 7 | 36.7 | 1.27 | 0.5% | tidak |
| 65 | 10 | 35.9 | 1.31 | 0.0% | tidak |
| 50 | 6 | 35.7 | 1.31 | 0.0% | tidak |
| 55 | 8 | 34.9 | 1.33 | 0.0% | ya |

## Catatan

- Pit akhir dihitung dengan min-cut (setara Lerchs-Grossmann) pada block model; untuk model besar/produksi gunakan MineFlow (pseudoflow) atau Whittle/Deswik.
- Ramp dimodelkan sebagai pita spiral yang memotong muka jenjang; geometri tikungan switchback & sambungan ke jalan luar dirapikan di CAD (Civil 3D/Surpac/Minescape).
- FK memakai Bishop disederhanakan + lapisan horizontal; PoF Monte Carlo. Verifikasi dengan Slide2/RS2, data uji lab, kinematik (planar/baji/toppling), dan muka air tanah aktual. Rekomendasi geoteknik wajib disahkan KTT.
- Impor `pit.xml` ke Civil 3D (Insert > LandXML) untuk surface EG/desain; DXF crest/toe berelevasi bisa dipakai langsung sebagai breakline.
