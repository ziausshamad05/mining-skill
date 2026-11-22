---
name: teknis-pertambangan-kepmen1827
description: "Skill payung teknis & pelaksanaan pertambangan minerba Indonesia berdasar Kepmen ESDM 1827 K/30/MEM/2018 (kaidah teknik pertambangan yang baik): checklist per tahap (eksplorasi, studi kelayakan, geoteknik, penambangan, peledakan, timbunan/disposal, stockpile, penyaliran, jalan, alat gali-muat-angkut, pengolahan, konservasi, reklamasi) + kalkulator sump, disposal, produktivitas & match factor, geometri peledakan, pemberaian, recovery. Mengarahkan ke skill desain-jalan-tambang, desain-pit-geoteknik, regulasi-rkab-esdm. Gunakan untuk pertanyaan atau dokumen teknis tambang, audit KTT, kajian teknis, RKAB."
---

# Teknis & Pelaksanaan Pertambangan (Kepmen ESDM 1827 K/30/MEM/2018)

## Peta skill
| Kebutuhan | Pakai |
|---|---|
| Jalan angkut, ramp, jalan akses: geometri, profil, penampang, koridor 3D, LandXML/DXF | `skills/desain-jalan-tambang` |
| Block model -> pit akhir -> desain jenjang/ramp, FK & PoF lereng, cadangan dalam pit | `skills/desain-pit-geoteknik` |
| Sump/penyaliran, disposal, armada & match factor, peledakan, pemberaian, recovery | `scripts/kalkulator_teknis.py` (skill ini) |
| Teks resmi peraturan, status berlaku, RKAB, kompetensi KTT | `skills/regulasi-rkab-esdm` |
| Validasi/reblock/ekspor block model | skill `miningpy-block-model` |
| Target eksplorasi ML | skill `eksplorasi-mineral-ml` |
| Sistem operasi tambang (P2H, WO) & data warehouse KPI | skill `desain-sistem-tambang-dan-dwh` |

## Cara kerja
1. Tentukan tahap & topik pertanyaan, buka `references/checklist-kepmen1827.md` bagian terkait. Kutip ambang **dengan nomor halaman**.
2. Butir bertanda **[verifikasi]**, atau klaim yang akan masuk dokumen resmi: ambil teks asli dengan `regulasi-rkab-esdm` (`jdih_fetch.py`) dan cocokkan.
3. Untuk angka, jalankan kalkulator; jangan menghitung di kepala. Setiap keluaran memuat baris `[MEMENUHI]/[TIDAK MEMENUHI]` + dasar halaman.
4. Desain geometri (jalan, pit, lereng) -> skill desain terkait; hasilnya LandXML/DXF/PDF siap Civil 3D.
5. Reklamasi & pascatambang: utamakan Kepmen ESDM 344.K/MB.01/MEM.B/2025; K3/SMKP: petunjuk teknis Dirjen Minerba terbaru. Cek status lewat `regulasi-rkab-esdm`.
6. Sampaikan bahwa hasil = alat bantu teknis; keputusan & pengesahan tetap oleh KTT dan kajian teknis berwenang.

## Kalkulator
```bash
K=skills/teknis-pertambangan-kepmen1827/scripts/kalkulator_teknis.py
python3 $K sump --luas-ha 35 --hujan-mm 120 --durasi-jam 24 --c 0.9 --pompa-m3jam 300 --volume-sump 60000
python3 $K disposal --lebar-dasar 400 --panjang-dasar 600 --tinggi-lift 10 --jumlah-lift 4 --berm 10 --kebutuhan-bcm 3e6 --tinggi-truk 3.6
python3 $K disposal --lebar-dasar 300 --panjang-dasar 300 --in-pit --jarak-kaki-m 150
python3 $K alat --bucket-m3 5.2 --fill 0.85 --ct-gali-s 30 --truk-ton 40 --densitas-lepas 1.8 --jarak-m 2500 --pa 0.92 --ma 0.88 --ua 0.8 --eu 0.7
python3 $K ledakan --diameter-mm 115 --tinggi-jenjang 8 --densitas-batuan 2.5 --densitas-handak 0.85
python3 $K pemberaian --ucs-mpa 25 --gsi 55 --vp-ms 1200
python3 $K konservasi --cadangan 1.2e6 --tertambang 1.1e6 --recovery-olah 0.9 --recovery-fs 0.88
```

## Referensi
- `references/checklist-kepmen1827.md`: ambang numerik per tahap dengan halaman, status regulasi.
- `references/rantai-alat-opensource.md`: GemPy, GeostatsPy, MiningPy, MineFlow, Pyomo + HiGHS, PyVista, geopandas dan urutan pemakaiannya.

## Uji
```bash
python3 -m pytest skills/teknis-pertambangan-kepmen1827/tests -q
```
