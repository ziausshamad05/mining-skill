#!/usr/bin/env python3
"""QA/QC assay otomatis: blank, CRM (Shewhart), duplikat (HARD), laju insersi.

Kolom input minimal (CSV):
  sample_id, batch, qc_type (ORIGINAL|BLANK|CRM|FIELD_DUP|COARSE_DUP|PULP_DUP), crm_id, parent_id, <analit...>
Contoh:  python qaqc_assay.py --data assay_qaqc.csv --config qaqc.yml --out laporan_qaqc

Ambang di config adalah PRAKTIK INDUSTRI dan wajib ditetapkan/disetujui CPI (KCMI 2017 / JORC 2012 Table 1 Sec. 1).
Exit code 1 bila ada batch GAGAL (dipakai sebagai status check PR).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_CONFIG = {
    "analit": ["Ni", "Co", "Fe"],
    "satuan": {"Ni": "%", "Co": "%", "Fe": "%"},
    "batas_deteksi": {"Ni": 0.01, "Co": 0.001, "Fe": 0.01},
    "blank_kali_bd": 5,                      # blank gagal bila > 5 x batas deteksi
    "crm": {},                               # crm_id: {analit: {nilai: x, sd: s}}
    "bias_peringatan": 0.05,                 # |rata2(hasil/sertifikat) - 1| > 5%
    "hard_ambang": {"FIELD_DUP": 0.20, "COARSE_DUP": 0.10, "PULP_DUP": 0.10},
    "hard_proporsi_lulus": 0.90,
    "insersi_target": {"BLANK": 0.025, "CRM": 0.05, "DUP": 0.05},
}


def muat_config(path: str | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path:
        p = Path(path)
        if p.suffix in (".yml", ".yaml"):
            import yaml
            user = yaml.safe_load(p.read_text()) or {}
        else:
            user = json.loads(p.read_text())
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def cek_blank(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    b = df[df.qc_type == "BLANK"]
    rows = []
    for a in cfg["analit"]:
        if a not in b:
            continue
        batas = cfg["blank_kali_bd"] * cfg["batas_deteksi"].get(a, 0)
        for _, r in b.iterrows():
            rows.append({"sample_id": r.sample_id, "batch": r.batch, "analit": a, "hasil": r[a],
                         "batas": batas, "status": "GAGAL" if r[a] > batas else "LULUS"})
    return pd.DataFrame(rows, columns=["sample_id", "batch", "analit", "hasil", "batas", "status"])


def cek_crm(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aturan Shewhart: |z|<=2 LULUS; 2<|z|<=3 PERINGATAN; |z|>3 GAGAL;
    dua berturut-turut |z|>2 di sisi sama (per CRM & analit, urutan baris) -> GAGAL."""
    c = df[df.qc_type == "CRM"].copy()
    rows = []
    for (crm_id, grp) in c.groupby("crm_id", sort=False):
        ref = cfg["crm"].get(str(crm_id))
        if not ref:
            continue
        for a, spec in ref.items():
            if a not in grp:
                continue
            z = (grp[a] - spec["nilai"]) / spec["sd"]
            prev = 0.0
            for (_, r), zi in zip(grp.iterrows(), z):
                st = "LULUS" if abs(zi) <= 2 else ("PERINGATAN" if abs(zi) <= 3 else "GAGAL")
                if abs(zi) > 2 and abs(prev) > 2 and np.sign(zi) == np.sign(prev):
                    st = "GAGAL"
                rows.append({"sample_id": r.sample_id, "batch": r.batch, "crm_id": crm_id, "analit": a,
                             "hasil": r[a], "sertifikat": spec["nilai"], "sd": spec["sd"],
                             "z": round(float(zi), 2), "status": st})
                prev = zi
    hasil = pd.DataFrame(rows, columns=["sample_id", "batch", "crm_id", "analit", "hasil",
                                        "sertifikat", "sd", "z", "status"])
    if hasil.empty:
        return hasil, pd.DataFrame(columns=["crm_id", "analit", "n", "bias", "status"])
    bias = (hasil.assign(r=hasil.hasil / hasil.sertifikat - 1)
            .groupby(["crm_id", "analit"]).agg(n=("r", "size"), bias=("r", "mean")).reset_index())
    bias["bias"] = bias["bias"].round(4)
    bias["status"] = np.where(bias["bias"].abs() > cfg["bias_peringatan"], "PERINGATAN", "LULUS")
    return hasil, bias


def hard(a: pd.Series, b: pd.Series) -> pd.Series:
    """Half absolute relative difference = |a-b| / (a+b)."""
    s = a + b
    return (a - b).abs() / s.where(s != 0, np.nan)


def cek_duplikat(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    asli = df[df.qc_type == "ORIGINAL"].set_index("sample_id")
    rows = []
    for tipe, ambang in cfg["hard_ambang"].items():
        d = df[df.qc_type == tipe]
        if d.empty:
            continue
        d = d[d.parent_id.isin(asli.index)]
        for a in cfg["analit"]:
            if a not in d:
                continue
            bd = cfg["batas_deteksi"].get(a, 0)
            p = asli.loc[d.parent_id, a].to_numpy()
            q = d[a].to_numpy()
            ok = (p > 10 * bd) & (q > 10 * bd)          # abaikan pasangan dekat batas deteksi
            h = hard(pd.Series(p[ok]), pd.Series(q[ok]))
            n = int(ok.sum())
            prop = float((h <= ambang).mean()) if n else float("nan")
            rows.append({"tipe": tipe, "analit": a, "n_pasangan": n, "ambang_hard": ambang,
                         "proporsi_lulus": round(prop, 3) if n else None,
                         "status": ("TIDAK CUKUP DATA" if n < 10 else
                                    "LULUS" if prop >= cfg["hard_proporsi_lulus"] else "GAGAL")})
    return pd.DataFrame(rows, columns=["tipe", "analit", "n_pasangan", "ambang_hard", "proporsi_lulus", "status"])


def laju_insersi(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    n = len(df)
    dup = df.qc_type.str.endswith("_DUP").sum()
    act = {"BLANK": (df.qc_type == "BLANK").sum() / n, "CRM": (df.qc_type == "CRM").sum() / n, "DUP": dup / n}
    return pd.DataFrame([{"jenis": k, "laju": round(float(v), 4), "target": cfg["insersi_target"][k],
                          "status": "LULUS" if v >= cfg["insersi_target"][k] else "PERINGATAN"}
                         for k, v in act.items()])


def status_batch(blank: pd.DataFrame, crm: pd.DataFrame) -> pd.DataFrame:
    rows = pd.concat([blank[["batch", "status"]], crm[["batch", "status"]]])
    if rows.empty:
        return pd.DataFrame(columns=["batch", "status"])
    urut = {"LULUS": 0, "PERINGATAN": 1, "GAGAL": 2}
    g = rows.assign(k=rows.status.map(urut)).groupby("batch").k.max()
    inv = {v: k for k, v in urut.items()}
    return g.map(inv).rename("status").reset_index()


def grafik_kontrol(crm: pd.DataFrame, out: Path) -> list[str]:
    if crm.empty:
        return []
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    files = []
    for (cid, a), g in crm.groupby(["crm_id", "analit"]):
        fig, ax = plt.subplots(figsize=(8, 3))
        x = np.arange(len(g))
        ax.plot(x, g.z, "o-", color="#1f3b57", ms=4)
        for k, ls in ((2, "--"), (3, "-")):
            ax.axhline(k, color="#b5651d", ls=ls, lw=0.8)
            ax.axhline(-k, color="#b5651d", ls=ls, lw=0.8)
        ax.axhline(0, color="grey", lw=0.6)
        ax.set_title(f"Kontrol CRM {cid} — {a} (z-score)")
        ax.set_xlabel("urutan analisis")
        ax.set_ylabel("z")
        f = out / f"kontrol_{cid}_{a}.png"
        fig.tight_layout()
        fig.savefig(f, dpi=120)
        plt.close(fig)
        files.append(f.name)
    return files


def jalankan(data: str, config: str | None, out: str) -> dict:
    cfg = muat_config(config)
    df = pd.read_csv(data)
    wajib = {"sample_id", "batch", "qc_type"}
    if not wajib.issubset(df.columns):
        raise SystemExit(f"Kolom wajib hilang: {wajib - set(df.columns)}")
    for k in ("crm_id", "parent_id"):
        if k not in df:
            df[k] = None
    df["qc_type"] = df.qc_type.str.upper().str.strip()
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)

    blank = cek_blank(df, cfg)
    crm, bias = cek_crm(df, cfg)
    dup = cek_duplikat(df, cfg)
    ins = laju_insersi(df, cfg)
    batch = status_batch(blank, crm)
    gambar = grafik_kontrol(crm, o)
    for nama, t in (("blank", blank), ("crm", crm), ("bias_crm", bias), ("duplikat", dup),
                    ("insersi", ins), ("status_batch", batch)):
        t.to_csv(o / f"{nama}.csv", index=False)

    gagal_batch = batch[batch.status == "GAGAL"].batch.tolist()
    ringkas = {
        "n_sampel": int(len(df)),
        "n_batch": int(df.batch.nunique()),
        "batch_gagal": gagal_batch,
        "blank_gagal": int((blank.status == "GAGAL").sum()),
        "crm_gagal": int((crm.status == "GAGAL").sum()),
        "crm_peringatan": int((crm.status == "PERINGATAN").sum()),
        "duplikat_gagal": dup[dup.status == "GAGAL"][["tipe", "analit"]].to_dict("records"),
        "bias_peringatan": bias[bias.status == "PERINGATAN"][["crm_id", "analit", "bias"]].to_dict("records"),
        "status": "GAGAL" if gagal_batch or (dup.status == "GAGAL").any() else "LULUS",
    }
    (o / "ringkasan.json").write_text(json.dumps(ringkas, indent=2, ensure_ascii=False))

    def md(t: pd.DataFrame) -> str:
        if t.empty:
            return "_(tidak ada data)_\n"
        cols = list(t.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)]
        return "\n".join(lines) + "\n"

    lap = [f"# Laporan QA/QC Assay\n\nStatus keseluruhan: **{ringkas['status']}**  \n",
           f"Sampel: {ringkas['n_sampel']} | Batch: {ringkas['n_batch']} | Batch gagal: "
           f"{', '.join(map(str, gagal_batch)) or '-'}\n",
           "\n> Ambang = praktik industri; ditetapkan CPI di config. Batch GAGAL wajib re-assay/investigasi "
           "sebelum data dipakai untuk estimasi.\n",
           "\n## Status per batch\n", md(batch),
           "\n## Blank\n", md(blank[blank.status != "LULUS"]) if not blank.empty else md(blank),
           "\n## CRM (non-LULUS)\n", md(crm[crm.status != "LULUS"]) if not crm.empty else md(crm),
           "\n## Bias CRM\n", md(bias), "\n## Duplikat (HARD)\n", md(dup), "\n## Laju insersi\n", md(ins)]
    lap += [f"\n![{g}]({g})\n" for g in gambar]
    (o / "laporan_qaqc.md").write_text("".join(lap))
    (o / "ringkasan_pr.md").write_text(
        f"### QA/QC assay: **{ringkas['status']}**\n"
        f"- Batch gagal: {', '.join(map(str, gagal_batch)) or 'tidak ada'}\n"
        f"- Blank gagal: {ringkas['blank_gagal']}, CRM gagal/peringatan: {ringkas['crm_gagal']}/{ringkas['crm_peringatan']}\n"
        f"- Duplikat gagal: {len(ringkas['duplikat_gagal'])}, bias CRM > ambang: {len(ringkas['bias_peringatan'])}\n"
        "Detail: artefak `laporan-qaqc`.\n")
    return ringkas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--config")
    ap.add_argument("--out", default="laporan_qaqc")
    a = ap.parse_args(argv)
    r = jalankan(a.data, a.config, a.out)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 1 if r["status"] == "GAGAL" else 0


if __name__ == "__main__":
    sys.exit(main())
