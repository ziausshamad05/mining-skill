# mining-skill

Kumpulan skill agen AI (format `SKILL.md`) untuk industri pertambangan dan energi.

| Skill | Fungsi |
|---|---|
| [`regulasi-rkab-esdm`](skills/regulasi-rkab-esdm/SKILL.md) | Ambil peraturan resmi dari JDIH ESDM / JDIH BPK / peraturan.go.id, pecah per Pasal, dan nilai kepatuhan RKAB Minerba & panas bumi (Permen ESDM 17/2025 jo. 6/2026, Kepmen 341.K/2025) |
| [`teknis-pertambangan-kepmen1827`](skills/teknis-pertambangan-kepmen1827/SKILL.md) | Skill payung teknis & pelaksanaan tambang (Kepmen ESDM 1827 K/30/MEM/2018): checklist per tahap + kalkulator sump, disposal, armada/match factor, peledakan, pemberaian, konservasi |
| [`desain-jalan-tambang`](skills/desain-jalan-tambang/SKILL.md) | Desain jalan angkut (lebar 3,5x unit, grade <= 12%, tanggul 3/4 roda, tikungan, profil teroptimasi HiGHS, penampang, koridor 3D) -> LandXML/DXF/OBJ/PDF gaya Civil 3D |
| [`desain-pit-geoteknik`](skills/desain-pit-geoteknik/SKILL.md) | Block model -> FK/PoF lereng (Tabel 1 Kepmen 1827) -> pit akhir (min-cut) -> jenjang + ramp -> surface 3D, tonase, penampang -> LandXML/DXF/OBJ/PDF |
| [`tata-kelola-github-tambang`](skills/tata-kelola-github-tambang/SKILL.md) | Tata kelola GitHub & data tambang: pemetaan ke UU Minerba/Kepmen 1827/RKAB/KCMI-SNI/SMKP/UU PDP, kebijakan Git, RBAC, SOP PR & MOC, ruleset, CI QA/QC assay, Git LFS, ETL FMS (PA/MA/UA/EU), format Surpac |
| [`tailings-dam-review`](skills/tailings-dam-review/SKILL.md) | Tinjauan risiko fasilitas tailing (GISTM) |
| [`water-quality-assessment`](skills/water-quality-assessment/SKILL.md) | Penilaian kualitas air terhadap baku mutu |

## Pemasangan dependensi
```bash
pip install numpy scipy shapely matplotlib ezdxf pandas pyyaml pytest
```

## Contoh cepat
```bash
python3 skills/desain-jalan-tambang/scripts/haul_road.py --demo --out hasil_jalan/
python3 skills/desain-pit-geoteknik/scripts/pit_design.py --demo --out hasil_pit/
python3 skills/teknis-pertambangan-kepmen1827/scripts/kalkulator_teknis.py alat --bucket-m3 5.2 --truk-ton 40 --jarak-m 2500
```
Contoh hasil (lembar gambar & laporan) ada di folder `contoh/` tiap skill.

## Instruksi agen
- [`AGENTS.md`](AGENTS.md): instruksi khusus lengkap (dibaca otomatis lewat `CLAUDE.md`).
- [`docs/instruksi-project-siap-tempel.md`](docs/instruksi-project-siap-tempel.md): versi ringkas untuk kolom instruksi Project.

## Uji
```bash
python3 -m pytest skills -q
```
