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
# XX.XX.XXXX jsi


import time

from .pilglobals import PILGLOBALS

from PySide6 import QtCore, QtGui, QtWidgets
from .serialio import cls_serialIO
from .pilcore import cls_Interface_Spec, AppException
from .pilconfig import PILCONFIG
from .iothread import cls_IOThread
from .pilinterface import cls_ConfigInterfaceGeneric, cls_TtyWindow


class cls_pilbox(cls_IOThread):

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
        self.__ttyDevice__ = PILCONFIG.get(self.__configName__, "device")
        self.__baudrate__ = PILCONFIG.get(self.__configName__, "baudrate")
        self.__idyframe__ = PILCONFIG.get(self.__configName__, "idyframes")
        self.__isController__ = PILCONFIG.get(self.__configName__, "controllermode")
        self.__ioDevice__ = cls_serialIO(self.__ttyDevice__)  # serial device object
        self.__lasth__ = 0
        if self.__isController__:
            print(self.__name__ + ": controller on mode")
        else:
            print(self.__name__ + ": controller off mode")

    #
    #  get connection speed
    #
    def getBaudRate(self):
        return self.__baudrate__

    #
    #  Open PIL-Box device, check baudrates if not specified and issue a TDIS
    #
    def open(self):

        cmd = PILGLOBALS.Pilbox_Command_TDIS
        msg = ""
        #
        #     open serial device, no autobaud mode
        #
        if self.__baudrate__ > 0:
            try:
                self.__ioDevice__.open(self.__baudrate__)
                self.sendCmd(cmd, PILGLOBALS.Tmout_Frm)
            except Exception as e:
                e.add_note(self.__name__ + ": cannot connect to PIL-Box")
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
                        self.__ioDevice__.open(baudrate)
                    else:
                        self.__ioDevice__.flushInput()
                        self.__ioDevice__.setBaudrate(baudrate)
                except Exception as e:
                    e.add_note(self.__name__ + ": cannot connect to PIL-Box")
                    raise e from e
                try:
                    self.sendCmd(cmd, PILGLOBALS.Tmout_Frm)
                    self.__baudrate__ = baudrate
                    break
                except Exception as e:
                    pass

        print(self.__name__ + ": connected at ", self.__baudrate__, "baud")
        if self.__baudrate__ == 0:
            self.__ioDevice__.close()
            raise AppException(
                self.__name__ + ": cannot connect to PIL-Box: baudrate mismatch"
            )

    #
    #  Disconnect PIL-Box, issue a TDIS
    #
    def close(self):
        try:
            self.sendCmd(PILGLOBALS.Pilbox_Command_TDIS, PILGLOBALS.Tmout_Frm)
        except:
            pass
        self.__ioDevice__.close()

    #
    #  Init Box, send either CON, COFI or COFF
    #
    def initBox(self):
        if self.__isController__:
            cmd = PILGLOBALS.Pilbox_Command_CON
        else:
            if self.__idyframe__:
                cmd = PILGLOBALS.Pilbox_Command_COFI
            else:
                cmd = PILGLOBALS.Pilbox_Command_COFF
        try:
            self.sendCmd(cmd, PILGLOBALS.Tmout_Frm)
        except Exception as e:
            e.add_note(self.__name__ + ": cannot initialize PIL-Box")
            raise e from e

    #
    #  PIL-Box reader thread
    #
    def reader(self):

        self.setStatus(self.STAT_CONNECTING)
        self.__lasth__ = 0
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
                        print(self.__name__ + " reconnecting device")
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
                    # read byte from PIL-Box. On error wait and check if device was unplugged
                    #
                    try:
                        ret = self.__ioDevice__.readByte()
                    except Exception as e:
                        time.sleep(PILGLOBALS.SerialDevicePlugDelay)
                        if self.__ioDevice__.checkDeviceExists():
                            e.add_note(self.__name__ + " reader error")
                            raise e from e
                        self.__deviceRemoved__ = True
                        self.setStatus(self.STAT_CONNECTING)
                        self.__lasth__ = 0
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
                                self.__ioDevice__.boxWrite(0x0D)
                        continue
                    #
                    # low byte, build frame
                    #
                    result = self.assemble_frame(self.__lasth__, byt)
                    # print(self.__name__+": main read result ", result)
                    #
                    # put frame to queue
                    #
                    self.__queue__.put([self.__id__, result])
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
        #     if we are not connected, do not output frame
        #
        if self.getStatus() != self.STAT_CONNECTED:
            self.__lasth__ = 0
            return

        #
        # disassemble into low and high byte
        #
        # print(self.__name__+": writer sends frame")
        hbyt, lbyt = self.disassemble_frame(frame)

        try:
            if hbyt != self.__lasth__:
                #
                # send high part if different from last one and low part
                #
                self.__lasth__ = hbyt
                self.__ioDevice__.writePilBoxFrame(lbyt, hbyt)
            else:
                #
                # otherwise send only low part
                #
                self.__ioDevice__.writePilBoxFrame(lbyt)
        #
        # Error handling
        #
        except Exception as e:
            time.sleep(PILGLOBALS.SerialDevicePlugDelay)
            if self.__ioDevice__.checkDeviceExists():
                e.add_note(self.__name__ + " write error")
                raise e from e
            else:
                self.__deviceRemoved__ = True
                self.__lasth__ = 0
        return


class cls_pilboxConfig(cls_ConfigInterfaceGeneric):

    def __init__(self, parent, name, id, interfaceSpecifications):

        super().__init__(parent, name, id, interfaceSpecifications)
        self.tty = PILCONFIG.get(self.configName, "device", "")
        self.ttyspeed = PILCONFIG.get(self.configName, "baudrate", 0)
        self.idyframe = PILCONFIG.get(self.configName, "idyframe", True)
        self.controllermode = PILCONFIG.get(self.configName, "controllermode", 0)

        #
        #     serial device
        #
        self.hboxtty = QtWidgets.QHBoxLayout()
        self.lbltxt1 = QtWidgets.QLabel("Serial Device: ")
        self.hboxtty.addWidget(self.lbltxt1)
        self.lblTty = QtWidgets.QLabel()
        self.lblTty.setText(self.tty)
        self.hboxtty.addWidget(self.lblTty)
        self.hboxtty.addStretch(1)
        self.butTty = QtWidgets.QPushButton()
        self.butTty.setText("change")
        self.butTty.pressed.connect(self.do_config_interface)
        self.hboxtty.addWidget(self.butTty)
        self.vb.addLayout(self.hboxtty)
        #
        #     tty speed combo box
        #
        self.hboxbaud = QtWidgets.QHBoxLayout()
        self.lbltxt2 = QtWidgets.QLabel("Baud rate ")
        self.hboxbaud.addWidget(self.lbltxt2)
        self.comboBaud = QtWidgets.QComboBox()
        i = 0
        for baud in PILGLOBALS.Baudrates:
            self.comboBaud.addItem(baud[0])
            if self.ttyspeed == baud[1]:
                self.comboBaud.setCurrentIndex(i)
            i += 1

        self.hboxbaud.addWidget(self.comboBaud)
        self.hboxbaud.addStretch(1)
        self.vb.addLayout(self.hboxbaud)

        #
        #     idy frames
        #
        self.cbIdyFrame = QtWidgets.QCheckBox("Enable IDY frames")
        self.cbIdyFrame.setChecked(self.idyframe)
        self.cbIdyFrame.setEnabled(True)
        self.cbIdyFrame.stateChanged.connect(self.do_cbIdyFrame)
        self.vb.addWidget(self.cbIdyFrame)

    def do_cbIdyFrame(self):
        self.idyframe = self.cbIdyFrame.isChecked()
        PILCONFIG.put(self.configName, "idyframe", self.idyframe)

    def do_config_interface(self):
        interface = cls_TtyWindow.getTtyDevice(self.tty)
        if interface == "":
            return
        self.tty = interface
        self.lblTty.setText(self.tty)
        PILCONFIG.put(self.configName, "device", self.tty)
        PILCONFIG.put(
            self.configName,
            "baudrate",
            PILGLOBALS.Baudrates[self.comboBaud.currentIndex()][1],
        )

    def setActive(self, flag):
        self.butTty.setEnabled(flag)
        self.cbIdyFrame.setEnabled(flag)
        self.comboBaud.setEnabled(flag)
        self.radBut.setChecked(flag)


def pilbox_spec():
    return [
        cls_Interface_Spec(
            PILGLOBALS.Interface_PilBox,
            "if_pilbox",
            cls_pilbox,
            "reader",
            "writer",
            cls_pilboxConfig,
            "PIL-Box",
        )
    ]
