#!/usr/bin/env python3
"""Guard data sensitif untuk pre-commit & CI.

Memblokir berkas yang memuat:
  1. Secrets (pola umum: AWS key, GitHub token, private key, password=..., connection string).
  2. Data pribadi (UU 27/2022): NIK 16 digit, nomor HP Indonesia, email non-domain perusahaan.
  3. Data mentah tambang: CSV dengan kolom assay/collar (hole_id + koordinat + analit) atau
     koordinat UTM yang jatuh di dalam bbox WIUP (bbox dari env, tidak disimpan di repo).

Pemakaian: python guard_data_sensitif.py [--bbox-env WIUP_BBOX] [--domain ssu.co.id] FILE...
Pengecualian per baris: tambahkan komentar `guard:izinkan` (wajib dijelaskan di PR).
Berkas di folder data/sintetis/ dan tests/ tetap dipindai untuk secrets & data pribadi, tetapi
pemeriksaan koordinat WIUP dilewati karena data di sana wajib sintetis/teranonimisasi.
Exit 1 bila ada temuan.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

POLA_SECRET = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "password_assign": re.compile(r"(?i)\b(password|passwd|pwd|secret|api_?key|token)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]"),
    "conn_string": re.compile(r"(?i)\b(postgres(ql)?|mysql|mongodb(\+srv)?|mssql)://[^:\s/]+:[^@\s]+@"),
}
POLA_NIK = re.compile(r"(?<!\d)([1-9]\d{5})(0[1-9]|[12]\d|3[01]|4[1-9]|[56]\d|7[01])(0[1-9]|1[0-2])(\d{2})(\d{4})(?!\d)")
POLA_HP = re.compile(r"(?<![\d.])(\+62|62|0)8[1-9]\d{7,10}(?!\d)")
POLA_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
KOLOM_ASSAY = {"ni", "ni_pct", "co", "co_pct", "fe", "fe_pct", "au", "au_ppm", "cu", "mgo", "sio2", "cal_val", "ash"}
KOLOM_ID_BOR = {"hole_id", "holeid", "bhid", "drillhole", "lubang"}
KOLOM_X = {"x", "easting", "east", "e", "utm_x"}
KOLOM_Y = {"y", "northing", "north", "n", "utm_y"}
EKST_TEKS = {".py", ".md", ".txt", ".csv", ".json", ".yml", ".yaml", ".ipynb", ".sql", ".sh", ".xml",
             ".geojson", ".ini", ".cfg", ".toml", ".env", ".str", ".dxf"}
DOMAIN_AMAN = {"example.com", "example.org", "noreply.github.com", "users.noreply.github.com",
               "anthropic.com"}
IZINKAN = "guard:izinkan"


def baca_bbox(env: str | None):
    if not env or not os.environ.get(env):
        return None
    v = [float(t) for t in os.environ[env].split(",")]
    if len(v) != 4:
        raise SystemExit(f"{env} harus 'xmin,ymin,xmax,ymax'")
    return v


def pindai_teks(path: str, teks: str, domain_perusahaan: set[str]) -> list[str]:
    temuan = []
    for i, baris in enumerate(teks.splitlines(), 1):
        if IZINKAN in baris:
            continue
        for nama, p in POLA_SECRET.items():
            if p.search(baris):
                temuan.append(f"{path}:{i}: SECRET ({nama})")
        if POLA_NIK.search(baris) and not re.search(r"(?i)sha|hash|md5|uuid", baris):
            temuan.append(f"{path}:{i}: DATA PRIBADI (pola NIK 16 digit)")
        if POLA_HP.search(baris):
            temuan.append(f"{path}:{i}: DATA PRIBADI (nomor HP)")
        for m in POLA_EMAIL.finditer(baris):
            dom = m.group(1).lower()
            if dom not in DOMAIN_AMAN and not any(dom.endswith(d) for d in domain_perusahaan):
                temuan.append(f"{path}:{i}: DATA PRIBADI (email {m.group(0)})")
    return temuan


def pindai_csv(path: str, teks: str, bbox, lewati_bbox: bool) -> list[str]:
    temuan = []
    try:
        rd = csv.reader(io.StringIO(teks))
        header = [h.strip().lower() for h in next(rd)]
    except Exception:
        return temuan
    hs = set(header)
    if hs & KOLOM_ID_BOR and hs & KOLOM_ASSAY and not lewati_bbox:
        temuan.append(f"{path}: DATA MENTAH (kolom ID lubang bor + kolom assay) — simpan di database geologi")
    if bbox and not lewati_bbox:
        ix = next((header.index(c) for c in header if c in KOLOM_X), None)
        iy = next((header.index(c) for c in header if c in KOLOM_Y), None)
        if ix is not None and iy is not None:
            n_dalam = 0
            for r in rd:
                try:
                    x, y = float(r[ix]), float(r[iy])
                except (ValueError, IndexError):
                    continue
                if bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                    n_dalam += 1
            if n_dalam:
                temuan.append(f"{path}: KOORDINAT AKTUAL WIUP ({n_dalam} baris di dalam bbox) — anonimisasi dulu")
    return temuan


def pindai(paths: list[str], bbox=None, domain_perusahaan: set[str] | None = None) -> list[str]:
    domain_perusahaan = domain_perusahaan or set()
    temuan = []
    for p in paths:
        fp = Path(p)
        if not fp.is_file() or fp.suffix.lower() not in EKST_TEKS and fp.name != ".env":
            continue
        if fp.name.startswith(".env") or fp.suffix == ".env":
            temuan.append(f"{p}: SECRET (berkas .env dilarang di repo)")
            continue
        try:
            teks = fp.read_text(errors="ignore")
        except OSError:
            continue
        if len(teks) > 20_000_000:
            continue
        temuan += pindai_teks(p, teks, domain_perusahaan)
        if fp.suffix.lower() == ".csv":
            lewati = any(part in ("sintetis", "tests", "teranonimisasi") for part in fp.parts)
            temuan += pindai_csv(p, teks, bbox, lewati)
    return temuan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--bbox-env", default="WIUP_BBOX", help="nama env berisi bbox WIUP 'xmin,ymin,xmax,ymax'")
    ap.add_argument("--domain", action="append", default=[], help="domain email perusahaan yang diizinkan")
    a = ap.parse_args(argv)
    t = pindai(a.files, baca_bbox(a.bbox_env), set(d.lower() for d in a.domain))
    for x in t:
        print(x)
    if t:
        print(f"\n{len(t)} temuan. Hapus data, pindahkan ke sistem data perusahaan, atau anonimisasi "
              f"(scripts/anonimisasi.py). Pengecualian: komentar '{IZINKAN}' + alasan di PR.", file=sys.stderr)
    return 1 if t else 0


if __name__ == "__main__":
    sys.exit(main())
