# -*- coding: utf-8 -*-
"""
Bangun Print Layout utuh dari preset.

Tata letak mengikuti pola peta kerja Kemenhut (Peta Hasil PNBP-PKH):
panel peta di kiri (satu atau dua), panel informasi tepi di kanan.
Semua ukuran ditulis untuk A3 mendatar lalu dikalikan menurut kertas.
"""

import os

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapOverview,
    QgsLayoutItemPage,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutUtils,
    QgsPrintLayout,
    QgsRectangle,
    QgsBasicNumericFormat,
    QgsLineSymbol,
    QgsScaleBarSettings,
    QgsTextRenderer,
)
from qgis.PyQt.QtCore import QRectF, Qt
from qgis.PyQt.QtGui import QColor

from . import apply
from .roles import RoleResult, save_role

A3_W, A3_H = 420.0, 297.0
PAPERS = ("A4", "A3", "A2", "A1", "A0")
NORTH_ARROW = ":/images/north_arrows/layout_default_north_arrow.svg"
NICE_SCALE_STEPS = (1, 2, 2.5, 5)

DEFAULT_CATATAN = ("Batas administrasi pemerintahan yang tergambar di atas "
                   "peta tidak sepenuhnya dapat digunakan sebagai acuan.")


class BuildOptions:
    """Isian dialog. Semua teks boleh kosong."""

    def __init__(self, **kw):
        self.name = kw.get("name", "Peta Rimba Layout")
        self.paper = kw.get("paper", "A3")
        self.panels = kw.get("panels", 1)
        self.themes = kw.get("themes", [None, None])     # nama tema peta
        self.years = kw.get("years", ["", ""])           # label tahun panel
        self.judul = kw.get("judul", "JUDUL PETA")
        self.sk = kw.get("sk", "")
        self.lokasi = kw.get("lokasi", "")
        self.dasar = kw.get("dasar", "")
        self.sumber = kw.get("sumber", "")
        self.catatan = kw.get("catatan", DEFAULT_CATATAN)
        self.ttd = kw.get("ttd", "")                     # kosong = tanpa TTD
        self.logo = kw.get("logo", "")
        self.instansi = kw.get("instansi", "")
        self.layers = kw.get("layers", [])
        self.extent = kw.get("extent", None)             # QgsRectangle
        self.crs = kw.get("crs", None)


# ------------------------------------------------------------- utilitas
def nice_scale(scale):
    """Skala bulat berikutnya: 1, 2, 2,5, 5 x 10^n (>= skala sekarang)."""
    if scale <= 0:
        return scale
    mag = 1.0
    while mag * 10 <= scale:
        mag *= 10
    for step in NICE_SCALE_STEPS + (10,):
        if step * mag >= scale - 1e-6:
            return step * mag
    return 10 * mag


def unique_name(manager, base):
    name, i = base, 2
    while manager.layoutByName(name) is not None:
        name = "{} ({})".format(base, i)
        i += 1
    return name


def proyeksi_parts(crs):
    """Dua kolom catatan proyeksi: nama dan nilai (tanda ':' sejajar)."""
    keys = "Sistem Proyeksi\nSistem Grid\nDatum"
    if crs is None or not crs.isValid():
        return keys, ": -\n: Grid Geografi\n: -"
    desc = crs.description()
    if crs.isGeographic():
        proj = "Geografis"
    elif "UTM" in desc.upper() or "Transverse Mercator" in desc:
        proj = "Transverse Mercator"
    else:
        proj = desc
    wgs = ("WGS 84" in desc or "WGS84" in desc.replace(" ", "")
           or crs.authid() in ("EPSG:4326", "EPSG:4979")
           or crs.authid().startswith(("EPSG:326", "EPSG:327")))
    datum = "WGS 1984" if wgs else (crs.ellipsoidAcronym() or "-")
    return keys, ": {}\n: Grid Geografi\n: {}".format(proj, datum)


def text_width(layout, label, line):
    ctx = QgsLayoutUtils.createRenderContextForLayout(layout, None)
    sf = ctx.scaleFactor() or 1.0
    return QgsTextRenderer.textWidth(ctx, label.textFormat(), [line]) / sf


def comma_format():
    nf = QgsBasicNumericFormat()
    nf.setShowThousandsSeparator(False)
    try:
        nf.setDecimalSeparator(",")
    except (AttributeError, TypeError):
        pass
    return nf


def wrapped_height(layout, label):
    """Tinggi label (mm) bila teksnya dibungkus mengikuti lebar kotak."""
    ctx = QgsLayoutUtils.createRenderContextForLayout(layout, None)
    sf = ctx.scaleFactor() or 1.0
    fmt = label.textFormat()
    width = label.rect().width() - 2 * label.marginX()
    lines = label.currentText().split("\n") or [""]
    total = 0
    for line in lines:
        count, cur = 1, ""
        for word in line.split():
            test = (cur + " " + word).strip()
            if cur and QgsTextRenderer.textWidth(ctx, fmt, [test]) / sf > \
                    width:
                count += 1
                cur = word
            else:
                cur = test
        total += count
    per_line = label.sizeForText().height() / max(1, len(lines))
    return per_line * total


def _point(x, y):
    from qgis.core import QgsLayoutPoint
    return QgsLayoutPoint(x, y)


def _m_unit():
    try:
        return Qgis.DistanceUnit.Meters
    except AttributeError:  # QGIS < 3.30
        from qgis.core import QgsUnitTypes
        return QgsUnitTypes.DistanceUnit.DistanceMeters


def _km_unit():
    try:
        return Qgis.DistanceUnit.Kilometers
    except AttributeError:  # QGIS < 3.30
        from qgis.core import QgsUnitTypes
        return QgsUnitTypes.DistanceUnit.DistanceKilometers


class _Builder:

    def __init__(self, project, preset, opts):
        self.project = project
        self.preset = preset
        self.o = opts
        self.layout = QgsPrintLayout(project)
        self.layout.initializeDefaults()
        page = self.layout.pageCollection().page(0)
        page.setPageSize(opts.paper if opts.paper in PAPERS else "A3",
                         QgsLayoutItemPage.Orientation.Landscape)
        size = page.pageSize()
        self.k = size.width() / A3_W          # skala posisi dari A3
        self.roles = []
        self.stack = []          # item kepala, disusun ulang setelah gaya
        self.warnings = []

    # --------------------------------------------------------- item dasar
    def r(self, x, y, w, h):
        k = self.k
        return QRectF(x * k, y * k, w * k, h * k)

    def add(self, item, rect, role, ident=""):
        self.layout.addLayoutItem(item)
        item.attemptSetSceneRect(rect)
        if ident:
            item.setId(ident)
        save_role(item, role)
        self.roles.append(RoleResult(item, role))
        return item

    def box(self, x, y, w, h):
        s = QgsLayoutItemShape(self.layout)
        s.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
        s.setSymbol(QgsFillSymbol.createSimple({
            "color": "0,0,0,0", "outline_color": "0,0,0,255",
            "outline_width": "0.3"}))
        return self.add(s, self.r(x, y, w, h), "kotak")

    def label(self, text, x, y, w, h, role, ident="", align="left",
              valign="top"):
        lab = QgsLayoutItemLabel(self.layout)
        lab.setText(text)
        lab.setHAlign({"left": Qt.AlignmentFlag.AlignLeft,
                       "center": Qt.AlignmentFlag.AlignHCenter,
                       "right": Qt.AlignmentFlag.AlignRight}[align])
        lab.setVAlign({"top": Qt.AlignmentFlag.AlignTop,
                       "center": Qt.AlignmentFlag.AlignVCenter}[valign])
        lab.setMarginX(0)
        lab.setMarginY(0)
        return self.add(lab, self.r(x, y, w, h), role, ident)

    # --------------------------------------------------------- peta
    def panel_map(self, x, y, w, h, ident, theme):
        m = QgsLayoutItemMap(self.layout)
        self.add(m, self.r(x, y, w, h), "peta", ident)
        if self.o.crs is not None and self.o.crs.isValid():
            m.setCrs(self.o.crs)
        if theme:
            m.setFollowVisibilityPreset(True)
            m.setFollowVisibilityPresetName(theme)
        elif self.o.layers:
            m.setLayers(self.o.layers)
            m.setKeepLayerSet(True)
        if self.o.extent is not None and not self.o.extent.isEmpty():
            m.zoomToExtent(self.o.extent)
            m.setScale(nice_scale(m.scale()))
        return m

    def situasi_map(self, x, y, w, h, main):
        m = QgsLayoutItemMap(self.layout)
        self.add(m, self.r(x, y, w, h), "peta_situasi", "Peta Situasi")
        if self.o.crs is not None and self.o.crs.isValid():
            m.setCrs(self.o.crs)
        if self.o.layers:
            m.setLayers(self.o.layers)
            m.setKeepLayerSet(True)
        ext = main.extent()
        if not ext.isEmpty():
            big = QgsRectangle(ext)
            big.scale(8.0)
            m.zoomToExtent(big)
        ov = QgsLayoutItemMapOverview("Lokasi", m)
        m.overviews().addOverview(ov)
        ov.setLinkedMap(main)
        ov.setFrameSymbol(QgsFillSymbol.createSimple({
            "color": "255,0,0,0", "outline_color": "230,0,0,255",
            "outline_width": "0.5"}))
        return m

    # --------------------------------------------------------- susun
    def build(self):
        o = self.o
        self.box(5, 5, 410, 287)                              # garis tepi luar

        # ---- panel peta
        maps = []
        if o.panels == 2:
            frames = [(10, 10, 316, 136), (10, 151, 316, 136)]
        else:
            frames = [(10, 10, 316, 277)]
        for i, (x, y, w, h) in enumerate(frames):
            self.box(x, y, w, h)
            mx, my, mw, mh = x + 9, y + 8, w - 18, h - 16
            theme = o.themes[i] if i < len(o.themes) else None
            m = self.panel_map(mx, my, mw, mh, "Map {}".format(i + 1),
                               theme)
            maps.append(m)
            year = o.years[i] if i < len(o.years) else ""
            if year:
                self.label(year, mx + mw - 47, my + mh - 11, 45, 9,
                           "label_tahun", "tahun_{}".format(i + 1),
                           align="center", valign="center")
        main = maps[0]

        # ---- panel informasi tepi (x 330..410)
        x0, w0 = 330, 80
        ttd = bool(o.ttd.strip())
        heights = ([106, 50, 38, 28, 30, 15] if ttd
                   else [108, 65, 45, 36, 0, 15])
        ys, y = [], 10.0
        for hgt in heights:
            ys.append(y)
            y += hgt + (2 if hgt else 0)
        head_y, ket_y, das_y, sit_y, ttd_y, ins_y = ys
        h_head, h_ket, h_das, h_sit, h_ttd, h_ins = heights

        # judul dan kepala
        self.head_shape = self.box(x0, head_y, w0, h_head)
        cx = x0 + 3
        cw = w0 - 6
        if o.logo and os.path.exists(o.logo):
            pic = QgsLayoutItemPicture(self.layout)
            pic.setPicturePath(o.logo)
            pic.setResizeMode(QgsLayoutItemPicture.ResizeMode.Zoom)
            self.add(pic, self.r(x0 + w0 / 2 - 6.25, head_y + 3, 12.5,
                                 12.7), "logo", "logo")
            self.stack.append(["item", pic, 3.5])
        self.stack.append(["item", self.label(
            o.judul, cx, head_y + 20, cw, 18, "judul", "judul",
            align="center"), 1.0])
        if o.sk.strip():
            self.stack.append(["item", self.label(
                o.sk, cx, head_y + 38, cw, 5, "teks", "sk",
                align="center"), 1.0])
        if o.lokasi.strip():
            self.stack.append(["item", self.label(
                o.lokasi, cx, head_y + 43, cw, 9, "subjudul", "lokasi",
                align="center"), 1.0])
        self.stack[-1][2] = 2.5           # jarak teks terakhir ke huruf U
        self.stack.append(["item", self.label(
            "U", x0 + w0 / 2 - 5, head_y + 54, 10, 5, "huruf_utara",
            "huruf_u", align="center"), 1.5])
        arrow = QgsLayoutItemPicture(self.layout)
        arrow.setPicturePath(NORTH_ARROW)
        self.add(arrow, self.r(x0 + w0 / 2 - 3.95, head_y + 59, 7.9, 10.6),
                 "panah_utara", "panah_utara")
        arrow.setLinkedMap(main)
        self.stack.append(["item", arrow, 4.0])
        self.stack.append(["item", self.label(
            "SKALA 1:[% replace(format_number(map_get("
            "item_variables('Map 1'), 'map_scale'), 0), ',', '.') %]",
            cx, head_y + 73, cw, 4, "skala_teks", "skala_teks",
            align="center"), 3.5])
        self.scale_bot = self._scalebar_km(main, x0, head_y + 79)
        self.stack.append(["scale", None, 2.3])
        keys, vals = proyeksi_parts(main.crs())
        k_lab = self.label(keys, cx, head_y + 92, 30, 12,
                           "catatan_proyeksi", "proyeksi_nama")
        v_lab = self.label(vals, cx + 31, head_y + 92, cw - 31, 12,
                           "catatan_proyeksi", "proyeksi_nilai")
        self.stack.append(["pair", (k_lab, v_lab), 0])
        self.head_box = (head_y, h_head)

        # keterangan + legenda
        self.ket_shape = self.box(x0, ket_y, w0, h_ket)
        self.ket_items = [self.label("KETERANGAN PETA :", cx, ket_y + 2, cw,
                                     4, "judul_bagian", "judul_keterangan")]
        leg = QgsLayoutItemLegend(self.layout)
        leg.setTitle("")
        leg.setLinkedMap(main)
        leg.setAutoUpdateModel(True)
        leg.setLegendFilterByMapEnabled(True)
        leg.setResizeToContents(True)
        self.add(leg, self.r(cx, ket_y + 7, cw, h_ket - 9), "legenda",
                 "legenda")
        self.ket_items.append(leg)

        # dasar, sumber, catatan
        self.box(x0, das_y, w0, h_das)
        part = h_das / 3.0
        for i, (head, body, role) in enumerate((
                ("DASAR :", o.dasar, "sumber_data"),
                ("SUMBER PETA :", o.sumber, "sumber_data"),
                ("CATATAN :", o.catatan, "catatan"))):
            yy = das_y + 2 + i * part
            ident = ("dasar", "sumber", "catatan")[i]
            self.label(head, cx, yy, cw, 4, "judul_bagian",
                       "judul_" + ident)
            self.label(body, cx, yy + 4, cw, part - 5, role, ident)

        # peta situasi
        self.box(x0, sit_y, w0, h_sit)
        sx, sy, sw, sh = x0 + 7, sit_y + 5, w0 - 14, h_sit - 10
        self.situasi_map(sx, sy, sw, sh, main)
        self.sit_head = self.label("PETA SITUASI", sx + sw - 24, sy + 1, 23,
                                   4, "judul_bagian", "judul_situasi",
                                   align="center", valign="center")

        # tanda tangan (opsional)
        if ttd:
            self.box(x0, ttd_y, w0, h_ttd)
            self.label(o.ttd, cx, ttd_y + 2, cw, h_ttd - 4, "tanda_tangan",
                       "ttd", align="center")

        # instansi penerbit
        self.box(x0, ins_y, w0, h_ins)
        self.label(o.instansi, cx, ins_y + 1.5, cw, h_ins - 3,
                   "instansi_penerbit", "instansi", align="center",
                   valign="center")

        # gaya dari preset (grid, huruf, bingkai)
        _, warns = apply.apply_preset(self.layout, self.preset, self.roles,
                                      undo=False)
        self.warnings.extend(w for w in warns
                             if "tidak muat" not in w)
        self._stack_header()
        self._finish_situasi_head()
        return self.layout

    # --------------------------------------------------------- skala bar
    def _segments(self, scale):
        """Panjang segmen (cm kertas) dan jumlah segmen skala bar."""
        target_cm = 5.0 * self.k
        cm_seg = 1.0 if target_cm <= 6.0 else 2.0
        nseg = max(2, int(round(target_cm / cm_seg)))
        return cm_seg, nseg

    def _scalebar_km(self, main, x0, y):
        """Skala bar bawah: batang + label Km di bawah batang."""
        scale = main.scale() or 25000.0
        cm_seg, nseg = self._segments(scale)
        sb = QgsLayoutItemScaleBar(self.layout)
        sb.setLinkedMap(main)
        sb.applyDefaultSettings()
        sb.setStyle("Double Box")
        sb.setUnits(_km_unit())
        sb.setUnitLabel("Km")
        sb.setNumberOfSegmentsLeft(0)
        sb.setNumberOfSegments(nseg)
        sb.setSegmentSizeMode(
            QgsScaleBarSettings.SegmentSizeMode.SegmentSizeFixed)
        sb.setUnitsPerSegment(cm_seg * scale / 100000.0)
        sb.setLabelVerticalPlacement(
            QgsScaleBarSettings.LabelVerticalPlacement.LabelBelowSegment)
        sb.setHeight(2.0 * self.k)
        sb.setLabelBarSpace(1.0 * self.k)
        sb.setNumericFormat(comma_format())
        self.add(sb, self.r(x0 + 8, y, 64, 10), "skala_bar", "skala_bar")
        self._scale_info = (scale, cm_seg, nseg)
        return sb

    def _scalebar_cm(self, bot):
        """Skala bar atas: hanya label cm kertas, batangnya transparan."""
        scale, cm_seg, nseg = self._scale_info
        top = QgsLayoutItemScaleBar(self.layout)
        top.setLinkedMap(bot.linkedMap())
        top.applyDefaultSettings()
        top.setStyle(bot.style())
        top.setUnits(_m_unit())
        top.setMapUnitsPerScaleBarUnit(scale / 100.0)   # m per cm kertas
        top.setUnitLabel("Cm")
        top.setNumberOfSegmentsLeft(0)
        top.setNumberOfSegments(nseg)
        top.setSegmentSizeMode(
            QgsScaleBarSettings.SegmentSizeMode.SegmentSizeFixed)
        top.setUnitsPerSegment(cm_seg * scale / 100.0)
        top.setLabelVerticalPlacement(
            QgsScaleBarSettings.LabelVerticalPlacement.LabelAboveSegment)
        top.setHeight(bot.height())
        top.setLabelBarSpace(bot.labelBarSpace())
        top.setBoxContentSpace(bot.boxContentSpace())
        top.setTextFormat(bot.textFormat())
        top.setNumericFormat(comma_format())
        clear = {"color": "0,0,0,0", "outline_style": "no"}
        top.setFillSymbol(QgsFillSymbol.createSimple(clear))
        top.setAlternateFillSymbol(QgsFillSymbol.createSimple(clear))
        top.setLineSymbol(QgsLineSymbol.createSimple({"line_style": "no"}))
        self.layout.addLayoutItem(top)
        top.setId("skala_bar_cm")
        top.refreshItemSize()
        return top

    # --------------------------------------------------------- susun kepala
    def _stack_header(self):
        """Susun kepala dari atas ke bawah sesuai tinggi isi sebenarnya."""
        head_y, h_head = self.head_box
        k = self.k
        box_x, box_w = 330 * k, 80 * k
        y = (head_y + 3) * k
        bottom = (head_y + h_head - 2) * k
        for kind, item, gap in self.stack:
            if kind == "item":
                rect = item.rect()
                x = self.layout.convertToLayoutUnits(
                    item.positionWithUnits()).x()
                if isinstance(item, QgsLayoutItemLabel):
                    h = max(wrapped_height(self.layout, item), 2 * k)
                else:
                    h = rect.height()
                item.attemptSetSceneRect(QRectF(x, y, rect.width(), h))
            elif kind == "scale":
                h = self._place_scale_pair(box_x, box_w, y)
            else:                                  # pasangan proyeksi
                h = self._place_proyeksi(item, box_x, box_w, y)
            y += h + gap * k
        if y > bottom + 0.5:
            self.warnings.append(
                "Isi kepala (judul, lokasi, skala) lebih panjang dari "
                "kotaknya; perpendek judul atau perbesar kotak secara manual.")
        else:
            self._give_space_to_legend(bottom + 2 * k - (y + 2 * k))

    def _give_space_to_legend(self, spare):
        """Kotak kepala dipas ke isinya; sisa ruang diberikan ke keterangan."""
        if spare <= 0.5:
            return
        hr = self.head_shape.rect()
        hp = self.head_shape.pos()
        self.head_shape.attemptSetSceneRect(
            QRectF(hp.x(), hp.y(), hr.width(), hr.height() - spare))
        kr = self.ket_shape.rect()
        kp = self.ket_shape.pos()
        self.ket_shape.attemptSetSceneRect(
            QRectF(kp.x(), kp.y() - spare, kr.width(), kr.height() + spare))
        for item in self.ket_items:
            p = item.pos()
            item.attemptMove(_point(p.x(), p.y() - spare))

    def _place_scale_pair(self, box_x, box_w, y):
        bot = self.scale_bot
        bot.refreshItemSize()
        top = self._scalebar_cm(bot)
        x = box_x + (box_w - bot.rect().width()) / 2.0
        # Tinggi item skala bar QGIS tidak rapat, jadi posisi batang dihitung
        # dari jarak isi, tinggi huruf angka (+-0,835 em), dan jarak label.
        bcs, lbs, bar = bot.boxContentSpace(), bot.labelBarSpace(), \
            bot.height()
        label_h = 0.835 * bot.textFormat().size() * 0.3528
        top.attemptMove(_point(x, y))
        bar_top = y + bcs + label_h + lbs
        bot.attemptMove(_point(x, bar_top - bcs))
        return (bar_top + bar + lbs + label_h) - y

    def _place_proyeksi(self, pair, box_x, box_w, y):
        k_lab, v_lab = pair
        kw = max(text_width(self.layout, k_lab, ln)
                 for ln in k_lab.text().split("\n")) + 0.3
        vw = max(text_width(self.layout, v_lab, ln)
                 for ln in v_lab.text().split("\n")) + 0.3
        gap = 1.0 * self.k
        x = box_x + max(2 * self.k, (box_w - kw - gap - vw) / 2.0)
        h = wrapped_height(self.layout, k_lab)
        k_lab.attemptSetSceneRect(QRectF(x, y, kw, h))
        v_lab.attemptSetSceneRect(QRectF(x + kw + gap, y, vw, h))
        return h

    def _finish_situasi_head(self):
        lab = self.sit_head
        lab.setBackgroundEnabled(True)
        lab.setBackgroundColor(QColor("#ffffff"))
        lab.setFrameEnabled(True)
        lab.setFrameStrokeColor(QColor("#000000"))


def build_layout(project, preset, opts):
    """Buat layout, daftarkan ke proyek, kembalikan QgsPrintLayout."""
    b = _Builder(project, preset, opts)
    lay = b.build()
    mgr = project.layoutManager()
    lay.setName(unique_name(mgr, opts.name or "Peta Rimba Layout"))
    mgr.addLayout(lay)
    return lay, b.warnings
