"""Ekspor/impor CAD bergaya Civil 3D untuk desain tambang.

Format yang ditulis:
- LandXML 1.2  : Surface (TIN), Alignment (Line/Curve), Profile (PVI/ParaCurve + ProfSurf EG),
                 CrossSects. Urutan koordinat LandXML = Northing Easting Elevation (Y X Z).
- DXF R2018    : layer gaya NCS (C-ROAD-*, C-PIT-*, C-TOPO-*), LWPOLYLINE berelevasi,
                 POLYLINE 3D, 3DFACE (TIN), MESH, TEXT.
- OBJ / STL    : mesh 3D untuk viewer (Blender, MeshLab, Leapfrog, Deswik, ParaView).
- CSV          : titik (PENZD) dan feature line.

Berkas ini identik di skill desain-jalan-tambang dan desain-pit-geoteknik (diuji di tests).
"""
from __future__ import annotations

import datetime as _dt
import math
import struct
from xml.sax.saxutils import escape

import numpy as np

LANDXML_NS = "http://www.landxml.org/schema/LandXML-1.2"


# --------------------------------------------------------------------------- TIN / terrain
def grid_tin(xs: np.ndarray, ys: np.ndarray, Z: np.ndarray, mask: np.ndarray | None = None):
    """Grid teratur -> (pts Nx3, tris Mx3). Sel dengan NaN/mask False dibuang."""
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    valid = np.isfinite(pts[:, 2])
    if mask is not None:
        valid &= mask.ravel()
    idx = np.arange(nx * ny).reshape(ny, nx)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    tris = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    keep = valid[tris].all(axis=1)
    tris = tris[keep]
    used = np.unique(tris)
    remap = -np.ones(len(pts), int)
    remap[used] = np.arange(len(used))
    return pts[used], remap[tris]


def delaunay_tin(pts3: np.ndarray, boundary=None):
    """Triangulasi Delaunay 2D; bila boundary (shapely Polygon) diberikan, segitiga di luar dibuang."""
    from scipy.spatial import Delaunay

    pts3 = np.asarray(pts3, float)
    tri = Delaunay(pts3[:, :2])
    tris = tri.simplices
    if boundary is not None:
        import shapely

        cen = pts3[tris, :2].mean(axis=1)
        inside = shapely.contains_xy(boundary.buffer(1e-6), cen[:, 0], cen[:, 1])
        tris = tris[inside]
    return pts3, tris


class Terrain:
    """Permukaan tanah asli (EG) yang bisa di-query z(x, y)."""

    def __init__(self, pts3: np.ndarray):
        from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

        self.pts = np.asarray(pts3, float)
        self._lin = LinearNDInterpolator(self.pts[:, :2], self.pts[:, 2])
        self._near = NearestNDInterpolator(self.pts[:, :2], self.pts[:, 2])

    def z(self, x, y):
        x = np.atleast_1d(np.asarray(x, float))
        y = np.atleast_1d(np.asarray(y, float))
        v = self._lin(x, y)
        bad = ~np.isfinite(v)
        if np.any(bad):
            v = np.where(bad, self._near(x, y), v)
        return v

    @classmethod
    def from_function(cls, f, xmin, xmax, ymin, ymax, step):
        xs = np.arange(xmin, xmax + step / 2, step)
        ys = np.arange(ymin, ymax + step / 2, step)
        X, Y = np.meshgrid(xs, ys)
        return cls(np.column_stack([X.ravel(), Y.ravel(), f(X, Y).ravel()]))

    @classmethod
    def from_csv(cls, path):
        """CSV x,y,z (atau P,E,N,Z,D gaya survei: kolom E/N/Z dikenali)."""
        import pandas as pd

        df = pd.read_csv(path)
        cols = {c.lower(): c for c in df.columns}
        xc = cols.get("x") or cols.get("e") or cols.get("easting")
        yc = cols.get("y") or cols.get("n") or cols.get("northing")
        zc = cols.get("z") or cols.get("elev") or cols.get("elevation") or cols.get("rl")
        if not (xc and yc and zc):
            raise ValueError(f"Kolom koordinat tidak dikenali: {list(df.columns)}")
        return cls(df[[xc, yc, zc]].to_numpy(float))

    @classmethod
    def from_landxml(cls, path, surface_name=None):
        pts, _ = read_landxml_surface(path, surface_name)
        return cls(pts)


def read_landxml_surface(path, surface_name=None):
    """Baca Surface TIN dari LandXML (ekspor Civil 3D / Global Mapper / Surpac). Return (pts, tris)."""
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    for srf in root.iter(f"{ns}Surface"):
        if surface_name and srf.get("name") != surface_name:
            continue
        ids, pts = [], []
        for p in srf.iter(f"{ns}P"):
            n, e, z = map(float, p.text.split()[:3])
            ids.append(int(p.get("id")))
            pts.append((e, n, z))
        lut = {pid: i for i, pid in enumerate(ids)}
        tris = []
        for f in srf.iter(f"{ns}F"):
            if f.get("i") == "1":  # face tak terlihat
                continue
            a, b, c = (lut[int(v)] for v in f.text.split()[:3])
            tris.append((a, b, c))
        return np.array(pts), np.array(tris, int).reshape(-1, 3)
    raise ValueError("Surface tidak ditemukan di LandXML")


def contours(pts3, tris, interval, zmin=None, zmax=None):
    """Kontur dari TIN. Return list of (elev, Nx2 array)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    z = pts3[:, 2]
    lo = math.floor((zmin if zmin is not None else np.nanmin(z)) / interval) * interval
    hi = math.ceil((zmax if zmax is not None else np.nanmax(z)) / interval) * interval
    levels = np.arange(lo, hi + interval / 2, interval)
    tri = mtri.Triangulation(pts3[:, 0], pts3[:, 1], tris)
    fig = plt.figure()
    cs = plt.tricontour(tri, z, levels=levels)
    out = []
    for lev, segs in zip(cs.levels, cs.allsegs):
        for s in segs:
            if len(s) >= 2:
                out.append((float(lev), np.asarray(s)))
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- LandXML
def _p(v, nd=4):
    return f"{v:.{nd}f}"


def _ne(x, y, nd=4):
    return f"{_p(y, nd)} {_p(x, nd)}"


class LandXML:
    """Penulis LandXML 1.2 sederhana yang bisa diimpor Civil 3D (Insert > LandXML)."""

    def __init__(self, project: str, desc: str = "", epsg: int | None = None, company: str = ""):
        self.project, self.desc, self.epsg, self.company = project, desc, epsg, company
        self.surfaces: list = []
        self.alignments: list = []
        self.cgpoints: list = []

    def add_surface(self, name, pts, tris, desc="", breaklines=None):
        self.surfaces.append((name, np.asarray(pts, float), np.asarray(tris, int), desc, breaklines or []))

    def add_alignment(self, name, elements, sta_start=0.0, profiles=None, cross_sections=None, desc=""):
        """elements: list dict {type:'Line'|'Curve', start, end, sta, length, [center, radius, rot, pi, delta]}.
        profiles: list dict {name, type:'ProfAlign'|'ProfSurf', pvis:[(sta, elev, vc_len)], pnts:[(sta, elev)]}.
        cross_sections: list dict {sta, surfaces:{name:[(offset, elev, code)]}, desc}."""
        self.alignments.append(dict(name=name, elements=elements, sta_start=sta_start,
                                    profiles=profiles or [], xs=cross_sections or [], desc=desc))

    def add_points(self, pts, codes=None, name="Titik"):
        self.cgpoints.append((name, np.asarray(pts, float), codes))

    def write(self, path):
        now = _dt.datetime.now()
        L = []
        w = L.append
        w('<?xml version="1.0" encoding="UTF-8"?>')
        w(f'<LandXML xmlns="{LANDXML_NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
          f'xsi:schemaLocation="{LANDXML_NS} http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd" '
          f'version="1.2" date="{now:%Y-%m-%d}" time="{now:%H:%M:%S}">')
        w('  <Units><Metric areaUnit="squareMeter" linearUnit="meter" volumeUnit="cubicMeter" '
          'temperatureUnit="celsius" pressureUnit="milliBars" diameterUnit="millimeter" '
          'angularUnit="decimal degrees" directionUnit="decimal degrees"/></Units>')
        if self.epsg:
            w(f'  <CoordinateSystem epsgCode="{self.epsg}" name="EPSG:{self.epsg}"/>')
        w(f'  <Project name="{escape(self.project)}" desc="{escape(self.desc)}"/>')
        w('  <Application name="mining-skill/minedesign" manufacturer="' + escape(self.company or "open source")
          + '" version="1.0" desc="Desain tambang sesuai Kepmen ESDM 1827 K/30/MEM/2018"/>')
        if self.cgpoints:
            w('  <CgPoints>')
            k = 1
            for name, pts, codes in self.cgpoints:
                for i, (x, y, z) in enumerate(pts):
                    code = escape(codes[i]) if codes is not None else name
                    w(f'    <CgPoint name="{k}" code="{code}">{_ne(x, y)} {_p(z)}</CgPoint>')
                    k += 1
            w('  </CgPoints>')
        if self.surfaces:
            w('  <Surfaces>')
            for name, pts, tris, desc, brk in self.surfaces:
                w(f'    <Surface name="{escape(name)}" desc="{escape(desc)}">')
                w(f'      <SourceData>')
                if brk:
                    w('        <Breaklines>')
                    for bname, bl in brk:
                        txt = " ".join(f"{_ne(x, y)} {_p(z)}" for x, y, z in bl)
                        w(f'          <Breakline name="{escape(bname)}" brkType="standard"><PntList3D>{txt}</PntList3D></Breakline>')
                    w('        </Breaklines>')
                w('      </SourceData>')
                zmin, zmax = float(np.nanmin(pts[:, 2])), float(np.nanmax(pts[:, 2]))
                area2d = _tin_area(pts, tris)
                w(f'      <Definition surfType="TIN" area2DSurf="{_p(area2d, 2)}" elevMin="{_p(zmin, 3)}" elevMax="{_p(zmax, 3)}">')
                w('        <Pnts>')
                for i, (x, y, z) in enumerate(pts, start=1):
                    w(f'          <P id="{i}">{_ne(x, y)} {_p(z)}</P>')
                w('        </Pnts>')
                w('        <Faces>')
                for a, b, c in tris:
                    w(f'          <F>{a + 1} {b + 1} {c + 1}</F>')
                w('        </Faces>')
                w('      </Definition>')
                w('    </Surface>')
            w('  </Surfaces>')
        if self.alignments:
            w(f'  <Alignments name="{escape(self.project)}">')
            for al in self.alignments:
                length = sum(e["length"] for e in al["elements"])
                w(f'    <Alignment name="{escape(al["name"])}" length="{_p(length)}" staStart="{_p(al["sta_start"])}" desc="{escape(al["desc"])}">')
                w('      <CoordGeom>')
                for e in al["elements"]:
                    if e["type"] == "Line":
                        w(f'        <Line staStart="{_p(e["sta"])}" length="{_p(e["length"])}">'
                          f'<Start>{_ne(*e["start"])}</Start><End>{_ne(*e["end"])}</End></Line>')
                    else:
                        w(f'        <Curve rot="{e["rot"]}" crvType="arc" staStart="{_p(e["sta"])}" length="{_p(e["length"])}" '
                          f'radius="{_p(e["radius"])}" delta="{_p(math.degrees(e["delta"]), 6)}">'
                          f'<Start>{_ne(*e["start"])}</Start><Center>{_ne(*e["center"])}</Center>'
                          f'<End>{_ne(*e["end"])}</End><PI>{_ne(*e["pi"])}</PI></Curve>')
                w('      </CoordGeom>')
                for pr in al["profiles"]:
                    w(f'      <Profile name="{escape(pr["name"])}">')
                    if pr["type"] == "ProfSurf":
                        txt = " ".join(f"{_p(s, 3)} {_p(z, 3)}" for s, z in pr["pnts"])
                        w(f'        <ProfSurf name="{escape(pr["name"])}"><PntList2D>{txt}</PntList2D></ProfSurf>')
                    else:
                        w(f'        <ProfAlign name="{escape(pr["name"])}">')
                        for s, z, vcl in pr["pvis"]:
                            if vcl and vcl > 0:
                                w(f'          <ParaCurve length="{_p(vcl, 3)}">{_p(s, 3)} {_p(z, 3)}</ParaCurve>')
                            else:
                                w(f'          <PVI>{_p(s, 3)} {_p(z, 3)}</PVI>')
                        w('        </ProfAlign>')
                    w('      </Profile>')
                if al["xs"]:
                    w('      <CrossSects>')
                    for xs in al["xs"]:
                        w(f'        <CrossSect sta="{_p(xs["sta"], 3)}" name="STA {fmt_sta(xs["sta"])}" desc="{escape(xs.get("desc", ""))}">')
                        for sname, pnts in xs["surfaces"].items():
                            tag = "DesignCrossSectSurf"
                            w(f'          <{tag} name="{escape(sname)}">')
                            for o, z, code in pnts:
                                ctxt = f' code="{escape(code)}"' if code else ""
                                w(f'            <CrossSectPnt{ctxt}>{_p(o, 3)} {_p(z, 3)}</CrossSectPnt>')
                            w(f'          </{tag}>')
                        w('        </CrossSect>')
                    w('      </CrossSects>')
                w('    </Alignment>')
            w('  </Alignments>')
        w('</LandXML>')
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(L) + "\n")
        return path


def _tin_area(pts, tris):
    if len(tris) == 0:
        return 0.0
    a, b, c = pts[tris[:, 0], :2], pts[tris[:, 1], :2], pts[tris[:, 2], :2]
    return float(0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])).sum())


def fmt_sta(s: float) -> str:
    """Format stasiun 0+000.00"""
    s = float(s)
    km = int(s // 1000)
    return f"{km}+{s - km * 1000:06.2f}"


# --------------------------------------------------------------------------- DXF
NCS_LAYERS = {
    # nama: (ACI color, linetype, deskripsi)
    "C-TOPO-MAJR": (8, "CONTINUOUS", "Kontur mayor tanah asli"),
    "C-TOPO-MINR": (9, "CONTINUOUS", "Kontur minor tanah asli"),
    "C-TOPO-FG-MAJR": (3, "CONTINUOUS", "Kontur mayor desain akhir"),
    "C-TOPO-FG-MINR": (83, "CONTINUOUS", "Kontur minor desain akhir"),
    "C-TINN-EG": (8, "CONTINUOUS", "TIN tanah asli (3DFACE)"),
    "C-TINN-FG": (3, "CONTINUOUS", "TIN desain (3DFACE)"),
    "C-ROAD-CNTR": (1, "CENTER", "Garis tengah alinyemen"),
    "C-ROAD-STAN": (7, "CONTINUOUS", "Label stasiun"),
    "C-ROAD-EDGE": (5, "CONTINUOUS", "Tepi jalur lalu lintas"),
    "C-ROAD-SHLD": (4, "CONTINUOUS", "Bahu / tepi formasi"),
    "C-ROAD-BERM": (30, "CONTINUOUS", "Tanggul pengaman (safety berm)"),
    "C-ROAD-DTCH": (150, "DASHED", "Saluran drainase"),
    "C-ROAD-DAYL": (6, "DASHED", "Garis daylight galian/timbunan"),
    "C-ROAD-CURV": (2, "CONTINUOUS", "Label tikungan"),
    "C-ROAD-XSEC": (7, "CONTINUOUS", "Garis potong penampang"),
    "C-PIT-CRST": (1, "CONTINUOUS", "Crest jenjang"),
    "C-PIT-TOES": (5, "CONTINUOUS", "Toe jenjang"),
    "C-PIT-RAMP": (2, "CENTER", "Garis tengah ramp"),
    "C-PIT-SHEL": (6, "DASHED", "Pit shell optimasi"),
    "C-PIT-XSEC": (7, "CONTINUOUS", "Garis penampang"),
    "C-ANNO-TEXT": (7, "CONTINUOUS", "Anotasi"),
    "C-ANNO-TTLB": (7, "CONTINUOUS", "Kop gambar"),
}


class DXF:
    def __init__(self, layers: dict | None = None):
        import ezdxf
        from ezdxf import units

        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = units.M
        self.doc.header["$INSUNITS"] = 6
        self.msp = self.doc.modelspace()
        for name, (color, lt, desc) in {**NCS_LAYERS, **(layers or {})}.items():
            if name not in self.doc.layers:
                lay = self.doc.layers.add(name, color=color)
                if lt in self.doc.linetypes:
                    lay.dxf.linetype = lt
                lay.description = desc

    def poly2d(self, xy, layer, closed=False, elevation=0.0):
        xy = np.asarray(xy, float)
        if len(xy) < 2:
            return
        e = self.msp.add_lwpolyline([tuple(p[:2]) for p in xy], close=closed, dxfattribs={"layer": layer})
        e.dxf.elevation = float(elevation)
        return e

    def poly3d(self, xyz, layer, closed=False):
        xyz = np.asarray(xyz, float)
        if len(xyz) < 2:
            return
        return self.msp.add_polyline3d([tuple(p) for p in xyz], close=closed, dxfattribs={"layer": layer})

    def faces(self, pts, tris, layer):
        for a, b, c in tris:
            pa, pb, pc = tuple(pts[a]), tuple(pts[b]), tuple(pts[c])
            self.msp.add_3dface([pa, pb, pc, pc], dxfattribs={"layer": layer})

    def mesh(self, pts, tris, layer):
        m = self.msp.add_mesh(dxfattribs={"layer": layer})
        with m.edit_data() as md:
            md.vertices = [tuple(p) for p in pts]
            md.faces = [tuple(int(i) for i in t) for t in tris]
        return m

    def text(self, s, xy, height=2.5, layer="C-ANNO-TEXT", rot=0.0, z=0.0, align="MIDDLE_CENTER"):
        from ezdxf.enums import TextEntityAlignment

        t = self.msp.add_text(str(s), height=height, rotation=rot, dxfattribs={"layer": layer})
        t.set_placement((float(xy[0]), float(xy[1]), float(z)), align=getattr(TextEntityAlignment, align))
        return t

    def line(self, p1, p2, layer):
        return self.msp.add_line(tuple(p1), tuple(p2), dxfattribs={"layer": layer})

    def save(self, path):
        self.doc.saveas(path)
        return path


# --------------------------------------------------------------------------- mesh
def write_obj(path, pts, tris, name="surface", origin=None):
    """OBJ: koordinat bisa digeser ke origin lokal agar presisi viewer terjaga."""
    pts = np.asarray(pts, float)
    off = np.zeros(3) if origin is None else np.asarray(origin, float)
    with open(path, "w") as f:
        f.write(f"# mining-skill minedesign; offset origin = {off.tolist()}\no {name}\n")
        for x, y, z in pts - off:
            f.write(f"v {x:.3f} {z:.3f} {-y:.3f}\n")  # Y-up untuk viewer umum
        for a, b, c in tris:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")
    return path


def write_stl(path, pts, tris, name="surface", origin=None):
    pts = np.asarray(pts, float) - (np.zeros(3) if origin is None else np.asarray(origin, float))
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p0, p1, p2 = pts[a], pts[b], pts[c]
            n = np.cross(p1 - p0, p2 - p0)
            nn = np.linalg.norm(n)
            n = n / nn if nn > 0 else n
            f.write(struct.pack("<12fH", *n, *p0, *p1, *p2, 0))
    return path


def write_points_csv(path, pts, codes=None):
    with open(path, "w") as f:
        f.write("P,E,N,Z,D\n")
        for i, (x, y, z) in enumerate(pts, start=1):
            f.write(f"{i},{x:.3f},{y:.3f},{z:.3f},{codes[i - 1] if codes is not None else ''}\n")
    return path


def tin_volume_between(pts_top, tris_top, f_bottom):
    """Volume (cut, fill) antara TIN atas dan fungsi permukaan bawah f(x,y) per segitiga (prisma)."""
    p = pts_top[tris_top]
    cen = p.mean(axis=1)
    dz = cen[:, 2] - f_bottom(cen[:, 0], cen[:, 1])
    a = 0.5 * np.abs((p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 2, 0] - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1]))
    fill = float((a * np.clip(dz, 0, None)).sum())
    cut = float((a * np.clip(-dz, 0, None)).sum())
    return cut, fill
