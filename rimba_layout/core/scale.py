# -*- coding: utf-8 -*-
"""Faktor ukuran menurut kertas.

Preset ditulis untuk A3 (sisi pendek 297 mm)."""

BASE_SHORT_MM = {"A4": 210.0, "A3": 297.0, "A2": 420.0, "A1": 594.0,
                 "A0": 841.0}
MIN_FONT_PT = 6.0


def _mm_unit():
    from qgis.core import Qgis, QgsUnitTypes
    try:
        return Qgis.LayoutUnit.Millimeters
    except AttributeError:  # QGIS < 3.30
        return QgsUnitTypes.LayoutUnit.LayoutMillimeters


def page_short_side_mm(layout):
    """Sisi pendek halaman pertama layout, dalam mm."""
    page = layout.pageCollection().page(0)
    conv = layout.renderContext().measurementConverter()
    size = conv.convert(page.pageSize(), _mm_unit())
    return min(size.width(), size.height())


def factor(short_side_mm, base="A3"):
    """Faktor pengali: sisi pendek kertas dibagi sisi pendek kertas dasar."""
    return float(short_side_mm) / BASE_SHORT_MM.get(base, 297.0)


def font_pt(value, f):
    """Ukuran huruf terskala, dibulatkan ke 0,5 pt, minimal 6 pt."""
    scaled = round(float(value) * f * 2.0) / 2.0
    return max(MIN_FONT_PT, scaled)


def length_mm(value, f):
    """Panjang/tebal garis terskala (mm), dibulatkan ke 0,05 mm."""
    return round(float(value) * f * 20.0) / 20.0
