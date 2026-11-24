# -*- coding: utf-8 -*-
"""
Pengenalan peran elemen Print Layout, tiga lapis:

1. tersimpan : custom property ``rimba_layout/role`` pada item
2. id        : ID item memuat kata kunci (judul, sumber_data, ...)
3. tebakan   : tipe item, ukuran, posisi, dan isi teks
"""

import re

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
)

ROLE_PROP = "rimba_layout/role"

SRC_SAVED = "tersimpan"
SRC_ID = "id"
SRC_GUESS = "tebakan"

ROLE_LABELS = {
    "judul": "Judul",
    "subjudul": "Subjudul",
    "teks": "Teks biasa",
    "catatan": "Catatan",
    "catatan_proyeksi": "Catatan proyeksi",
    "sumber_data": "Dasar / sumber data",
    "judul_bagian": "Judul bagian",
    "skala_teks": "Teks skala",
    "label_tahun": "Label tahun panel",
    "tanda_tangan": "Tanda tangan",
    "instansi_penerbit": "Instansi penerbit",
    "huruf_utara": "Huruf U",
    "legenda": "Legenda",
    "skala_bar": "Skala bar",
    "skala_angka": "Skala angka",
    "peta": "Panel peta",
    "peta_situasi": "Peta situasi",
    "panah_utara": "Panah utara",
    "logo": "Logo",
    "kotak": "Kotak pembatas",
    "abaikan": "Abaikan",
}

# Kata kunci pada ID item -> peran (dicocokkan sebagai kata/potongan)
_ID_KEYWORDS = [
    ("subjudul", "subjudul"), ("subtitle", "subjudul"),
    ("judul_bagian", "judul_bagian"),
    ("judul", "judul"), ("title", "judul"),
    ("proyeksi", "catatan_proyeksi"), ("projection", "catatan_proyeksi"),
    ("sumber", "sumber_data"), ("dasar", "sumber_data"),
    ("source", "sumber_data"),
    ("catatan", "catatan"), ("note", "catatan"),
    ("tahun", "label_tahun"), ("year", "label_tahun"),
    ("ttd", "tanda_tangan"), ("tanda_tangan", "tanda_tangan"),
    ("signature", "tanda_tangan"),
    ("instansi", "instansi_penerbit"), ("penerbit", "instansi_penerbit"),
    ("situasi", "peta_situasi"), ("inset", "peta_situasi"),
    ("logo", "logo"),
]

_HEADINGS = ("keterangan", "dasar", "sumber", "catatan", "fungsi kawasan",
             "legenda", "peta situasi", "tim pelaksana")
_RE_TAHUN = re.compile(r"^\s*tahun\s+\d{4}", re.I)
_RE_SKALA = re.compile(r"^\s*skala\s*1\s*:\s*[\d.,]+\s*$", re.I)
_RE_NIP = re.compile(r"\bnip\b|mengetahui|\bketua\b|\banggota\b", re.I)


class RoleResult:
    __slots__ = ("item", "role", "source", "reason")

    def __init__(self, item, role, source, reason=""):
        self.item = item
        self.role = role
        self.source = source
        self.reason = reason

    def __repr__(self):
        return "<{} {} ({})>".format(self.item.id() or "?", self.role,
                                     self.source)


# --------------------------------------------------------------- helpers
def _label_text(label):
    try:
        txt = label.currentText()
    except (AttributeError, RuntimeError):
        txt = label.text()
    return (txt or "").strip()


def _label_size(label):
    try:
        return float(label.textFormat().size())
    except AttributeError:  # QGIS < 3.24
        return float(label.font().pointSizeF())


def _rect(item):
    return item.sceneBoundingRect()


def _inside(inner, outer, tol=1.0):
    return (inner.left() >= outer.left() - tol and
            inner.right() <= outer.right() + tol and
            inner.top() >= outer.top() - tol and
            inner.bottom() <= outer.bottom() + tol)


def saved_role(item):
    val = item.customProperty(ROLE_PROP, "")
    return str(val) if val else ""


def save_role(item, role):
    item.setCustomProperty(ROLE_PROP, role)


def _role_from_id(item):
    ident = (item.id() or "").lower().replace(" ", "_").replace("-", "_")
    if not ident:
        return ""
    for key, role in _ID_KEYWORDS:
        if key in ident:
            return role
    return ""


# --------------------------------------------------------------- guessing
def _guess_non_label(item, maps_big):
    if isinstance(item, QgsLayoutItemMap):
        return ("peta", "peta besar") if item in maps_big else (
            "peta_situasi", "peta kecil")
    if isinstance(item, QgsLayoutItemLegend):
        return "legenda", "tipe item"
    if isinstance(item, QgsLayoutItemScaleBar):
        if (item.style() or "").lower().startswith("numeric"):
            return "skala_angka", "gaya Numeric"
        return "skala_bar", "tipe item"
    if isinstance(item, QgsLayoutItemPicture):
        linked = None
        try:
            linked = item.linkedMap()
        except AttributeError:
            linked = None
        if linked is not None:
            return "panah_utara", "terhubung ke peta"
        path = (item.picturePath() or "").lower()
        if "north" in path or "arrow" in path or "utara" in path:
            return "panah_utara", "nama file panah"
        return "logo", "gambar lain"
    if isinstance(item, QgsLayoutItemShape):
        return "kotak", "tipe item"
    return "", ""


def _guess_label(label, ctx):
    text = _label_text(label)
    low = text.lower()
    first = low.splitlines()[0].strip() if low else ""
    r = _rect(label)

    if text.strip().upper() == "U":
        return "huruf_utara", "teks U"
    for m in ctx["maps_big"]:
        if _inside(r, _rect(m)) and (_RE_TAHUN.match(text) or
                                     len(text) <= 30):
            return "label_tahun", "di dalam panel peta"
    if _RE_TAHUN.match(text):
        return "label_tahun", "teks TAHUN"
    if _RE_SKALA.match(text):
        return "skala_teks", "teks SKALA 1:..."
    if any(k in low for k in ("proyeksi", "datum", "spheroid",
                              "sistem grid", "sistem koordinat")):
        return "catatan_proyeksi", "kata proyeksi/datum"
    if _RE_NIP.search(text):
        return "tanda_tangan", "NIP/ketua/anggota"
    if _heading_kind(text):
        return "judul_bagian", "judul bagian"
    if first.startswith(("dasar", "sumber")):
        return "sumber_data", "diawali Dasar/Sumber"
    if first.startswith("catatan"):
        return "catatan", "diawali Catatan"
    for head_rect, kind in ctx["headings"]:
        gap = r.top() - head_rect.bottom()
        overlap = min(r.right(), head_rect.right()) - max(
            r.left(), head_rect.left())
        if -1 <= gap <= 12 and overlap > 0:
            if kind in ("dasar", "sumber"):
                return "sumber_data", "di bawah judul " + kind.upper()
            if kind == "catatan":
                return "catatan", "di bawah judul CATATAN"
    if label is ctx["lowest"] and ("kementerian" in low or
                                   "balai" in low or "dinas" in low):
        return "instansi_penerbit", "label paling bawah"
    if label is ctx["biggest"]:
        return "judul", "huruf terbesar"
    if label is ctx["second"] and ctx["second_near_title"]:
        return "subjudul", "huruf terbesar kedua dekat judul"
    if ctx["smallest_size"] is not None and \
            _label_size(label) <= ctx["smallest_size"] + 0.01 and \
            ctx["smallest_size"] < ctx["median_size"]:
        return "catatan", "huruf terkecil"
    return "teks", "label lain"


def _heading_kind(text):
    low = text.lower().strip()
    if "\n" in low or len(low) > 40:
        return ""
    stripped = low.rstrip(" :")
    for h in _HEADINGS:
        if stripped.startswith(h):
            return h
    return ""


def _context(layout, items):
    maps = [i for i in items if isinstance(i, QgsLayoutItemMap)]
    if maps:
        biggest_area = max(_rect(m).width() * _rect(m).height()
                           for m in maps)
        maps_big = [m for m in maps
                    if _rect(m).width() * _rect(m).height() >=
                    0.25 * biggest_area]
    else:
        maps_big = []

    # label kandidat judul: yang tidak jelas perannya dari teks
    labels = [i for i in items if isinstance(i, QgsLayoutItemLabel)]
    plain = []
    for lab in labels:
        txt = _label_text(lab)
        low = txt.lower()
        if txt.strip().upper() == "U" or _RE_TAHUN.match(txt) or \
                _RE_SKALA.match(txt) or _RE_NIP.search(txt):
            continue
        if any(k in low for k in ("proyeksi", "datum", "spheroid")):
            continue
        if any(_inside(_rect(lab), _rect(m)) for m in maps_big):
            continue
        if _heading_kind(txt):
            continue
        plain.append(lab)
    by_size = sorted(plain, key=_label_size, reverse=True)
    biggest = by_size[0] if by_size else None
    second = by_size[1] if len(by_size) > 1 else None
    second_near = False
    if biggest is not None and second is not None and \
            _label_size(second) < _label_size(biggest):
        rb, rs = _rect(biggest), _rect(second)
        second_near = 0 <= rs.top() - rb.bottom() <= 15
    sizes = sorted(_label_size(lab) for lab in labels) or [0]
    lowest = max(labels, key=lambda lab: _rect(lab).bottom()) \
        if labels else None
    headings = []
    for lab in labels:
        kind = _heading_kind(_label_text(lab))
        if kind:
            headings.append((_rect(lab), kind))
    return {
        "headings": headings,
        "maps_big": maps_big,
        "biggest": biggest,
        "second": second,
        "second_near_title": second_near,
        "smallest_size": sizes[0] if labels else None,
        "median_size": sizes[len(sizes) // 2],
        "lowest": lowest,
    }


# --------------------------------------------------------------- public
def layout_items(layout):
    """Item layout yang relevan (bukan halaman, bukan grup)."""
    kinds = (QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
             QgsLayoutItemPicture, QgsLayoutItemScaleBar, QgsLayoutItemShape)
    return [i for i in layout.items() if isinstance(i, kinds)]


def detect(layout):
    """Kenali peran semua elemen. Kembalikan list RoleResult urut posisi."""
    items = layout_items(layout)
    ctx = _context(layout, items)
    results = []
    for item in items:
        role = saved_role(item)
        if role:
            results.append(RoleResult(item, role, SRC_SAVED, "dikoreksi"))
            continue
        role = _role_from_id(item)
        if role and (role != "peta_situasi" or
                     isinstance(item, QgsLayoutItemMap)):
            results.append(RoleResult(item, role, SRC_ID,
                                      "ID '{}'".format(item.id())))
            continue
        if isinstance(item, QgsLayoutItemLabel):
            role, why = _guess_label(item, ctx)
        else:
            role, why = _guess_non_label(item, ctx["maps_big"])
        if role:
            results.append(RoleResult(item, role, SRC_GUESS, why))
    results.sort(key=lambda r: (round(_rect(r.item).left() / 50),
                                _rect(r.item).top()))
    return results
