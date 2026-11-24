# -*- coding: utf-8 -*-
"""Peran elemen layout. Peran disimpan di custom property item."""

ROLE_PROP = "rimba_layout/role"

ROLE_LABELS = {
    "judul": "Judul",
    "subjudul": "Subjudul",
    "teks": "Teks biasa",
    "catatan": "Catatan",
    "catatan_proyeksi": "Catatan proyeksi",
    "sumber_data": "Dasar / sumber data",
    "judul_bagian": "Judul bagian",
    "skala_teks": "Teks skala",
    "label_tahun": "Label tahun panel",
    "tanda_tangan": "Tanda tangan",
    "instansi_penerbit": "Instansi penerbit",
    "huruf_utara": "Huruf U",
    "legenda": "Legenda",
    "skala_bar": "Skala bar",
    "skala_angka": "Skala angka",
    "peta": "Panel peta",
    "peta_situasi": "Peta situasi",
    "panah_utara": "Panah utara",
    "logo": "Logo",
    "kotak": "Kotak pembatas",
}


class RoleResult:
    __slots__ = ("item", "role")

    def __init__(self, item, role):
        self.item = item
        self.role = role


def saved_role(item):
    val = item.customProperty(ROLE_PROP, "")
    return str(val) if val else ""


def save_role(item, role):
    item.setCustomProperty(ROLE_PROP, role)
