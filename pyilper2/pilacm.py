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
import sys
import os

from .serialio import SerialIOError, cls_serialIO
from .pilglobals import PILGLOBALS
from .pilcore import (
    cls_Interface_Spec,
    checkSerialDeviceExists,
    assemble_frame,
    disassemble_frame,
)

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets
from .iothread import IOThreadException, cls_IOThread


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
    #  send command to ACM device, check return value.
    #
    def __sendCmd__(self, cmdfrm, tmout):
        hbyt, lbyt = disassemble_frame(cmdfrm)
        self.write(lbyt, hbyt)
        bytrx = self.__tty__.rcv(tmout, 1)
        if bytrx is None:
            raise SerialIOError("Timeout")
            self.__tty__.close()
        try:
            tst = ord(bytrx)
        except (ValueError,TypeError):
            self.__tty__.close()
            raise SerialIOError("illegal return value for command")
        if tst != lbyt:
            print("pilacm: return value mismatch %x %x" % (tst,lbyt))
            self.__tty__.close()
            raise SerialIOError("illegal return value for command")
        print("pilacm: command sent and acknowledged 0x{0:02x}".format(cmdfrm))

    #
    # Send one or two bytes to the PIL-Box
    #
    def write(self, lbyt, hbyt=None):
        if hbyt is None:
            buf = bytearray([lbyt])
        else:
            buf = bytearray([hbyt, lbyt])
        try:
            self.__tty__.snd(buf)
        except SerialIOError as e:
            raise IOThreadException("pilacm: send frame error" + e.msg)

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
        except SerialIOError as e:
            raise IOThreadException("Cannot connect to ACM device: " + e.msg)

        #
        # Send disconnect
        #
        try:
            self.__sendCmd__(self.TDIS, PILGLOBALS.Tmout_Cmd)
        except SerialIOError as e:
            errmsg = e.msg
            raise IOThreadException("Cannot connect to ACM device: " + errmsg)
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
        try:
            frmrx = self.__tty__.rcv(PILGLOBALS.Tmout_Frm, 2)
        except SerialIOError as e:
            raise IOThreadException("ACM read frame error" + e.msg)
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
        except SerialIOError as e:
            raise IOThreadException("Cannot initialize PIL-Box" + e.msg)

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
                    except SerialIOError as e:
                        time.sleep(PILGLOBALS.SerialDevicePlugDelay)
                        if checkSerialDeviceExists(self.__ttydevice__):
                            print("pilacm reader error")
                            raise IOThreadException(e.msg)
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
        except IOThreadException as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print("pilacm: IOThreadException ", e.msg)
            print("pilacm: reader error exit")
            #
            # put error status and message to queue
            #
            self.__queue__.put([self.__id__, -1, e.msg])
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
        except SerialIOError as e:
            time.sleep(PILGLOBALS.SerialDevicePlugDelay)
            if checkSerialDeviceExists(self.__ttydevice__):
                print("pilacm writer error")
                raise IOThreadException(e.msg)
        return
