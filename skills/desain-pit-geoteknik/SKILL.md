---
name: desain-pit-geoteknik
description: "Desain pit tambang terbuka dari block model sesuai Kepmen ESDM 1827 K/30/MEM/2018: kestabilan lereng (Bishop + probabilitas longsor Monte Carlo vs Tabel 1 FK/PoF hal. 57), optimasi geometri jenjang, pit akhir (min-cut setara Lerchs-Grossmann), desain crest/toe/berm/ramp spiral, permukaan 3D, tonase & nisbah kupas, penampang 2D. Ekspor seperti Civil 3D/Surpac: LandXML surface, DXF 2D/3D, OBJ/STL, CSV block model, PDF. Gunakan untuk desain pit, pit shell, blok model, jenjang, lereng, FK, PoF, rekomendasi geoteknik."
---

# Desain Pit + Geoteknik (Kepmen ESDM 1827)

## Kapan dipakai
- Dari block model (CSV) ingin pit akhir, desain jenjang + ramp, cadangan dalam pit, dan gambar 2D/3D.
- Menilai/merekomendasikan geometri lereng (tinggi jenjang, sudut muka, berm) terhadap FK & PoF Kepmen.
- Menyiapkan surface/breakline untuk Civil 3D, Surpac, Minescape, Deswik.

## Alur (scripts/pit_design.py)
1. Block model: CSV `x,y,z,kadar,densitas` (centroid, ukuran blok di `block_model.ukuran_blok`). Untuk validasi/reblock/ekspor Vulcan pakai skill `miningpy-block-model` lebih dulu.
2. Nilai blok: `(kadar x recovery x harga - biaya olah - biaya tambang) x tonase`; cut-off dihitung otomatis bila `cutoff_kadar` null.
3. Pit awal (sudut sementara) -> tinggi dinding -> **geoteknik** (`geotek.py`): profil berjenjang, Bishop disederhanakan (statis + pseudo-statik kh), PoF Monte Carlo pada c, phi, gamma per lapisan; lereng tunggal & inter-ramp dinilai di bagian atas dinding (zona lapuk). Bila `optimasi: true`, dicari kombinasi sudut muka x berm dengan sudut keseluruhan paling curam yang masih memenuhi FK, FK dinamis, dan PoF untuk keparahan longsor (CoF) yang dipilih.
4. Pit akhir dengan sudut keseluruhan dikurangi 3 derajat (kelonggaran ramp), max-flow scipy (Dinic).
5. Desain jenjang dari bawah ke atas: lantai minimum, toe -> crest (sudut muka), berm, ramp spiral (lebar 3,5 x unit + tanggul + saluran, grade <= 12%) yang memotong muka jenjang.
6. Permukaan desain (grid TIN) = min(topografi, pit); tonase blok di atas permukaan desain; volume galian TIN.
7. Ekspor + lembar PDF + laporan kepatuhan.

## Menjalankan
```bash
pip install numpy scipy shapely matplotlib ezdxf pandas
python3 scripts/pit_design.py --demo --out hasil_demo/     # data sintetis, ~1 menit
python3 scripts/pit_design.py --config pit.json --out hasil/
python3 scripts/geotek.py --H 10 --muka 65 --berm 8 --n 8 --c 120 --phi 34 --cof tinggi   # cek lereng cepat
```
Templat konfigurasi: `templates/contoh_pit.json`. Material berlapis: `geoteknik.material.lapisan` (urut atas ke bawah,
`z_atas` = elevasi atas lapisan). Topografi: `demo`, CSV `x,y,z`, atau LandXML surface.

## Keluaran
| Berkas | Isi |
|---|---|
| `pit.xml` | LandXML 1.2: Surface EG_Topografi, Pit_Desain_Final (breakline CREST/TOE), Pit_Saja |
| `pit_plan.dxf` | crest/toe (LWPOLYLINE berelevasi), garis tengah ramp, pit shell per level, kontur, label elevasi, garis penampang |
| `pit_3d.dxf` | crest/toe/ramp sebagai POLYLINE 3D + TIN pit (3DFACE) |
| `pit_penampang.dxf` | penampang topografi, desain, blok bijih |
| `pit_final.obj/.stl`, `pit_saja.obj` | mesh 3D |
| `block_model_hasil.csv` | blok + tonase, nilai, flag bijih, pit_optimasi, pit_desain |
| `lembar_gambar.pdf` + PNG | denah, penampang + block model, 3D, analisis lereng (lingkaran kritis), grade-tonnage & kepatuhan |
| `laporan.md/json` | geometri, tonase/SR/nilai (optimasi vs desain), FK/PoF, iterasi optimasi, tabel kepatuhan |

## Aturan Kepmen yang diperiksa
`references/kriteria_geoteknik_kepmen1827.json` (dengan halaman). FK/PoF Tabel 1 hal. 57 (rentang -> batas atas, konservatif;
ubah `pakai_batas`), FK timbunan pakai parameter residual (hal. 58), tinggi jenjang <= jangkauan alat gali (hal. 91),
baris ledak terakhir >= 2 x tinggi jenjang dari lereng akhir (hal. 93), jarak aman bibir pit akhir 1 m + 4% tinggi lereng (hal. 94),
dua akses bila kedalaman akhir > 45 m (hal. 95), ramp: lebar/tanggul/grade (hal. 99).

## Batasan (sampaikan ke pengguna)
- Pit akhir min-cut cocok s.d. ~10^5-10^6 blok; model produksi besar: MineFlow (pseudoflow), Whittle, Deswik.
- Ramp konseptual (spiral tunggal); switchback, sambungan ke jalan luar dan akses kedua dirapikan di CAD. Jalan di luar pit: skill `desain-jalan-tambang`.
- Geoteknik: Bishop lingkaran + lapisan horizontal; belum analisis kinematik (planar, baji, toppling), muka air tanah 2D, atau anisotropi. Hasil = penyaring desain; verifikasi Slide2/RS2/GeoStudio dengan data lab, lalu sahkan KTT.
- Data demo sintetis; angka demo bukan cadangan nyata.

## Uji
```bash
python3 -m pytest skills/desain-pit-geoteknik/tests -q
```
