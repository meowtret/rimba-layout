# Rimba Layout

Plugin QGIS untuk mengganti gaya **Print Layout yang sudah ada** dengan satu klik, tanpa memindahkan posisi elemen. Satu keluarga dengan [Rimba Grid](https://github.com/meowtret/rimba_grid).

> Status: dalam pengembangan. Tahap 1–2 (inti preset, skala kertas, pengenalan peran elemen) selesai. Dialog dan penerapan gaya menyusul.

## Preset bawaan

| Preset | Ciri |
|---|---|
| Kemenhut SK 399/2024 | Semua Arial hitam, judul kapital bold rata tengah, grid garis biru R190 G232 B255, label `122° 33' 0" BT` |
| Klasik | Judul Times New Roman, grid berbingkai zebra |
| Minimalis | Huruf abu tua, tanpa garis grid, tick ke luar |

Ukuran di preset ditulis untuk kertas A3 dan diskalakan otomatis untuk A4 sampai A0.

## Menjalankan uji

Dari OSGeo4W Shell (Windows):

```
python-qgis-ltr tests\test_core.py
```

Di Linux:

```
python3 tests/test_core.py
```

## Lisensi

GPL-2.0 atau yang lebih baru.
