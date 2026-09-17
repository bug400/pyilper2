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
# pilsocket.py: pluggable interface code for an TCP/IP based HP-IL interface
# to DOSBOX instances running one of J.F. Garniers HP calculator emulators
#
#


import sys
import time
import threading
import queue
import signal
import os
import select
import socket

from .pilglobals import PILGLOBALS

from PySide6 import QtCore, QtGui, QtWidgets
from .pilconfig import PILCONFIG
from .pilcore import cls_Interface_Spec, AppException
from .iothread import cls_IOThread
from .pilinterface import cls_ConfigInterfaceGeneric


class cls_pilsocket(cls_IOThread):

    RET_TIMEOUT = -1

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

        self.port = PILCONFIG.get(self.__configName__, "serverport")
        self.outsocket = None
        self.inconnected = False

        self.serverlist = []
        self.clientlist = []
        #
        # This flag is used to tell the reader thread that an acknowledge byte is awaited
        #
        self.requestAcknowledgeLock = threading.Lock()
        self.requestAcknowledge = False

    def setRequestAcknowledge(self, value):
        self.requestAcknowledgeLock.acquire()
        self.requestAcknowledge = value
        self.requestAcknowledgeLock.release()

    def getRequestAcknowledge(self):
        self.requestAcknowledgeLock.acquire()
        value = self.requestAcknowledge
        self.requestAcknowledgeLock.release()
        return value

    #
    #  Connect to Network
    #
    def open(self):
        #
        #     open network connections
        #
        host = None
        self.serverlist.clear()
        self.clientlist.clear()
        for res in socket.getaddrinfo(
            host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE
        ):
            af, socktype, proto, canonname, sa = res
            try:
                s = socket.socket(af, socktype, proto)
            except OSError as msg:
                s = None
                continue
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(sa)
                s.listen(1)
                self.serverlist.append(s)
            except OSError as msg:
                s.close()
                continue
        if len(self.serverlist) == 0:
            raise AppException(self.__name__ + ": cannot bind to port")

    def isConnected(self):
        return self.inconnected

    #
    #  Disconnect from Network
    #
    def close(self):
        for s in self.clientlist:
            s.close()
        for s in self.serverlist:
            s.close()

    #
    #  Read HP-IL frame from PIL-Box (2 byte), handle connect to server socket
    #
    def read(self, timeout):

        readable, writable, errored = select.select(
            self.serverlist + self.clientlist, [], [], timeout
        )
        if readable == []:
            return self.RET_TIMEOUT
        for s in readable:
            if self.serverlist.count(s) > 0:
                cs, addr = s.accept()
                self.clientlist.append(cs)
                self.inconnected = True
                print(self.__name__ + ": inconnected true")
            else:
                bytrx = s.recv(1)
                if bytrx:
                    return bytrx
                else:
                    self.clientlist.remove(s)
                    s.close()
                    self.inconnected = False
                    print(self.__name__ + ": inconnected false")
        return None

    #
    # Write to socket
    #
    def write(self, lbyt, hbyt=None):
        # print(f"{self.name}: write {lbyt} {hbyt}")
        if self.inconnected == False:
            raise AppException("cannot send data to socket, no connection")
        if hbyt is None:
            buf = bytearray([lbyt])
        else:
            buf = bytearray([lbyt, hbyt])
        try:
            self.clientlist[0].sendall(buf)  ## correct ?
        except OSError as e:
            e.add_note(f"cannot send data to socket {e.strerror}")
            raise e from e

    #
    # TCP/IP frame writer, called by controlthread
    #
    def writer(self, frame):
        #
        # disassemble answer frame
        #
        hbyt, lbyt = self.disassemble_frame(frame)

        if hbyt != self.__lasth__:
            #
            # send high part if different from last one
            #
            self.__lasth__ = hbyt
            self.write(hbyt)
            #
            # read acknowledge (note: this clashes with the tread job!), so set flag for the reader thread
            #
            self.setRequestAcknowledge(True)
            """
            b = self.read(PILGLOBALS.Com_Tmout_Ack)
            if b is None:
                raise AppException("cannot get acknowledge: timeout")
            if ord(b) != 0x0D:
                raise AppException("cannot get acknowledge: unexpected value")
            """
        #
        #        otherwise send only low part
        #
        self.write(lbyt)

    #
    #  Socket reader thread
    #
    def reader(self):

        self.setStatus(self.STAT_CONNECTING)
        self.__lasth__ = 0
        try:
            #
            # open server port
            #
            self.open()
            connected = False
            print(self.__name__ + ": reader thread started")

            #
            # read frame from Network
            #
            while True:
                result = self.read(1.0)
                if self.__stopEvent__.is_set():
                    break
                if result == self.RET_TIMEOUT:
                    continue
                if self.isConnected():
                    if not connected:
                        connected = True
                        self.setStatus(self.STAT_CONNECTED)
                        print(self.__name__ + ": connected to client")
                else:
                    if connected:
                        connected = False
                        self.setStatus(self.STAT_CONNECTING)
                        print(self.__name__ + ": not connected to client")

                # print(self.__name__+": main read result ", result)
                if result is None:
                    continue

                byt = ord(result)
                if self.getRequestAcknowledge():
                    self.setRequestAcknowledge(False)
                    if byt != 0x0D:
                        raise AppException(
                            f"cannot get acknowledge, unexpected value {byt}"
                        )
                #
                # is not a low byte
                #
                if (byt & 0xC0) == 0x00:
                    #
                    # check for high byte, else ignore
                    #
                    if (byt & 0x20) != 0:
                        #
                        # got high byte, save it and continue
                        #
                        self.__lasth__ = byt & 0xFF
                    continue
                #
                # low byte, assemble frame according to 7- oder 8 bit format
                #
                frame = self.assemble_frame(self.__lasth__, byt)
                # print(f"{self.__name__} frame {frame}")
                #
                # send acknowledge if we received a pil box command
                #
                if frame & 0x7F4 == 0x494:
                    #
                    # send only original low byte as acknowledge, we can write here because we are in the thread job
                    #
                    lbyt = byt
                    self.write(byt)
                else:
                    self.__queue__.put([self.__id__, frame])
            #
            #     normal termination
            #
            print(self.__name__ + ": reader normal exit")

            self.close()
        #
        # error exit
        #
        except ExceptionGroup as e:
            #
            # put error status and message to queue
            #
            self.__queue__.put([self.__id__, self.MSG_ERROR, e])
            print(self.__name__, ": reader error exit")
        finally:
            self.setStatus(self.STAT_DISCONNECTED)
        return


class cls_pilsocket_config(cls_ConfigInterfaceGeneric):

    def __init__(self, parent, name, id, interfacespecifications):

        super().__init__(parent, name, id, interfacespecifications)

        self.port = PILCONFIG.get(self.configName, "serverport", 59999)

        self.intvalidator = QtGui.QIntValidator()
        self.glayout = QtWidgets.QGridLayout()
        self.lbltxt3 = QtWidgets.QLabel("Port:")
        self.glayout.addWidget(self.lbltxt3, 0, 0)
        self.edtPort = QtWidgets.QLineEdit()
        self.glayout.addWidget(self.edtPort, 0, 1)
        self.edtPort.setText(str(self.port))
        self.edtPort.setValidator(self.intvalidator)
        self.vb.addLayout(self.glayout)

        self.edtPort.editingFinished.connect(self.do_storePort)

    def setActive(self, flag):
        self.edtPort.setEnabled(flag)
        self.radBut.setChecked(flag)

    def do_storePort(self):
        PILCONFIG.put(self.configName, "serverport", int(self.edtPort.text()))


def pilsocket_spec():
    return [
        cls_Interface_Spec(
            PILGLOBALS.Interface_Socket,
            "if_socket",
            cls_pilsocket,
            "reader",
            "writer",
            cls_pilsocket_config,
            "Socket",
        )
    ]
