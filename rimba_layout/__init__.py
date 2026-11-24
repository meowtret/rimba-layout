# -*- coding: utf-8 -*-


def classFactory(iface):  # noqa: N802
    from .rimba_layout import RimbaLayoutPlugin
    return RimbaLayoutPlugin(iface)
