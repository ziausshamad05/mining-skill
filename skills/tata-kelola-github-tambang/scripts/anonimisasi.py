#!/usr/bin/env python3
"""Anonimisasi data tambang untuk berbagi / CI (bukan untuk pelaporan resmi).

Transformasi (kunci rahasia dari env ANON_KEY, tidak pernah disimpan di repo):
  - Koordinat: translasi + rotasi kaku di bidang XY (jarak, luas, volume, dan geometri relatif tetap),
    Z digeser konstan. Parameter diturunkan deterministik dari kunci (HMAC-SHA256).
  - ID (hole_id, sample_id, operator_id, unit_id ...): HMAC-SHA256 dipotong -> "H-xxxxxxxxxx".
  - Kadar: faktor skala tunggal per analit (opsional, mempertahankan korelasi & CV) + pembulatan.
  - Kolom yang disebut --hapus dibuang (nama, NIK, telepon, catatan bebas).

Contoh:
  ANON_KEY=... python anonimisasi.py --in collar.csv --out collar_anon.csv \
     --xyz x y z --id hole_id --kadar Ni Co --skala-kadar --hapus driller_name
Catatan: anonimisasi koordinat dengan rotasi kaku dapat dibalik bila titik kontrol publik diketahui;
untuk pihak eksternal gabungkan dengan generalisasi (pembulatan) dan perjanjian kerahasiaan.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import math
import os
import sys

import numpy as np
import pandas as pd


def _hm(key: bytes, label: str) -> bytes:
    return hmac.new(key, label.encode(), hashlib.sha256).digest()


def _u(key: bytes, label: str) -> float:
    """Bilangan [0,1) deterministik dari kunci."""
    return int.from_bytes(_hm(key, label)[:8], "big") / 2**64


def parameter(key: bytes) -> dict:
    return {
        "dx": 1_000 + _u(key, "dx") * 50_000,
        "dy": 1_000 + _u(key, "dy") * 50_000,
        "dz": -200 + _u(key, "dz") * 400,
        "rot_deg": _u(key, "rot") * 360,
    }


def hash_id(nilai, key: bytes, panjang: int = 10, awalan: str = "H-") -> str:
    if pd.isna(nilai):
        return nilai
    return awalan + hmac.new(key, str(nilai).encode(), hashlib.sha256).hexdigest()[:panjang]


def anonimkan(df: pd.DataFrame, key: bytes, xyz=None, ids=(), kadar=(), skala_kadar=False,
              hapus=(), desimal_koord=1, desimal_kadar=3, pusat=None) -> pd.DataFrame:
    out = df.drop(columns=[c for c in hapus if c in df.columns]).copy()
    if xyz:
        par = parameter(key)
        x, y = out[xyz[0]].astype(float), out[xyz[1]].astype(float)
        cx, cy = pusat if pusat else (0.0, 0.0)
        t = math.radians(par["rot_deg"])
        xr = (x - cx) * math.cos(t) - (y - cy) * math.sin(t)
        yr = (x - cx) * math.sin(t) + (y - cy) * math.cos(t)
        out[xyz[0]] = (xr + par["dx"]).round(desimal_koord)
        out[xyz[1]] = (yr + par["dy"]).round(desimal_koord)
        if len(xyz) > 2 and xyz[2] in out:
            out[xyz[2]] = (out[xyz[2]].astype(float) + par["dz"]).round(desimal_koord)
    for c in ids:
        if c in out:
            out[c] = out[c].map(lambda v: hash_id(v, key))
    for c in kadar:
        if c in out:
            f = 0.8 + 0.4 * _u(key, "kadar:" + c) if skala_kadar else 1.0
            out[c] = (out[c].astype(float) * f).round(desimal_kadar)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--xyz", nargs="+")
    ap.add_argument("--id", nargs="*", default=[])
    ap.add_argument("--kadar", nargs="*", default=[])
    ap.add_argument("--skala-kadar", action="store_true")
    ap.add_argument("--hapus", nargs="*", default=[])
    ap.add_argument("--key-env", default="ANON_KEY")
    a = ap.parse_args(argv)
    k = os.environ.get(a.key_env)
    if not k or len(k) < 16:
        print(f"Set env {a.key_env} (>= 16 karakter) dari vault; kunci tidak boleh di repo.", file=sys.stderr)
        return 2
    df = pd.read_csv(a.inp)
    pusat = None
    if a.xyz:
        pusat = (float(np.floor(df[a.xyz[0]].mean())), float(np.floor(df[a.xyz[1]].mean())))
    out = anonimkan(df, k.encode(), a.xyz, a.id, a.kadar, a.skala_kadar, a.hapus, pusat=pusat)
    out.to_csv(a.out, index=False)
    print(f"Tertulis {a.out} ({len(out)} baris). Simpan sebagai data/teranonimisasi/ dan catat di README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
