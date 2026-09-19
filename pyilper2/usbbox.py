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
# usbbox.py: pluggable interface code for a USB to HP-IL converter
# implemented using a microcontroller that includes a USB interface.
# Frames are transferred as 16 bit values which makes the conversion
# fully transparent. There is a speed increase of about 10% compared
# to using the PIL-Box protocol
#
# The PIL-Box protocol is only used to send commands to the box which
# only implements the TDIS and the custom PASSTHRU mode.
#
# On the PC side, the bulk endpoints are accessed directly via the
# libusb. This results in additional 10% speed increase compared to
# the acmbox.py implementation.
#

import usb.core
import usb.util
import time

from .pilglobals import PILGLOBALS

from PySide6 import QtCore, QtGui, QtWidgets
from .pilconfig import PILCONFIG
from .iothread import cls_IOThread
from .usbio import cls_usbio
from .pilcore import cls_Interface_Spec
from .pilinterface import cls_ConfigInterfaceGeneric


class cls_usbbox(cls_IOThread):

    USB_BUFFER = usb.util.create_buffer(64)

    def __init__(
        self,
        parent,
        stopEvent,
        queue,
        interfaceIndex,
        interfaceConfigName,
        interfaceName,
    ):

        super().__init__(
            parent,
            stopEvent,
            queue,
            interfaceIndex,
            interfaceConfigName,
            interfaceName,
        )
        usbdevice = PILCONFIG.get(self.__configName__, "usbdevice")
        temp = usbdevice.split(":")
        self.__vendor__ = int(temp[0], 16)
        self.__product__ = int(temp[1], 16)
        self.__ioDevice__ = cls_usbio(self.__vendor__, self.__product__)
        self.__isOpen__ = False
        self.__timeout__ = 0

    def isOpen(self):
        return self.__isOpen__

    #
    #  Open the ILUSB CDC VCP USB interface
    #
    def open(self):

        #
        #     Open USB device and send TDIS
        #
        try:
            self.__ioDevice__.open()
        except Exception as e:
            e.add_note(self.__name__ + ": cannot connect to USB device")
            raise e from e
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_TDIS, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot connect to USB device")
            raise e from e
        return

    #
    #  close the PILUSB device and reattach kernel driver
    #
    def close(self):
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_TDIS, PILGLOBALS.Tmout_Cmd)
            self.__ioDevice__.close()
        except Exception:
            pass

    #
    #  Init Box, send  PASSTHRU
    #
    def initBox(self):
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_PASSTHRU, PILGLOBALS.Tmout_Cmd)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot initialize USB-Box")
            raise e from e

    #
    #  USB-Box reader thread
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
                    # print(self.__name__+": read frame %x" % frame)
                    #
                    # put frame to queue
                    #
                    for processMethod in self.__deviceProcessors__:
                        frame = processMethod(frame)
                    #
                    # write to the next interface
                    #
                    self.__writer__(frame)

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
            self.__queue__.put([self.__id__, self.MSG_ERROR, e])
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

        # print(self.__name__+": writer sends frame")

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


class cls_USB_validator(QtGui.QValidator):

    def validate(self, string, pos):
        self.regexp = QtCore.QRegularExpression("[A-Fa-f0-9:]*")
        self.validator = QtGui.QRegularExpressionValidator(self.regexp)
        result = self.validator.validate(string, pos)
        return result[0], result[1], result[2]


class cls_usbbox_config(cls_ConfigInterfaceGeneric):

    def __init__(self, parent, name, id, interfaceSpecifications):
        super().__init__(parent, name, id, interfaceSpecifications)

        self.usbDevice = PILCONFIG.get(self.configName, "usbdevice", "0483:5740")

        self.hbox = QtWidgets.QHBoxLayout()
        self.lbl = QtWidgets.QLabel("USB Device: ")
        self.hbox.addWidget(self.lbl)
        self.ledtUSBDevice = QtWidgets.QLineEdit()
        self.ledtUSBDevice.setText(self.usbDevice)
        self.ledtUSBDevice.textChanged.connect(self.do_edit_done)
        self.validator = cls_USB_validator()
        self.ledtUSBDevice.setValidator(self.validator)
        self.hbox.addWidget(self.ledtUSBDevice)
        self.hbox.addStretch(1)
        self.vb.addLayout(self.hbox)

    def do_edit_done(self):
        self.usbDevice = self.ledtUSBDevice.text()
        PILCONFIG.put(self.configName, "usbdevice", self.usbDevice)

    def setActive(self, flag):
        self.radBut.setChecked(flag)
        self.ledtUSBDevice.setEnabled(flag)


def usbbox_spec():
    return [
        cls_Interface_Spec(
            PILGLOBALS.Interface_UsbBox,
            "if_usbbox",
            cls_usbbox,
            "reader",
            "writer",
            cls_usbbox_config,
            "USB-Box",
        )
    ]
