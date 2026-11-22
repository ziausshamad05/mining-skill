#!/usr/bin/env python3
"""
jdih_fetch.py - Ambil dokumen peraturan resmi dari portal JDIH untuk diolah sendiri.

Sumber yang didukung:
  bpk   : Database Peraturan JDIH BPK  (https://peraturan.bpk.go.id)
  esdm  : JDIH Kementerian ESDM         (https://jdih.esdm.go.id)
  pgo   : JDIH Kemenkum / peraturan.go.id (https://peraturan.go.id/files/<slug>.pdf)

Perintah:
  search   Cari peraturan (BPK) -> daftar Details ID + judul.
  detail   Ambil metadata satu peraturan (BPK Details / halaman JDIH ESDM).
  guess    Susun URL kandidat dari jenis+nomor+tahun (BPK, peraturan.go.id, JDIH ESDM).
  download Unduh PDF resmi + manifest (URL sumber, waktu, SHA-256).
  extract  Ubah PDF jadi teks + pecah per Pasal (JSON) agar bisa diolah.
  pasal    Tampilkan isi Pasal tertentu dari hasil extract.
  catalog  Tampilkan katalog regulasi RKAB yang sudah dipetakan (references/katalog_regulasi.json).

Hanya memakai pustaka standar Python. Ekstraksi PDF memakai pypdf bila terpasang,
jika tidak memakai `pdftotext` (poppler-utils).

Etika akses: jeda antar-permintaan (default 1,5 detik), User-Agent jujur, cache lokal,
tanpa melewati login/captcha. Dokumen tetap milik penerbitnya; selalu cantumkan URL sumber.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BPK_BASE = "https://peraturan.bpk.go.id"
ESDM_BASE = "https://jdih.esdm.go.id"
PGO_BASE = "https://peraturan.go.id"

USER_AGENT = (
    "Mozilla/5.0 (compatible; regulasi-rkab-esdm/1.0; "
    "+https://github.com/ziausshamad05/mining-skill) riset-kepatuhan"
)
DEFAULT_DELAY = 1.5
CACHE_DIR = Path(os.environ.get("JDIH_CACHE", Path.home() / ".cache" / "jdih_fetch"))

# Label metadata pada halaman Details BPK (urutan sesuai tampilan situs).
BPK_META_LABELS = [
    "Tipe Dokumen", "Judul", "T.E.U.", "Nomor", "Bentuk", "Bentuk Singkat", "Tahun",
    "Tempat Penetapan", "Tanggal Penetapan", "Tanggal Pengundangan", "Tanggal Berlaku",
    "Sumber", "Subjek", "Status", "Bahasa", "Lokasi", "Bidang", "Alias",
]
STATUS_HEADERS = [
    "Mencabut", "Dicabut dengan", "Mengubah", "Diubah dengan", "Dicabut sebagian dengan",
    "Mencabut sebagian", "Ditetapkan dengan", "Menetapkan", "Dilaksanakan dengan",
    "Melaksanakan", "Uji Materi",
]

# Singkatan jenis -> (slug peraturan.go.id / BPK, nama panjang)
JENIS = {
    "uu": ("uu", "Undang-undang"),
    "pp": ("pp", "Peraturan Pemerintah"),
    "perpres": ("perpres", "Peraturan Presiden"),
    "permen-esdm": ("permen-esdm", "Peraturan Menteri Energi dan Sumber Daya Mineral"),
    "kepmen-esdm": ("kepmen-esdm", "Keputusan Menteri Energi dan Sumber Daya Mineral"),
    "permenlhk": ("permen-lhk", "Peraturan Menteri Lingkungan Hidup dan Kehutanan"),
}


# --------------------------------------------------------------------------- HTTP
class FetchError(RuntimeError):
    pass


_last_request = 0.0


def http_get(url: str, *, delay: float = DEFAULT_DELAY, retries: int = 3,
             timeout: int = 60, use_cache: bool = True, binary: bool = False):
    """GET dengan jeda sopan, retry eksponensial, dan cache berbasis hash URL."""
    global _last_request
    key = hashlib.sha256(url.encode()).hexdigest()[:32]
    cache_file = CACHE_DIR / (key + (".bin" if binary else ".html"))
    if use_cache and cache_file.exists():
        data = cache_file.read_bytes()
        return data if binary else data.decode("utf-8", "replace")

    last_err: Exception | None = None
    for attempt in range(retries):
        wait = delay - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "id,en;q=0.7",
        })
        try:
            _last_request = time.monotonic()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(data)
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (400, 401, 403, 404, 410):
                break  # tidak berguna diulang
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last_err = e
        time.sleep(delay * (2 ** attempt))
    raise FetchError(f"Gagal mengambil {url}: {last_err}")


# --------------------------------------------------------------------------- HTML util
def html_to_lines(page: str) -> list[str]:
    """Ubah HTML menjadi baris teks bersih (urutan tampilan dipertahankan)."""
    page = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>", "\n", page)
    page = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|dt|dd|td|th|section|ul|ol|table|label|span)>", "\n", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    page = html.unescape(page)
    lines = []
    for ln in page.split("\n"):
        ln = re.sub(r"[ \t\r\f\v ]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return lines


def find_links(page: str, base: str) -> list[tuple[str, str]]:
    """Kembalikan [(href_absolut, teks_link)]."""
    out = []
    for m in re.finditer(r'(?is)<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', page):
        href = html.unescape(m.group(1)).strip()
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", m.group(2)))).strip()
        out.append((urllib.parse.urljoin(base, href), text))
    return out


def is_maintenance(page: str) -> bool:
    low = page.lower()
    return "sedang dalam perbaikan" in low or "esdm-maintenance" in low


# --------------------------------------------------------------------------- data
@dataclass
class Regulation:
    source: str
    url: str
    title: str = ""
    metadata: dict = field(default_factory=dict)
    status_peraturan: dict = field(default_factory=dict)
    abstrak: str = ""
    pdf_links: list = field(default_factory=list)
    retrieved_at: str = ""
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------- BPK
def bpk_search_url(keywords: str = "", tentang: str = "", nomor: str = "", tahun: str = "",
                   jenis: str = "", entitas: str = "", page: int = 1) -> str:
    params = {k: v for k, v in {
        "keywords": keywords, "tentang": tentang, "nomor": nomor, "tahun": tahun,
        "jenis": jenis, "entitas": entitas, "p": str(page) if page > 1 else "",
    }.items() if v}
    return f"{BPK_BASE}/Search?" + urllib.parse.urlencode(params)


def parse_bpk_search(page: str) -> list[dict]:
    results, seen = [], set()
    for href, text in find_links(page, BPK_BASE):
        m = re.search(r"/Details/(\d+)(?:/([^?#\"']*))?", href)
        if not m or not text:
            continue
        did = m.group(1)
        if did in seen:
            # simpan teks terpanjang sebagai judul
            for r in results:
                if r["id"] == did and len(text) > len(r["judul"]):
                    r["judul"] = text
            continue
        seen.add(did)
        results.append({"id": did, "slug": m.group(2) or "", "judul": text,
                        "url": f"{BPK_BASE}/Details/{did}" + (f"/{m.group(2)}" if m.group(2) else "")})
    return results


def parse_bpk_detail(page: str, url: str) -> Regulation:
    reg = Regulation(source="bpk", url=url, retrieved_at=now_iso())
    lines = html_to_lines(page)
    labels = set(BPK_META_LABELS)

    # Metadata: label pada satu baris, nilai di baris berikutnya (pola tampilan BPK).
    multi = {"Subjek", "Alias"}
    stop_prefix = ("UJI MATERI", "STATUS PERATURAN", "Halaman ini telah diakses", "MATERI POKOK")
    for i, ln in enumerate(lines):
        if ln not in labels or ln in reg.metadata:
            continue
        vals = []
        for nxt in lines[i + 1:]:
            if nxt in labels or nxt.startswith(stop_prefix):
                break
            vals.append(nxt)
            if ln not in multi:
                break
        if vals:
            reg.metadata[ln] = " ".join(vals).strip()
    reg.title = reg.metadata.get("Judul") or next(
        (ln for ln in lines if re.match(r"(?i)^(peraturan|undang|keputusan)", ln)), "")

    # Abstrak (blok setelah "Abstrak" sampai "METADATA PERATURAN")
    try:
        a = next(i for i, ln in enumerate(lines) if ln.lower() == "abstrak")
        b = next((i for i in range(a + 1, len(lines)) if lines[i].upper().startswith("METADATA")), len(lines))
        reg.abstrak = " ".join(lines[a + 1:b]).strip()
    except StopIteration:
        pass

    # Status peraturan
    try:
        s = next(i for i, ln in enumerate(lines) if ln.upper().startswith("STATUS PERATURAN"))
        e = next((i for i in range(s + 1, len(lines)) if lines[i].upper().startswith(
            ("TENTANG DATABASE", "KONTAK", "DISCLAIMER"))), len(lines))
        current = None
        for ln in lines[s + 1:e]:
            head = ln.rstrip(" :").strip()
            if head in STATUS_HEADERS:
                current = head
                reg.status_peraturan.setdefault(current, [])
                continue
            if current:
                item = re.sub(r"^\d+\.\s*", "", ln)
                if item and item.lower() != "belum tersedia":
                    reg.status_peraturan[current].append(item)
    except StopIteration:
        pass

    for href, text in find_links(page, url):
        if re.search(r"/Download/\d+/", href) or href.lower().endswith(".pdf"):
            entry = {"url": href, "nama": text or Path(urllib.parse.urlparse(href).path).name}
            if entry not in reg.pdf_links:
                reg.pdf_links.append(entry)
    if not reg.pdf_links:
        reg.warnings.append("Tidak ada tautan PDF ditemukan; buka halaman secara manual.")
    return reg


# --------------------------------------------------------------------------- JDIH ESDM
def parse_esdm_page(page: str, url: str) -> Regulation:
    reg = Regulation(source="esdm", url=url, retrieved_at=now_iso())
    if is_maintenance(page):
        reg.warnings.append(
            "JDIH ESDM sedang maintenance. Gunakan BPK (peraturan.bpk.go.id) atau peraturan.go.id "
            "sebagai sumber cermin resmi, lalu cocokkan ulang ke JDIH ESDM saat aktif.")
        return reg
    lines = html_to_lines(page)
    # Metadata gaya JDIHN: label: nilai atau label \n nilai
    known = ["Judul", "Nomor", "Tahun", "Jenis", "Singkatan Jenis", "Tempat Penetapan",
             "Tanggal Penetapan", "Tanggal Pengundangan", "Sumber", "Subjek", "Status",
             "Bahasa", "Bidang Hukum", "Pemrakarsa", "Penandatanganan", "T.E.U. Badan",
             "Tipe Dokumen", "Tempat Terbit", "Lokasi"]
    for i, ln in enumerate(lines):
        for k in known:
            if ln == k and i + 1 < len(lines) and k not in reg.metadata:
                reg.metadata[k] = lines[i + 1]
            elif ln.startswith(k + " :") or ln.startswith(k + ":"):
                reg.metadata.setdefault(k, ln.split(":", 1)[1].strip())
    reg.title = reg.metadata.get("Judul") or next(
        (ln for ln in lines if re.match(r"(?i)^(peraturan|keputusan|undang)", ln)), "")
    for href, text in find_links(page, url):
        if "/storage/document/" in href or href.lower().endswith(".pdf"):
            entry = {"url": href, "nama": text or Path(urllib.parse.urlparse(href).path).name}
            if entry not in reg.pdf_links:
                reg.pdf_links.append(entry)
    return reg


# --------------------------------------------------------------------------- guess URLs
def guess_urls(jenis: str, nomor: str, tahun: str) -> dict:
    j = jenis.lower().strip()
    slug_j, nama = JENIS.get(j, (j, j))
    slug = f"{slug_j}-no-{nomor}-tahun-{tahun}"
    nama_singkat = {"permen-esdm": "Permen ESDM", "kepmen-esdm": "Kepmen ESDM", "pp": "PP",
                    "uu": "UU", "perpres": "Perpres"}.get(j, jenis)
    q = urllib.parse.quote
    return {
        "peraturan_go_id_pdf": f"{PGO_BASE}/files/{slug}.pdf",
        "bpk_search": bpk_search_url(keywords=f"{nama_singkat} {nomor} {tahun}"),
        "bpk_search_nomor": bpk_search_url(nomor=nomor, tahun=tahun),
        "jdih_esdm_storage_candidates": [
            f"{ESDM_BASE}/storage/document/{q(f'{nama_singkat} Nomor {nomor} Tahun {tahun}.pdf')}",
            f"{ESDM_BASE}/storage/document/{q(f'{nama_singkat} No. {nomor} Tahun {tahun}.pdf')}",
            f"{ESDM_BASE}/storage/document/{q(f'{nama} Nomor {nomor} Tahun {tahun}.pdf')}",
        ],
        "catatan": "Nama file JDIH ESDM tidak seragam; kandidat bisa 404. "
                   "BPK Details ID didapat dari hasil search.",
    }


# --------------------------------------------------------------------------- download / extract
def safe_name(s: str) -> str:
    s = urllib.parse.unquote(s)
    s = re.sub(r"[^\w.\- ]+", "_", s).strip().replace(" ", "_")
    return s[:150] or "dokumen.pdf"


def download_pdf(url: str, outdir: Path, meta: dict | None = None, delay=DEFAULT_DELAY) -> dict:
    data = http_get(url, binary=True, delay=delay, use_cache=True)
    if not data.startswith(b"%PDF"):
        raise FetchError(f"Respon dari {url} bukan PDF (mungkin halaman error/maintenance).")
    outdir.mkdir(parents=True, exist_ok=True)
    name = safe_name(Path(urllib.parse.urlparse(url).path).name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    path = outdir / name
    path.write_bytes(data)
    manifest = {
        "file": str(path), "source_url": url, "retrieved_at": now_iso(),
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "metadata": meta or {},
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def pdf_to_text(pdf: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(pdf))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception as e:  # PDF rusak / terenkripsi
        print(f"[peringatan] pypdf gagal: {e}; mencoba pdftotext", file=sys.stderr)
    if shutil.which("pdftotext"):
        res = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
    raise FetchError("Tidak bisa mengekstrak teks. Pasang `pip install pypdf` atau poppler-utils. "
                     "Jika PDF hasil scan, lakukan OCR (mis. ocrmypdf) terlebih dahulu.")


PASAL_RE = re.compile(r"(?m)^\s*Pasal\s+(\d+[A-Z]?)\s*$")
BAB_RE = re.compile(r"(?m)^\s*BAB\s+([IVXLC]+[A-Z]?)\s*$")
NOISE_RE = re.compile(r"(?mi)^\s*(www\.peraturan\.go\.id|www\.jdih\.esdm\.go\.id|-\s*\d+\s*-|\d{4}, No\.\s*\d+.*)\s*$")


def split_pasal(text: str) -> list[dict]:
    """Pecah teks peraturan per Pasal. Pasal sisipan (mis. 34A) didukung."""
    clean = NOISE_RE.sub("", text)
    marks = list(PASAL_RE.finditer(clean))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(clean)
        body = clean[m.end():end].strip()
        bab = None
        for b in BAB_RE.finditer(clean[:m.start()]):
            bab = b.group(1)
        ayat = re.findall(r"(?m)^\s*\((\d+)\)", body)
        out.append({"pasal": m.group(1), "bab": bab, "jumlah_ayat": len(ayat),
                    "teks": re.sub(r"[ \t]+\n", "\n", body)})
    return out


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- CLI
def cmd_search(a):
    url = a.url or bpk_search_url(a.keywords or "", a.tentang or "", a.nomor or "", a.tahun or "",
                                  a.jenis or "", a.entitas or "", a.page)
    page = http_get(url, delay=a.delay, use_cache=not a.no_cache)
    res = parse_bpk_search(page)
    emit({"query_url": url, "jumlah": len(res), "hasil": res[: a.limit]}, a)


def cmd_detail(a):
    target = a.target
    if re.fullmatch(r"\d+", target):
        target = f"{BPK_BASE}/Details/{target}"
    page = http_get(target, delay=a.delay, use_cache=not a.no_cache)
    host = urllib.parse.urlparse(target).netloc
    reg = parse_esdm_page(page, target) if "esdm.go.id" in host else parse_bpk_detail(page, target)
    emit(asdict(reg), a)


def cmd_guess(a):
    emit(guess_urls(a.jenis, a.nomor, a.tahun), a)


def cmd_download(a):
    outdir = Path(a.out)
    urls = []
    meta = {}
    if a.target.lower().endswith(".pdf") or "/Download/" in a.target or "/files/" in a.target:
        urls = [a.target]
    else:
        tgt = f"{BPK_BASE}/Details/{a.target}" if re.fullmatch(r"\d+", a.target) else a.target
        page = http_get(tgt, delay=a.delay, use_cache=not a.no_cache)
        host = urllib.parse.urlparse(tgt).netloc
        reg = parse_esdm_page(page, tgt) if "esdm.go.id" in host else parse_bpk_detail(page, tgt)
        meta = {"title": reg.title, "detail_url": tgt, **reg.metadata,
                "status_peraturan": reg.status_peraturan}
        urls = [p["url"] for p in reg.pdf_links][: a.max_files]
        if not urls:
            raise FetchError("Tidak ada PDF pada halaman: " + "; ".join(reg.warnings))
    results = [download_pdf(u, outdir, meta, delay=a.delay) for u in urls]
    emit({"diunduh": results}, a)


def cmd_extract(a):
    pdf = Path(a.pdf)
    text = pdf_to_text(pdf)
    txt_path = pdf.with_suffix(".txt")
    txt_path.write_text(text)
    pasal = split_pasal(text)
    js_path = pdf.with_suffix(".pasal.json")
    manifest = pdf.with_suffix(".manifest.json")
    src = json.loads(manifest.read_text()) if manifest.exists() else {}
    js_path.write_text(json.dumps({"sumber": src, "jumlah_pasal": len(pasal), "pasal": pasal},
                                  ensure_ascii=False, indent=2))
    emit({"teks": str(txt_path), "pasal_json": str(js_path), "jumlah_pasal": len(pasal),
          "karakter": len(text),
          "peringatan": [] if len(text.strip()) > 500 else ["Teks sangat sedikit - kemungkinan PDF scan, perlu OCR."]}, a)


def cmd_pasal(a):
    data = json.loads(Path(a.pasal_json).read_text())
    wanted = {p.upper() for p in a.nomor}
    hits = [p for p in data["pasal"] if p["pasal"].upper() in wanted]
    if a.grep:
        rx = re.compile(a.grep, re.I)
        hits = [p for p in data["pasal"] if rx.search(p["teks"])] if not wanted else [
            p for p in hits if rx.search(p["teks"])]
    emit({"sumber": data.get("sumber", {}).get("source_url"), "hasil": hits}, a)


def cmd_catalog(a):
    path = Path(__file__).resolve().parent.parent / "references" / "katalog_regulasi.json"
    data = json.loads(path.read_text())
    if a.topik:
        data["regulasi"] = [r for r in data["regulasi"] if a.topik.lower() in json.dumps(r).lower()]
    emit(data, a)


def emit(obj, a):
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    if getattr(a, "save", None):
        Path(a.save).write_text(s)
        print(f"Tersimpan: {a.save}", file=sys.stderr)
    print(s)


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="jeda antar-permintaan (detik)")
    p.add_argument("--no-cache", action="store_true", help="abaikan cache lokal")
    p.add_argument("--save", help="simpan output JSON ke file")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="cari di Database Peraturan BPK")
    s.add_argument("keywords", nargs="?")
    s.add_argument("--tentang"); s.add_argument("--nomor"); s.add_argument("--tahun")
    s.add_argument("--jenis", help="ID jenis BPK (lihat references/sumber-data-api.md)")
    s.add_argument("--entitas", help="ID entitas BPK")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--url", help="pakai URL pencarian BPK mentah")
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("detail", help="metadata: BPK Details ID/URL atau URL JDIH ESDM")
    d.add_argument("target"); d.set_defaults(func=cmd_detail)

    g = sub.add_parser("guess", help="susun URL kandidat dari jenis/nomor/tahun")
    g.add_argument("jenis", help="permen-esdm | kepmen-esdm | pp | uu | perpres")
    g.add_argument("nomor"); g.add_argument("tahun"); g.set_defaults(func=cmd_guess)

    dl = sub.add_parser("download", help="unduh PDF (URL PDF, BPK Details ID/URL, atau URL JDIH ESDM)")
    dl.add_argument("target"); dl.add_argument("--out", default="regulasi")
    dl.add_argument("--max-files", type=int, default=3); dl.set_defaults(func=cmd_download)

    e = sub.add_parser("extract", help="PDF -> .txt + .pasal.json")
    e.add_argument("pdf"); e.set_defaults(func=cmd_extract)

    ps = sub.add_parser("pasal", help="ambil Pasal tertentu dari .pasal.json")
    ps.add_argument("pasal_json"); ps.add_argument("nomor", nargs="*", default=[])
    ps.add_argument("--grep", help="regex pencarian di isi pasal"); ps.set_defaults(func=cmd_pasal)

    c = sub.add_parser("catalog", help="katalog regulasi RKAB yang dipetakan")
    c.add_argument("--topik"); c.set_defaults(func=cmd_catalog)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.func(a)
    except FetchError as e:
        print(f"[galat] {e}", file=sys.stderr)
        print("[saran] Coba sumber lain: `guess` untuk URL peraturan.go.id, atau buka di browser "
              "lalu unduh manual dan jalankan `extract`.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
