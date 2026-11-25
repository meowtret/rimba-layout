# -*- coding: utf-8 -*-
"""Uji dialog dan siklus plugin.

Jalankan: python3 tests/test_dialog.py
"""
import os
import sys
import tempfile
from unittest.mock import MagicMock

if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from qgis.core import (  # noqa: E402
    QgsApplication, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry,
    QgsProject, QgsRectangle, QgsVectorLayer,
)

APP = QgsApplication([], True)
APP.initQgis()

from qgis.gui import QgsMapCanvas  # noqa: E402
from qgis.PyQt.QtWidgets import QMessageBox  # noqa: E402

import rimba_layout  # noqa: E402

FAILS = []
OUT = os.environ.get("RIMBA_OUT", tempfile.gettempdir())


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


vl = QgsVectorLayer("Polygon?crs=EPSG:4326", "Areal", "memory")
f = QgsFeature()
f.setGeometry(QgsGeometry.fromWkt(
    "POLYGON((122.52 -1.25,122.56 -1.20,122.63 -1.21,122.58 -1.255,"
    "122.52 -1.25))"))
vl.dataProvider().addFeature(f)
QgsProject.instance().addMapLayer(vl)

canvas = QgsMapCanvas()
canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
canvas.resize(800, 500)
canvas.setLayers([vl])
canvas.setExtent(QgsRectangle(122.50, -1.27, 122.67, -1.19))

iface = MagicMock()
iface.mainWindow.return_value = None
iface.mapCanvas.return_value = canvas

print("== Siklus plugin")
plugin = rimba_layout.classFactory(iface)
plugin.initGui()
plugin.run()
dlg = plugin.dlg
check(dlg is not None, "dialog terbuka")
check(dlg.cb_preset.count() >= 3, "tiga preset tampil")
check(dlg.cb_paper.currentData() == "A3", "kertas bawaan A3")

print("== Isi form dan buat layout")
dlg.ed_name.setText("Uji Dialog")
dlg.cb_preset.setCurrentIndex(dlg.cb_preset.findText("Kemenhut SK 399/2024"))
dlg.cb_panels.setCurrentIndex(dlg.cb_panels.findData(2))
check(dlg.ed_year2.isEnabled(), "isian panel 2 aktif bila dua panel")
dlg.ed_year1.setText("TAHUN 2024 - 2025")
dlg.ed_year2.setText("TAHUN 2025 - 2026")
dlg.ed_judul.setPlainText("PETA UJI\nRIMBA LAYOUT")
dlg.ed_sk.setText("SK.1/UJI/2026")
dlg.ed_instansi.setPlainText("KEMENTERIAN KEHUTANAN\n2026")
dlg.chk["dasar"].setChecked(False)
check(not dlg.ed_dasar.isEnabled(), "Dasar tidak dicentang: isian mati")
dlg.chk_ttd.setChecked(True)
check(dlg.ed_ttd.isEnabled(), "Tanda tangan dicentang: isian aktif")
dlg.ed_ttd.setPlainText("KETUA\n\n\nNAMA")
dlg.build()
lay = QgsProject.instance().layoutManager().layoutByName("Uji Dialog")
check(lay is not None, "layout 'Uji Dialog' dibuat di proyek")
check(iface.openLayoutDesigner.called, "Layout Designer dibuka")
ids = {i.id() for i in lay.items() if hasattr(i, "id")} if lay else set()
check({"Map 1", "Map 2", "Peta Situasi", "ttd", "tahun_1",
       "tahun_2"} <= ids, "dua panel, TTD, dua label tahun ada")
check("dasar" not in ids and "judul_dasar" not in ids,
      "Dasar tidak dicentang: tidak dimuat di layout")

print("== Isian diingat")
plugin.dlg = None
plugin.run()
check(not plugin.dlg.chk["dasar"].isChecked(),
      "status centang diingat")
check(plugin.dlg.ed_sk.text() == "SK.1/UJI/2026" and
      plugin.dlg.cb_panels.currentData() == 2,
      "isian terakhir muncul lagi saat dialog dibuka")
plugin.dlg.show()
plugin.dlg.resize(560, 760)
APP.processEvents()
shot = os.path.join(OUT, "rimba_layout_dialog.png")
plugin.dlg.grab().save(shot)

print("== Kanvas kosong")
canvas.setLayers([])
plugin.dlg.cb_panels.setCurrentIndex(0)
before = len(QgsProject.instance().layoutManager().printLayouts())
QMessageBox.warning = MagicMock()
plugin.dlg.build()
check(QMessageBox.warning.called and
      len(QgsProject.instance().layoutManager().printLayouts()) == before,
      "kanvas tanpa layer: diberi peringatan, layout tidak dibuat")

plugin.unload()
check(plugin.dlg is None, "plugin dilepas bersih")
print()
print("Tangkapan dialog:", shot)
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
