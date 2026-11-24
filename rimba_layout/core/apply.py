# -*- coding: utf-8 -*-
"""
Terapkan preset ke elemen layout sesuai perannya.

Setiap item dibungkus ``beginCommand``/``endCommand`` di dalam satu macro,
sehingga satu Ctrl+Z di Layout Designer membatalkan seluruh penerapan.
Posisi elemen tidak pernah diubah.
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLegendStyle,
    QgsTextFormat,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

from . import grid_core, scale

GRID_NAME = "Grid Rimba Layout"
TEXT_ROLES_ON_LABEL = (
    "judul", "subjudul", "teks", "catatan", "catatan_proyeksi",
    "sumber_data", "judul_bagian", "skala_teks", "label_tahun",
    "tanda_tangan", "instansi_penerbit", "huruf_utara",
)

_ALIGN = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
    "justify": Qt.AlignmentFlag.AlignJustify,
}


# ------------------------------------------------------------ teks
def _mm_unit():
    try:
        return Qgis.LayoutUnit.Millimeters
    except AttributeError:  # QGIS < 3.30
        from qgis.core import QgsUnitTypes
        return QgsUnitTypes.LayoutUnit.LayoutMillimeters


def _points_unit():
    try:
        return Qgis.RenderUnit.Points
    except AttributeError:  # QGIS < 3.30
        from qgis.core import QgsUnitTypes
        return QgsUnitTypes.RenderUnit.RenderPoints


def _caps(upper):
    try:
        cap = Qgis.Capitalization
    except AttributeError:  # QGIS < 3.24
        from qgis.core import QgsStringUtils
        cap = QgsStringUtils.Capitalization
    return cap.AllUppercase if upper else cap.MixedCase


class Applier:
    """Menyimpan konteks penerapan (faktor kertas, huruf, peringatan)."""

    def __init__(self, layout, preset):
        self.layout = layout
        self.preset = preset
        self.f = scale.factor(scale.page_short_side_mm(layout),
                              preset.get("base_paper", "A3"))
        self.families = set(QFontDatabase().families())
        self.warnings = []
        self.changed = 0
        self._missing_fonts = set()

    # -------------------------------------------------- helpers
    def warn(self, text):
        if text not in self.warnings:
            self.warnings.append(text)

    def family(self, name):
        if not name or name in self.families:
            return name or "Arial"
        if name == "Arial":
            # Arial tidak ada (mis. Linux): Qt memakai pengganti yang
            # ukurannya sama, jadi tidak perlu peringatan.
            return name
        if name not in self._missing_fonts:
            self._missing_fonts.add(name)
            self.warn("Huruf '{}' tidak terpasang, diganti Arial.".format(
                name))
        return "Arial"

    def text_format(self, spec, base=None):
        fmt = QgsTextFormat(base) if base is not None else QgsTextFormat()
        font = QFont(fmt.font())
        if "font" in spec or base is None:
            font.setFamily(self.family(spec.get("font", "Arial")))
        if "bold" in spec:
            font.setBold(spec["bold"])
        if "italic" in spec:
            font.setItalic(spec["italic"])
        fmt.setFont(font)
        if "size" in spec:
            fmt.setSize(scale.font_pt(spec["size"], self.f))
            fmt.setSizeUnit(_points_unit())
        if "color" in spec:
            fmt.setColor(QColor(spec["color"]))
        if "uppercase" in spec:
            fmt.setCapitalization(_caps(spec["uppercase"]))
        return fmt

    def mm(self, value):
        return scale.length_mm(value, self.f)

    # -------------------------------------------------- per peran
    def label(self, item, spec):
        try:
            html = item.mode() == QgsLayoutItemLabel.Mode.ModeHtml
        except AttributeError:
            html = False
        if html:
            self.warn("Label '{}' memakai mode HTML, dilewati.".format(
                item.id() or item.text()[:20]))
            return False
        try:
            item.setTextFormat(self.text_format(spec, item.textFormat()))
        except AttributeError:  # QGIS < 3.24
            fmt = self.text_format(spec)
            font = fmt.font()
            font.setPointSizeF(fmt.size())
            item.setFont(font)
            item.setFontColor(fmt.color())
        if spec.get("align") in _ALIGN:
            item.setHAlign(_ALIGN[spec["align"]])
        if spec.get("frame"):
            item.setVAlign(Qt.AlignmentFlag.AlignVCenter)
            item.setFrameEnabled(True)
            item.setFrameStrokeColor(QColor("#000000"))
            item.setFrameStrokeWidth(QgsLayoutMeasurement(
                self.mm(0.3), _mm_unit()))
            item.setBackgroundEnabled(True)
            item.setBackgroundColor(QColor("#ffffff"))
        self._check_label_fit(item)
        return True

    def _check_label_fit(self, item):
        try:
            need = item.sizeForText()
        except AttributeError:
            return
        rect = item.rect()
        if need.width() > rect.width() + 0.5 or \
                need.height() > rect.height() + 0.5:
            name = item.id() or item.currentText().splitlines()[0][:30]
            self.warn("Teks '{}' tidak muat di kotaknya; perbesar kotak "
                      "label secara manual.".format(name))

    def legend(self, item, spec):
        parts = (("title", QgsLegendStyle.Style.Title),
                 ("group", QgsLegendStyle.Style.Group),
                 ("group", QgsLegendStyle.Style.Subgroup),
                 ("item", QgsLegendStyle.Style.SymbolLabel))
        for key, style in parts:
            if key not in spec:
                continue
            st = item.style(style)
            try:
                st.setTextFormat(self.text_format(spec[key],
                                                  st.textFormat()))
            except AttributeError:  # QGIS < 3.30
                fmt = self.text_format(spec[key])
                font = fmt.font()
                font.setPointSizeF(fmt.size())
                st.setFont(font)
            item.setStyle(style, st)
        item.adjustBoxSize()
        item.refresh()
        return True

    def scalebar(self, item, spec, numeric):
        if not numeric and spec.get("style"):
            item.setStyle(spec["style"])
        if "font" in spec:
            try:
                item.setTextFormat(self.text_format(spec["font"],
                                                    item.textFormat()))
            except AttributeError:
                pass
        if not numeric and "line_width_mm" in spec:
            try:
                sym = item.lineSymbol().clone()
                sym.setWidth(self.mm(spec["line_width_mm"]))
                item.setLineSymbol(sym)
            except AttributeError:  # QGIS < 3.14
                item.setLineWidth(self.mm(spec["line_width_mm"]))
        item.update()
        return True

    def shape(self, item, spec):
        try:
            sym = item.symbol().clone()
        except AttributeError:
            return False
        layer = sym.symbolLayer(0)
        if layer is None:
            return False
        if "color" in spec and hasattr(layer, "setStrokeColor"):
            layer.setStrokeColor(QColor(spec["color"]))
        if "line_width_mm" in spec and hasattr(layer, "setStrokeWidth"):
            layer.setStrokeWidth(self.mm(spec["line_width_mm"]))
        item.setSymbol(sym)
        return True

    def map_item(self, item, spec, grid_spec):
        if spec:
            item.setFrameEnabled(True)
            if "frame_width_mm" in spec:
                item.setFrameStrokeWidth(QgsLayoutMeasurement(
                    self.mm(spec["frame_width_mm"]), _mm_unit()))
            if "frame_color" in spec:
                item.setFrameStrokeColor(QColor(spec["frame_color"]))
        if grid_spec:
            self._grid(item, grid_spec)
        grid_core.refresh_map(item)
        return True

    def _grid(self, item, gs):
        grids = item.grids().asList()
        geo = [g for g in grids
               if grid_core.grid_crs(g, item).isGeographic()]
        projected = [g for g in grids if g not in geo and g.enabled()]
        if projected and not geo:
            self.warn("Peta '{}' memakai grid proyeksi (UTM). Grid UTM "
                      "mT/mU belum didukung, grid itu dibiarkan.".format(
                          item.displayName()))
            return
        if geo:
            grid = geo[0]
            ivx, ivy = grid.intervalX(), grid.intervalY()
        else:
            grid = QgsLayoutItemMapGrid(GRID_NAME, item)
            item.grids().addGrid(grid)
            ext = grid_core.map_extent_wgs84(item)
            target = gs.get("max_lines", 3)
            # interval sama untuk bujur dan lintang, diambil dari sisi
            # terpendek supaya tiap arah punya minimal `target` garis
            # (SK 399/2024: paling sedikit 2 angka lintang dan 2 bujur)
            iv = min(grid_core.auto_interval(ext.width(), target),
                     grid_core.auto_interval(ext.height(), target))
            # batasi jumlah garis di sisi panjang agar label tidak rapat
            cap = gs.get("max_lines_long", 6)
            longest = max(ext.width(), ext.height())
            for nice in grid_core.NICE_INTERVALS:
                if nice >= iv and longest / nice <= cap:
                    iv = nice
                    break
            ivx = ivy = iv
        expr = grid_core.build_label_expression(
            fmt=gs.get("format", "dms"), decimals=gs.get("decimals", 0),
            pad=gs.get("pad", True), dec_sep=gs.get("dec_sep", ","),
            space=True, spaced=gs.get("spaced", False))
        grid_core.configure_grid(grid, {
            "interval_x": ivx, "interval_y": ivy,
            "style": gs.get("style", "lines"),
            "cross_length": self.mm(gs.get("cross_length_mm", 2.0)),
            "line_color": gs.get("line_color", "#000000"),
            "line_width": self.mm(gs.get("line_width_mm", 0.2)),
            "frame": gs.get("frame", "line"),
            "frame_width": self.mm(gs.get("frame_width_mm", 1.5)),
            "font_family": self.family(gs.get("font", "Arial")),
            "font_size": scale.font_pt(gs.get("size", 9), self.f),
            "font_color": gs.get("color", "#000000"),
            "side_vertical": gs.get("side_vertical", True),
            "annot_inside": False,
            "annot_distance": self.mm(gs.get("distance_mm", 1.0)),
            "expression": expr,
        })
        grid.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    # -------------------------------------------------- utama
    def apply_one(self, item, role):
        roles = self.preset.get("roles", {})
        spec = roles.get(role)
        if role in TEXT_ROLES_ON_LABEL and isinstance(item,
                                                      QgsLayoutItemLabel):
            return spec is not None and self.label(item, spec)
        if role == "legenda" and isinstance(item, QgsLayoutItemLegend):
            return spec is not None and self.legend(item, spec)
        if role in ("skala_bar", "skala_angka") and isinstance(
                item, QgsLayoutItemScaleBar):
            return spec is not None and self.scalebar(
                item, spec, role == "skala_angka")
        if role == "kotak" and isinstance(item, QgsLayoutItemShape):
            return spec is not None and self.shape(item, spec)
        if role in ("peta", "peta_situasi") and isinstance(
                item, QgsLayoutItemMap):
            gkey = "grid" if role == "peta" else "grid_situasi"
            return self.map_item(item, spec, self.preset.get(gkey))
        return False


def apply_preset(layout, preset, results):
    """
    Terapkan preset ke daftar RoleResult (dari roles.detect).

    Kembalikan (jumlah elemen diubah, daftar peringatan).
    """
    ap = Applier(layout, preset)
    stack = layout.undoStack()
    stack.beginMacro("Rimba Layout: " + preset.get("name", "preset"))
    try:
        for res in results:
            if res.role == "abaikan":
                continue
            stack.beginCommand(res.item, "Rimba Layout")
            try:
                done = ap.apply_one(res.item, res.role)
            finally:
                stack.endCommand()
            if done:
                ap.changed += 1
    finally:
        stack.endMacro()
    layout.refresh()
    return ap.changed, ap.warnings
