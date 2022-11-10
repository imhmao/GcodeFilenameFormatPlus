import re
import os.path
# from PyQt6.QtWidgets import QFileDialog, QMessageBox

# Substitute print setting values in filename format

def parseFilenameFormat(print_settings, filename_format):

    short = 0
    dos = False
    # 设置了 8.3 格式 [8.3.2] .2 截取参数的长度
    # 截取参数的长度
    ma = re.match("^\[8\.3\.?(\d?)\]", filename_format)
    if ma != None:
        dos = True
        # QMessageBox.information(None,'test',ma.group(1))
        try:
            short = int(ma.group(1))
        except:
            short = 0
        filename_format = filename_format[ma.span()[1]:]                                     
    else:
        dos = False

    for setting, value in print_settings.items():
        val = str(value)
        if dos:
            val = val.replace(" ", "").replace(".", "")
            if short > 0:
                val = val[0:short]

        filename_format = filename_format.replace("[" + setting + "]", val)

    filename = re.sub(
        '[^A-Za-z0-9.,_\-%°$£€#\[\]\(\)\|\+\'\" ]+', '', filename_format)

    return filename
