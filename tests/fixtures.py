# -*- coding: utf-8 -*-
"""Layout tiruan untuk pengujian (pola Peta Hasil PNBP-PKH PLN, A3)."""
from qgis.core import (
    QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
    QgsLayoutItemPage, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsCoordinateReferenceSystem, QgsLayoutItemShape, QgsPrintLayout,
    QgsProject, QgsRectangle, QgsTextFormat,
)
from qgis.PyQt.QtCore import QRectF
from qgis.PyQt.QtGui import QColor, QFont


# ------------------------------------------------------------------ helpers
def new_layout(name, paper="A3"):
    lay = QgsPrintLayout(QgsProject.instance())
    lay.initializeDefaults()
    lay.setName(name)
    page = lay.pageCollection().page(0)
    page.setPageSize(paper, QgsLayoutItemPage.Orientation.Landscape)
    return lay


def add_label(lay, text, x, y, w, h, size, bold=False, ident=""):
    lab = QgsLayoutItemLabel(lay)
    lab.setText(text)
    fmt = QgsTextFormat()
    f = QFont("Arial")
    f.setBold(bold)
    fmt.setFont(f)
    fmt.setSize(size)
    try:
        lab.setTextFormat(fmt)
    except AttributeError:
        f.setPointSizeF(size)
        lab.setFont(f)
    if ident:
        lab.setId(ident)
    lay.addLayoutItem(lab)
    lab.attemptSetSceneRect(QRectF(x, y, w, h))
    return lab


def add_map(lay, x, y, w, h, ident=""):
    m = QgsLayoutItemMap(lay)
    lay.addLayoutItem(m)
    m.attemptSetSceneRect(QRectF(x, y, w, h))
    m.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    m.zoomToExtent(QgsRectangle(122.5, -1.26, 122.66, -1.19))
    if ident:
        m.setId(ident)
    return m


def add_shape(lay, x, y, w, h):
    s = QgsLayoutItemShape(lay)
    s.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
    sym = s.symbol().clone()
    sym.symbolLayer(0).setFillColor(QColor(0, 0, 0, 0))   # tanpa isi
    s.setSymbol(sym)
    lay.addLayoutItem(s)
    s.attemptSetSceneRect(QRectF(x, y, w, h))
    return s


def build_pln(two_panels=True, with_ttd=True, with_year=True, ids=False):
    """Tiruan layout PNBP-PKH PLN: A3 mendatar, panel peta kiri, info kanan."""
    lay = new_layout("PLN {}".format(2 if two_panels else 1))
    add_shape(lay, 5, 5, 410, 287)                      # bingkai luar
    ph = 135 if two_panels else 270
    m1 = add_map(lay, 16, 16, 282, ph - 26, "peta_utama" if ids else "")
    add_shape(lay, 8, 8, 298, ph - 7)
    if with_year:
        add_label(lay, "TAHUN 2024 - 2025", 246, ph - 22, 48, 8, 11, True,
                  "tahun1" if ids else "")
    if two_panels:
        add_map(lay, 16, 156, 282, 110)
        add_shape(lay, 8, 148, 298, 128)
        if with_year:
            add_label(lay, "TAHUN 2025 - 2026", 246, 255, 48, 8, 11, True)
    # panel kanan
    add_shape(lay, 310, 8, 103, 95)
    logo = QgsLayoutItemPicture(lay)
    logo.setPicturePath("/tmp/logo_kemenhut.png")
    lay.addLayoutItem(logo)
    logo.attemptSetSceneRect(QRectF(352, 10, 18, 14))
    add_label(lay, "PETA HASIL\nVERIFIKASI PENERIMAAN NEGARA BUKAN PAJAK",
              315, 26, 93, 14, 10, True, "judul" if ids else "")
    add_label(lay, "SK.913/MENLHK/SETJEN/PLA.0/10/2019", 315, 41, 93, 4, 8)
    add_label(lay, "DI KABUPATEN BANGGAI PROVINSI SULAWESI TENGAH",
              315, 46, 93, 8, 9, True)
    add_label(lay, "U", 357, 56, 6, 5, 12, True)
    arrow = QgsLayoutItemPicture(lay)
    lay.addLayoutItem(arrow)
    arrow.setPicturePath(
        ":/images/north_arrows/layout_default_north_arrow.svg")
    arrow.setLinkedMap(m1)
    arrow.attemptSetSceneRect(QRectF(356, 61, 8, 12))
    add_label(lay, "SKALA 1:25.000", 340, 74, 40, 5, 9, True)
    sb = QgsLayoutItemScaleBar(lay)
    sb.setStyle("Single Box")
    sb.setLinkedMap(m1)
    sb.applyDefaultSettings()
    sb.setStyle("Single Box")
    lay.addLayoutItem(sb)
    sb.attemptSetSceneRect(QRectF(320, 80, 80, 8))
    add_label(lay, "Proyeksi : Transverse Mercator\nSistem Grid : Grid "
              "Geografi\nSpheroid : WGS 1984", 330, 90, 60, 12, 8)
    add_shape(lay, 310, 105, 103, 65)
    add_label(lay, "KETERANGAN PETA :", 313, 107, 50, 5, 9, True)
    leg = QgsLayoutItemLegend(lay)
    lay.addLayoutItem(leg)
    leg.attemptSetSceneRect(QRectF(313, 113, 95, 35))
    add_label(lay, "Fungsi Kawasan Hutan", 313, 150, 50, 5, 9, True)
    add_shape(lay, 310, 172, 103, 45)
    add_label(lay, "DASAR :", 313, 174, 30, 4, 9, True)
    add_label(lay, "1. Peraturan Menteri Kehutanan Nomor 14 Tahun 2025\n"
              "2. Keputusan Menteri LHK Nomor 399 Tahun 2024",
              313, 178, 95, 10, 7)
    add_label(lay, "SUMBER PETA :", 313, 190, 40, 4, 9, True)
    add_label(lay, "1. Peta RBI Skala 1:25.000 Tahun 2021\n2. Citra "
              "Sentinel-2 L2A", 313, 194, 95, 10, 7)
    add_label(lay, "CATATAN :", 313, 206, 30, 4, 9, True)
    add_label(lay, "Batas administrasi pemerintahan tidak sepenuhnya dapat "
              "digunakan sebagai acuan.", 313, 210, 95, 6, 7)
    add_shape(lay, 310, 219, 103, 35)
    add_map(lay, 314, 222, 95, 30, "")                   # peta situasi
    add_label(lay, "PETA SITUASI", 385, 223, 22, 4, 7, True)
    if with_ttd:
        add_shape(lay, 310, 256, 103, 20)
        add_label(lay, "TIM PELAKSANA\nKETUA", 340, 257, 40, 6, 6, True)
        add_label(lay, "DEWI PERMATASARI ANANDA, S.Hut\nNIP. 19921004 "
                  "202321 2 027", 330, 266, 55, 6, 6)
    add_label(lay, "KEMENTERIAN KEHUTANAN\nDIREKTORAT JENDERAL PLANOLOGI "
              "KEHUTANAN\nBALAI PEMANTAPAN KAWASAN HUTAN WILAYAH XVI\n2026",
              315, 278, 93, 12, 8, True)
    return lay
