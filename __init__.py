# AGPLv3

from . import GcodeFilenameFormatPlus
from . import DosNameOutputDevice

def getMetaData():
    return {}

def register(app):
    return {
        "output_device": DosNameOutputDevice.DosNameOutputDevicePlugin(),
        "extension": GcodeFilenameFormatPlus.GcodeFilenameFormatPlus()
    }
