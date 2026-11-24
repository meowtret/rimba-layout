# -*- coding: utf-8 -*-
"""Muat, validasi, dan simpan preset Rimba Layout (file JSON)."""

import json
import os

BUILTIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "presets")

# Peran yang dikenal. Preset boleh hanya mengisi sebagian.
TEXT_ROLES = (
    "judul", "subjudul", "teks", "catatan", "catatan_proyeksi",
    "sumber_data", "judul_bagian", "skala_teks", "label_tahun",
    "tanda_tangan", "instansi_penerbit", "huruf_utara",
)
OTHER_ROLES = ("legenda", "skala_bar", "skala_angka", "peta",
               "peta_situasi", "panah_utara", "logo", "kotak")
ALL_ROLES = TEXT_ROLES + OTHER_ROLES

_TEXT_KEYS = {"font": str, "size": (int, float), "bold": bool,
              "italic": bool, "uppercase": bool, "align": str,
              "color": str, "frame": bool}
_ALIGN = ("left", "center", "right", "justify")
_GRID_FORMATS = ("dms", "dm", "dd")
_GRID_STYLES = ("lines", "cross", "frame")
_GRID_FRAMES = ("zebra", "zebra_nautical", "line", "ticks_in",
                "ticks_out", "none")
PAPERS = ("A4", "A3", "A2", "A1", "A0")


class PresetError(ValueError):
    """Preset tidak valid; pesan dalam bahasa Indonesia."""


def _check_color(value, where):
    v = str(value)
    if not (v.startswith("#") and len(v) in (7, 9)):
        raise PresetError("{}: warna harus #RRGGBB, bukan '{}'".format(
            where, value))
    try:
        int(v[1:], 16)
    except ValueError:
        raise PresetError("{}: warna '{}' tidak valid".format(where, value))


def _check_text(spec, where):
    if not isinstance(spec, dict):
        raise PresetError("{}: harus berupa objek".format(where))
    for key, val in spec.items():
        if key not in _TEXT_KEYS:
            raise PresetError("{}: kunci '{}' tidak dikenal".format(
                where, key))
        if not isinstance(val, _TEXT_KEYS[key]) or (
                _TEXT_KEYS[key] is not bool and isinstance(val, bool)):
            raise PresetError("{}.{}: tipe nilai salah".format(where, key))
    if "size" in spec and not (2 <= spec["size"] <= 200):
        raise PresetError("{}.size: di luar 2-200 pt".format(where))
    if "align" in spec and spec["align"] not in _ALIGN:
        raise PresetError("{}.align: pilih salah satu {}".format(
            where, ", ".join(_ALIGN)))
    if "color" in spec:
        _check_color(spec["color"], where + ".color")


def validate(data):
    """Periksa struktur preset. Kembalikan data yang sama bila valid."""
    if not isinstance(data, dict):
        raise PresetError("Preset harus berupa objek JSON")
    for key in ("name", "version", "base_paper", "roles"):
        if key not in data:
            raise PresetError("Kunci wajib '{}' tidak ada".format(key))
    if data["base_paper"] not in PAPERS:
        raise PresetError("base_paper harus salah satu {}".format(
            ", ".join(PAPERS)))
    roles = data["roles"]
    if not isinstance(roles, dict):
        raise PresetError("roles harus berupa objek")
    for role, spec in roles.items():
        where = "roles." + role
        if role not in ALL_ROLES:
            raise PresetError("{}: peran tidak dikenal".format(where))
        if role in TEXT_ROLES:
            _check_text(spec, where)
        elif role == "legenda":
            for part in spec:
                if part not in ("title", "group", "item"):
                    raise PresetError("{}: bagian '{}' tidak dikenal".format(
                        where, part))
                _check_text(spec[part], where + "." + part)
        elif role in ("skala_bar", "skala_angka"):
            if "font" in spec:
                _check_text(spec["font"], where + ".font")
        elif role in ("peta", "peta_situasi", "kotak"):
            for k in ("frame_color", "color"):
                if k in spec:
                    _check_color(spec[k], where + "." + k)
    for gkey in ("grid", "grid_situasi"):
        grid = data.get(gkey)
        if grid is None:
            continue
        if grid.get("format", "dms") not in _GRID_FORMATS:
            raise PresetError(gkey + ".format tidak dikenal")
        if grid.get("style", "lines") not in _GRID_STYLES:
            raise PresetError(gkey + ".style tidak dikenal")
        if grid.get("frame", "line") not in _GRID_FRAMES:
            raise PresetError(gkey + ".frame tidak dikenal")
        if "line_color" in grid:
            _check_color(grid["line_color"], gkey + ".line_color")
    return data


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as err:
            raise PresetError("{}: JSON rusak ({})".format(
                os.path.basename(path), err))
    return validate(data)


def save(data, path):
    validate(data)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def list_presets(user_dir=None):
    """Daftar (nama, path, bawaan?) dari folder bawaan dan folder pengguna."""
    out = []
    for folder, builtin in ((BUILTIN_DIR, True), (user_dir, False)):
        if not folder or not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(folder, name)
            try:
                out.append((load(path)["name"], path, builtin))
            except (PresetError, OSError):
                continue
    return out
