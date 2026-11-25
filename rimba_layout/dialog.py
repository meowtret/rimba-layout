# -*- coding: utf-8 -*-
"""Dialog Rimba Layout: isi form, pilih preset, buat layout."""

import os

from qgis.core import QgsApplication, QgsProject, QgsSettings
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .core import builder, presets

SKEY = "rimba_layout/form/"
CANVAS = "__kanvas__"

PLACEHOLDER = {
    "judul": "PETA ...\nPADA AREAL ...\nA.N. ...",
    "sk": "SK.xxx/MENLHK/SETJEN/PLA.0/xx/20xx",
    "lokasi": "DI KABUPATEN ... PROVINSI ...\nSELUAS ... HA",
    "dasar": "1. Peraturan Menteri ...\n2. Keputusan Menteri LHK Nomor 399 "
             "Tahun 2024",
    "sumber": "1. Peta RBI Skala 1:25.000 Tahun ...\n2. Citra Sentinel-2 ...",
    "ttd": "TIM PELAKSANA\nKETUA\n\n\n\nNAMA LENGKAP\nNIP. ...",
    "instansi": "KEMENTERIAN KEHUTANAN\nDIREKTORAT JENDERAL ...\nBALAI ...\n"
                "2026",
}


def INFO_FIELDS(dlg):  # noqa: N802
    """(kunci, nama di form, widget isian) informasi tepi, urut tampil."""
    return [
        ("judul", "Judul", dlg.ed_judul),
        ("sk", "Nomor SK", dlg.ed_sk),
        ("lokasi", "Lokasi / luas", dlg.ed_lokasi),
        ("dasar", "Dasar", dlg.ed_dasar),
        ("sumber", "Sumber peta", dlg.ed_sumber),
        ("catatan", "Catatan", dlg.ed_catatan),
        ("ttd", "Tanda tangan", dlg.ed_ttd),
        ("instansi", "Instansi penerbit", dlg.ed_instansi),
    ]


# isian yang tercentang saat dialog pertama kali dibuka
DEFAULT_ON = {"judul", "sk", "lokasi", "dasar", "sumber", "catatan",
              "instansi"}


def user_preset_dir():
    path = os.path.join(QgsApplication.qgisSettingsDirPath(),
                        "rimba_layout", "presets")
    os.makedirs(path, exist_ok=True)
    return path


def _text_box(key, lines=3):
    box = QPlainTextEdit()
    box.setPlaceholderText(PLACEHOLDER.get(key, ""))
    box.setFixedHeight(18 * lines + 14)
    return box


class RimbaLayoutDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Rimba Layout — buat layout dari preset")
        self.resize(560, 760)
        self._build_ui()
        self.reload_presets()
        self.reload_themes()
        self._load()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        main = QVBoxLayout(inner)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        g = QGroupBox("Halaman")
        f = QFormLayout(g)
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Nama layout di proyek")
        f.addRow("Nama layout", self.ed_name)
        self.cb_preset = QComboBox()
        f.addRow("Preset", self.cb_preset)
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color:#777;")
        f.addRow("", self.lbl_desc)
        self.cb_paper = QComboBox()
        for p in builder.PAPERS:
            self.cb_paper.addItem(p + " mendatar", p)
        f.addRow("Kertas", self.cb_paper)
        self.cb_panels = QComboBox()
        self.cb_panels.addItem("Satu panel peta", 1)
        self.cb_panels.addItem("Dua panel peta", 2)
        f.addRow("Panel", self.cb_panels)
        self.cb_theme1 = QComboBox()
        self.cb_theme2 = QComboBox()
        f.addRow("Isi panel 1", self.cb_theme1)
        f.addRow("Isi panel 2", self.cb_theme2)
        self.ed_year1 = QLineEdit()
        self.ed_year2 = QLineEdit()
        for ed in (self.ed_year1, self.ed_year2):
            ed.setPlaceholderText("mis. TAHUN 2024 - 2025 (kosongkan bila "
                                  "tidak perlu)")
        f.addRow("Label tahun panel 1", self.ed_year1)
        f.addRow("Label tahun panel 2", self.ed_year2)
        row = QHBoxLayout()
        self.ed_logo = QLineEdit()
        self.ed_logo.setPlaceholderText("Opsional: file PNG/SVG/JPG")
        btn = QPushButton("…")
        btn.setFixedWidth(30)
        btn.clicked.connect(self.pick_logo)
        row.addWidget(self.ed_logo, 1)
        row.addWidget(btn)
        f.addRow("Logo instansi", row)
        main.addWidget(g)

        g = QGroupBox("Isi informasi tepi")
        f = QFormLayout(g)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft |
                            Qt.AlignmentFlag.AlignTop)
        hint = QLabel("Centang isian yang ingin dimuat di layout.")
        hint.setStyleSheet("color:#777;")
        f.addRow(hint)
        self.ed_judul = _text_box("judul", 4)
        self.ed_sk = QLineEdit()
        self.ed_sk.setPlaceholderText(PLACEHOLDER["sk"])
        self.ed_lokasi = _text_box("lokasi", 2)
        self.ed_dasar = _text_box("dasar", 3)
        self.ed_sumber = _text_box("sumber", 3)
        self.ed_catatan = _text_box("catatan", 2)
        self.ed_ttd = _text_box("ttd", 4)
        self.ed_instansi = _text_box("instansi", 4)
        self.chk = {}
        for key, title, field in INFO_FIELDS(self):
            chk = QCheckBox(title)
            chk.toggled.connect(field.setEnabled)
            self.chk[key] = chk
            f.addRow(chk, field)
        self.chk_ttd = self.chk["ttd"]
        main.addWidget(g)
        main.addStretch(1)

        note = QLabel("Peta diambil dari kanvas QGIS saat ini: layer yang "
                      "tampil, cakupan, dan sistem koordinatnya.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#777;")
        outer.addWidget(note)
        bb = QDialogButtonBox()
        role = QDialogButtonBox.ButtonRole
        self.btn_build = bb.addButton("Buat layout", role.ActionRole)
        bb.addButton("Tutup", role.RejectRole)
        self.btn_build.clicked.connect(self.build)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)

        self.cb_preset.currentIndexChanged.connect(self.update_desc)
        self.cb_panels.currentIndexChanged.connect(self.update_enabled)

    # ------------------------------------------------------------ data
    def reload_presets(self):
        current = self.cb_preset.currentData()
        self.cb_preset.blockSignals(True)
        self.cb_preset.clear()
        for name, path, builtin in presets.list_presets(user_preset_dir()):
            self.cb_preset.addItem(
                name if builtin else name + " (milik saya)", path)
        i = self.cb_preset.findData(current)
        if i >= 0:
            self.cb_preset.setCurrentIndex(i)
        self.cb_preset.blockSignals(False)
        self.update_desc()

    def reload_themes(self):
        names = QgsProject.instance().mapThemeCollection().mapThemes()
        for cb in (self.cb_theme1, self.cb_theme2):
            cur = cb.currentData()
            cb.clear()
            cb.addItem("Kanvas saat ini", CANVAS)
            for n in names:
                cb.addItem("Tema: " + n, n)
            i = cb.findData(cur)
            if i >= 0:
                cb.setCurrentIndex(i)

    def update_desc(self):
        pre = self.current_preset(quiet=True)
        self.lbl_desc.setText(pre.get("description", "") if pre else "")

    def update_enabled(self):
        two = self.cb_panels.currentData() == 2
        self.cb_theme2.setEnabled(two)
        self.ed_year2.setEnabled(two)
        for key, _, field in INFO_FIELDS(self):
            field.setEnabled(self.chk[key].isChecked())

    def current_preset(self, quiet=False):
        path = self.cb_preset.currentData()
        if not path:
            return None
        try:
            return presets.load(path)
        except presets.PresetError as err:
            if not quiet:
                QMessageBox.warning(self, "Rimba Layout",
                                    "Preset tidak bisa dipakai:\n{}".format(
                                        err))
            return None

    def pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih logo", self.ed_logo.text(),
            "Gambar (*.png *.svg *.jpg *.jpeg)")
        if path:
            self.ed_logo.setText(path)

    # ------------------------------------------------------- simpan isian
    def _fields(self):
        return {
            "name": self.ed_name, "year1": self.ed_year1,
            "year2": self.ed_year2, "logo": self.ed_logo,
            "sk": self.ed_sk, "judul": self.ed_judul,
            "lokasi": self.ed_lokasi, "dasar": self.ed_dasar,
            "sumber": self.ed_sumber, "catatan": self.ed_catatan,
            "ttd": self.ed_ttd, "instansi": self.ed_instansi,
        }

    @staticmethod
    def _get(w):
        return w.toPlainText() if isinstance(w, QPlainTextEdit) else w.text()

    def _load(self):
        s = QgsSettings()
        for key, w in self._fields().items():
            default = builder.DEFAULT_CATATAN if key == "catatan" else ""
            val = s.value(SKEY + key, default, type=str)
            if isinstance(w, QPlainTextEdit):
                w.setPlainText(val)
            else:
                w.setText(val)
        i = self.cb_paper.findData(s.value(SKEY + "paper", "A3", type=str))
        if i >= 0:
            self.cb_paper.setCurrentIndex(i)
        i = self.cb_panels.findData(s.value(SKEY + "panels", 1, type=int))
        if i >= 0:
            self.cb_panels.setCurrentIndex(i)
        i = self.cb_preset.findData(s.value(SKEY + "preset", "", type=str))
        if i >= 0:
            self.cb_preset.setCurrentIndex(i)
        for key, _, _ in INFO_FIELDS(self):
            self.chk[key].setChecked(s.value(
                SKEY + "use_" + key, key in DEFAULT_ON, type=bool))
        self.update_enabled()

    def _save(self):
        s = QgsSettings()
        for key, w in self._fields().items():
            s.setValue(SKEY + key, self._get(w))
        s.setValue(SKEY + "paper", self.cb_paper.currentData())
        s.setValue(SKEY + "panels", self.cb_panels.currentData())
        s.setValue(SKEY + "preset", self.cb_preset.currentData())
        for key, _, _ in INFO_FIELDS(self):
            s.setValue(SKEY + "use_" + key, self.chk[key].isChecked())

    # ------------------------------------------------------------ buat
    def _val(self, key):
        """Isi field bila dicentang; kosong berarti tidak dimuat."""
        if not self.chk[key].isChecked():
            return ""
        field = dict((k, w) for k, _, w in INFO_FIELDS(self))[key]
        return self._get(field).strip()

    def build(self):
        pre = self.current_preset()
        if pre is None:
            return
        canvas = self.iface.mapCanvas()
        layers = canvas.layers()
        panels = self.cb_panels.currentData()
        themes = [self.cb_theme1.currentData(), self.cb_theme2.currentData()]
        used = themes[:panels]
        if not layers and CANVAS in used:
            QMessageBox.warning(
                self, "Rimba Layout",
                "Kanvas belum menampilkan layer. Tampilkan layer yang ingin "
                "dipetakan dulu, lalu coba lagi.")
            return
        opts = builder.BuildOptions(
            name=self.ed_name.text().strip() or "Peta Rimba Layout",
            paper=self.cb_paper.currentData(),
            panels=panels,
            themes=[None if t == CANVAS else t for t in themes],
            years=[self.ed_year1.text().strip(),
                   self.ed_year2.text().strip() if panels == 2 else ""],
            judul=self._val("judul"),
            sk=self._val("sk"),
            lokasi=self._val("lokasi"),
            dasar=self._val("dasar"),
            sumber=self._val("sumber"),
            catatan=self._val("catatan"),
            ttd=self._val("ttd"),
            logo=self.ed_logo.text().strip(),
            instansi=self._val("instansi"),
            layers=layers,
            extent=canvas.extent(),
            crs=canvas.mapSettings().destinationCrs(),
        )
        lay, warnings = builder.build_layout(QgsProject.instance(), pre,
                                             opts)
        self._save()
        self.iface.openLayoutDesigner(lay)
        self.iface.messageBar().pushSuccess(
            "Rimba Layout", "Layout '{}' dibuat dengan preset '{}'.".format(
                lay.name(), pre["name"]))
        if opts.logo and not os.path.exists(opts.logo):
            warnings.append("File logo tidak ditemukan: " + opts.logo)
        if warnings:
            QMessageBox.information(
                self, "Rimba Layout — perlu dicek",
                "Layout sudah dibuat, tapi ada yang perlu dicek:\n\n- " +
                "\n- ".join(warnings))
