# -*- coding: utf-8 -*-
"""Uji tahap 4: dialog dan siklus plugin.

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
sys.path.insert(0, HERE)

from qgis.core import QgsApplication, QgsProject  # noqa: E402

APP = QgsApplication([], True)
APP.initQgis()

import rimba_layout  # noqa: E402
from fixtures import build_pln  # noqa: E402
from rimba_layout.core import roles  # noqa: E402
from rimba_layout.dialog import COL_ROLE  # noqa: E402

FAILS = []
OUT = os.environ.get("RIMBA_OUT", tempfile.gettempdir())


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


lay = build_pln()
lay.setName("Peta Hasil PLN")
QgsProject.instance().layoutManager().addLayout(lay)

iface = MagicMock()
iface.mainWindow.return_value = None
iface.openLayoutDesigners.return_value = []

print("== Siklus plugin")
plugin = rimba_layout.classFactory(iface)
plugin.initGui()
plugin.run()
dlg = plugin.dlg
check(dlg is not None and dlg.cb_layout.currentText() == "Peta Hasil PLN",
      "dialog terbuka dengan layout terpilih")
check(dlg.cb_preset.count() >= 3, "preset bawaan tampil di daftar")
check(dlg.table.rowCount() == len(roles.detect(lay)),
      "tabel peran berisi {} elemen".format(dlg.table.rowCount()))

print("== Koreksi peran lalu terapkan")
i = dlg.cb_preset.findText("Kemenhut SK 399/2024")
dlg.cb_preset.setCurrentIndex(i)
row = [r for r, res in enumerate(dlg.results)
       if res.item.id() == "" and hasattr(res.item, "text")
       and res.item.text().startswith("SK.913")][0]
combo = dlg.table.cellWidget(row, COL_ROLE)
combo.setCurrentIndex(combo.findData("subjudul"))
sk_item = dlg.results[row].item
dlg.apply()
check(roles.saved_role(sk_item) == "subjudul",
      "koreksi 'SK.913' -> subjudul tersimpan di item")
check(sk_item.textFormat().font().bold() and sk_item.textFormat().size() == 8,
      "SK.913 diberi gaya subjudul (bold 8 pt)")
check(iface.messageBar().pushSuccess.called, "pesan sukses ditampilkan")
dlg.show()
dlg.resize(760, 640)
APP.processEvents()
shot = os.path.join(OUT, "rimba_layout_dialog.png")
dlg.grab().save(shot)
plugin.unload()
check(plugin.dlg is None, "plugin dilepas bersih")

print()
print("Tangkapan dialog:", shot)
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
