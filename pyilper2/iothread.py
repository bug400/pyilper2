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
# iothread.py: base class for reader thread
# See the diagrad im controlthread.py for an overview of the architecture.
#
# Note: that all interfaces implement an autoreconnect feature
#
# The pseudocode of a reader thread is:
#
# while True:
#     # outer reconnect loop
#     check for client/device connection
#     if connected:
#         put status change to queue
#         while true:
#              # inner read data loop
#              if data available (blocked read with timeout):
#                   put data to queue
#                   continue
#              if i/o error:
#                   if error cause is device unplugged or client disconnect:
#                       # return to connect loop
#                       break
#                    else:
#                        put error message and status change to queue
#                        disconnect client/close device
#                        exit
#              iff stop signal set by controlthread:
#                  disconnect client/device
#                  exit
#

import threading
from .pilglobals import PILGLOBALS
from .pilcore import AppException


class cls_IOThread(threading.Thread):

    STAT_DISABLED = 4
    STAT_DISCONNECTED = 2
    STAT_CONNECTING = 1
    STAT_CONNECTED = 0

    MSG_ERROR = -10
    MSG_STATUS = -11

    def __init__(
        self, parent, stopEvent, queue, id, interfaceConfigName, interfaceName
    ):
        super().__init__()
        self.__parent__ = parent
        self.__stopEvent__ = stopEvent
        self.__queue__ = queue
        self.__id__ = id
        self.__name__ = interfaceName
        self.__configName__ = interfaceConfigName
        self.__status__ = self.STAT_DISCONNECTED
        self.__statLock__ = threading.Lock()
        self.USE_8BITS = True
        self.__ioDevice__ = None
        self.__deviceRemoved__ = True

    def setStatus(self, stat):
        with self.__statLock__:
            self.__status__ = stat
        self.__queue__.put([self.__id__, self.MSG_STATUS, stat])

    #
    #  assemble frame from low and high byte according to 7- oder 8-bit format
    #
    def assemble_frame(self, hbyt, lbyt):

        if lbyt & 0x80:
            self.USE_8BITS = True
            return ((hbyt & 0x1E) << 6) + (lbyt & 0x7F)
        else:
            self.USE_8BITS = False
            return ((hbyt & 0x1F) << 6) + (lbyt & 0x3F)

    #
    #  disassemble frame from low and high byte according to 7- oder 8-bit format
    #
    def disassemble_frame(self, frame):
        if not self.USE_8BITS:
            hbyt = ((frame >> 6) & 0x1F) | 0x20
            lbyt = (frame & 0x3F) | 0x40
        else:
            hbyt = ((frame >> 6) & 0x1E) | 0x20
            lbyt = (frame & 0x7F) | 0x80
        return (hbyt, lbyt)

    def getStatus(self):
        with self.__statLock__:
            return self.__status__

    #
    #  send command to PIL-Box, check return value.
    #
    def sendCmd(self, cmdfrm, tmout):
        hbyt, lbyt = self.disassemble_frame(cmdfrm)
        try:
            self.__ioDevice__.writePilBoxFrame(lbyt, hbyt)
            bytrx = self.__ioDevice__.readByte(tmout)
        except Exception as e:
            e.add_note(self.__name__ + ": i/o error in sendCMD")
            raise e from e
        if bytrx is None:
            raise AppException(self.__name__ + ": timeout getting response of command")
            self.__ioDevice__.close()
        try:
            tst = ord(bytrx)
        except (ValueError, TypeError):
            self.__ioDevice__.close()
            raise AppException(self.__name__ + ": illegal return value for command")
        if tst != lbyt:
            print("pilacm: return value mismatch %x %x" % (tst, lbyt))
            self.__ioDevice__.close()
            raise AppException(self.__name__ + ": illegal return value for command")
        print(
            self.__name__ + ": command sent and acknowledged 0x{0:02x}".format(cmdfrm)
        )
