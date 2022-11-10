// AGPLv3

import UM 1.5 as UM
import QtQuick 2.15
import QtQuick.Window 2.2
import QtQuick.Controls 2.15

import Cura 1.5 as Cura

UM.Dialog
{
    id: base
    title: "Gcode Filename Format Plus - Edit Format"
    width: 600 * screenScaleFactor
    height: 80 * screenScaleFactor
    minimumWidth: 300 * screenScaleFactor
    minimumHeight: 70 * screenScaleFactor

    Cura.TextField
    {
        id: textfield
        text: UM.Preferences.getValue("gcode_filename_format_plus/filename_format")
        width: base.width - 15 * screenScaleFactor
    }

    leftButtons: Cura.SecondaryButton
    {
        text: "Default"
        onClicked: textfield.text = "[8.3.2][base_name][profile_name][layer_height][material_bed_temperature]"
    }

    rightButtons: Cura.SecondaryButton
    {
        text: "Close"
        onClicked:
        {
            base.visible = false;
            UM.Preferences.setValue("gcode_filename_format_plus/filename_format", textfield.text)
        }
    }
}
