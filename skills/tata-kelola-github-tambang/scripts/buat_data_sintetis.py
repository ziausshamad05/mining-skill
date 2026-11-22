#!/usr/bin/env python3
"""Bangkitkan data sintetis (BUKAN data proyek) untuk uji CI: assay QA/QC dan event FMS."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def assay(n_batch=8, per_batch=40, seed=7, batch_rusak=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    crm = {"CRM-DEMO-LOW": (1.20, 0.03, 0.050, 0.003, 18.0, 0.4), "CRM-DEMO-HIGH": (2.10, 0.04, 0.110, 0.005, 25.0, 0.5)}
    rows, sid = [], 0
    for b in range(1, n_batch + 1):
        asli = []
        for _ in range(per_batch):
            sid += 1
            ni = float(np.clip(rng.lognormal(np.log(1.4), 0.35), 0.2, 3.5))
            r = {"sample_id": f"S{sid:05d}", "batch": f"B{b:03d}", "qc_type": "ORIGINAL", "crm_id": "", "parent_id": "",
                 "Ni": round(ni, 3), "Co": round(ni * 0.06 * rng.uniform(0.7, 1.3), 4), "Fe": round(10 + ni * 8 * rng.uniform(0.8, 1.2), 2)}
            rows.append(r)
            asli.append(r)
        sid += 1
        bl = 0.08 if b == batch_rusak else 0.01  # kontaminasi di batch rusak
        rows.append({"sample_id": f"S{sid:05d}", "batch": f"B{b:03d}", "qc_type": "BLANK", "crm_id": "", "parent_id": "",
                     "Ni": round(abs(rng.normal(bl, 0.005)), 3), "Co": 0.001, "Fe": 0.05})
        for cid, (ni, sdn, co, sdc, fe, sdf) in crm.items():
            sid += 1
            geser = 4 * sdn if (b == batch_rusak and cid == "CRM-DEMO-HIGH") else 0
            rows.append({"sample_id": f"S{sid:05d}", "batch": f"B{b:03d}", "qc_type": "CRM", "crm_id": cid, "parent_id": "",
                         "Ni": round(rng.normal(ni, sdn * 0.8) + geser, 3), "Co": round(rng.normal(co, sdc * 0.8), 4),
                         "Fe": round(rng.normal(fe, sdf * 0.8), 2)})
        for tipe, cv in (("FIELD_DUP", 0.06), ("COARSE_DUP", 0.03), ("PULP_DUP", 0.015)):
            for p in rng.choice(len(asli), 2, replace=False):
                sid += 1
                o = asli[p]
                rows.append({"sample_id": f"S{sid:05d}", "batch": o["batch"], "qc_type": tipe, "crm_id": "", "parent_id": o["sample_id"],
                             "Ni": round(o["Ni"] * rng.normal(1, cv), 3), "Co": round(o["Co"] * rng.normal(1, cv), 4),
                             "Fe": round(o["Fe"] * rng.normal(1, cv), 2)})
    return pd.DataFrame(rows)


def fms(seed=3, hari=2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    t0 = pd.Timestamp("2026-11-01 07:00")
    for u, prof in (("DT-001", (0.80, 0.12, 0.08)), ("DT-002", (0.60, 0.15, 0.25)), ("EX-001", (0.78, 0.15, 0.07))):
        t = t0
        while t < t0 + pd.Timedelta(days=hari):
            st = rng.choice(["WORKING", "STANDBY", "BREAKDOWN"], p=prof)
            dur = pd.Timedelta(minutes=int(rng.integers(20, 150)))
            rows.append({"unit_id": u, "operator_id": f"EMP{rng.integers(100, 120)}", "waktu_mulai": t, "waktu_selesai": t + dur,
                         "status": st, "muatan_ton": round(float(rng.uniform(20, 40)), 1) if st == "WORKING" and u.startswith("DT") else 0})
            t += dur
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sintetis")
    out.mkdir(parents=True, exist_ok=True)
    assay().to_csv(out / "assay_qaqc.csv", index=False)
    fms().to_csv(out / "fms_event.csv", index=False)
    print("data sintetis ditulis ke", out)
