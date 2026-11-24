# -*- coding: utf-8 -*-
"""Dialog Rimba Layout: pilih layout dan preset, periksa peran, terapkan."""

import os

from qgis.core import (
    QgsApplication, QgsLayoutItemLabel, QgsProject, QgsSettings,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from .core import apply, presets, roles, scale

SKEY = "rimba_layout/"
COL_ITEM, COL_TYPE, COL_ROLE, COL_SRC = range(4)


def user_preset_dir():
    path = os.path.join(QgsApplication.qgisSettingsDirPath(),
                        "rimba_layout", "presets")
    os.makedirs(path, exist_ok=True)
    return path


def describe(item):
    if isinstance(item, QgsLayoutItemLabel):
        txt = item.currentText().strip().splitlines()
        first = txt[0] if txt else ""
        return first[:45] + ("…" if len(first) > 45 else "")
    return item.displayName()


def type_name(item):
    name = type(item).__name__.replace("QgsLayoutItem", "")
    return {"Label": "Label", "Map": "Peta", "Legend": "Legenda",
            "ScaleBar": "Skala", "Picture": "Gambar",
            "Shape": "Kotak"}.get(name, name)


class RimbaLayoutDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.results = []
        self.setWindowTitle("Rimba Layout — ganti gaya layout")
        self.resize(720, 620)
        self._build_ui()
        self.reload_presets()
        self.reload_layouts()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        main = QVBoxLayout(self)
        form = QFormLayout()
        row = QHBoxLayout()
        self.cb_layout = QComboBox()
        btn = QPushButton("↻")
        btn.setFixedWidth(30)
        btn.setToolTip("Muat ulang daftar layout")
        btn.clicked.connect(self.reload_layouts)
        row.addWidget(self.cb_layout, 1)
        row.addWidget(btn)
        form.addRow("Layout", row)
        self.cb_preset = QComboBox()
        form.addRow("Preset", self.cb_preset)
        self.lbl_info = QLabel()
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("color:#555;")
        form.addRow("", self.lbl_info)
        main.addLayout(form)

        main.addWidget(QLabel(
            "Periksa peran tiap elemen. Ubah kolom <b>Peran</b> bila "
            "tebakannya salah; koreksi disimpan di layout."))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Elemen", "Tipe", "Peran", "Sumber"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(COL_ITEM, QHeaderView.ResizeMode.Stretch)
        for c in (COL_TYPE, COL_ROLE):
            hh.setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_SRC, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(COL_SRC, 190)
        self.table.verticalHeader().setVisible(False)
        main.addWidget(self.table, 1)
        self.lbl_empty = QLabel()
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setStyleSheet(
            "color:#8a6d00; font-weight:bold; padding:6px;")
        self.lbl_empty.hide()
        main.addWidget(self.lbl_empty)

        bb = QDialogButtonBox()
        role = QDialogButtonBox.ButtonRole
        self.btn_scan = bb.addButton("Pindai ulang", role.ActionRole)
        self.btn_apply = bb.addButton("Terapkan", role.ApplyRole)
        bb.addButton("Tutup", role.RejectRole)
        self.btn_scan.clicked.connect(self.scan)
        self.btn_apply.clicked.connect(self.apply)
        bb.rejected.connect(self.reject)
        main.addWidget(bb)

        self.cb_layout.currentIndexChanged.connect(self.scan)
        self.cb_preset.currentIndexChanged.connect(self.update_info)

    # ------------------------------------------------------------ data
    def reload_presets(self):
        last = QgsSettings().value(SKEY + "preset", "", type=str)
        self.cb_preset.blockSignals(True)
        self.cb_preset.clear()
        for name, path, builtin in presets.list_presets(user_preset_dir()):
            label = name if builtin else name + " (milik saya)"
            self.cb_preset.addItem(label, path)
        i = self.cb_preset.findData(last)
        if i >= 0:
            self.cb_preset.setCurrentIndex(i)
        self.cb_preset.blockSignals(False)

    def reload_layouts(self, preferred=None):
        current = preferred or self.cb_layout.currentText()
        self.cb_layout.blockSignals(True)
        self.cb_layout.clear()
        for lay in QgsProject.instance().layoutManager().printLayouts():
            self.cb_layout.addItem(lay.name())
        i = self.cb_layout.findText(current)
        if i >= 0:
            self.cb_layout.setCurrentIndex(i)
        self.cb_layout.blockSignals(False)
        self.scan()

    def current_layout(self):
        name = self.cb_layout.currentText()
        if not name:
            return None
        return QgsProject.instance().layoutManager().layoutByName(name)

    def current_preset(self):
        path = self.cb_preset.currentData()
        if not path:
            return None
        try:
            return presets.load(path)
        except presets.PresetError as err:
            QMessageBox.warning(self, "Rimba Layout",
                                "Preset tidak bisa dipakai:\n{}".format(err))
            return None

    def update_info(self):
        lay = self.current_layout()
        pre = self.current_preset()
        parts = []
        if pre:
            parts.append(pre.get("description", ""))
        if lay:
            short = scale.page_short_side_mm(lay)
            f = scale.factor(short, pre.get("base_paper", "A3")
                             if pre else "A3")
            parts.append("Kertas sisi pendek {:.0f} mm, ukuran preset "
                         "dikali {}.".format(short,
                                             "{:.2f}".format(f).replace(
                                                 ".", ",")))
        self.lbl_info.setText(" ".join(p for p in parts if p))

    def _show_empty(self, text):
        self.lbl_empty.setText(text)
        self.lbl_empty.setVisible(bool(text))
        self.btn_apply.setEnabled(not text)

    def scan(self):
        self.table.setRowCount(0)
        self.results = []
        lay = self.current_layout()
        self.update_info()
        if not lay:
            self._show_empty(
                "Proyek ini belum punya Print Layout. Buat layout dulu "
                "(Project \u2192 New Print Layout), lalu klik Pindai ulang.")
            return
        self.results = roles.detect(lay)
        if not self.results:
            self._show_empty(
                "Layout '{}' belum berisi elemen (peta, label, legenda, "
                "skala). Rimba Layout hanya mengganti gaya elemen yang sudah "
                "ada: isi layout dulu, lalu klik Pindai ulang.".format(
                    lay.name()))
            return
        self._show_empty("")
        self.table.setRowCount(len(self.results))
        keys = list(roles.ROLE_LABELS)
        for row, res in enumerate(self.results):
            it = QTableWidgetItem(describe(res.item))
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, COL_ITEM, it)
            ty = QTableWidgetItem(type_name(res.item))
            ty.setFlags(ty.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, COL_TYPE, ty)
            combo = QComboBox()
            for k in keys:
                combo.addItem(roles.ROLE_LABELS[k], k)
            combo.setCurrentIndex(max(0, combo.findData(res.role)))
            combo.setProperty("orig", res.role)
            self.table.setCellWidget(row, COL_ROLE, combo)
            src = QTableWidgetItem(
                "{} – {}".format(res.source, res.reason))
            src.setFlags(src.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if res.source == roles.SRC_GUESS:
                src.setForeground(QColor("#8a6d00"))
            self.table.setItem(row, COL_SRC, src)

    # ------------------------------------------------------------ apply
    def apply(self):
        lay = self.current_layout()
        pre = self.current_preset()
        if not lay or not pre:
            QMessageBox.warning(self, "Rimba Layout",
                                "Pilih layout dan preset dulu.")
            return
        for row, res in enumerate(self.results):
            combo = self.table.cellWidget(row, COL_ROLE)
            chosen = combo.currentData()
            if chosen != combo.property("orig"):
                roles.save_role(res.item, chosen)
            res.role = chosen
        n, warnings = apply.apply_preset(lay, pre, self.results)
        QgsSettings().setValue(SKEY + "preset", self.cb_preset.currentData())
        self.iface.messageBar().pushSuccess(
            "Rimba Layout", "Preset '{}' diterapkan ke {} elemen di '{}'. "
            "Ctrl+Z di Layout Designer untuk membatalkan.".format(
                pre["name"], n, lay.name()))
        if warnings:
            QMessageBox.information(
                self, "Rimba Layout — perlu dicek",
                "Preset sudah diterapkan, tapi ada yang perlu dicek:\n\n- " +
                "\n- ".join(warnings))
        self.scan()
