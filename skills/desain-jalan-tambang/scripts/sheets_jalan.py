"""Lembar gambar PDF + PNG untuk desain jalan tambang (denah, profil, penampang, 3D, mass-haul, laporan)."""
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

import cad_export as cx  # noqa: E402

INK = "#1d2327"
MUTED = "#6b7378"
CUT = "#c8743a"
FILL = "#4f8a5b"
ROAD = "#2b2f33"
EG = "#9aa3a8"
ACC = "#b3261e"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.edgecolor": INK, "axes.linewidth": 0.6,
                     "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK})


def _frame(fig, cfg, judul, no, total):
    """Kop gambar sederhana di kanan bawah (A3 lanskap)."""
    fig.patches.append(plt.Rectangle((0.01, 0.01), 0.98, 0.98, transform=fig.transFigure, fill=False, lw=1.0, ec=INK))
    ax = fig.add_axes([0.70, 0.015, 0.285, 0.085])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=0.8, ec=INK))
    ax.plot([0, 1], [0.55, 0.55], lw=0.5, c=INK)
    ax.plot([0.62, 0.62], [0, 0.55], lw=0.5, c=INK)
    ax.text(0.02, 0.78, cfg.get("perusahaan") or "-", fontsize=8, weight="bold", va="center")
    ax.text(0.02, 0.63, cfg["proyek"], fontsize=6.5, va="center", color=MUTED)
    ax.text(0.02, 0.36, judul, fontsize=8.5, weight="bold", va="center")
    ax.text(0.02, 0.14, "Acuan: Kepmen ESDM 1827 K/30/MEM/2018", fontsize=5.5, va="center", color=MUTED)
    ax.text(0.64, 0.36, f"Lembar {no}/{total}", fontsize=7, va="center")
    ax.text(0.64, 0.14, f"{_dt.date.today():%d-%m-%Y}  |  EPSG {cfg.get('epsg') or '-'}", fontsize=5.5, va="center", color=MUTED)


def render(cfg, al, prof, eg_prof, xs, vol_rows, summary, eg_pts, eg_tris, cp_pts, cp_tris, cpts, ctris, pdf_path, out_dir):
    total = 6
    A3 = (16.54, 11.69)
    figs = []

    # ---------------------------------------------------------------- 1 DENAH
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.04, 0.12, 0.64, 0.84])
    tri = mtri.Triangulation(eg_pts[:, 0], eg_pts[:, 1], eg_tris)
    z = eg_pts[:, 2]
    lv = np.arange(math.floor(z.min()), math.ceil(z.max()) + 1, 1.0)
    ax.tricontour(tri, z, levels=lv, colors=EG, linewidths=0.25)
    cs = ax.tricontour(tri, z, levels=lv[lv % 5 == 0], colors=MUTED, linewidths=0.6)
    ax.clabel(cs, fmt="%d", fontsize=5)
    # klasifikasi galian/timbunan per segitiga koridor
    cen = cpts[ctris].mean(axis=1)
    dz = cen[:, 2] - np.interp(0, [0], [0])  # placeholder
    from scipy.interpolate import LinearNDInterpolator
    egi = LinearNDInterpolator(eg_pts[:, :2], eg_pts[:, 2])
    dz = cen[:, 2] - egi(cen[:, 0], cen[:, 1])
    ctri = mtri.Triangulation(cpts[:, 0], cpts[:, 1], ctris)
    colors = np.where(dz < 0, 0.0, 1.0)
    ax.tripcolor(ctri, facecolors=colors, cmap=matplotlib.colors.ListedColormap([CUT, FILL]), alpha=0.35, edgecolors="none")
    from haul_road import _feature_lines  # noqa
    for name, runs in _feature_lines(xs).items():
        for r in runs:
            r = np.array(r)
            if name.startswith("ETW"):
                ax.plot(r[:, 0], r[:, 1], c=ROAD, lw=0.9)
            elif name.startswith("BERM_TO"):
                ax.plot(r[:, 0], r[:, 1], c="#7a4f2a", lw=0.6)
            elif name.startswith("DTCH_BO"):
                ax.plot(r[:, 0], r[:, 1], c="#2f6fb0", lw=0.5, ls="--")
            elif name.startswith("DAYL"):
                ax.plot(r[:, 0], r[:, 1], c=ACC, lw=0.5, ls=(0, (4, 2)))
    ss = np.arange(al.sta0, al.sta_end, 1.0)
    cl = np.array([al.at(s)[0] for s in ss])
    ax.plot(cl[:, 0], cl[:, 1], c=ACC, lw=0.7, ls=(0, (8, 2, 2, 2)))
    for s in np.arange(al.sta0, al.sta_end + 1e-6, 20.0):
        p, t, _, _ = al.at(s)
        n = np.array([t[1], -t[0]])
        L = 4 if abs(s % 100) < 1e-6 else 2
        ax.plot([p[0] - n[0] * L, p[0] + n[0] * L], [p[1] - n[1] * L, p[1] + n[1] * L], c=INK, lw=0.5)
        if abs(s % 100) < 1e-6:
            ang = math.degrees(math.atan2(n[1], n[0]))
            ang = ang - 180 if abs(ang) > 90 else ang
            q = p + n * 14
            ax.text(q[0], q[1], cx.fmt_sta(s), fontsize=5.5, rotation=ang, ha="center", va="center")
    for c in al.curves:
        e = c["elem"]
        ax.plot(*e.pi, marker="^", ms=3, c=INK)
        ax.text(e.pi[0], e.pi[1] + 10, f"PI{c['pi_no']}", fontsize=6, ha="center", weight="bold")
        for q, lab in ((e.start, "PC"), (e.end, "PT")):
            ax.plot(*q, "o", ms=2, c=INK)
            ax.text(q[0] + 3, q[1] - 6, lab, fontsize=5)
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    ax.grid(lw=0.2, c="#d8dcde")
    ax.set_title("DENAH ALINYEMEN JALAN TAMBANG", loc="left", fontsize=10, weight="bold")
    # panah utara & legenda
    xl, yl = ax.get_xlim(), ax.get_ylim()
    ax.annotate("U", xy=(xl[1] - 25, yl[1] - 15), xytext=(xl[1] - 25, yl[1] - 50), ha="center", fontsize=9, weight="bold",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1))
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    hand = [Line2D([], [], c=ACC, lw=0.7, ls=(0, (8, 2, 2, 2)), label="Garis tengah (CL)"),
            Line2D([], [], c=ROAD, lw=0.9, label="Tepi jalur lalu lintas"),
            Line2D([], [], c="#7a4f2a", lw=0.6, label="Tanggul pengaman"),
            Line2D([], [], c="#2f6fb0", lw=0.5, ls="--", label="Saluran drainase"),
            Line2D([], [], c=ACC, lw=0.5, ls=(0, (4, 2)), label="Daylight"),
            Patch(fc=CUT, alpha=0.35, label="Galian"), Patch(fc=FILL, alpha=0.35, label="Timbunan"),
            Line2D([], [], c=MUTED, lw=0.6, label="Kontur EG (1 m / 5 m)")]
    ax.legend(handles=hand, loc="lower right", fontsize=6, frameon=True, framealpha=0.9)
    # tabel tikungan
    axt = fig.add_axes([0.70, 0.55, 0.285, 0.41]); axt.axis("off")
    axt.set_title("DATA TIKUNGAN", loc="left", fontsize=8, weight="bold")
    rows = [[f"PI{c['pi_no']}", c["arah"], f"{c['radius']:.0f}", f"{c['delta_deg']:.2f}", f"{c['T']:.1f}", f"{c['L']:.1f}",
             f"{c.get('e', 0) * 100:.1f}%", f"{c.get('W', 0):.2f}", cx.fmt_sta(c["sta_pc"]), cx.fmt_sta(c["sta_pt"])] for c in summary["tikungan"]]
    if rows:
        tb = axt.table(cellText=rows, colLabels=["PI", "Arah", "R", "Delta", "T", "L", "e", "W", "PC", "PT"], loc="upper left", cellLoc="center")
        tb.auto_set_font_size(False); tb.set_fontsize(5.8); tb.scale(1, 1.25)
    gtxt = (f"Unit terbesar : {cfg['unit_terbesar']['nama']}\n"
            f"Lebar unit     : {cfg['unit_terbesar']['lebar_m']:.2f} m  |  D roda {cfg['unit_terbesar']['diameter_roda_m']:.2f} m\n"
            f"Jumlah jalur   : {cfg['jumlah_jalur']}  |  V rencana {cfg['kecepatan_rencana_kmh']:.0f} km/j\n"
            f"Lebar lurus    : {summary['lebar_lurus_m']:.2f} m (>= {cfg['_kriteria']['lebar_jalan_dua_jalur_min_x_lebar_unit'] if cfg['jumlah_jalur'] >= 2 else 2}x lebar unit)\n"
            f"Tanggul        : {summary['tanggul_tinggi_m']:.2f} m (>= 3/4 D roda)\n"
            f"Grade maks     : {summary['grade_maks_pct']:.2f}% (<= 12%)\n"
            f"Cross fall     : {max(cfg['kemiringan_melintang'], 0.02) * 100:.1f}% (>= 2%)\n"
            f"Panjang        : {summary['panjang_m']:.1f} m\n"
            f"Galian / Timb. : {summary['volume_galian_m3']:,.0f} / {summary['volume_timbunan_m3']:,.0f} m3")
    axt.text(0, 0.38, gtxt, fontsize=6.5, family="DejaVu Sans Mono", va="top")
    _frame(fig, cfg, "Denah & Data Geometri", 1, total)
    figs.append(("denah", fig))

    # ---------------------------------------------------------------- 2 PROFIL
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.06, 0.36, 0.90, 0.58])
    s_eg = np.array([p[0] for p in eg_prof]); z_eg = np.array([p[1] for p in eg_prof])
    sf = np.arange(al.sta0, al.sta_end + 0.1, 1.0); zf = prof.z(sf)
    ze = np.interp(sf, s_eg, z_eg)
    ax.fill_between(sf, zf, ze, where=zf < ze, color=CUT, alpha=0.35, lw=0)
    ax.fill_between(sf, zf, ze, where=zf >= ze, color=FILL, alpha=0.35, lw=0)
    ax.plot(s_eg, z_eg, c=MUTED, lw=0.8, ls="--", label="Tanah asli (EG)")
    ax.plot(sf, zf, c=ACC, lw=1.2, label="Desain (FG)")
    g = prof.grades()
    for i, (st, zz, L) in enumerate(prof.pvis):
        ax.plot(st, zz, "o", ms=3, mfc="white", mec=INK)
        ax.annotate(f"PVI {cx.fmt_sta(st)}\nEL {zz:.2f}" + (f"\nL={L:.0f} m" if L else ""), (st, zz), xytext=(0, 18),
                    textcoords="offset points", ha="center", fontsize=5.5, arrowprops=dict(arrowstyle="-", lw=0.4))
        if L:
            ax.plot([st - L / 2, st + L / 2], [prof.z(st - L / 2)[0], prof.z(st + L / 2)[0]], "|", c=INK, ms=6)
        if i < len(g):
            st2, z2, _ = prof.pvis[i + 1]
            col = ACC if abs(g[i]) > 0.12 else INK
            ax.text((st + st2) / 2, (zz + z2) / 2 - 2.5, f"{g[i] * 100:+.2f}%", ha="center", fontsize=7, color=col, weight="bold")
    for c in al.curves:
        ax.axvspan(c["sta_pc"], c["sta_pt"], color="#e9edef", lw=0, zorder=0)
    ax.set_xlim(al.sta0, al.sta_end)
    ax.set_ylabel("Elevasi (m)")
    ax.grid(lw=0.2, c="#d8dcde")
    ax.legend(loc="upper left", fontsize=7)
    ax.set_title(f"PROFIL MEMANJANG {cfg['alinyemen'].get('nama', '')}", loc="left", fontsize=10, weight="bold")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: cx.fmt_sta(v)))
    # pita data
    axb = fig.add_axes([0.06, 0.13, 0.90, 0.20], sharex=ax); axb.set_ylim(0, 4); axb.set_yticks([])
    labels = ["Elev EG", "Elev FG", "Galian(+)/Timb(-)", "Grade"]
    for k, lab in enumerate(labels):
        axb.axhline(k, c=INK, lw=0.4)
        axb.text(al.sta0 - (al.sta_end - al.sta0) * 0.005, 3.5 - k, lab, ha="right", va="center", fontsize=6)
    for st in np.arange(al.sta0, al.sta_end + 0.1, 50.0):
        zg = float(np.interp(st, s_eg, z_eg)); zz = float(prof.z(st)[0])
        axb.axvline(st, c="#d8dcde", lw=0.3)
        axb.text(st, 3.5, f"{zg:.2f}", rotation=90, ha="center", va="center", fontsize=5)
        axb.text(st, 2.5, f"{zz:.2f}", rotation=90, ha="center", va="center", fontsize=5)
        axb.text(st, 1.5, f"{zg - zz:+.2f}", rotation=90, ha="center", va="center", fontsize=5, color=CUT if zg > zz else FILL)
        axb.text(st, 0.5, f"{prof.grade_at(min(max(st, al.sta0 + 0.1), al.sta_end - 0.1)) * 100:.1f}%", rotation=90, ha="center", va="center", fontsize=5)
    axb.tick_params(labelsize=6)
    _frame(fig, cfg, "Profil Memanjang", 2, total)
    figs.append(("profil", fig))

    # ---------------------------------------------------------------- 3-4 PENAMPANG
    pick = [x for x in xs if abs(x["sta"] % 40) < 1e-6 or any(abs(x["sta"] - c["sta_pc"] - c["L"] / 2) < 1e-3 for c in al.curves)]
    pick = pick[:24]
    pages = [pick[:12], pick[12:24]]
    for pno, pg in enumerate(pages):
        fig = plt.figure(figsize=A3)
        for i, x in enumerate(pg):
            r, c = divmod(i, 4)
            ax = fig.add_axes([0.04 + c * 0.24, 0.72 - r * 0.29, 0.215, 0.22])
            gg = x["ground"]
            d = np.array([(o, zz) for o, zz, _ in x["design"]])
            omin, omax = d[0, 0] - 6, d[-1, 0] + 6
            m = (gg[:, 0] >= omin) & (gg[:, 0] <= omax)
            oo = np.linspace(d[0, 0], d[-1, 0], 300)
            zd = np.interp(oo, d[:, 0], d[:, 1]); zg = np.interp(oo, gg[:, 0], gg[:, 1])
            ax.fill_between(oo, zd, zg, where=zd < zg, color=CUT, alpha=0.4, lw=0)
            ax.fill_between(oo, zd, zg, where=zd >= zg, color=FILL, alpha=0.4, lw=0)
            ax.plot(gg[m, 0], gg[m, 1], c=MUTED, lw=0.7, ls="--")
            ax.plot(d[:, 0], d[:, 1], c=ACC, lw=1.0)
            ax.axvline(0, c=INK, lw=0.4, ls=(0, (6, 2, 1, 2)))
            ax.set_aspect("equal", adjustable="datalim")
            ax.grid(lw=0.2, c="#d8dcde")
            ax.tick_params(labelsize=5)
            ax.set_title(f"STA {cx.fmt_sta(x['sta'])}   EL CL {x['zc']:.2f}", fontsize=6.5, weight="bold", loc="left")
            ax.text(0.02, 0.04, f"G {x['cut']:.1f} m2 | T {x['fill']:.1f} m2 | W {x['lebar']:.1f} m" + (f" | e {x['e'] * 100:.1f}%" if x["e"] else ""),
                    transform=ax.transAxes, fontsize=5.2, color=INK, bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
        _frame(fig, cfg, f"Penampang Melintang ({pno + 1})", 3 + pno, total)
        figs.append((f"penampang{pno + 1}", fig))

    # ---------------------------------------------------------------- 5 3D + MASS HAUL
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.02, 0.30, 0.62, 0.64], projection="3d")
    sub = eg_tris[::3]
    ax.plot_trisurf(cp_pts[:, 0], cp_pts[:, 1], cp_pts[:, 2], triangles=cp_tris, cmap="gist_earth", lw=0, alpha=0.55, antialiased=True)
    ax.plot_trisurf(cpts[:, 0], cpts[:, 1], cpts[:, 2] + 0.05, triangles=ctris, color="#c9b48f", lw=0.05, edgecolor="#6d5b3c", alpha=1.0)
    ax.plot(cl[:, 0], cl[:, 1], prof.z(ss) + 0.3, c=ACC, lw=1.2)
    ax.set_box_aspect((np.ptp(cp_pts[:, 0]), np.ptp(cp_pts[:, 1]), np.ptp(cp_pts[:, 2]) * 3))
    ax.view_init(elev=32, azim=-60)
    ax.set_title("MODEL 3D KORIDOR (vertikal x3)", loc="left", fontsize=10, weight="bold")
    ax.tick_params(labelsize=5)
    del sub
    axm = fig.add_axes([0.06, 0.12, 0.58, 0.15])
    stv = [r["sta"] for r in vol_rows]
    axm.plot(stv, [r["kumulatif_massa"] for r in vol_rows], c=INK, lw=1)
    axm.axhline(0, c=MUTED, lw=0.5)
    axm.set_title("DIAGRAM MASS-HAUL (kumulatif galian - timbunan/faktor susut, m3)", loc="left", fontsize=7.5, weight="bold")
    axm.grid(lw=0.2, c="#d8dcde"); axm.tick_params(labelsize=6)
    axm.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: cx.fmt_sta(v)))
    axr = fig.add_axes([0.67, 0.12, 0.31, 0.85]); axr.axis("off")
    axr.set_title("PEMERIKSAAN KEPATUHAN", loc="left", fontsize=9, weight="bold")
    yy = 0.97
    for cchk in summary["pemeriksaan"]:
        ok = cchk["status"] == "MEMENUHI"
        axr.text(0.0, yy, "OK" if ok else "X", fontsize=7, weight="bold", color=FILL if ok else ACC, va="top")
        axr.text(0.07, yy, f"{cchk['item']}\n{cchk['nilai']}  |  syarat {cchk['syarat']}", fontsize=5.8, va="top", wrap=True)
        yy -= 0.052
        if yy < 0.05:
            break
    _frame(fig, cfg, "Model 3D, Mass-Haul & Kepatuhan", 5, total)
    figs.append(("3d", fig))

    # ---------------------------------------------------------------- 6 TIPIKAL PENAMPANG
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes([0.05, 0.40, 0.90, 0.52])
    tip = max(xs, key=lambda x: (x["sisi"].get(1) != x["sisi"].get(-1), x["cut"] + x["fill"]))
    d = np.array([(o, zz) for o, zz, _ in tip["design"]])
    dzc = d[:, 1] - tip["zc"]
    ax.plot(d[:, 0], dzc, c=ACC, lw=1.4)
    for (o, zz, code) in tip["design"]:
        if code in ("ETW", "SHLD", "BERM_TO", "DTCH_BO", "CL"):
            ax.annotate(code, (o, zz - tip["zc"]), xytext=(0, 10), textcoords="offset points", fontsize=6, ha="center")
    gg = tip["ground"]
    ax.plot(gg[:, 0], gg[:, 1] - tip["zc"], c=MUTED, ls="--", lw=0.7)
    ax.set_xlim(d[0, 0] - 5, d[-1, 0] + 5)
    ax.set_aspect("equal", adjustable="datalim"); ax.grid(lw=0.2, c="#d8dcde")
    ax.set_title(f"PENAMPANG TIPIKAL (STA {cx.fmt_sta(tip['sta'])}, elevasi relatif CL)", loc="left", fontsize=10, weight="bold")
    u = cfg["unit_terbesar"]
    ket = (f"Lebar jalur lalu lintas {summary['lebar_lurus_m']:.2f} m  |  bahu {cfg['bahu_m']} m  |  cross fall {max(cfg['kemiringan_melintang'], 0.02) * 100:.1f}% (crown)\n"
           f"Tanggul pengaman tinggi {summary['tanggul_tinggi_m']:.2f} m, lebar atas {cfg['tanggul']['lebar_atas_m']} m, sisi {cfg['tanggul']['kemiringan_sisi_HV']}H:1V  (>= 3/4 x D roda {u['diameter_roda_m']} m)\n"
           f"Saluran: dasar {cfg['saluran']['lebar_dasar_m']} m, dalam {cfg['saluran']['dalam_m']} m, sisi {cfg['saluran']['kemiringan_sisi_HV']}H:1V  |  Galian {cfg['galian']['kemiringan_HV']}H:1V jenjang {cfg['galian']['tinggi_jenjang_m']}/{cfg['galian']['lebar_jenjang_m']} m  |  Timbunan {cfg['timbunan']['kemiringan_HV']}H:1V\n"
           f"Lapis perkerasan {cfg['lapis_perkerasan']['tebal_m']} m {cfg['lapis_perkerasan']['material']} (perlu {summary['perkerasan']['tebal_perlu_m']:.2f} m @ CBR {summary['perkerasan']['cbr_tanah_dasar']}%)")
    fig.text(0.05, 0.30, ket, fontsize=7.5, va="top", family="DejaVu Sans Mono")
    _frame(fig, cfg, "Penampang Tipikal", 6, total)
    figs.append(("tipikal", fig))

    with PdfPages(pdf_path) as pdf:
        for name, f in figs:
            pdf.savefig(f)
            f.savefig(os.path.join(out_dir, f"lembar_{name}.png"), dpi=110)
            plt.close(f)
    return pdf_path
