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
# TCP/IP i/o thread object class  ---------------------------------------------
#
#
# Changelog
#
# XX.XX.2026 jsi
# - code taken from pyILPER 1.9 and modified for pyILPER 2.0


import sys
import time
import threading
import queue
import signal
import os
import select
import socket


from .pilglobals import PILGLOBALS

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets

from .iothread import IOThreadException, cls_IOThread


class cls_piltcpip(cls_IOThread):

    RET_TIMEOUT = -1

    def __init__(self, stopEvent, queue, id, params):
        super().__init__(stopEvent, queue, id)

        self.port = params[0]
        self.remotehost = params[1]
        self.remoteport = params[2]
        self.outsocket = None
        self.outconnected = False
        self.inconnected = False

        self.serverlist = []
        self.clientlist = []

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
            raise IOThreadError("cannot bind to port")

    def openclient(self):
        #
        #     connect to remote host
        #
        self.outsocket = None
        self.outconnected = False
        for res in socket.getaddrinfo(
            self.remotehost, self.remoteport, socket.AF_UNSPEC, socket.SOCK_STREAM
        ):
            af, socktype, proto, canonname, sa = res
            try:
                self.outsocket = socket.socket(af, socktype, proto)
            except OSError as msg:
                self.outsocket = None
                continue
            try:
                self.outsocket.connect(sa)
                self.outconnected = True
            except OSError as msg:
                self.outsocket.close()
                self.outsocket = None
                continue
            break
        return self.outconnected

    def isConnected(self):
        return self.outconnected and self.inconnected

    #
    #  Disconnect from Network
    #
    def close(self):
        for s in self.clientlist:
            s.close()
        for s in self.serverlist:
            s.close()
        if self.outconnected:
            self.outsocket.shutdown(socket.SHUT_WR)
            self.outsocket.close()
            self.outsocket = None
            self.outconnected = False

    #
    # Close output socket
    #
    def close_outsocket(self):
        if self.outconnected:
            self.outsocket.shutdown(socket.SHUT_WR)
            self.outsocket.close()
            self.outsocket = None
            self.outconnected = False

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
                print("tcpip: inconnected true")
            else:
                bytrx = s.recv(2)
                print("tcpip: bytrx ", bytrx)
                if bytrx:
                    return socket.ntohs((bytrx[1] << 8) | bytrx[0])
                else:
                    self.clientlist.remove(s)
                    s.close()
                    self.inconnected = False
                    print("tcpip: inconnected false")
        return None

    #
    # TCP/IP frame writer
    #
    def writer(self, frame):
        bRetry = True
        b = bytearray(2)
        f = socket.htons(frame)
        b[0] = f & 0xFF
        b[1] = f >> 8
        while bRetry:
            if self.isConnected():
                try:
                    self.outsocket.send(b)
                    break
                except ConnectionError:
                    self.outsocket.shutdown(socket.SHUT_WR)
                    self.outsocket.close()
                    self.outsocket = None
                    self.outconnected = False
            else:
                bRetry = self.openclient()

    #
    #  TCP/IP reader thread
    #
    def reader(self):

        self.setStatus(self.STAT_CONNECTING)
        try:
            #
            # open server port
            #
            self.open()
            connected = False
            print("tcpip: reader thread started")

            #
            # read frame from Network
            #
            while True:
                result = self.read(1.0)
                if self.__stopEvent__.is_set():
                    break
                if result == cls_piltcpip.RET_TIMEOUT:
                    continue
                if self.isConnected():
                    if not connected:
                        connected = True
                        self.setStatus(self.STAT_CONNECTED)
                        print("tcpip: connected to virtual HP-IL devices")
                else:
                    if connected:
                        connected = False
                        self.close_outsocket()
                        self.setStatus(self.STAT_CONNECTING)
                        print("tcpip: not connected to virtual HP-IL devices")

                print("tcpip: main read result ", result)
                if result is None:
                    continue
                self.__queue__.put([self.__id__, result])
            #
            #     normal termination
            #
            print("tcpip: reader normal exit")
            
            self.close()
        #
        # error exit
        #
        except IOThreadException as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print("tcpip: IOThreadException ", e.msg)
            print("tcpip: reader error exit")
            #
            #        put error status and message to queue
            #
            self.__queue__.put([self.__id__, -1, e.msg])
            
        finally:
            self.setStatus(self.STAT_DISCONNECTED)
        return
        
