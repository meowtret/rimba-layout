# -*- coding: utf-8 -*-
"""Rimba Layout - ganti gaya Print Layout dengan preset."""

import os

from qgis.core import Qgis, QgsMessageLog
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
        self.action = QAction(icon, "Rimba Layout (ganti gaya layout)",
                              self.iface.mainWindow())
        self.action.setToolTip(
            "Terapkan preset gaya (Kemenhut, Klasik, Minimalis) ke layout")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)
        self.iface.layoutDesignerOpened.connect(self._add_to_designer)

    def _add_to_designer(self, designer):
        try:
            tb = designer.actionsToolbar()
            if tb is not None:
                tb.addAction(self.action)
        except (AttributeError, RuntimeError) as err:
            QgsMessageLog.logMessage(
                "Gagal menambah ikon ke Layout Designer: {}".format(err),
                "Rimba Layout", Qgis.MessageLevel.Warning)

    def unload(self):
        try:
            self.iface.layoutDesignerOpened.disconnect(self._add_to_designer)
        except (TypeError, RuntimeError):
            QgsMessageLog.logMessage(
                "Sinyal Layout Designer sudah terputus.", "Rimba Layout",
                Qgis.MessageLevel.Info)
        self.iface.removePluginMenu(MENU, self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dlg:
            self.dlg.close()
            self.dlg = None

    def _active_layout_name(self):
        try:
            designers = self.iface.openLayoutDesigners()
        except AttributeError:
            return None
        for d in reversed(list(designers or [])):
            try:
                if d.window().isActiveWindow():
                    return d.layout().name()
            except (AttributeError, RuntimeError):
                continue
        return None

    def run(self):
        from .dialog import RimbaLayoutDialog
        if self.dlg is None:
            self.dlg = RimbaLayoutDialog(self.iface, self.iface.mainWindow())
        self.dlg.reload_presets()
        self.dlg.reload_layouts(self._active_layout_name())
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
