# -*- coding: utf-8 -*-
#
# pyILPER 2.0
#
# An emulator for virtual HP-IL devices for the PIL-Box
# derived from ILPER 1.4.5 for Windows
# Copyright (c) 2008-2013   Jean-Francois Garnier
# C++ version (c) 2013 Christoph Gießelink
# Python Version (c) 2026 Joachim Siebold
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
# pilterminal.py: virtual terminal with keyboard support (gui and HP-IL device)
#

import threading
import array
from .pilconfig import PILCONFIG
from .pilwidgets import cls_tabtermgeneric, T_STRING
from .pilkeymap import KEYBOARD_TYPE_HP71, keyboardtypes
from .pildevbase import cls_pildevbase
from .pilcharconv import CHARSET_HP71, charsets
from .pilcore import cls_Tab_Spec, PILGLOBALS

#
# Terminal tab object classes ----------------------------------------------
#


class cls_tabterminal(cls_tabtermgeneric):

    def __init__(self, mainUI, name):
        super().__init__(mainUI, name)
        #
        #     init local configuration parameters
        #
        self.charset = PILCONFIG.get(self.name, "charset", CHARSET_HP71)
        self.keyboardtype = PILCONFIG.get(self.name, "keyboardtype", KEYBOARD_TYPE_HP71)
        #
        #     add terminal config options to cascading menu
        #
        self.cBut.add_option("Character set", "charset", T_STRING, charsets)
        self.cBut.add_option("Keyboard type", "keyboardtype", T_STRING, keyboardtypes)

        #
        #     create HP-IL device and let the GUI object know it
        #
        self.pildevice = cls_pilterminal(self.guiobject)
        self.guiobject.set_pildevice(self.pildevice)
        self.guiobject.set_charset(self.charset)
        self.guiobject.set_keyboardtype(self.keyboardtype)
        self.cBut.config_changed_signal.connect(self.do_tabconfig_changed)

    #
    #  handle changes of the character set
    #
    def do_tabconfig_changed(self):
        param = self.cBut.get_changed_option_name()
        #
        #     change local config parameters
        #
        if param == "charset":
            self.charset = PILCONFIG.get(self.name, "charset")
            self.guiobject.set_charset(self.charset)

        if param == "keyboardtype":
            self.keyboardtype = PILCONFIG.get(self.name, "keyboardtype")
            self.guiobject.set_keyboardtype(self.keyboardtype)

        super().do_tabconfig_changed()

    #
    #     enable/disable
    #
    def enable(self):
        super().enable()
        self.pildevice.setactive(PILCONFIG.get(self.name, "active"))
        self.guiobject.enable_keyboard()

    def disable(self):
        super().disable()
        self.guiobject.disable_keyboard()

    #
    #     enable keyboard only if terminal active
    #
    def toggle_active(self):
        if self.active:
            self.guiobject.enable_keyboard()
        else:
            self.guiobject.disable_keyboard()

    #
    #  output guiqueue content to terminal
    #
    def out_device(self, items):
        for i in items:
            self.guiobject.HPTerminal.processTerminal(i)


#
# HP-IL device class for the terminal
#
class cls_pilterminal(cls_pildevbase):

    def __init__(self, guiobject):
        super().__init__()

        self.__aid__ = 0x3E  # accessory id = general interface
        self.__defaddr__ = 8  # default address alter AAU
        self.__did__ = "PILTERM"  # device id
        self.__guiobject__ = guiobject  # terminal gui object

    #
    # private (overloaded) --------
    #
    #  forward data coming from HP-IL to the terminal frontend widget
    #
    def __indata__(self, frame):
        self.putGuiQueueItem(frame & 0xFF)

    #
    #  clear device: empty HP-IL outdata buffer and reset terminal
    #
    def __clear_device__(self):
        super().__clear_device__()  # this clears srq
        self.clearOutQueue()
        #
        #     reset device
        #
        self.__guiobject__.reset_terminal()
        return

    #
    #  send data from HP-IL outdata buffer to the loop
    #
    def __outdata__(self, frame):
        self.__status_lock__.acquire()
        self.__status__ = self.__status__ & 0xBF  # clear srq bit
        if self.__outqueue__.empty():
            frame = 0x540  # EOT
        else:
            frame = self.__outqueue__.get_nowait()
            if self.__outqueue__.empty():
                self.__status__ = self.__status__ & 0xEF  # clear ready for data bit
        self.__status_lock__.release()
        return frame


def pilterminal_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Terminal,
            PILGLOBALS.Tab_Type_Device,
            None,
            cls_tabterminal,
            "Terminal",
        )
    ]
