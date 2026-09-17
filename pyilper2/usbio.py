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
# usbio.py: class to access USB bulk endpoints of USB ACM devices.
#
# Note: the code to unbind and rebind the serial driver of the USB device
# is LINUX specific and will not work on Windows or macOS.
#

import usb.core
import usb.util
import time

from .pilglobals import PILGLOBALS
from .pilcore import cls_Interface_Spec, AppException


class cls_usbio:

    USB_BUFFER = usb.util.create_buffer(64)

    def __init__(self, vendor, product):
        self.__vendor__ = vendor
        self.__product__ = product
        self.__device__ = None
        self.__isOpen__ = False
        self.__timeout__ = 0
        self.__interfaceNumber__ = None
        self.__endpoint_in__ = None
        self.__endpoint_out__ = None

    #
    #  Open the ILUSB CDC VCP USB interface
    #
    def open(self):

        #     Find the USB device
        self.__device__ = usb.core.find(
            idVendor=self.__vendor__, idProduct=self.__product__
        )

        if self.__device__ is None:
            raise AppException("USB Device not found")

        #     Check if the device is a VCP (you might need to adapt this based on your specific device)
        if self.__device__.bDeviceClass == 0x02:  # CDC (Communications Device Class)
            print("Device is a VCP")
        else:
            raise AppException("USB Device is not a VCP")

        #
        #     Detach an active kernel driver. According to internet sources, the control interface must
        #     be used to detach the driver
        #
        self.__detached_interfaceNumber__ = 0
        for cfg in self.__device__:
            for config_index in range(cfg.bNumInterfaces):
                if self.__device__.is_kernel_driver_active(config_index):
                    self.__device__.detach_kernel_driver(config_index)
                    self.__detached_interfaceNumber__ = config_index
        self.__device__.set_configuration()

        #
        #     Set the first configuration (the device has only one)
        #
        cfg_desired = 1
        try:
            cfg = self.__device__.get_active_configuration()
        except usb.core.USBError:
            cfg = None
        if cfg is None or cfg.bConfigurationValue != cfg_desired:
            self.__device__.set_configuration(cfg_desired)

        self.__device__.reset()

        #
        #     Find VCP interface and its bulk IN and OUT endpoints
        #
        for intf in cfg.interfaces():
            for endpt in intf.endpoints():
                if (
                    usb.util.endpoint_type(endpt.bmAttributes)
                    == usb.util.ENDPOINT_TYPE_BULK
                ):
                    self.__interfaceNumber__ = intf.bInterfaceNumber
                    if (
                        usb.util.endpoint_direction(endpt.bEndpointAddress)
                        == usb.util.ENDPOINT_IN
                    ):
                        self.__endpoint_in__ = endpt
                        print("    Bulk endpoint  in found")
                    else:
                        self.__endpoint_out__ = endpt
                        print("    Bulk endpoint out found")

        if self.__endpoint_in__ is None or self.__endpoint_out__ is None:
            raise AppException("Could not find IN and OUT endpoints of USB device")
        return

    #
    #  close the PILUSB device and reattach kernel driver
    #
    def close(self):
        try:
            self.__device__.reset()
            usb.util.dispose_resources(self.__device__)
            usb.util.release_interface(self.__device__, self.__interfaceNumber__)
            self.__endpoint_in__ = None
            self.__endpoint_out__ = None
            self.__device__.attach_kernel_driver(self.__detached_interfaceNumber__)
            self.__isOpen__ = False
        except usb.core.USBError as e:
            e.add_note("Could not release interface (" + str(e.args[0]) + ")")
            raise e from e
        self.__device__ = ""
        time.sleep(0.5)
        print("usb device released")

    def send_data(self, data):
        self.__endpoint_out__.write(data)

    #
    #  receive data from IN endpoint with timeout
    #
    def receive_data(self, l, timeout=None):

        data = []
        while len(data) != l:
            try:
                n = self.__device__.read(
                    self.__endpoint_in__.bEndpointAddress,
                    self.USB_BUFFER,
                    timeout,
                )
            except usb.core.USBError as e:
                if e.args[0] == 110:
                    return None
                else:
                    e.add_note("Error receiving data")
                    raise e from e

            for i in range(0, n):
                data.append(self.USB_BUFFER[i])
        return data

    #
    # Read frame from ILUSB
    #
    def readFrame(self, tmout=None):
        ret = self.receive_data(2, tmout)
        if ret:
            return (ret[1] << 8) + ret[0]
        else:
            return None

    #
    # Write frame to PILUSB
    #
    def writeFrame(self, frame):
        buf = bytes(frame.to_bytes(2, "little"))
        self.send_data(buf)

    #
    #  Read byte from PIL-Box return as byte string!
    #
    def readByte(self, tmout=PILGLOBALS.Tmout_Frm):
        bytrx = self.receive_data(1, tmout)
        if bytrx is None:
            return b""
        else:
            return bytes(bytrx[0].to_bytes(1, "little"))

    #
    # Send one or two bytes to the PIL-Box
    #
    def writePilBoxFrame(self, lbyt, hbyt=None):
        if hbyt is None:
            buf = bytearray([lbyt])
        else:
            buf = bytearray([hbyt, lbyt])
        self.send_data(buf)

    def checkDeviceExists(self):
        return (
            usb.core.find(idVendor=self.__vendor__, idProduct=self.__product__)
            is not None
        )
