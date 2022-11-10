# LGPLv3

import re
import os.path
import sys

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

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from UM.Message import Message
from UM.Logger import Logger
from UM.Mesh.MeshWriter import MeshWriter
from UM.FileHandler.WriteFileJob import WriteFileJob

from UM.OutputDevice import OutputDeviceError
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin

from GcodeFilenameFormatPlus.PrintSettingConverter import getPrintSettings

catalog = i18nCatalog("uranium")


class DosNameOutputDevicePlugin(OutputDevicePlugin):
    def start(self):
        self.getOutputDeviceManager().addOutputDevice(DosNameOutputDevice())

    def stop(self):
        self.getOutputDeviceManager().removeOutputDevice("dos_name_output_device")


class DosNameOutputDevice(OutputDevice):
    def __init__(self):
        # Give an ID which is used to refer to the output device.
        super().__init__("dos_name_output_device")

        Application.getInstance().getPreferences().addPreference(
            "dos_name_output_device/last_used_type", "")
        Application.getInstance().getPreferences().addPreference(
            "dos_name_output_device/dialog_save_path", "")

        # Optionally set some metadata.
        # Human-readable name (you may want to internationalise this). Gets put in messages and such.
        self.setName("DOS File Name Output Device")
        # This is put on the save button.
        self.setShortDescription("Save DOS Name")
        self.setDescription("Save DOS Format File Name")
        self.setIconName("save")
        self._writing = False

    def requestWrite(self, nodes, file_name=None, limit_mimetypes=None, file_handler=None, **kwargs):

        application = cast(CuraApplication, Application.getInstance())
        machine_manager = application.getMachineManager()
        global_stack = machine_manager.activeMachine

        print_information = application.getPrintInformation()
        job_name = print_information.jobName

        filename_format = application.getPreferences().getValue(
            "gcode_filename_format_plus/filename_format")

        # QMessageBox.information(None,'filename_format',filename_format)

        print_settings = getPrintSettings(filename_format)

        if print_settings:
            file_name = parseFilenameFormat(print_settings, filename_format)

        # QMessageBox.information(None,'file_name',file_name)

        if file_name is None:
            file_name = job_name

        file_name = file_name + ".g"

        if self._writing:
            raise OutputDeviceError.DeviceBusyError()

        if not file_handler:
            file_handler = Application.getInstance().getMeshFileHandler()

        file_types = file_handler.getSupportedFileTypesWrite()
        selected_type = None
        for item in file_types:
            #QMessageBox.information(None,'id',item["id"])
            #QMessageBox.information(None,'mime_type',item["mime_type"])
            if item["id"] == 'GCodeWriter':
                selected_type = item
                break

        if selected_type is None:
            raise Exception('GCodeWrite Not Found')

        dialog = QFileDialog()

        dialog.setWindowTitle(catalog.i18nc("@title:window", "Save to File"))
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)

        if sys.platform == "linux" and "KDE_FULL_SESSION" in os.environ:
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog)

        filters = ["GCode File (*.g)"]
        selected_filter = None

        stored_directory = Application.getInstance().getPreferences().getValue(
            "dos_name_output_device/dialog_save_path")
        dialog.setDirectory(stored_directory)

        if file_name is not None:
            dialog.selectFile(file_name)

        dialog.setNameFilters(filters)
        if selected_filter is not None:
            dialog.selectNameFilter(selected_filter)

        if not dialog.exec():
            raise OutputDeviceError.UserCanceledError()

        save_path = dialog.directory().absolutePath()
        Application.getInstance().getPreferences().setValue(
            "dos_name_output_device/dialog_save_path", save_path)

        file_name = dialog.selectedFiles()[0]

        #QMessageBox.information(None, 'file_name', file_name)
        if os.path.exists(file_name):
            result = QMessageBox.question(None, catalog.i18nc("@title:window", "File Already Exists"), catalog.i18nc(
                "@label Don't translate the XML tag <filename>!", "The file <filename>{0}</filename> already exists. Are you sure you want to overwrite it?").format(file_name))
            if result == QMessageBox.ButtonRole.NoRole:
                raise OutputDeviceError.UserCanceledError()

        self.writeStarted.emit(self)

        if file_handler:
            file_writer = file_handler.getWriter(selected_type["id"])
        else:
            file_writer = Application.getInstance(
            ).getMeshFileHandler().getWriter(selected_type["id"])

        try:
            mode = selected_type["mode"]
            if mode == MeshWriter.OutputMode.TextMode:
                Logger.log(
                    "d", "Writing to Local File %s in text mode", file_name)
                stream = open(file_name, "wt", encoding="utf-8")
            elif mode == MeshWriter.OutputMode.BinaryMode:
                Logger.log(
                    "d", "Writing to Local File %s in binary mode", file_name)
                stream = open(file_name, "wb")
            else:
                Logger.log("e", "Unrecognised OutputMode.")
                return None

            job = WriteFileJob(file_writer, stream, nodes, mode)
            job.setFileName(file_name)
            job.setAddToRecentFiles(True)
            job.progress.connect(self._onJobProgress)
            job.finished.connect(self._onWriteJobFinished)

            message = Message(catalog.i18nc("@info:progress Don't translate the XML tags <filename>!", "Saving to <filename>{0}</filename>").format(file_name),
                              0, False, -1, catalog.i18nc("@info:title", "Saving"))
            message.show()


            job.setMessage(message)
            self._writing = True
            job.start()


        except PermissionError as e:
            Logger.log(
                "e", "Permission denied when trying to write to %s: %s", file_name, str(e))
            raise OutputDeviceError.PermissionDeniedError(catalog.i18nc(
                "@info:status Don't translate the XML tags <filename>!", "Permission denied when trying to save <filename>{0}</filename>").format(file_name)) from e
        except OSError as e:
            Logger.log(
                "e", "Operating system would not let us write to %s: %s", file_name, str(e))
            raise OutputDeviceError.WriteRequestFailedError(catalog.i18nc(
                "@info:status Don't translate the XML tags <filename> or <message>!", "Could not save to <filename>{0}</filename>: <message>{1}</message>").format()) from e

    def _onJobProgress(self, job, progress):
        self.writeProgress.emit(self, progress)

    def _onWriteJobFinished(self, job):
        self._writing = False
        self.writeFinished.emit(self)
        if job.getResult():
            self.writeSuccess.emit(self)
            message = Message(catalog.i18nc("@info:status Don't translate the XML tags <filename>!",
                              "Saved to <filename>{0}</filename>").format(job.getFileName()), title=catalog.i18nc("@info:title", "File Saved"))
            message.addAction("open_folder", catalog.i18nc("@action:button", "Open Folder"),
                              "open-folder", catalog.i18nc("@info:tooltip", "Open the folder containing the file"))
            message._folder = os.path.dirname(job.getFileName())
            message.actionTriggered.connect(self._onMessageActionTriggered)
            message.show()
        else:
            message = Message(catalog.i18nc("@info:status Don't translate the XML tags <filename> or <message>!", "Could not save to <filename>{0}</filename>: <message>{1}</message>").format(
                job.getFileName(), str(job.getError())), lifetime=0, title=catalog.i18nc("@info:title", "Warning"))
            message.show()
            self.writeError.emit(self)

        try:
            job.getStream().close()
        except (OSError, PermissionError):
            message = Message(catalog.i18nc("@info:status", "Something went wrong saving to <filename>{0}</filename>: <message>{1}</message>").format(
                job.getFileName(), str(job.getError())), title=catalog.i18nc("@info:title", "Error"))
            message.show()
            self.writeError.emit(self)

    def _onMessageActionTriggered(self, message, action):
        if action == "open_folder" and hasattr(message, "_folder"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(message._folder))