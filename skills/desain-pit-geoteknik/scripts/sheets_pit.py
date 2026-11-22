"""Lembar gambar PDF/PNG desain pit: denah, penampang, 3D, geoteknik, grade-tonnage & kepatuhan."""
from __future__ import annotations

import datetime as _dt
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

INK, MUTED, ACC = "#1d2327", "#6b7378", "#b3261e"
CREST, TOE, RAMP, SHELL = "#b3261e", "#2f5f8f", "#c48a1a", "#7a3fa0"
OK, BAD = "#4f8a5b", "#b3261e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.edgecolor": INK, "axes.linewidth": 0.6})


def _frame(fig, cfg, judul, no, total):
    fig.patches.append(plt.Rectangle((0.01, 0.01), 0.98, 0.98, transform=fig.transFigure, fill=False, lw=1.0, ec=INK))
    ax = fig.add_axes([0.70, 0.015, 0.285, 0.085]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=0.8, ec=INK))
    ax.plot([0, 1], [0.55, 0.55], lw=0.5, c=INK); ax.plot([0.62, 0.62], [0, 0.55], lw=0.5, c=INK)
    ax.text(0.02, 0.78, cfg.get("perusahaan") or "-", fontsize=8, weight="bold", va="center")
    ax.text(0.02, 0.63, cfg["proyek"], fontsize=6.5, va="center", color=MUTED)
    ax.text(0.02, 0.36, judul, fontsize=8.5, weight="bold", va="center")
    ax.text(0.02, 0.14, "Acuan: Kepmen ESDM 1827 K/30/MEM/2018", fontsize=5.5, va="center", color=MUTED)
    ax.text(0.64, 0.36, f"Lembar {no}/{total}", fontsize=7, va="center")
    ax.text(0.64, 0.14, f"{_dt.date.today():%d-%m-%Y}  |  EPSG {cfg.get('epsg') or '-'}", fontsize=5.5, va="center", color=MUTED)


def render(cfg, s, benches, crest_runs, toe_runs, ramp_runs, shell_rings, eg_pts, eg_tris, fin_pts, fin_tris,
           secs, ev, bm, ton, ore, in_design, pdf_path, out_dir, H):
    A3 = (16.54, 11.69)
    total = 5
    figs = []
    g = s["geometri"]

    # 1 DENAH
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.04, 0.12, 0.62, 0.84])
    tri = mtri.Triangulation(eg_pts[:, 0], eg_pts[:, 1], eg_tris)
    lv = np.arange(math.floor(eg_pts[:, 2].min() / 5) * 5, eg_pts[:, 2].max() + 5, 5)
    ax.tricontour(tri, eg_pts[:, 2], levels=lv, colors="#b9c0c4", linewidths=0.35)
    ftri = mtri.Triangulation(fin_pts[:, 0], fin_pts[:, 1], fin_tris)
    ax.tricontourf(ftri, fin_pts[:, 2], levels=30, cmap="Greys_r", alpha=0.35)
    for z, r in shell_rings:
        ax.plot(r[:, 0], r[:, 1], c=SHELL, lw=0.3, alpha=0.5)
    for z, r in toe_runs:
        ax.plot(r[:, 0], r[:, 1], c=TOE, lw=0.6)
    for z, r in crest_runs:
        ax.plot(r[:, 0], r[:, 1], c=CREST, lw=0.7)
    for r in ramp_runs:
        ax.plot(r[:, 0], r[:, 1], c=RAMP, lw=1.4, ls=(0, (6, 2)))
        ax.annotate("", xy=r[-1, :2], xytext=r[-2, :2], arrowprops=dict(arrowstyle="-|>", color=RAMP, lw=1))
    for b in benches:
        p = np.array(b["toe"].exterior.coords)
        k = int(np.argmax(p[:, 1]))
        ax.text(p[k, 0], p[k, 1] + 1.5, f"{b['z']:.0f}", fontsize=5, color=TOE, ha="center")
    for sd in secs:
        ax.plot([sd["a"][0], sd["b"][0]], [sd["a"][1], sd["b"][1]], c=INK, lw=0.6, ls=(0, (10, 3, 2, 3)))
        ax.text(*sd["a"], sd["nama"].split("-")[0], fontsize=8, weight="bold", ha="right")
        ax.text(*sd["b"], sd["nama"].split("-")[1], fontsize=8, weight="bold")
    ax.set_aspect("equal"); ax.grid(lw=0.2, c="#e1e4e6")
    ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    ax.set_title("DENAH DESAIN PIT", loc="left", fontsize=10, weight="bold")
    xb = np.concatenate([r[:, 0] for _, r in crest_runs]) if crest_runs else fin_pts[:, 0]
    yb = np.concatenate([r[:, 1] for _, r in crest_runs]) if crest_runs else fin_pts[:, 1]
    ax.set_xlim(xb.min() - 60, xb.max() + 60); ax.set_ylim(yb.min() - 60, yb.max() + 60)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], c=CREST, label="Crest jenjang"), Line2D([], [], c=TOE, label="Toe jenjang"),
                       Line2D([], [], c=RAMP, ls="--", lw=1.4, label="Garis tengah ramp"),
                       Line2D([], [], c=SHELL, lw=0.5, label="Pit shell optimasi"),
                       Line2D([], [], c="#b9c0c4", label="Kontur topografi 5 m")], loc="lower right", fontsize=6)
    axt = fig.add_axes([0.69, 0.30, 0.29, 0.66]); axt.axis("off")
    c, o = s["cadangan"]["desain"], s["cadangan"]["optimasi"]
    txt = (f"PARAMETER DESAIN\n"
           f"Tinggi jenjang      {g['tinggi_jenjang']:.1f} m\n"
           f"Sudut muka jenjang  {g['sudut_muka']:.0f} deg\n"
           f"Lebar berm          {g['lebar_berm']:.1f} m\n"
           f"Sudut inter-ramp    {g['sudut_inter_ramp']:.1f} deg\n"
           f"Sudut keseluruhan   {g['sudut_keseluruhan']:.1f} deg\n"
           f"Lebar ramp          {g['lebar_ramp']:.2f} m\n"
           f"Grade ramp          {g['grade_ramp'] * 100:.1f} %\n"
           f"Dasar pit           EL {g['dasar_pit']:.1f}\n"
           f"Tinggi dinding maks {g['tinggi_dinding_maks']:.1f} m\n"
           f"Jumlah jenjang      {g['jumlah_jenjang']}\n\n"
           f"TONASE                 OPTIMASI        DESAIN\n"
           f"Bijih (t)        {o['bijih_ton']:>14,.0f} {c['bijih_ton']:>13,.0f}\n"
           f"Kadar rata       {o['kadar_rata']:>14.3f} {c['kadar_rata']:>13.3f}\n"
           f"Waste (t)        {o['waste_ton']:>14,.0f} {c['waste_ton']:>13,.0f}\n"
           f"Nisbah kupas     {o['nisbah_kupas'] or 0:>14.2f} {c['nisbah_kupas'] or 0:>13.2f}\n"
           f"Nilai (USD)      {o['nilai']:>14,.0f} {c['nilai']:>13,.0f}\n"
           f"Cut-off kadar    {s['cutoff']:.3f} {cfg['ekonomi']['satuan_kadar']}")
    axt.text(0, 1, txt, family="DejaVu Sans Mono", fontsize=7, va="top")
    _frame(fig, cfg, "Denah Desain Pit", 1, total)
    figs.append(("denah", fig))

    # 2 PENAMPANG
    fig = plt.figure(figsize=A3)
    import matplotlib.cm as cm
    gmax = float(np.percentile(bm["kadar"], 99.5))
    norm = matplotlib.colors.Normalize(0, gmax)
    for i, sd in enumerate(secs[:3]):
        ax = fig.add_axes([0.05, 0.62 - i * 0.30 if len(secs) > 2 else 0.58 - i * 0.43, 0.90, 0.26 if len(secs) > 2 else 0.36])
        bl = sd["blocks"]
        dx, _, dz = sd["dims"]
        for s_, z_, gr, mi, de in zip(bl["s"], bl["z"], bl["kadar"], bl["mined"], bl["desain"]):
            ax.add_patch(plt.Rectangle((s_ - dx / 2, z_ - dz / 2), dx, dz, fc=cm.viridis(norm(gr)), ec="white", lw=0.15, alpha=0.9 if de else 0.35))
        ax.plot(sd["s"], sd["zt"], c=MUTED, lw=0.9, ls="--", label="Topografi")
        ax.plot(sd["s"], sd["zd"], c=ACC, lw=1.3, label="Desain pit")
        ax.set_xlim(0, sd["s"][-1]); ax.set_aspect("equal", adjustable="datalim")
        ax.grid(lw=0.2, c="#e1e4e6")
        ax.set_title(f"PENAMPANG {sd['nama']}", loc="left", fontsize=9, weight="bold")
        ax.set_ylabel("Elevasi (m)")
        ax.legend(loc="lower right", fontsize=6)
    cax = fig.add_axes([0.05, 0.08, 0.3, 0.012])
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap="viridis"), cax=cax, orientation="horizontal", label=f"Kadar ({cfg['ekonomi']['satuan_kadar']}); blok pudar = di luar desain")
    _frame(fig, cfg, "Penampang Pit & Block Model", 2, total)
    figs.append(("penampang", fig))

    # 3 3D
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.84], projection="3d")
    ax.plot_trisurf(fin_pts[:, 0], fin_pts[:, 1], fin_pts[:, 2], triangles=fin_tris, cmap="terrain", lw=0, antialiased=False, alpha=0.95)
    for _, r in crest_runs:
        ax.plot(r[:, 0], r[:, 1], r[:, 2] + 0.2, c=CREST, lw=0.5)
    for r in ramp_runs:
        ax.plot(r[:, 0], r[:, 1], r[:, 2] + 0.5, c=RAMP, lw=1.2)
    ax.set_box_aspect((np.ptp(fin_pts[:, 0]), np.ptp(fin_pts[:, 1]), np.ptp(fin_pts[:, 2]) * 1.5))
    ax.view_init(elev=38, azim=-55)
    ax.set_title("MODEL 3D PERMUKAAN AKHIR (vertikal x1,5)", loc="left", fontsize=10, weight="bold")
    ax.tick_params(labelsize=5)
    _frame(fig, cfg, "Model 3D Pit", 3, total)
    figs.append(("3d", fig))

    # 4 GEOTEKNIK
    fig = plt.figure(figsize=A3)
    for i, (jenis, v) in enumerate(ev.items()):
        ax = fig.add_axes([0.05 + i * 0.315, 0.40, 0.29, 0.52])
        xz = np.array(v["xz"])
        ax.fill_between(xz[:, 0], xz[:, 1], xz[:, 1].min() - 0.3 * np.ptp(xz[:, 1]) - 5, color="#e4ddd0")
        ax.plot(xz[:, 0], xz[:, 1], c=INK, lw=1)
        for L in cfg["geoteknik"]["material"].get("lapisan", [])[1:]:
            if xz[:, 1].min() - 20 < L["z_atas"] < xz[:, 1].max():
                ax.axhline(L["z_atas"], c=MUTED, lw=0.6, ls="--")
                ax.text(xz[0, 0], L["z_atas"] - 1, f"  batas {L['nama']} EL {L['z_atas']:.0f}", fontsize=5.5, color=MUTED, va="top")
        if v["lingkaran"]:
            xc, zc, R = v["lingkaran"]
            t = np.linspace(0, 2 * np.pi, 400)
            xx, zz = xc + R * np.cos(t), zc + R * np.sin(t)
            surf = np.interp(xx, xz[:, 0], xz[:, 1])
            m = zz <= surf
            ax.plot(np.where(m, xx, np.nan), np.where(m, zz, np.nan), c=ACC, lw=1.2)
            ax.plot(xc, zc, "+", c=ACC)
        ok = v["status"] == "MEMENUHI"
        ax.set_aspect("equal", adjustable="datalim"); ax.grid(lw=0.2, c="#e1e4e6")
        ax.set_title(f"Lereng {jenis.replace('_', '-')}  H={v['tinggi']:.0f} m  {v['sudut']:.1f} deg", loc="left", fontsize=8, weight="bold")
        sy = v["syarat"]
        ax.text(0.02, 0.97, f"FK statis  {v['fk_statis']:.2f}  (>= {sy['fk_statis']})\n" +
                (f"FK dinamis {v['fk_dinamis']:.2f}  (>= {sy['fk_dinamis']})\n" if sy['fk_dinamis'] and v['fk_dinamis'] else "") +
                f"PoF        {v['pof'] * 100:.1f}%  (<= {sy['pof_maks'] * 100:.0f}%)\n{v['status']}",
                transform=ax.transAxes, va="top", family="DejaVu Sans Mono", fontsize=6.5, color=OK if ok else BAD,
                bbox=dict(fc="white", ec=OK if ok else BAD, lw=0.6))
    mt = cfg["geoteknik"]["material"]
    lines = ["MATERIAL (lapisan, dari atas):"]
    for L in mt.get("lapisan", [mt]):
        lines.append(f"  {L.get('nama', 'material')}: gamma {L['gamma']} kN/m3, c {L['c']} kPa (sd {L.get('sd_c', 0)}), phi {L['phi']} deg (sd {L.get('sd_phi', 0)})"
                     + (f", di bawah EL {L['z_atas']:.0f}" if L.get('z_atas', 1e9) < 1e8 else ""))
    lines.append(f"ru = {cfg['geoteknik']['ru']}, kh = {cfg['geoteknik']['kh']} (pseudo-statik), CoF = {cfg['geoteknik']['keparahan_longsor']}")
    lines.append("Metode: Bishop disederhanakan, grid pusat x titik keluar + penghalusan; PoF Monte Carlo (normal) pada c, phi, gamma.")
    lines.append("Syarat: Kepmen ESDM 1827 K/30/MEM/2018 Tabel 1 hal. 57. Verifikasi akhir dengan Slide2/RS2 + analisis kinematik.")
    fig.text(0.05, 0.33, "\n".join(lines), fontsize=7.5, va="top", family="DejaVu Sans Mono")
    _frame(fig, cfg, "Analisis Kestabilan Lereng", 4, total)
    figs.append(("geoteknik", fig))

    # 5 GRADE-TONNAGE + KEPATUHAN
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.06, 0.45, 0.42, 0.48])
    m = in_design
    cogs = np.linspace(0, np.percentile(bm["kadar"][m], 98) if m.any() else 1, 40)
    tt, gg = [], []
    for cg in cogs:
        sel = m & (bm["kadar"] >= cg)
        t = ton[sel].sum()
        tt.append(t / 1e6)
        gg.append((bm["kadar"][sel] * ton[sel]).sum() / t if t > 0 else np.nan)
    ax.plot(cogs, tt, c=INK, lw=1.2)
    ax.set_xlabel(f"Cut-off kadar ({cfg['ekonomi']['satuan_kadar']})"); ax.set_ylabel("Tonase di atas cut-off (Mt)")
    ax2 = ax.twinx(); ax2.plot(cogs, gg, c=ACC, lw=1.2); ax2.set_ylabel("Kadar rata-rata", color=ACC)
    ax.axvline(s["cutoff"], c=MUTED, ls="--", lw=0.8)
    ax.set_title("KURVA GRADE-TONNAGE (dalam pit desain)", loc="left", fontsize=9, weight="bold")
    ax.grid(lw=0.2, c="#e1e4e6")
    axr = fig.add_axes([0.53, 0.12, 0.45, 0.82]); axr.axis("off")
    axr.set_title("PEMERIKSAAN KEPATUHAN", loc="left", fontsize=9, weight="bold")
    yy = 0.96
    for ch in s["pemeriksaan"]:
        ok = ch["status"] == "MEMENUHI"
        axr.text(0, yy, "OK" if ok else "X", color=OK if ok else BAD, weight="bold", fontsize=7, va="top")
        axr.text(0.05, yy, f"{ch['item']}\n{ch['nilai']}  |  syarat {ch['syarat']}  |  {ch['dasar']}", fontsize=6, va="top")
        yy -= 0.07
    _frame(fig, cfg, "Grade-Tonnage & Kepatuhan", 5, total)
    figs.append(("kepatuhan", fig))

    with PdfPages(pdf_path) as pdf:
        for name, f in figs:
            pdf.savefig(f)
            f.savefig(os.path.join(out_dir, f"lembar_{name}.png"), dpi=110)
            plt.close(f)
