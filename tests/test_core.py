# -*- coding: utf-8 -*-
"""Uji headless tahap 1-2 Rimba Layout.

Jalankan:  QT_QPA_PLATFORM=offscreen python3 tests/test_core.py
"""
import os
import sys

import tempfile  # noqa: E402

# Di Linux tanpa layar pakai "offscreen". Di Windows biarkan bawaan, supaya
# Qt memakai huruf sistem (offscreen di Windows tidak menemukan folder font).
if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgis.core import (  # noqa: E402
    QgsApplication, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
    QgsLayoutItemPage, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsLayoutItemShape, QgsPrintLayout,
    QgsProject, QgsRectangle, QgsTextFormat,
)
from qgis.PyQt.QtCore import QRectF  # noqa: E402
from qgis.PyQt.QtGui import QFont  # noqa: E402

APP = QgsApplication([], False)
APP.initQgis()

from rimba_layout.core import presets, roles, scale  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


# ------------------------------------------------------------------ helpers
def new_layout(name, paper="A3"):
    lay = QgsPrintLayout(QgsProject.instance())
    lay.initializeDefaults()
    lay.setName(name)
    page = lay.pageCollection().page(0)
    page.setPageSize(paper, QgsLayoutItemPage.Orientation.Landscape)
    return lay


def add_label(lay, text, x, y, w, h, size, bold=False, ident=""):
    lab = QgsLayoutItemLabel(lay)
    lab.setText(text)
    fmt = QgsTextFormat()
    f = QFont("Arial")
    f.setBold(bold)
    fmt.setFont(f)
    fmt.setSize(size)
    try:
        lab.setTextFormat(fmt)
    except AttributeError:
        f.setPointSizeF(size)
        lab.setFont(f)
    if ident:
        lab.setId(ident)
    lay.addLayoutItem(lab)
    lab.attemptSetSceneRect(QRectF(x, y, w, h))
    return lab


def add_map(lay, x, y, w, h, ident=""):
    m = QgsLayoutItemMap(lay)
    lay.addLayoutItem(m)
    m.attemptSetSceneRect(QRectF(x, y, w, h))
    m.setExtent(QgsRectangle(122.5, -1.26, 122.66, -1.19))
    if ident:
        m.setId(ident)
    return m


def add_shape(lay, x, y, w, h):
    s = QgsLayoutItemShape(lay)
    s.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
    lay.addLayoutItem(s)
    s.attemptSetSceneRect(QRectF(x, y, w, h))
    return s


def build_pln(two_panels=True, with_ttd=True, with_year=True, ids=False):
    """Tiruan layout PNBP-PKH PLN: A3 mendatar, panel peta kiri, info kanan."""
    lay = new_layout("PLN {}".format(2 if two_panels else 1))
    add_shape(lay, 5, 5, 410, 287)                      # bingkai luar
    ph = 135 if two_panels else 270
    m1 = add_map(lay, 12, 12, 290, ph - 15, "peta_utama" if ids else "")
    add_shape(lay, 8, 8, 298, ph - 7)
    if with_year:
        add_label(lay, "TAHUN 2024 - 2025", 250, ph - 15, 48, 8, 11, True,
                  "tahun1" if ids else "")
    if two_panels:
        add_map(lay, 12, 152, 290, 120)
        add_shape(lay, 8, 148, 298, 132)
        if with_year:
            add_label(lay, "TAHUN 2025 - 2026", 250, 262, 48, 8, 11, True)
    # panel kanan
    add_shape(lay, 310, 8, 103, 95)
    logo = QgsLayoutItemPicture(lay)
    logo.setPicturePath("/tmp/logo_kemenhut.png")
    lay.addLayoutItem(logo)
    logo.attemptSetSceneRect(QRectF(352, 10, 18, 14))
    add_label(lay, "PETA HASIL\nVERIFIKASI PENERIMAAN NEGARA BUKAN PAJAK",
              315, 26, 93, 14, 10, True, "judul" if ids else "")
    add_label(lay, "SK.913/MENLHK/SETJEN/PLA.0/10/2019", 315, 41, 93, 4, 8)
    add_label(lay, "DI KABUPATEN BANGGAI PROVINSI SULAWESI TENGAH",
              315, 46, 93, 8, 9, True)
    add_label(lay, "U", 357, 56, 6, 5, 12, True)
    arrow = QgsLayoutItemPicture(lay)
    lay.addLayoutItem(arrow)
    arrow.setLinkedMap(m1)
    arrow.attemptSetSceneRect(QRectF(356, 61, 8, 12))
    add_label(lay, "SKALA 1:25.000", 340, 74, 40, 5, 9, True)
    sb = QgsLayoutItemScaleBar(lay)
    sb.setStyle("Single Box")
    sb.setLinkedMap(m1)
    lay.addLayoutItem(sb)
    sb.attemptSetSceneRect(QRectF(320, 80, 80, 8))
    add_label(lay, "Proyeksi : Transverse Mercator\nSistem Grid : Grid "
              "Geografi\nSpheroid : WGS 1984", 330, 90, 60, 12, 8)
    add_shape(lay, 310, 105, 103, 65)
    add_label(lay, "KETERANGAN PETA :", 313, 107, 50, 5, 9, True)
    leg = QgsLayoutItemLegend(lay)
    lay.addLayoutItem(leg)
    leg.attemptSetSceneRect(QRectF(313, 113, 95, 35))
    add_label(lay, "Fungsi Kawasan Hutan", 313, 150, 50, 5, 9, True)
    add_shape(lay, 310, 172, 103, 45)
    add_label(lay, "DASAR :", 313, 174, 30, 4, 9, True)
    add_label(lay, "1. Peraturan Menteri Kehutanan Nomor 14 Tahun 2025\n"
              "2. Keputusan Menteri LHK Nomor 399 Tahun 2024",
              313, 178, 95, 10, 7)
    add_label(lay, "SUMBER PETA :", 313, 190, 40, 4, 9, True)
    add_label(lay, "1. Peta RBI Skala 1:25.000 Tahun 2021\n2. Citra "
              "Sentinel-2 L2A", 313, 194, 95, 10, 7)
    add_label(lay, "CATATAN :", 313, 206, 30, 4, 9, True)
    add_label(lay, "Batas administrasi pemerintahan tidak sepenuhnya dapat "
              "digunakan sebagai acuan.", 313, 210, 95, 6, 7)
    add_shape(lay, 310, 219, 103, 35)
    add_map(lay, 314, 222, 95, 30, "")                   # peta situasi
    add_label(lay, "PETA SITUASI", 385, 223, 22, 4, 7, True)
    if with_ttd:
        add_shape(lay, 310, 256, 103, 20)
        add_label(lay, "TIM PELAKSANA\nKETUA", 340, 257, 40, 6, 6, True)
        add_label(lay, "DEWI PERMATASARI ANANDA, S.Hut\nNIP. 19921004 "
                  "202321 2 027", 330, 266, 55, 6, 6)
    add_label(lay, "KEMENTERIAN KEHUTANAN\nDIREKTORAT JENDERAL PLANOLOGI "
              "KEHUTANAN\nBALAI PEMANTAPAN KAWASAN HUTAN WILAYAH XVI\n2026",
              315, 278, 93, 12, 8, True)
    return lay


def roles_by_text(results):
    out = {}
    for r in results:
        if isinstance(r.item, QgsLayoutItemLabel):
            key = r.item.text().splitlines()[0][:28]
        else:
            key = "{}#{}".format(type(r.item).__name__.replace(
                "QgsLayoutItem", ""), id(r.item) % 1000)
        out[key] = r.role
    return out


# ------------------------------------------------------------------ tests
print("== Tahap 1: skala kertas")
for paper, expect in (("A4", 210), ("A3", 297), ("A1", 594), ("A0", 841)):
    lay = new_layout("uji " + paper, paper)
    short = scale.page_short_side_mm(lay)
    check(abs(short - expect) < 0.5,
          "{}: sisi pendek {:.0f} mm".format(paper, short))
f_a4 = scale.factor(210)
check(scale.font_pt(18, f_a4) == 12.5, "judul 18 pt di A4 -> 12,5 pt")
check(scale.font_pt(8, f_a4) == 6.0, "catatan 8 pt di A4 -> 6 pt (batas)")
check(scale.font_pt(18, scale.factor(841)) == 51.0,
      "judul 18 pt di A0 -> 51")
check(scale.font_pt(8, scale.factor(420)) == 11.5,
      "catatan 8 pt di A2 -> 11,5")

print("== Tahap 1: preset")
listed = presets.list_presets()
names = sorted(n for n, _, _ in listed)
check(names == ["Kemenhut SK 399/2024", "Klasik", "Minimalis"],
      "tiga preset bawaan terbaca: " + ", ".join(names))
kem = [presets.load(p) for n, p, _ in listed if n.startswith("Kemenhut")][0]
check(kem["roles"]["judul"]["bold"] and kem["roles"]["judul"]["uppercase"],
      "Kemenhut: judul bold kapital")
check(kem["grid"]["line_color"].upper() == "#BEE8FF",
      "Kemenhut: garis grid biru R190 G232 B255")
check(kem["grid"]["spaced"] and not kem["grid"]["pad"],
      "Kemenhut: label grid 122° 33' 0\" BT")
bad_cases = [
    ({"name": "x", "version": 1, "base_paper": "A5", "roles": {}},
     "kertas A5"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judulx": {}}}, "peran tidak dikenal"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judul": {"size": "besar"}}}, "ukuran bukan angka"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judul": {"color": "merah"}}}, "warna bukan #RRGGBB"),
]
for data, why in bad_cases:
    try:
        presets.validate(data)
        check(False, "preset rusak ditolak: " + why)
    except presets.PresetError as err:
        check(True, "preset rusak ditolak: {} ({})".format(why, err))
tmp = os.path.join(tempfile.gettempdir(), "rimba_layout_uji.json")
presets.save(kem, tmp)
check(presets.load(tmp) == kem, "simpan lalu muat ulang preset identik")

print("== Tahap 2: pengenalan peran, layout PLN dua panel")
EXPECT = {
    "TAHUN 2024 - 2025": "label_tahun",
    "TAHUN 2025 - 2026": "label_tahun",
    "PETA HASIL": "judul",
    "SK.913/MENLHK/SETJEN/PLA.0/1": "teks",
    "DI KABUPATEN BANGGAI PROVINS": "subjudul",
    "U": "huruf_utara",
    "SKALA 1:25.000": "skala_teks",
    "Proyeksi : Transverse Mercat": "catatan_proyeksi",
    "KETERANGAN PETA :": "judul_bagian",
    "Fungsi Kawasan Hutan": "judul_bagian",
    "DASAR :": "judul_bagian",
    "1. Peraturan Menteri Kehutan": "sumber_data",
    "SUMBER PETA :": "judul_bagian",
    "1. Peta RBI Skala 1:25.000 T": "sumber_data",
    "CATATAN :": "judul_bagian",
    "Batas administrasi pemerinta": "catatan",
    "PETA SITUASI": "judul_bagian",
    "TIM PELAKSANA": "tanda_tangan",
    "DEWI PERMATASARI ANANDA, S.H": "tanda_tangan",
    "KEMENTERIAN KEHUTANAN": "instansi_penerbit",
}


def run_case(title, lay, expect_maps, expect_labels):
    print("-- " + title)
    res = roles.detect(lay)
    got = roles_by_text(res)
    for key, role in expect_labels.items():
        check(got.get(key) == role, "{:<30} -> {} (dapat: {})".format(
            key, role, got.get(key)))
    kinds = {}
    for r in res:
        if not isinstance(r.item, QgsLayoutItemLabel):
            kinds.setdefault(r.role, 0)
            kinds[r.role] += 1
    for role, n in expect_maps.items():
        check(kinds.get(role, 0) == n, "{} x{} (dapat {})".format(
            role, n, kinds.get(role, 0)))
    return res


run_case("dua panel, TTD, tahun", build_pln(),
         {"peta": 2, "peta_situasi": 1, "legenda": 1, "skala_bar": 1,
          "panah_utara": 1, "logo": 1}, EXPECT)

one = {k: v for k, v in EXPECT.items()
       if k not in ("TAHUN 2025 - 2026", "TIM PELAKSANA",
                    "DEWI PERMATASARI ANANDA, S.H")}
run_case("satu panel, tanpa TTD", build_pln(False, False, True),
         {"peta": 1, "peta_situasi": 1}, one)

print("-- lapis ID dan peran tersimpan")
lay = build_pln(False, False, True, ids=True)
res = roles.detect(lay)
src = {r.item.id(): (r.role, r.source) for r in res if r.item.id()}
check(src.get("judul") == ("judul", roles.SRC_ID), "ID 'judul' dikenali")
check(src.get("tahun1") == ("label_tahun", roles.SRC_ID),
      "ID 'tahun1' dikenali")
sk = [r for r in res if isinstance(r.item, QgsLayoutItemLabel) and
      r.item.text().startswith("SK.913")][0]
roles.save_role(sk.item, "subjudul")
again = [r for r in roles.detect(lay) if r.item is sk.item][0]
check((again.role, again.source) == ("subjudul", roles.SRC_SAVED),
      "koreksi pengguna tersimpan dan dipakai ulang")

print()
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
