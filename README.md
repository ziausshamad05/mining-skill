# mining-skill

Kumpulan skill agen AI (format `SKILL.md`) untuk industri pertambangan dan energi.

| Skill | Fungsi |
|---|---|
| [`regulasi-rkab-esdm`](skills/regulasi-rkab-esdm/SKILL.md) | Ambil peraturan resmi dari JDIH ESDM / JDIH BPK / peraturan.go.id, pecah per Pasal, dan nilai kepatuhan RKAB Minerba & panas bumi (Permen ESDM 17/2025 jo. 6/2026, Kepmen 341.K/2025) |
| [`tailings-dam-review`](skills/tailings-dam-review/SKILL.md) | Tinjauan risiko fasilitas tailing (GISTM) |
| [`water-quality-assessment`](skills/water-quality-assessment/SKILL.md) | Penilaian kualitas air terhadap baku mutu |

## Uji
```bash
python3 -m pytest skills/regulasi-rkab-esdm/tests -q
```
