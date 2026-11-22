#!/usr/bin/env python3
"""Pertukaran format terbuka dengan software tambang (Surpac, Datamine, Vulcan, Deswik).

- Surpac string (.str, ASCII): tulis_str / baca_str
    baris 1: header  "<lokasi>, <tanggal dd-Mmm-yy>, <keterangan>, ssi_styles:styles.ssi"
    baris 2: axis    "0, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000"
    titik:   "<string_no>, <Y/northing>, <X/easting>, <Z>, <D1>[, D2 ...]"
    akhir segmen: "0, 0.000, 0.000, 0.000,"
    akhir file:   "0, 0.000, 0.000, 0.000, END"
  Catatan: Surpac menulis Y sebelum X. Verifikasi impor pertama di Surpac (File > Open) sebelum produksi.
- Block model CSV generik (Datamine/Deswik/Vulcan via import CSV): tulis_bm_csv dengan header XC,YC,ZC,XINC,...

Contoh:
  python format_tambang.py csv2str --in crest.csv --out crest.str --string-col str --d1 label
  python format_tambang.py str2csv --in pit.str --out pit.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

AKHIR_SEG = "0, 0.000, 0.000, 0.000,"
AKHIR_FILE = "0, 0.000, 0.000, 0.000, END"


def tulis_str(path, segmen: list[dict], lokasi="ssu", keterangan="dibuat oleh mining-skill",
              tanggal: dt.date | None = None, desimal: int = 3) -> Path:
    """segmen: [{'string': int 1..32000, 'titik': [(x, y, z), ...], 'd': ['label', ...] opsional}]"""
    tanggal = tanggal or dt.date.today()
    f = Path(path)
    ln = [f"{lokasi}, {tanggal.strftime('%d-%b-%y')}, {keterangan}, ssi_styles:styles.ssi",
          "0, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000"]
    for s in segmen:
        no = int(s["string"])
        if not 1 <= no <= 32000:
            raise ValueError("nomor string Surpac harus 1..32000")
        d = s.get("d")
        for i, (x, y, z) in enumerate(s["titik"]):
            extra = ""
            if d is not None:
                dv = d[i] if isinstance(d, (list, tuple)) else d
                extra = f", {dv}" if dv not in (None, "") else ""
            ln.append(f"{no}, {y:.{desimal}f}, {x:.{desimal}f}, {z:.{desimal}f}{extra}")
        ln.append(AKHIR_SEG)
    ln[-1] = AKHIR_FILE
    f.write_text("\n".join(ln) + "\n")
    return f


def baca_str(path) -> pd.DataFrame:
    rows, seg = [], 1
    lines = Path(path).read_text().splitlines()[2:]
    for t in lines:
        parts = [p.strip() for p in t.split(",")]
        if not parts or parts[0] == "":
            continue
        if parts[0] == "0":
            if len(parts) > 4 and parts[4].upper() == "END":
                break
            seg += 1
            continue
        rows.append({"string": int(parts[0]), "segmen": seg, "y": float(parts[1]), "x": float(parts[2]),
                     "z": float(parts[3]), "d1": parts[4] if len(parts) > 4 and parts[4] else None})
    return pd.DataFrame(rows, columns=["string", "segmen", "x", "y", "z", "d1"])


def df_ke_segmen(df: pd.DataFrame, string_col="string", seg_col=None, d_col=None, xyz=("x", "y", "z")) -> list[dict]:
    keys = [string_col] + ([seg_col] if seg_col else [])
    out = []
    for k, g in df.groupby(keys, sort=False):
        no = k[0] if isinstance(k, tuple) else k
        out.append({"string": int(no), "titik": list(zip(g[xyz[0]], g[xyz[1]], g[xyz[2]])),
                    "d": g[d_col].tolist() if d_col else None})
    return out


def tulis_bm_csv(bm: pd.DataFrame, path, xyz=("x", "y", "z"), dims=(10, 10, 5), atribut=None) -> Path:
    """Block model -> CSV gaya Datamine (XC,YC,ZC,XINC,YINC,ZINC + atribut huruf besar)."""
    atribut = atribut or [c for c in bm.columns if c not in xyz]
    out = pd.DataFrame({"XC": bm[xyz[0]], "YC": bm[xyz[1]], "ZC": bm[xyz[2]],
                        "XINC": dims[0], "YINC": dims[1], "ZINC": dims[2]})
    for c in atribut:
        out[c.upper()[:8]] = bm[c]
    out.to_csv(path, index=False)
    return Path(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a1 = sp.add_parser("csv2str")
    a1.add_argument("--in", dest="inp", required=True)
    a1.add_argument("--out", required=True)
    a1.add_argument("--string-col", default="string")
    a1.add_argument("--seg-col")
    a1.add_argument("--d1")
    a2 = sp.add_parser("str2csv")
    a2.add_argument("--in", dest="inp", required=True)
    a2.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "csv2str":
        df = pd.read_csv(a.inp)
        if a.string_col not in df:
            df[a.string_col] = 1
        tulis_str(a.out, df_ke_segmen(df, a.string_col, a.seg_col, a.d1))
    else:
        baca_str(a.inp).to_csv(a.out, index=False)
    print(f"Tertulis {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
