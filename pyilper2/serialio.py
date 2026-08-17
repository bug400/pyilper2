#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pyILPER 1.2.1 for Linux
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
# serial device object class --------------------------------------------
#
# Changelog
#
# XX.XX.XXXX jsi
# - derived from pilrs232
#
import serial, time
from .pilglobals import PILGLOBALS


class cls_serialIO:

    def __init__(self, device):
        #
        #     use Windows device naming (hint by cg)
        #
        self.__device__ = device
        """TODO: check: DO WE NEED THIS
        if PILGLOBALS.isWindows:
            self.__device__ = "\\\\.\\" + device
        else:
            self.__device__ = device
        """
        self.__isOpen__ = False
        self.__timeout__ = 0

    #
    #  Windows needs much time to reconfigure the timeout value of the serial
    #  device, so alter the device settings only if necessary. Give the device
    #  some time to settle.
    #
    def __settimeout__(self, timeout):
        if timeout != self.__timeout__:
            try:
                self.__ser__.timeout = timeout
            except Exception as e:
                self.close()
                e.add_note("cannot set timeout value of serial device")
                raise e from e
            self.__timeout__ = timeout

    def isOpen(self):
        return self.__isOpen__

    def open(self, baudrate):
        try:
            self.__ser__ = serial.Serial(
                port=self.__device__, baudrate=baudrate, timeout=0.10
            )
            self.__isOpen__ = True
            time.sleep(0.5)
        except Exception as e:
            self.__ser__ = None
            e.add_note("cannot open serial device")
            raise e from e

    #
    #  close serial device
    #
    def close(self):
        if not self.__isOpen__:
            return
        try:
            self.__ser__.close()
            self.__ser__ = None
            self.__isOpen__ = False
        except:
            pass

    def snd(self, buf):
        try:
            self.__ser__.write(buf)
        except Exception as e:
            self.close()
            e.add_note("cannot write to serial device")
            raise e from e

    def rcv(self, timeout, n):
        self.__settimeout__(timeout)
        try:
            c = self.__ser__.read(n)
        except Exception as e:
            self.close()
            e.add_note("cannot read from serial device")
            raise e from e
        return c

    def flushInput(self):
        try:
            self.__ser__.flushInput()
        except Exception as e:
            self.close()
            e.add_note("cannot reset serial device")
            raise e from e

    def setBaudrate(self, baudrate):
        try:
            self.__ser__.baudrate = baudrate
        except Exception as e:
            self.close()
            e.add_note("cannot read from serial device")
            raise e from e

    #
    #  Read byte from Box
    #
    def readByte(self, tmout=PILGLOBALS.Tmout_Frm):
        bytrx = self.rcv(tmout, 1)
        return bytrx

    #
    # Send frame to Box in PIL-Box protocol
    #
    def writePilBoxFrame(self, lbyt, hbyt=None):
        if hbyt is None:
            buf = bytearray([lbyt])
        else:
            buf = bytearray([hbyt, lbyt])
        self.snd(buf)

    #
    # Read frame from ACM device
    #
    def readFrame(self):
        frmrx = self.rcv(PILGLOBALS.Tmout_Frm, 2)
        if frmrx != b"":
            return int.from_bytes(frmrx, "little")
        else:
            return None

    #
    # Write frame to ACM device
    #
    def writeFrame(self, frame):
        buf = bytes(frame.to_bytes(2, "little"))
        self.snd(buf)

    #
    # check if serial device exists
    #
    #
    #
    #  check existence of a serial device
    #
    def checkDeviceExists(self):
        if PILGLOBALS.Diagnostics:
            print("check for ", self.__device__)
            for p in serial.tools.list_ports.comports():
                print(
                    "Device found: ",
                    p.device,
                    " ",
                    p.description,
                    " ",
                    p.manufacturer,
                    " ",
                    p.product,
                    " ",
                    p.location,
                    " ",
                    p.interface,
                )
        for p in serial.tools.list_ports.grep(self.__device__):
            if p.device == self.__device__:
                return True
        return False
