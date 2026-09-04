#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pyILPER 2.0
#
# An emulator for virtual HP-IL devices for the PIL-Box
# derived from ILPER 1.4.5 for Windows
# Copyright (c) 2008-2013   Jean-Francois Garnier
# C++ version (c) 2013 Christoph Gießelink
# Python Version (c) 2015 Joachim Siebold
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#
# Scope tab object classes ----------------------------------------------------
#
# Changelog
#
# XX.XX.XXXX jsi

import datetime

from PySide6 import QtWidgets
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG
from .pilwidgets import cls_tabtermgeneric, T_BOOLEAN, T_STRING, O_DEFAULT
from .pildevbase import cls_pildevbase
from .pilcore import cls_Tab_Spec


class cls_tabscope(cls_tabtermgeneric):
    LOG_PROBE1 = 0
    LOG_PROBE2 = 1
    LOG_BOTH = 2
    DISPLAY_MNEMONIC = 0
    DISPLAY_HEX = 1
    DISPLAY_BOTH = 2
    ID_PROBE1 = 1
    ID_PROBE2 = 2
    MNEMO = [
        [0x000, 0x700, "DAB"],
        [0x100, 0x700, "DSR"],
        [0x200, 0x700, "END"],
        [0x300, 0x700, "ESR"],
        [0x400, 0x7FF, "NUL"],
        [0x401, 0x7FF, "GTL"],
        [0x404, 0x7FF, "SDC"],
        [0x405, 0x7FF, "PPD"],
        [0x408, 0x7FF, "GET"],
        [0x40F, 0x7FF, "ELN"],
        [0x410, 0x7FF, "NOP"],
        [0x411, 0x7FF, "LLO"],
        [0x414, 0x7FF, "DCL"],
        [0x415, 0x7FF, "PPU"],
        [0x418, 0x7FF, "EAR"],
        [0x43F, 0x7FF, "UNL"],
        [0x420, 0x7E0, "LAD"],
        [0x45F, 0x7FF, "UNT"],
        [0x440, 0x7E0, "TAD"],
        [0x460, 0x7E0, "SAD"],
        [0x480, 0x7F0, "PPE"],
        [0x490, 0x7FF, "IFC"],
        [0x492, 0x7FF, "REN"],
        [0x493, 0x7FF, "NRE"],
        [0x49A, 0x7FF, "AAU"],
        [0x49B, 0x7FF, "LPD"],
        [0x4A0, 0x7E0, "DDL"],
        [0x4C0, 0x7E0, "DDT"],
        [0x400, 0x700, "CMD"],
        [0x500, 0x7FF, "RFC"],
        [0x540, 0x7FF, "ETO"],
        [0x541, 0x7FF, "ETE"],
        [0x542, 0x7FF, "NRD"],
        [0x560, 0x7FF, "SDA"],
        [0x561, 0x7FF, "SST"],
        [0x562, 0x7FF, "SDI"],
        [0x563, 0x7FF, "SAI"],
        [0x564, 0x7FF, "TCT"],
        [0x580, 0x7E0, "AAD"],
        [0x5A0, 0x7E0, "AEP"],
        [0x5C0, 0x7E0, "AES"],
        [0x5E0, 0x7E0, "AMP"],
        [0x500, 0x700, "RDY"],
        [0x600, 0x700, "IDY"],
        [0x700, 0x700, "ISR"],
    ]

    def __init__(self, guiObject, name, queue):
        super().__init__(guiObject, name)
        self.log_mode = ["Probe1", "Probe2", "Both"]
        self.display_mode = ["Mnemonic", "Hex", "Both"]

        self.queue = queue
        self.probePildevices = {}
        self.scope_charpos = 0
        #
        #     init local config parameters
        #
        self.showIdy = PILCONFIG.get(self.name, "showidy", False)
        self.displayMode = PILCONFIG.get(
            self.name, "displaymode", self.DISPLAY_MNEMONIC
        )
        self.logMode = PILCONFIG.get(self.name, "logmode", self.LOG_PROBE1)
        #
        #     add logging
        #
        self.add_logging()
        #
        #     add tag button
        #
        self.tagButton = QtWidgets.QPushButton("Tag Logfile")
        self.add_controlwidget(self.tagButton)
        self.tagButton.setEnabled(False)
        self.tagButton.clicked.connect(self.do_tagbutton)
        #
        #     add scope config options to cascading menu
        #
        self.cBut.add_option("Show IDY frames", "showidy", T_BOOLEAN, [True, False])
        self.cBut.add_option("Display Mode", "displaymode", T_STRING, self.display_mode)
        self.cBut.add_option("Log mode", "logmode", T_STRING, self.log_mode)
        #
        #     create HP-IL devices and let the GUI object know them
        #
        self.pildevice = None
        self.guiobject.set_pildevice(self.pildevice)

        self.cBut.config_changed_signal.connect(self.do_tabconfig_changed)

    #
    #  handle changes of tab configuration
    #
    def do_tabconfig_changed(self):
        param = self.cBut.get_changed_option_name()
        #
        #     change local config parameters
        #
        if param == "showidy":
            self.showIdy = PILCONFIG.get(self.name, "showidy")
        elif param == "displaymode":
            self.displayMode = PILCONFIG.get(self.name, "displaymode")
        elif param == "logmode":
            self.logMode = PILCONFIG.get(self.name, "logmode")
            self.controlProbes()
        super().do_tabconfig_changed()

    def enable(self):
        super().enable()
        self.queue.clear()
        self.controlProbes()

        if self.logging:
            self.tagButton.setEnabled(True)

    def disable(self):
        super().disable()

    def do_cbActive(self):
        self.active = self.cbActive.isChecked()
        PILCONFIG.put(self.name, "active", self.active)
        self.controlProbes()
        self.toggle_active()
        return

    #
    #  set tag button active/inactive
    #
    def do_cbLogging(self):
        super().do_cbLogging()
        if self.logging:
            self.tagButton.setEnabled(True)
        else:
            self.tagButton.setEnabled(False)

    #
    # exec tag button, because we may write it asynchronous pause the thread
    #
    def do_tagbutton(self):
        text, okPressed = QtWidgets.QInputDialog.getText(
            self, "Tag Logfile", "Logfile tag", QtWidgets.QLineEdit.Normal, ""
        )
        if okPressed and text != "":
            self.UpdateTimer.stop()
            #
            #  all errors that might occur during log write are handled from the
            #  cbLogging methods, we do not need to catch errors
            #
            self.cbLogging.logWrite("\n")
            self.cbLogging.logWrite(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.cbLogging.logWrite(" ** ")
            self.cbLogging.logWrite(text)
            self.cbLogging.logWrite("\n")
            self.UpdateTimer.start(PILGLOBALS.Update_Timer)

    #
    #
    #  Forward items to the terminal frontend widget and do logging
    #  Note: for the scope a single item is a string not the integer representation of a character
    #
    def out_device(self, items):
        for s in items:
            l = len(s)
            if self.scope_charpos + l >= self.guiobject.get_cols():
                self.guiobject.HPTerminal.process(0x0D)
                self.guiobject.HPTerminal.process(0x0A)
                self.cbLogging.logWrite("\n")
                self.cbLogging.logFlush()
                self.scope_charpos = 0
            for i in range(0, l):
                self.guiobject.HPTerminal.process(ord(s[i]))
            self.cbLogging.logWrite(s)
            self.scope_charpos += l

    def process_queue(self):
        items = self.queue.getItems()
        resultItems = []
        if len(items):
            for item in items:
                id = item[0]
                frame = item[1]
                if ((frame & 0x700) == 0x600) and not self.showIdy:
                    continue
                #
                # get mnemo
                for i in self.MNEMO:
                    if (frame & i[1]) == i[0]:
                        # mnemonic
                        s = i[2]
                        # has argument
                        arg = (~i[1]) & 0xFF
                        if arg != 0:
                            # add argument
                            s += " {:02X}".format(frame & arg)
                        break
                if self.displayMode == self.DISPLAY_MNEMONIC:
                    s = "{:6s}  ".format(s)
                elif self.displayMode == self.DISPLAY_HEX:
                    s = "{:03X}  ".format(frame)
                elif self.displayMode == self.DISPLAY_BOTH:
                    s = "{:6s} ({:03X}) ".format(s, frame)
                if id == self.ID_PROBE2:
                    s = s.lower()
                resultItems.append(s)
        self.out_device(resultItems)

        # self.out_device(items)

        self.guiobject.HPTerminal.refresh()
        self.UpdateTimer.start(PILGLOBALS.Update_Timer)
        return

    def registerProbe(self, name, pildevice):
        id = int("".join([char for char in name[::-1] if char.isdigit()])[::-1])
        self.probePildevices[id] = pildevice
        pildevice.setactive(self.active)

    def controlProbes(self):
        print(f"control probes {self.active} {self.logMode}")
        if self.active:
            if self.logMode == self.LOG_BOTH:
                self.probePildevices[1].setactive(True)
                self.probePildevices[2].setactive(True)
            elif self.logMode == self.LOG_PROBE1:
                self.probePildevices[1].setactive(True)
                self.probePildevices[2].setactive(False)
            else:
                self.probePildevices[1].setactive(False)
                self.probePildevices[2].setactive(True)
        else:
            self.probePildevices[1].setactive(False)
            self.probePildevices[2].setactive(False)


def pilscope_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Scope,
            PILGLOBALS.Tab_Type_Scope,
            None,
            cls_tabscope,
            "Scope",
        )
    ]
