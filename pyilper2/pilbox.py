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
# PIL-Box i/o thread object class  ---------------------------------------------
#
# Changelog
#
# XX.XX.2026 jsi
# - code taken from pyILPER 1.9 and modified for pyILPER 2.0


import time
import threading
from .pilglobals import PILGLOBALS

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets
from .serialio import cls_serialIO
from .pilcore import (
    cls_Interface_Spec,
    checkSerialDeviceExists,
    AppException,
)
from .iothread import cls_IOThread


class cls_pilbox(cls_IOThread):

    #
    # PIL-Box Commands
    #
    TDIS = 0x494  # disconnect
    COFF = 0x497  # initialize in controller off mode
    COFI = 0x495  # initialize in controlle off mode and send/receive IDY frames
    CON = 0x496  # initialize in controller on mode

    def __init__(self, stopEvent, queue, id, params):

        super().__init__(stopEvent, queue, id)
        self.__ttydevice__ = params[0]  # serial port name
        self.__baudrate__ = params[1]  # baudrate of connection or 0 for autodetect
        self.__idyframe__ = params[2]  # enable idy frames
        self.__isController__ = params[3]  # PIL-Box Controller mode
        self.__tty__ = cls_serialIO()  # serial device object
        self.__lasth__ = 0
        if self.__isController__:
            print("pilbox: controller on mode")
        else:
            print("pilbox: controller off mode")

    #
    #  get connection speed
    #
    def getBaudRate(self):
        return self.__baudrate__

    #
    #  Open PIL-Box device, check baudrates if not specified and issue a TDIS
    #
    def open(self):

        cmd = self.TDIS
        msg = ""
        #
        #     open serial device, no autobaud mode
        #
        if self.__baudrate__ > 0:
            try:
                self.__tty__.open(self.__ttydevice__, self.__baudrate__)
                self.__sendCmd__(cmd, PILGLOBALS.Tmout_Frm)
            except Exception as e:
                e.add_note("Cannot connect to PIL-Box")
                raise e from e
        else:
            #
            # open serial device, detect baud rate, use predefined baudrates in
            # PILGLOBALS.Baudrates list in reverse order
            #
            errmsg = ""
            for i, b in reversed(list(enumerate(PILGLOBALS.Baudrates))):
                baudrate = b[1]
                if baudrate == 0:
                    break
                try:
                    if i == len(PILGLOBALS.Baudrates) - 1:
                        self.__tty__.open(self.__ttydevice__, baudrate)
                    else:
                        self.__tty__.flushInput()
                        self.__tty__.setBaudrate(baudrate)
                except Exception as e:
                    e.add_note("Cannot connect to PIL-Box")
                    raise e from e
                try:
                    self.__sendCmd__(cmd, PILGLOBALS.Tmout_Frm)
                    self.__baudrate__ = baudrate
                    break
                except Exception as e:
                    pass

        print("pilbox: connected at ", self.__baudrate__, "baud")
        if self.__baudrate__ == 0:
            self.__tty__.close()
            raise AppException("Cannot connect to PIL-Box: baudrate mismatch")

    #
    #  Disconnect PIL-Box, issue a TDIS
    #
    def close(self):
        try:
            self.__sendCmd__(self.TDIS, PILGLOBALS.Tmout_Frm)
        except:
            pass
        self.__tty__.close()

    #
    #  Init Box, send either CON, COFI or COFF
    #
    def initBox(self):
        if self.__isController__:
            cmd = self.CON
        else:
            if self.__idyframe__:
                cmd = self.COFI
            else:
                cmd = self.COFF
        try:
            self.__sendCmd__(cmd, PILGLOBALS.Tmout_Frm)
        except Exception as e:
            e.add_note("Cannot initialize PIL-Box")
            raise e from e

    #
    #  PIL-Box reader thread
    #
    def reader(self):

        deviceRemoved = True
        self.setStatus(self.STAT_CONNECTING)
        self.__lasth__ = 0
        print("pilbox: reader thread started")
        try:
            #
            # outer auto reconnect loop
            #

            while True:
                #
                #           exit if stop event
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
                        print("pilbox reconnecting device")
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
                print("pilbox: open/init passed")
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
                    # read byte from PIL-Box. On error wait and check if device was unplugged
                    #
                    try:
                        ret = self.readByte()
                    except Exception as e:
                        time.sleep(PILGLOBALS.SerialDevicePlugDelay)
                        if checkSerialDeviceExists(self.__ttydevice__):
                            e.add_note("pilbox reader error")
                            raise e from e
                        deviceRemoved = True
                        self.setStatus(self.STAT_CONNECTING)
                        break
                    #
                    # Timeout
                    #
                    if ret == b"":
                        continue
                    byt = ord(ret)
                    #
                    # process byte read from the PIL-Box, is not a low byte
                    #
                    if (byt & 0xC0) == 0x00:
                        #
                        # check for high byte, else ignore
                        #
                        if (byt & 0x20) != 0:
                            #
                            # got high byte, save it
                            #
                            self.__lasth__ = byt & 0xFF
                            #
                            # send acknowledge only at 9600 baud connection
                            #
                            if self.__baudrate__ == 9600:
                                self.boxWrite(0x0D)
                        continue
                    #
                    # low byte, build frame
                    #
                    result = self.assemble_frame(self.__lasth__, byt)
                    #                   print("pilbox: main read result ", result)
                    if result is None:
                        continue
                    self.__queue__.put([self.__id__, result])
            #
            # normal termination
            #

            if self.getStatus() == self.STAT_CONNECTED:
                self.close()
            print("pilbox: reader normal exit")
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
        #     if we are not connected, do not output frame
        #
        if self.getStatus() != self.STAT_CONNECTED:
            self.__lasth__ = 0
            return

        #
        # disassemble into low and high byte
        #
        #       print("pilbox: writer sends frame")
        hbyt, lbyt = self.disassemble_frame(frame)

        try:
            if hbyt != self.__lasth__:
                #
                # send high part if different from last one and low part
                #
                self.__lasth__ = hbyt
                self.writeOneOrTwoBytes(lbyt, hbyt)
            else:
                #
                # otherwise send only low part
                #
                self.writeOneOrTwoBytes(lbyt)
        #
        # Error handling
        #
        except Exception as e:
            time.sleep(PILGLOBALS.SerialDevicePlugDelay)
            if checkSerialDeviceExists(self.__ttydevice__):
                e.add_note("pilbox write error")
                raise e from e
            else:
                self.__lasth__ = 0
        return
