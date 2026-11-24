# -*- coding: utf-8 -*-
"""Uji tahap 3: penerapan preset. Jalankan: python3 tests/test_apply.py"""
import os
import sys
import tempfile

if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from qgis.core import (  # noqa: E402
    QgsApplication, QgsExpression, QgsExpressionContext,
    QgsExpressionContextScope, QgsFeature, QgsGeometry, QgsLayoutExporter,
    QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
    QgsLayoutItemScaleBar, QgsLayoutItemShape, QgsProject, QgsVectorLayer,
)

APP = QgsApplication([], False)
APP.initQgis()

from fixtures import build_pln  # noqa: E402
from rimba_layout.core import apply, presets, roles  # noqa: E402

FAILS = []
OUT = os.environ.get("RIMBA_OUT", tempfile.gettempdir())


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


def add_data(lay):
    """Isi peta dengan satu poligon agar render tidak kosong."""
    vl = QgsVectorLayer("Polygon?crs=EPSG:4326", "HPK", "memory")
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(
        "POLYGON((122.52 -1.25,122.56 -1.20,122.60 -1.22,122.63 -1.21,"
        "122.64 -1.245,122.58 -1.255,122.52 -1.25))"))
    vl.dataProvider().addFeature(f)
    QgsProject.instance().addMapLayer(vl)
    for m in [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)]:
        m.setLayers([vl])
    return vl


def export(lay, name):
    path = os.path.join(OUT, name)
    s = QgsLayoutExporter.ImageExportSettings()
    s.dpi = 110
    QgsLayoutExporter(lay).exportToImage(path, s)
    return path


def label(lay, start):
    return [i for i in lay.items() if isinstance(i, QgsLayoutItemLabel)
            and i.text().startswith(start)][0]


def grid_label(grid, value, axis):
    ctx = QgsExpressionContext()
    sc = QgsExpressionContextScope()
    sc.setVariable("grid_number", value)
    sc.setVariable("grid_axis", axis)
    ctx.appendScope(sc)
    return QgsExpression(grid.annotationExpression()).evaluate(ctx)


PRESETS = {n: presets.load(p) for n, p, _ in presets.list_presets()}
KEM = PRESETS["Kemenhut SK 399/2024"]

print("== Kemenhut pada layout PLN dua panel (A3)")
lay = build_pln()
add_data(lay)
before_png = export(lay, "rimba_layout_sebelum.png")
res = roles.detect(lay)
n, warns = apply.apply_preset(lay, KEM, res)
after_png = export(lay, "rimba_layout_sesudah.png")
print("  elemen diubah:", n, "| peringatan:", len(warns))
for w in warns:
    print("   -", w)

j = label(lay, "PETA HASIL")
fmt = j.textFormat()
check(fmt.size() == 9 and fmt.font().bold(), "judul Arial Bold 9 pt")
check(fmt.capitalization() == apply._caps(True), "judul kapital")
check(fmt.font().family() in ("Arial", "Liberation Sans"),
      "judul huruf Arial (dapat: {})".format(fmt.font().family()))
check(label(lay, "Batas administrasi").textFormat().size() == 5.5,
      "catatan 5,5 pt")
check(label(lay, "KETERANGAN PETA").textFormat().font().bold(),
      "judul bagian bold")
t = label(lay, "TAHUN 2024")
check(t.frameEnabled() and t.hasBackground(), "label tahun berbingkai putih")

maps = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)]
big = [m for m in maps if m.rect().width() > 200]
small = [m for m in maps if m.rect().width() <= 200][0]
for m in big:
    g = m.grids().asList()[0]
    check(g.crs().authid() == "EPSG:4326", "panel: grid EPSG:4326")
    ext = m.extent()
    ivx = g.intervalX()
    nx = int(ext.xMaximum() / ivx) - int(ext.xMinimum() / ivx)
    ny = int(abs(ext.yMinimum()) / g.intervalY()) - int(
        abs(ext.yMaximum()) / g.intervalY())
    check(nx >= 2 and ny >= 2 and g.intervalX() == g.intervalY(),
          "panel: {} garis bujur, {} garis lintang (interval {:.0f}' x "
          "{:.0f}')".format(nx, ny, g.intervalX() * 60, g.intervalY() * 60))
    check(g.lineSymbol().color().name() == "#bee8ff",
          "panel: garis grid biru #bee8ff")
    check(grid_label(g, 122 + 33 / 60, "x") == "122° 33' 0\" BT",
          "panel: label 122° 33' 0\" BT")
    check(grid_label(g, -(1 + 12 / 60), "y") == "1° 12' 0\" LS",
          "panel: label 1° 12' 0\" LS")
    check(m.frameEnabled() and abs(m.frameStrokeWidth().length() - 0.7)
          < 1e-6, "panel: bingkai 0,7 mm")
gs = small.grids().asList()[0]
check(gs.annotationTextFormat().size() == 3.5,
      "peta situasi: label grid 3,5 pt")
leg = [i for i in lay.items() if isinstance(i, QgsLayoutItemLegend)][0]
check(leg.style(apply.QgsLegendStyle.Style.Title).textFormat().size() == 6.5,
      "legenda: judul 6,5 pt")
sb = [i for i in lay.items() if isinstance(i, QgsLayoutItemScaleBar)][0]
check(sb.style() == "Single Box", "skala bar Single Box")
shp = [i for i in lay.items() if isinstance(i, QgsLayoutItemShape)][0]
check(abs(shp.symbol().symbolLayer(0).strokeWidth() - 0.4) < 1e-6,
      "kotak: garis 0,4 mm")

print("== Undo")
stack = lay.undoStack().stack()
stack.undo()
check(label(lay, "PETA HASIL").textFormat().size() == 10,
      "satu Ctrl+Z: judul kembali 10 pt")
check(all(m.grids().size() == 0 for m in maps),
      "satu Ctrl+Z: grid yang dibuat hilang lagi")
stack.redo()
check(label(lay, "PETA HASIL").textFormat().size() == 9,
      "redo: judul 9 pt lagi")

print("== Grid yang sudah ada dipertahankan intervalnya")
lay2 = build_pln(False, False, True)
m2 = [i for i in lay2.items() if isinstance(i, QgsLayoutItemMap)
      and i.rect().width() > 200][0]
from qgis.core import QgsLayoutItemMapGrid  # noqa: E402
old = QgsLayoutItemMapGrid("lama", m2)
old.setIntervalX(0.05)
old.setIntervalY(0.05)
m2.grids().addGrid(old)
apply.apply_preset(lay2, KEM, roles.detect(lay2))
check(m2.grids().size() == 1 and abs(m2.grids().asList()[0].intervalX()
                                     - 0.05) < 1e-9,
      "grid lama dipakai, interval 0,05° tetap")

print("== Kertas A4")
lay3 = build_pln(False, False, False)
lay3.pageCollection().page(0).setPageSize(
    "A4", lay3.pageCollection().page(0).Orientation.Landscape)
apply.apply_preset(lay3, KEM, roles.detect(lay3))
check(label(lay3, "PETA HASIL").textFormat().size() == 6.5,
      "A4: judul 6,5 pt")

print("== Preset lain berjalan tanpa error")
for name in ("Klasik", "Minimalis"):
    lx = build_pln()
    n, w = apply.apply_preset(lx, PRESETS[name], roles.detect(lx))
    check(n > 20, "{}: {} elemen diubah".format(name, n))
    if name == "Klasik":
        g = [i for i in lx.items() if isinstance(i, QgsLayoutItemMap)
             and i.rect().width() > 200][0].grids().asList()[0]
        check(g.frameStyle() == g.FrameStyle.Zebra, "Klasik: bingkai zebra")
        export(lx, "rimba_layout_klasik.png")

print()
print("Gambar:", before_png, after_png)
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
