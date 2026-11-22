#!/usr/bin/env python3
"""ETL telemetri FMS/dispatch -> jam status per unit & shift -> KPI PA/MA/UA/EU.

Input: satu atau lebih CSV event status (format umum ekspor FMS):
  unit_id, operator_id, waktu_mulai, waktu_selesai, status, [lokasi, material, muatan_ton]
  status: WORKING | DELAY | STANDBY | BREAKDOWN | MAINTENANCE  (pemetaan bisa diubah --peta-status)

Definisi (praktik umum Indonesia; W=kerja, S=siap tidak dipakai (standby+delay), R=perbaikan):
  MA = W/(W+R)   PA = (W+S)/(W+S+R)   UA = W/(W+S)   EU = W/(W+S+R)
Ambang: PA >= 90%, MA >= 85%, UA >= 75%, EU >= 65% (Kepmen ESDM 1827 K/30/MEM/2018 hal. 118).

Perlindungan data (UU 27/2022): operator_id di-pseudonimisasi HMAC-SHA256 dengan salt dari env
OPERATOR_SALT sebelum ditulis; kolom nama/telepon dibuang.

Contoh: OPERATOR_SALT=... python etl_telemetri.py --input fms/ --out dwh_staging/ --jam-shift 7 --zona Asia/Makassar
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pandas as pd

PETA_STATUS = {"WORKING": "W", "OPERASI": "W", "DELAY": "S", "STANDBY": "S", "IDLE": "S",
               "BREAKDOWN": "R", "MAINTENANCE": "R", "REPAIR": "R", "PM": "R"}
AMBANG = {"PA": 0.90, "MA": 0.85, "UA": 0.75, "EU": 0.65}
KOLOM_WAJIB = ["unit_id", "waktu_mulai", "waktu_selesai", "status"]
KOLOM_PRIBADI = ["nama_operator", "operator_name", "telepon", "phone", "nik"]


def pseudonim(v, salt: bytes) -> str:
    if pd.isna(v):
        return v
    return "OP-" + hmac.new(salt, str(v).encode(), hashlib.sha256).hexdigest()[:12]


def baca(input_path: str) -> pd.DataFrame:
    p = Path(input_path)
    files = sorted(p.glob("*.csv")) if p.is_dir() else [p]
    if not files:
        raise SystemExit(f"Tidak ada CSV di {input_path}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def validasi(df: pd.DataFrame, peta: dict) -> tuple[pd.DataFrame, list[str]]:
    masalah = []
    hilang = [c for c in KOLOM_WAJIB if c not in df]
    if hilang:
        raise SystemExit(f"Kolom wajib hilang: {hilang}")
    df = df.copy()
    df["status"] = df.status.astype(str).str.upper().str.strip()
    tak_dikenal = sorted(set(df.status) - set(peta))
    if tak_dikenal:
        masalah.append(f"status tidak dikenal (dibuang): {tak_dikenal}")
    df = df[df.status.isin(peta)]
    df["kat"] = df.status.map(peta)
    df["waktu_mulai"] = pd.to_datetime(df.waktu_mulai, errors="coerce")
    df["waktu_selesai"] = pd.to_datetime(df.waktu_selesai, errors="coerce")
    rusak = df.waktu_mulai.isna() | df.waktu_selesai.isna() | (df.waktu_selesai <= df.waktu_mulai)
    if rusak.any():
        masalah.append(f"{int(rusak.sum())} baris waktu tidak valid (dibuang)")
    df = df[~rusak].sort_values(["unit_id", "waktu_mulai"])
    tumpang = df.groupby("unit_id").apply(
        lambda g: int((g.waktu_mulai.iloc[1:].values < g.waktu_selesai.iloc[:-1].values).sum()),
        include_groups=False).sum()
    if tumpang:
        masalah.append(f"{int(tumpang)} event tumpang-tindih (dipotong ke awal event berikutnya)")
        nxt = df.groupby("unit_id").waktu_mulai.shift(-1)
        df["waktu_selesai"] = df.waktu_selesai.where(nxt.isna() | (df.waktu_selesai <= nxt), nxt)
    return df, masalah


def pecah_shift(df: pd.DataFrame, jam_shift: int, panjang_jam: int = 12) -> pd.DataFrame:
    """Pecah event yang melintasi batas shift; kembalikan durasi jam per (tanggal_shift, shift, unit, kat)."""
    rows = []
    step = pd.Timedelta(hours=panjang_jam)
    for r in df.itertuples(index=False):
        t0, t1 = r.waktu_mulai, r.waktu_selesai
        while t0 < t1:
            base = t0.normalize() + pd.Timedelta(hours=jam_shift)
            if t0 < base:
                base -= pd.Timedelta(days=1)
            k = int((t0 - base) // step)
            awal = base + k * step
            akhir = min(t1, awal + step)
            rows.append({"tanggal_shift": awal.date().isoformat(), "shift": "SIANG" if k == 0 else "MALAM",
                         "unit_id": r.unit_id, "operator_ps": getattr(r, "operator_ps", None),
                         "kat": r.kat, "jam": (akhir - t0).total_seconds() / 3600,
                         "muatan_ton": getattr(r, "muatan_ton", 0) if t0 == r.waktu_mulai else 0})
            t0 = akhir
    return pd.DataFrame(rows)


def kpi(jam: pd.DataFrame, kunci: list[str]) -> pd.DataFrame:
    p = jam.pivot_table(index=kunci, columns="kat", values="jam", aggfunc="sum", fill_value=0)
    for c in "WSR":
        if c not in p:
            p[c] = 0.0
    W, S, R = p.W, p.S, p.R
    out = pd.DataFrame({"jam_W": W.round(2), "jam_S": S.round(2), "jam_R": R.round(2)})
    out["MA"] = (W / (W + R)).where((W + R) > 0)
    out["PA"] = ((W + S) / (W + S + R)).where((W + S + R) > 0)
    out["UA"] = (W / (W + S)).where((W + S) > 0)
    out["EU"] = (W / (W + S + R)).where((W + S + R) > 0)
    for k, lim in AMBANG.items():
        out[k] = out[k].round(4)
        out[f"{k}_ok"] = out[k] >= lim
    return out.reset_index()


def jalankan(inp: str, out: str, jam_shift: int = 7, zona: str = "Asia/Makassar",
             salt: bytes | None = None, peta: dict | None = None) -> dict:
    peta = peta or PETA_STATUS
    df = baca(inp)
    df = df.drop(columns=[c for c in KOLOM_PRIBADI if c in df.columns])
    if "operator_id" in df:
        if not salt:
            raise SystemExit("OPERATOR_SALT wajib di-set (Secrets) untuk pseudonimisasi operator_id")
        df["operator_ps"] = df.operator_id.map(lambda v: pseudonim(v, salt))
        df = df.drop(columns=["operator_id"])
    if "muatan_ton" not in df:
        df["muatan_ton"] = 0.0
    df, masalah = validasi(df, peta)
    for c in ("waktu_mulai", "waktu_selesai"):
        if df[c].dt.tz is not None:
            df[c] = df[c].dt.tz_convert(zona).dt.tz_localize(None)
    jam = pecah_shift(df, jam_shift)
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    k_shift = kpi(jam, ["tanggal_shift", "shift", "unit_id"])
    k_unit = kpi(jam, ["unit_id"])
    prod = jam.groupby(["tanggal_shift", "shift", "unit_id"]).muatan_ton.sum().reset_index()
    jam.to_csv(o / "fakta_jam_status.csv", index=False)
    k_shift.merge(prod, on=["tanggal_shift", "shift", "unit_id"], how="left").to_csv(o / "kpi_shift_unit.csv", index=False)
    k_unit.to_csv(o / "kpi_unit.csv", index=False)
    ring = {"n_event": int(len(df)), "n_unit": int(df.unit_id.nunique()), "masalah_data": masalah,
            "unit_di_bawah_ambang": {k: k_unit.loc[~k_unit[f"{k}_ok"], "unit_id"].tolist() for k in AMBANG},
            "dasar_ambang": "Kepmen ESDM 1827 K/30/MEM/2018 hal. 118"}
    (o / "ringkasan_etl.json").write_text(json.dumps(ring, indent=2, ensure_ascii=False))
    return ring


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jam-shift", type=int, default=7, help="jam mulai shift siang (default 07.00)")
    ap.add_argument("--zona", default="Asia/Makassar")
    ap.add_argument("--peta-status", help="JSON {status: W|S|R}")
    a = ap.parse_args(argv)
    salt = os.environ.get("OPERATOR_SALT", "").encode() or None
    peta = json.loads(Path(a.peta_status).read_text()) if a.peta_status else None
    print(json.dumps(jalankan(a.input, a.out, a.jam_shift, a.zona, salt, peta), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
