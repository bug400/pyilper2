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
# ACM i/o thread class  ---------------------------------------------
#
# Changelog
#
# XX.XX.2026 jsi
# - code taken from pyILPER 1.9 and modified for pyILPER 2.0


import time
import threading

from .serialio import cls_serialIO
from .pilglobals import PILGLOBALS

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets
from .iothread import cls_IOThread


class cls_acmbox(cls_IOThread):

    def __init__(self, stopEvent, queue, id, name, params):
        super().__init__(stopEvent, queue, id, name)
        self.__ttyDevice__ = params[0]
        self.__ioDevice__ = cls_serialIO(self.__ttyDevice__)  # acm device object
        self.__baudrate__ = 0

    def getBaudRate(self):
        return self.__baudrate__

    #
    #  Connect to ACM device and put it to TDIS mode.
    #
    def open(self):

        #
        #     open tty device The baudrate is not relevant for USB CDC, simply use the highest one
        #
        self.__baudrate__ = PILGLOBALS.Baudrates[len(PILGLOBALS.Baudrates) - 1][1]
        try:
            self.__ioDevice__.open(self.__baudrate__)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot connect to ACM device")
            raise e from e

        #
        # Send disconnect
        #
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_TDIS, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot connect to ACM device")
            raise e from e
        return

    #
    #  Disconnect ACM device
    #
    def close(self):
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_TDIS, PILGLOBALS.Tmout_Cmd)
            pass
        finally:
            self.__ioDevice__.close()

    #
    #  Init Box, send  PASSTHRU
    #
    def initBox(self):
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Commands_PASSTHRU, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot initialize PIL-Box")
            raise e from e

    #
    #  PIL-Box reader thread
    #
    def reader(self):

        self.setStatus(self.STAT_CONNECTING)
        print(self.__name__ + ": reader thread started")
        try:
            #
            # outer auto reconnect loop
            #

            while True:
                #
                # exit if stop event
                #
                if self.__stopEvent__.is_set():
                    break
                #
                # check for device if removed
                #
                if self.__deviceRemoved__:
                    if not self.__ioDevice__.checkDeviceExists():
                        time.sleep(PILGLOBALS.AutoreconnectInterval)
                        continue
                    else:
                        print(self.__name__ + ": reconnecting device")
                        time.sleep(PILGLOBALS.AutoreconnectInterval)
                        self.__deviceRemoved__ = False
                #
                # open device
                #
                self.open()
                #
                # init PIL-Box mode
                #
                self.initBox()
                print(self.__name__ + ": open/init passed")
                self.setStatus(self.STAT_CONNECTED)
                #
                # inner read loop
                #
                while True:
                    #
                    # check stop event
                    #
                    if self.__stopEvent__.is_set():
                        break
                    #
                    # read frame from box
                    #
                    try:
                        frame = self.__ioDevice__.readFrame()
                    except Exception as e:
                        time.sleep(PILGLOBALS.SerialDevicePlugDelay)
                        if self.__ioDevice__.checkDeviceExists():
                            e.add_note(self.__name__ + ": reader error")
                            raise e from e
                        self.__deviceRemoved__ = True
                        self.setStatus(self.STAT_CONNECTING)
                        break
                    #
                    # Timeout
                    #
                    if frame is None:
                        continue
                    # print(self.__name__ + ": read frame %x" % frame)
                    #
                    # put frame to queue
                    #
                    self.__queue__.put([self.__id__, frame])
            #
            # normal termination
            #

            if self.getStatus() == self.STAT_CONNECTED:
                self.close()
            print(self.__name__ + ": reader normal exit")
        #
        # error exit
        #
        except Exception as e:
            #
            # put error status and message to queue
            #
            self.__queue__.put([self.__id__, -1, e])
        finally:
            self.setStatus(self.STAT_DISCONNECTED)
        return

    #
    #  frame writer. Note: this method is called from the controller thread
    #
    def writer(self, frame):
        #
        # if we are not connected, do not output frame
        #
        if self.getStatus() != self.STAT_CONNECTED:
            return

        # print(self.__name__ + ": writer sends frame")

        try:
            self.__ioDevice__.writeFrame(frame)
        #
        # Error handling
        #
        except Exception as e:
            time.sleep(PILGLOBALS.SerialDevicePlugDelay)
            if self.__ioDevice__.checkDeviceExists():
                e.add_note(self.__name__ + ": writer error")
                raise e from e
            else:
                self.__deviceRemoved__ = True
        return
