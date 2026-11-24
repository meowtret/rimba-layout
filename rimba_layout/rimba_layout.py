# -*- coding: utf-8 -*-
"""Rimba Layout - buat Print Layout lengkap dari preset."""

import os

from qgis.PyQt.QtGui import QIcon

try:  # Qt6 / QGIS 4: QAction ada di QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:  # Qt5 / QGIS 3
    from qgis.PyQt.QtWidgets import QAction

MENU = "&Rimba Layout"


class RimbaLayoutPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):  # noqa: N802
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
        self.action = QAction(icon, "Rimba Layout (buat layout dari preset)",
                              self.iface.mainWindow())
        self.action.setToolTip(
            "Buat Print Layout lengkap dari preset (Kemenhut, Klasik, "
            "Minimalis)")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

    def unload(self):
        self.iface.removePluginMenu(MENU, self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dlg:
            self.dlg.close()
            self.dlg = None

    def run(self):
        from .dialog import RimbaLayoutDialog
        if self.dlg is None:
            self.dlg = RimbaLayoutDialog(self.iface, self.iface.mainWindow())
        self.dlg.reload_presets()
        self.dlg.reload_themes()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
