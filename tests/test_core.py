# -*- coding: utf-8 -*-
"""Uji inti Rimba Layout: skala kertas dan preset.

Jalankan:  QT_QPA_PLATFORM=offscreen python3 tests/test_core.py
"""
import os
import sys

import tempfile  # noqa: E402

# Di Linux tanpa layar pakai "offscreen". Di Windows biarkan bawaan, supaya
# Qt memakai huruf sistem (offscreen di Windows tidak menemukan folder font).
if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from qgis.core import QgsApplication  # noqa: E402

APP = QgsApplication([], False)
APP.initQgis()

from rimba_layout.core import presets, scale  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


from qgis.core import (  # noqa: E402
    QgsLayoutItemPage, QgsPrintLayout, QgsProject,
)


def new_layout(name, paper="A3"):
    lay = QgsPrintLayout(QgsProject.instance())
    lay.initializeDefaults()
    lay.setName(name)
    lay.pageCollection().page(0).setPageSize(
        paper, QgsLayoutItemPage.Orientation.Landscape)
    return lay


# ------------------------------------------------------------------ tests
print("== Tahap 1: skala kertas")
for paper, expect in (("A4", 210), ("A3", 297), ("A1", 594), ("A0", 841)):
    lay = new_layout("uji " + paper, paper)
    short = scale.page_short_side_mm(lay)
    check(abs(short - expect) < 0.5,
          "{}: sisi pendek {:.0f} mm".format(paper, short))
f_a4 = scale.factor(210)
check(scale.font_pt(18, f_a4) == 12.5, "judul 18 pt di A4 -> 12,5 pt")
check(scale.font_pt(8, f_a4) == 5.5, "catatan 8 pt di A4 -> 5,5 pt")
check(scale.font_pt(3.5, f_a4) == 3.5, "3,5 pt di A4 tetap 3,5 (batas bawah)")
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

print()
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
