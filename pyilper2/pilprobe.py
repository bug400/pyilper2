# -*- coding: utf-8 -*-
#
# pyILPER 2.0
#
# (c) 2026 Joachim Siebold
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
# pilprobe.py: virtual HP-IL probe (gui and virtual HP-IL device)
#
from PySide6 import QtCore, QtWidgets
import threading

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


#
# This is a stub for a GUI which is only used to initialize the probe in the same way as
# the other virtual devices that have a GUI. The tab is not added to the tab bar and
# deleted after the initialization of the devices.
#
class cls_tabprobe(QtWidgets.QWidget):

    def __init__(self, parent, name, queue):
        self.queue = queue

        self.id = int("".join([char for char in name[::-1] if char.isdigit()])[::-1])

        self.pildevice = cls_pilprobe(self.queue, self.id)


#
# Probe virtual device object
#


class cls_pilprobe:

    def __init__(self, queue, id):
        self.id = id
        self.queue = queue
        self.__isactive__ = False  # device active in loop
        self.__isactive_lock__ = threading.Lock()

    def process(self, frame):
        if self.getactive():
            self.queue.putItem([self.id, frame])
        return frame

    def setactive(self, active):
        # print(f"probe {self.id} setactive {active}")
        self.__isactive_lock__.acquire()
        self.__isactive__ = active
        self.__isactive_lock__.release()

    #
    # get decive active status
    #
    def getactive(self):
        self.__isactive_lock__.acquire()
        active = self.__isactive__
        self.__isactive_lock__.release()
        return active


def pilprobe_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Probe,
            PILGLOBALS.Tab_Type_Probe,
            None,
            cls_tabprobe,
            "Probe",
        )
    ]
