# LGPLv3

import re
import os.path

from typing import cast

from PyQt6.QtCore import QDateTime
from PyQt6.QtCore import QObject

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.Application import Application
from UM.Qt.Duration import DurationFormat
from UM.PluginRegistry import PluginRegistry
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Scene.SceneNode import SceneNode
from UM.Version import Version

from cura.CuraApplication import CuraApplication
from cura.Settings.ExtruderManager import ExtruderManager
from cura.UI.ObjectsModel import ObjectsModel

from GcodeFilenameFormatPlus.ParseFilenameFormat import parseFilenameFormat

from GcodeFilenameFormatPlus.PrintSettingConverter import getPrintSettings

from PyQt6.QtWidgets import QFileDialog, QMessageBox

catalog = i18nCatalog("cura")

DEFAULT_FILENAME_FORMAT = "[8.3.2][base_name][profile_name][layer_height][material_bed_temperature]"

class GcodeFilenameFormatPlus(Extension, QObject):
    def __init__(self, parent = None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        Application.getInstance().getPreferences().addPreference("gcode_filename_format_plus/filename_format", DEFAULT_FILENAME_FORMAT)
        Application.getInstance().getPreferences().addPreference("gcode_filename_format_plus/object_count", self.getObjectCount())

        self.setMenuName("Gcode Filename Format Plus")
        self.addMenuItem("Edit Format", self.editFormat)
        self.format_window = None
        self.addMenuItem("Help", self.help)
        self.help_window = None

        self._application = CuraApplication.getInstance()
        self._print_information = None

        self._application.engineCreatedSignal.connect(self._onEngineCreated)

    def editFormat(self):
        if not self.format_window:
            self.format_window = self._createDialogue()
        self.format_window.show()

    def _createDialogue(self):
        qml_file_path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "Format.qml")
        component = Application.getInstance().createQmlComponent(qml_file_path)

        return component

    def help(self):
        if not self.help_window:
            self.help_window = self._createHelpDialog()
        self.help_window.show()

    def _createHelpDialog(self):
        qml_file_path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "Help.qml")
        component = Application.getInstance().createQmlComponent(qml_file_path)

        return component

    def _onEngineCreated(self) -> None:
        self._print_information = self._application.getPrintInformation()
        self._print_information.currentPrintTimeChanged.connect(self._triggerJobNameUpdate)
        self._print_information.materialWeightsChanged.connect(self._triggerJobNameUpdate)
        self._print_information.jobNameChanged.connect(self._onJobNameChanged)

        self._global_stack = None
        CuraApplication.getInstance().getMachineManager().globalContainerChanged.connect(self._onMachineChanged)
        self._onMachineChanged()

    def _onJobNameChanged(self) -> None:
        if self._print_information._is_user_specified_job_name:
            job_name = self._print_information._job_name
            if job_name == catalog.i18nc("@text Print job name", "Untitled"):
                return

            self._print_information._is_user_specified_job_name = False

    def _onMachineChanged(self) -> None:
        if self._global_stack:
            self._global_stack.containersChanged.disconnect(self._triggerJobNameUpdate)
            self._global_stack.metaDataChanged.disconnect(self._triggerJobNameUpdate)

        self._global_stack = CuraApplication.getInstance().getGlobalContainerStack()

        if self._global_stack:
            self._global_stack.containersChanged.connect(self._triggerJobNameUpdate)
            self._global_stack.metaDataChanged.connect(self._triggerJobNameUpdate)

    def _triggerJobNameUpdate(self, *args, **kwargs) -> None:
        self._print_information._job_name = ""      # Fixes filename clobbering from repeated calls
        filename_format = Application.getInstance().getPreferences().getValue("gcode_filename_format_plus/filename_format")
        Application.getInstance().getPreferences().setValue("gcode_filename_format_plus/object_count", self.getObjectCount())

        print_settings = getPrintSettings(filename_format)

        # Only update job name on valid print_settings dict
        # Necessary when getPrintSettings() attempts to access unavailable print settings during Cura exit
        if print_settings:
            file_name = parseFilenameFormat(print_settings, filename_format)
            self._print_information._job_name = file_name
        else:
            return

    def getObjectCount(self) -> int:
        count = 0

        for node in DepthFirstIterator(Application.getInstance().getController().getScene().getRoot()):
            if not ObjectsModel()._shouldNodeBeHandled(node):
                continue

            count += 1

        return count

