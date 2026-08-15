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
from .pilcore import (
    cls_Interface_Spec,
    checkSerialDeviceExists,
)

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets
from .iothread import cls_IOThread


class cls_pilacm(cls_IOThread):

    #
    # pilacm device Commands
    #
    TDIS = 0x494  # disconnect
    PASSTHRU = 0x49C  # passthru

    def __init__(self, stopEvent, queue, id, params):
        super().__init__(stopEvent, queue, id)
        self.__tty__ = cls_serialIO()  # acm device object
        self.__ttydevice__ = params[0]  # acm device name
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
            self.__tty__.open(self.__ttydevice__, self.__baudrate__)
        except Exception as e:
            e.add_note("Cannot connect to ACM device") 
            raise e from e

        #
        # Send disconnect
        #
        try:
            self.__sendCmd__(self.TDIS, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note("Cannot connect to ACM device")
            raise e from e
        return

    #
    #  Disconnect ACM device
    #
    def close(self):
        try:
            self.__sendCmd__(self.TDIS, PILGLOBALS.Tmout_Cmd)
            pass
        finally:
            self.__tty__.close()

    #
    # Read frame from ACM device
    #
    def readFrame(self):
        frmrx = self.__tty__.rcv(PILGLOBALS.Tmout_Frm, 2)
        if frmrx != b"":
            return int.from_bytes(frmrx, "little")
        else:
            return None

    #
    # Write frame to ACM device
    #
    def writeFrame(self, frame):
        buf = bytes(frame.to_bytes(2, "little"))
        self.__tty__.snd(buf)

    #
    #  Init Box, send  PASSTHRU
    #
    def initBox(self):
        try:
            self.__sendCmd__(self.PASSTHRU, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note("Cannot initialize PIL-Box")
            raise e from e

    #
    #  PIL-Box reader thread
    #
    def reader(self):

        deviceRemoved = True
        self.setStatus(self.STAT_CONNECTING)
        print("pilacm: reader thread started")
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
                if deviceRemoved:
                    deviceExists = checkSerialDeviceExists(self.__ttydevice__)
                    if not deviceExists:
                        time.sleep(PILGLOBALS.AutoreconnectInterval)
                        continue
                    else:
                        print("pilacm reconnecting device")
                        time.sleep(PILGLOBALS.AutoreconnectInterval)
                        deviceRemoved = False
                #
                # open device
                #
                self.open()
                #
                # init PIL-Box mode
                #
                self.initBox()
                print("pilacm: open/init passed")
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
                        frame = self.readFrame()
                    except Exception as e:
                        time.sleep(PILGLOBALS.SerialDevicePlugDelay)
                        if checkSerialDeviceExists(self.__ttydevice__):
                            e.add_note("pilacm reader error")
                            raise e from e
                        deviceRemoved = True
                        self.setStatus(self.STAT_CONNECTING)
                        break
                    #
                    # Timeout
                    #
                    if frame is None:
                        continue
#                   print("pilacm read frame %x" % frame)
                    self.__queue__.put([self.__id__, frame])
            #
            # normal termination
            #

            if self.getStatus() == self.STAT_CONNECTED:
                self.close()
            print("pilacm: reader normal exit")
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

#       print("pilacm: writer sends frame")

        try:
            self.writeFrame(frame)
        #
        # Error handling
        #
        except Exception as e:
            time.sleep(PILGLOBALS.SerialDevicePlugDelay)
            if checkSerialDeviceExists(self.__ttydevice__):
                e.add_note("pilacm writer error")
                raise e from e
        return
