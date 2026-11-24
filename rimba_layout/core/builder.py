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


def proyeksi_text(crs):
    if crs is None or not crs.isValid():
        return "Sistem Proyeksi : -\nSistem Grid : Grid Geografi"
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
    return ("Sistem Proyeksi : {}\nSistem Grid : Grid Geografi\n"
            "Datum : {}".format(proj, datum))


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
        self.box(x0, head_y, w0, h_head)
        cx = x0 + 3
        cw = w0 - 6
        if o.logo and os.path.exists(o.logo):
            pic = QgsLayoutItemPicture(self.layout)
            pic.setPicturePath(o.logo)
            pic.setResizeMode(QgsLayoutItemPicture.ResizeMode.Zoom)
            self.add(pic, self.r(x0 + w0 / 2 - 8, head_y + 3, 16, 15),
                     "logo", "logo")
            self.stack.append((pic, 2.0))
        self.stack.append((self.label(o.judul, cx, head_y + 20, cw, 18,
                                      "judul", "judul", align="center"),
                           1.0))
        if o.sk.strip():
            self.stack.append((self.label(o.sk, cx, head_y + 38, cw, 5,
                                          "teks", "sk", align="center"),
                               1.0))
        if o.lokasi.strip():
            self.stack.append((self.label(o.lokasi, cx, head_y + 43, cw, 9,
                                          "subjudul", "lokasi",
                                          align="center"), 3.0))
        self.stack.append((self.label("U", x0 + w0 / 2 - 5, head_y + 54, 10,
                                      5, "huruf_utara", "huruf_u",
                                      align="center"), 0.5))
        arrow = QgsLayoutItemPicture(self.layout)
        arrow.setPicturePath(NORTH_ARROW)
        self.add(arrow, self.r(x0 + w0 / 2 - 4, head_y + 59, 8, 12),
                 "panah_utara", "panah_utara")
        arrow.setLinkedMap(main)
        self.stack.append((arrow, 2.0))
        self.stack.append((self.label(
            "SKALA 1:[% replace(format_number(map_get("
            "item_variables('Map 1'), 'map_scale'), 0), ',', '.') %]",
            cx, head_y + 73, cw, 4, "skala_teks", "skala_teks",
            align="center"), 1.0))
        sb = QgsLayoutItemScaleBar(self.layout)
        sb.setLinkedMap(main)
        sb.applyDefaultSettings()
        sb.setStyle("Single Box")
        sb.setUnits(_km_unit())
        sb.setUnitLabel("Km")
        sb.setNumberOfSegmentsLeft(0)
        sb.setNumberOfSegments(4)
        sb.setSegmentSizeMode(
            QgsScaleBarSettings.SegmentSizeMode.SegmentSizeFitWidth)
        sb.setMinimumBarWidth(45 * self.k)
        sb.setMaximumBarWidth(60 * self.k)
        self.add(sb, self.r(x0 + 8, head_y + 79, 64, 10), "skala_bar",
                 "skala_bar")
        self.stack.append((sb, 2.0))
        self.stack.append((self.label(proyeksi_text(main.crs()), cx + 6,
                                      head_y + 92, cw - 6, 12,
                                      "catatan_proyeksi", "proyeksi"), 0))
        self.head_box = (head_y, h_head)

        # keterangan + legenda
        self.box(x0, ket_y, w0, h_ket)
        self.label("KETERANGAN PETA :", cx, ket_y + 2, cw, 4,
                   "judul_bagian", "judul_keterangan")
        leg = QgsLayoutItemLegend(self.layout)
        leg.setTitle("")
        leg.setLinkedMap(main)
        leg.setAutoUpdateModel(True)
        leg.setLegendFilterByMapEnabled(True)
        leg.setResizeToContents(True)
        self.add(leg, self.r(cx, ket_y + 7, cw, h_ket - 9), "legenda",
                 "legenda")

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

    def _stack_header(self):
        """Susun kepala dari atas ke bawah sesuai tinggi teks sebenarnya."""
        head_y, h_head = self.head_box
        k = self.k
        y = (head_y + 3) * k
        bottom = (head_y + h_head - 2) * k
        for item, gap in self.stack:
            rect = item.rect()
            pos = item.positionWithUnits()
            x = self.layout.convertToLayoutUnits(pos).x()
            w = rect.width()
            if isinstance(item, QgsLayoutItemLabel):
                h = max(wrapped_height(self.layout, item), 2 * k)
            else:
                h = rect.height()
            item.attemptSetSceneRect(QRectF(x, y, w, h))
            y += h + gap * k
        if y > bottom + 0.5:
            self.warnings.append(
                "Isi kepala (judul, lokasi, skala) lebih panjang dari "
                "kotaknya; perpendek judul atau perbesar kotak secara manual.")

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
