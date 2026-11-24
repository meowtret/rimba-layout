# -*- coding: utf-8 -*-
"""Uji headless tahap 1-2 Rimba Layout.

Jalankan:  QT_QPA_PLATFORM=offscreen python3 tests/test_core.py
"""
import os
import sys

import tempfile  # noqa: E402

# Di Linux tanpa layar pakai "offscreen". Di Windows biarkan bawaan, supaya
# Qt memakai huruf sistem (offscreen di Windows tidak menemukan folder font).
if not sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from qgis.core import QgsApplication, QgsLayoutItemLabel  # noqa: E402

APP = QgsApplication([], False)
APP.initQgis()

from rimba_layout.core import presets, roles, scale  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  GAGAL ") + msg)
    if not cond:
        FAILS.append(msg)


from fixtures import build_pln, new_layout  # noqa: E402


def roles_by_text(results):
    out = {}
    for r in results:
        if isinstance(r.item, QgsLayoutItemLabel):
            key = r.item.text().splitlines()[0][:28]
        else:
            key = "{}#{}".format(type(r.item).__name__.replace(
                "QgsLayoutItem", ""), id(r.item) % 1000)
        out[key] = r.role
    return out


# ------------------------------------------------------------------ tests
print("== Tahap 1: skala kertas")
for paper, expect in (("A4", 210), ("A3", 297), ("A1", 594), ("A0", 841)):
    lay = new_layout("uji " + paper, paper)
    short = scale.page_short_side_mm(lay)
    check(abs(short - expect) < 0.5,
          "{}: sisi pendek {:.0f} mm".format(paper, short))
f_a4 = scale.factor(210)
check(scale.font_pt(18, f_a4) == 12.5, "judul 18 pt di A4 -> 12,5 pt")
check(scale.font_pt(8, f_a4) == 5.5, "catatan 8 pt di A4 -> 5,5 pt")
check(scale.font_pt(3.5, f_a4) == 3.5, "3,5 pt di A4 tetap 3,5 (batas bawah)")
check(scale.font_pt(18, scale.factor(841)) == 51.0,
      "judul 18 pt di A0 -> 51")
check(scale.font_pt(8, scale.factor(420)) == 11.5,
      "catatan 8 pt di A2 -> 11,5")

print("== Tahap 1: preset")
listed = presets.list_presets()
names = sorted(n for n, _, _ in listed)
check(names == ["Kemenhut SK 399/2024", "Klasik", "Minimalis"],
      "tiga preset bawaan terbaca: " + ", ".join(names))
kem = [presets.load(p) for n, p, _ in listed if n.startswith("Kemenhut")][0]
check(kem["roles"]["judul"]["bold"] and kem["roles"]["judul"]["uppercase"],
      "Kemenhut: judul bold kapital")
check(kem["grid"]["line_color"].upper() == "#BEE8FF",
      "Kemenhut: garis grid biru R190 G232 B255")
check(kem["grid"]["spaced"] and not kem["grid"]["pad"],
      "Kemenhut: label grid 122° 33' 0\" BT")
bad_cases = [
    ({"name": "x", "version": 1, "base_paper": "A5", "roles": {}},
     "kertas A5"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judulx": {}}}, "peran tidak dikenal"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judul": {"size": "besar"}}}, "ukuran bukan angka"),
    ({"name": "x", "version": 1, "base_paper": "A3",
      "roles": {"judul": {"color": "merah"}}}, "warna bukan #RRGGBB"),
]
for data, why in bad_cases:
    try:
        presets.validate(data)
        check(False, "preset rusak ditolak: " + why)
    except presets.PresetError as err:
        check(True, "preset rusak ditolak: {} ({})".format(why, err))
tmp = os.path.join(tempfile.gettempdir(), "rimba_layout_uji.json")
presets.save(kem, tmp)
check(presets.load(tmp) == kem, "simpan lalu muat ulang preset identik")

print("== Tahap 2: pengenalan peran, layout PLN dua panel")
EXPECT = {
    "TAHUN 2024 - 2025": "label_tahun",
    "TAHUN 2025 - 2026": "label_tahun",
    "PETA HASIL": "judul",
    "SK.913/MENLHK/SETJEN/PLA.0/1": "teks",
    "DI KABUPATEN BANGGAI PROVINS": "subjudul",
    "U": "huruf_utara",
    "SKALA 1:25.000": "skala_teks",
    "Proyeksi : Transverse Mercat": "catatan_proyeksi",
    "KETERANGAN PETA :": "judul_bagian",
    "Fungsi Kawasan Hutan": "judul_bagian",
    "DASAR :": "judul_bagian",
    "1. Peraturan Menteri Kehutan": "sumber_data",
    "SUMBER PETA :": "judul_bagian",
    "1. Peta RBI Skala 1:25.000 T": "sumber_data",
    "CATATAN :": "judul_bagian",
    "Batas administrasi pemerinta": "catatan",
    "PETA SITUASI": "judul_bagian",
    "TIM PELAKSANA": "tanda_tangan",
    "DEWI PERMATASARI ANANDA, S.H": "tanda_tangan",
    "KEMENTERIAN KEHUTANAN": "instansi_penerbit",
}


def run_case(title, lay, expect_maps, expect_labels):
    print("-- " + title)
    res = roles.detect(lay)
    got = roles_by_text(res)
    for key, role in expect_labels.items():
        check(got.get(key) == role, "{:<30} -> {} (dapat: {})".format(
            key, role, got.get(key)))
    kinds = {}
    for r in res:
        if not isinstance(r.item, QgsLayoutItemLabel):
            kinds.setdefault(r.role, 0)
            kinds[r.role] += 1
    for role, n in expect_maps.items():
        check(kinds.get(role, 0) == n, "{} x{} (dapat {})".format(
            role, n, kinds.get(role, 0)))
    return res


run_case("dua panel, TTD, tahun", build_pln(),
         {"peta": 2, "peta_situasi": 1, "legenda": 1, "skala_bar": 1,
          "panah_utara": 1, "logo": 1}, EXPECT)

one = {k: v for k, v in EXPECT.items()
       if k not in ("TAHUN 2025 - 2026", "TIM PELAKSANA",
                    "DEWI PERMATASARI ANANDA, S.H")}
run_case("satu panel, tanpa TTD", build_pln(False, False, True),
         {"peta": 1, "peta_situasi": 1}, one)

print("-- lapis ID dan peran tersimpan")
lay = build_pln(False, False, True, ids=True)
res = roles.detect(lay)
src = {r.item.id(): (r.role, r.source) for r in res if r.item.id()}
check(src.get("judul") == ("judul", roles.SRC_ID), "ID 'judul' dikenali")
check(src.get("tahun1") == ("label_tahun", roles.SRC_ID),
      "ID 'tahun1' dikenali")
sk = [r for r in res if isinstance(r.item, QgsLayoutItemLabel) and
      r.item.text().startswith("SK.913")][0]
roles.save_role(sk.item, "subjudul")
again = [r for r in roles.detect(lay) if r.item is sk.item][0]
check((again.role, again.source) == ("subjudul", roles.SRC_SAVED),
      "koreksi pengguna tersimpan dan dipakai ulang")

print()
print("GAGAL: {}".format(len(FAILS)) if FAILS else "SEMUA LULUS")
sys.exit(1 if FAILS else 0)
