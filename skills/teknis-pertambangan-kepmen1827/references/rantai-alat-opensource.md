# Rantai alat open-source untuk teknis pertambangan

Dipakai bila pekerjaan melampaui kalkulator bawaan. Semua Python kecuali dinyatakan lain.

| Tahap | Alat | Peran | Catatan pemakaian |
|---|---|---|---|
| Data spasial & batas IUP | geopandas (github.com/geopandas/geopandas) | Baca SHP/GeoJSON batas WIUP, titik bor, transformasi CRS (mis. EPSG:4326 -> UTM 51S EPSG:32751) | Selalu proyeksikan ke UTM sebelum menghitung jarak/luas |
| Model geologi 3D | GemPy (github.com/gempy-project/gempy) | Model implisit kontak litologi & sesar dari data bor/peta | Hasil dipakai untuk domain estimasi dan lapisan geoteknik |
| Estimasi kadar | GeostatsPy (github.com/GeostatsGuy/GeostatsPy) | Variogram, kriging, SGS (port GSLIB) | Estimasi per domain; validasi swath plot & cross-validation |
| Block model | MiningPy (skill `miningpy-block-model`) | ijk/xyz, reblock, grade-tonnage, ekspor Vulcan | Kadar di-reblock berbobot tonase |
| Pit akhir | MineFlow (github.com/MineFlowCSM/MineFlow, C++) | Pseudoflow ultimate pit untuk model besar | Skill `desain-pit-geoteknik` memakai min-cut scipy (cukup s.d. ~10^5-10^6 blok) |
| Penjadwalan produksi | Pyomo (github.com/Pyomo/pyomo) + HiGHS (github.com/ERGO-Code/HiGHS) | MILP penjadwalan blok/push-back, blending kadar, optimasi armada | Skill jalan memakai HiGHS (via scipy.linprog) untuk optimasi garis kemiringan |
| Visualisasi 3D | PyVista (github.com/pyvista/pyvista) | Render block model, permukaan pit/jalan, ekspor VTK/ParaView | OBJ/STL dari skill bisa dibaca langsung |
| CAD | ezdxf | Tulis/baca DXF | Layer gaya NCS: C-ROAD-*, C-PIT-*, C-TOPO-* |
| Prospektivitas | skill `eksplorasi-mineral-ml` | ML untuk target eksplorasi | Validasi spasial (blok), bukan acak |
| Sistem operasi & DWH | skill `desain-sistem-tambang-dan-dwh` | P2H, work order, data warehouse KPI | KPI PA/MA/UA/EU mengikuti ambang Kepmen hal. 118 |

## Contoh rantai lengkap
1. geopandas: batas IUP + titik bor -> UTM.
2. GemPy: domain litologi -> GeostatsPy: kriging kadar per domain -> MiningPy: block model teratur.
3. `desain-pit-geoteknik`: geoteknik (FK/PoF) -> pit akhir -> desain jenjang + ramp -> LandXML/DXF.
4. `desain-jalan-tambang`: jalan dari exit ramp ke stockpile/ROM -> LandXML/DXF.
5. Pyomo + HiGHS: jadwal produksi per tahun (RKAB) dari blok dalam pit desain.
6. `kalkulator_teknis.py`: sump, disposal, armada, peledakan untuk tiap tahap jadwal.
7. `regulasi-rkab-esdm`: susun matriks RKAB dan cek kepatuhan.
