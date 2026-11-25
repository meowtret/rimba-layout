# -*- coding: utf-8 -*-
"""Uji pembuat layout. Jalankan: python3 tests/test_builder.py"""
import os
import sys
import tempfile

if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from qgis.core import (  # noqa: E402
    QgsApplication, QgsCoordinateReferenceSystem, QgsExpression,
    QgsExpressionContext, QgsExpressionContextScope, QgsFeature,
    QgsGeometry, QgsLayoutExporter, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemMap, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsProject, QgsRectangle, QgsVectorLayer,
)

APP = QgsApplication([], False)
APP.initQgis()

from rimba_layout.core import builder, presets  # noqa: E402

FAILS = []
OUT = os.environ.get("RIMBA_OUT", tempfile.gettempdir())


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


def sample_layers():
    poly = QgsVectorLayer("Polygon?crs=EPSG:4326", "Areal PPKH", "memory")
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(
        "POLYGON((122.52 -1.25,122.56 -1.20,122.60 -1.22,122.63 -1.21,"
        "122.64 -1.245,122.58 -1.255,122.52 -1.25))"))
    poly.dataProvider().addFeature(f)
    road = QgsVectorLayer("LineString?crs=EPSG:4326", "Jalan", "memory")
    g = QgsFeature()
    g.setGeometry(QgsGeometry.fromWkt(
        "LINESTRING(122.50 -1.26,122.55 -1.23,122.60 -1.235,122.66 -1.20)"))
    road.dataProvider().addFeature(g)
    QgsProject.instance().addMapLayers([poly, road])
    return [poly, road]


def by_id(lay, ident):
    for i in lay.items():
        if hasattr(i, "id") and i.id() == ident:
            return i
    return None


def labels(lay):
    return [i for i in lay.items() if isinstance(i, QgsLayoutItemLabel)]


def grid_text(grid, value, axis):
    ctx = QgsExpressionContext()
    sc = QgsExpressionContextScope()
    sc.setVariable("grid_number", value)
    sc.setVariable("grid_axis", axis)
    ctx.appendScope(sc)
    return QgsExpression(grid.annotationExpression()).evaluate(ctx)


LAYERS = sample_layers()
P = {n: presets.load(p) for n, p, _ in presets.list_presets()}
BASE = dict(
    judul="PETA HASIL\nVERIFIKASI PENERIMAAN NEGARA BUKAN PAJAK (PNBP - PKH)"
          "\nPADA AREAL PERSETUJUAN PENGGUNAAN KAWASAN HUTAN\nA.N. PT. PLN "
          "(PERSERO)",
    sk="SK.913/MENLHK/SETJEN/PLA.0/10/2019",
    lokasi="DI KABUPATEN BANGGAI PROVINSI SULAWESI TENGAH\nSELUAS 0,95 HA",
    dasar="1. Peraturan Menteri Kehutanan Nomor 14 Tahun 2025",
    sumber="1. Peta RBI Skala 1:25.000 Tahun 2021",
    instansi="KEMENTERIAN KEHUTANAN\nBALAI ...\n2026",
    layers=LAYERS, extent=QgsRectangle(122.50, -1.27, 122.67, -1.19),
    crs=QgsCoordinateReferenceSystem("EPSG:4326"))

CASES = [
    ("Kemenhut A3 satu panel", "Kemenhut SK 399/2024",
     dict(paper="A3", panels=1, years=["TAHUN 2025", ""])),
    ("Kemenhut A3 dua panel TTD", "Kemenhut SK 399/2024",
     dict(paper="A3", panels=2, years=["TAHUN 2024", "TAHUN 2025"],
          ttd="TIM PELAKSANA\nKETUA\n\n\nNAMA\nNIP. 1990")),
    ("Klasik A4", "Klasik", dict(paper="A4", panels=1)),
    ("Minimalis A1", "Minimalis", dict(paper="A1", panels=1)),
]

for title, preset, extra in CASES:
    print("== " + title)
    opts = builder.BuildOptions(name=title, **BASE, **extra)
    lay, warns = builder.build_layout(QgsProject.instance(), P[preset], opts)
    warns = [w for w in warns if "tidak terpasang" not in w]
    check(not warns, "tanpa peringatan {}".format(warns or ""))
    page = lay.pageCollection().page(0)
    pw = page.rect().width()
    ph = page.rect().height()
    # kotak item (tanpa perkiraan ruang label grid milik QGIS)
    outside = [i for i in lay.items()
               if hasattr(i, "id") and i is not page and
               (i.pos().x() + i.rect().width() > pw + 0.5 or
                i.pos().y() + i.rect().height() > ph + 0.5 or
                i.pos().x() < -0.5 or i.pos().y() < -0.5)]
    check(not outside, "semua elemen di dalam halaman")
    maps = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)]
    n_panel = extra["panels"]
    check(len(maps) == n_panel + 1, "{} panel + peta situasi".format(
        n_panel))
    m1 = by_id(lay, "Map 1")
    check(m1 is not None and m1.layers() == LAYERS,
          "Map 1 memakai layer kanvas")
    g = m1.grids().asList()[0]
    check(grid_text(g, 122.55, "x").endswith("BT") and
          grid_text(g, -1.2, "y").endswith("LS"), "grid berlabel BT / LS")
    sit = by_id(lay, "Peta Situasi")
    check(sit.overviews().size() == 1 and
          sit.overviews().overview(0).linkedMap() is m1,
          "peta situasi menandai cakupan Map 1")
    leg = [i for i in lay.items() if isinstance(i, QgsLayoutItemLegend)][0]
    check(leg.linkedMap() is m1, "legenda terhubung ke Map 1")
    bars = {i.id(): i for i in lay.items()
            if isinstance(i, QgsLayoutItemScaleBar)}
    sb, sbc = bars.get("skala_bar"), bars.get("skala_bar_cm")
    check(sb is not None and sbc is not None and sb.linkedMap() is m1,
          "skala bar Km + Cm terhubung ke Map 1")
    check(sb.unitLabel() == "Km" and sbc.unitLabel() == "Cm" and
          abs(sb.pos().x() - sbc.pos().x()) < 1e-6 and
          sbc.pos().y() < sb.pos().y(),
          "label Cm di atas, Km di bawah, sejajar kiri")
    cm_per_seg = sbc.unitsPerSegment() / sbc.mapUnitsPerScaleBarUnit()
    km_per_seg = sb.unitsPerSegment()
    check(abs(km_per_seg - cm_per_seg * m1.scale() / 100000) < 1e-6,
          "1 segmen = {:g} cm = {:g} km".format(cm_per_seg, km_per_seg))
    kn, kv = by_id(lay, "proyeksi_nama"), by_id(lay, "proyeksi_nilai")
    check(kv.text().count("\n: ") == 2 and kv.text().startswith(": ") and
          kv.pos().x() > kn.pos().x() + kn.rect().width() - 0.01 and
          abs(kn.pos().y() - kv.pos().y()) < 1e-6,
          "kolom proyeksi: tanda ':' sejajar dalam satu kolom")
    arrow = by_id(lay, "panah_utara")
    check(isinstance(arrow, QgsLayoutItemPicture) and
          arrow.linkedMap() is m1, "panah utara terhubung ke Map 1")
    skala = by_id(lay, "skala_teks").currentText()
    check(skala.startswith("SKALA 1:") and "." in skala,
          "teks skala dinamis: " + skala)
    check(abs(m1.scale() - builder.nice_scale(m1.scale() - 1)) < 1,
          "skala Map 1 bulat (1:{:,.0f})".format(m1.scale()))
    # kepala tidak saling menimpa
    head = [by_id(lay, k) for k in ("judul", "sk", "lokasi", "huruf_u")]
    tops = [h.sceneBoundingRect() for h in head]
    check(all(tops[i].bottom() <= tops[i + 1].top() + 0.01
              for i in range(len(tops) - 1)),
          "judul, SK, lokasi, U tersusun tanpa tumpang")
    check((by_id(lay, "ttd") is not None) == bool(extra.get("ttd")),
          "blok TTD hanya bila diisi")
    years = [x for x in extra.get("years", []) if x]
    got = [lab.text() for lab in labels(lay) if lab.id().startswith(
        "tahun_")]
    check(sorted(got) == sorted(years), "label tahun: {}".format(got))
    png = os.path.join(OUT, "rimba_" + title.replace(" ", "_") + ".png")
    s = QgsLayoutExporter.ImageExportSettings()
    s.dpi = 90
    QgsLayoutExporter(lay).exportToImage(png, s)

print("== Nama layout tidak bentrok")
lay2, _ = builder.build_layout(
    QgsProject.instance(), P["Klasik"],
    builder.BuildOptions(name="Klasik A4", **BASE))
check(lay2.name() == "Klasik A4 (2)", "nama kembar jadi 'Klasik A4 (2)'")

print("== Skala bulat")
check([builder.nice_scale(s) for s in (23000, 25000, 61000, 140000)] ==
      [25000, 25000, 100000, 200000], "23rb->25rb, 61rb->100rb, 140rb->200rb")

print()
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
