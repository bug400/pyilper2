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
# controller object class  ---------------------------------------------

import sys
import time
import threading
import queue
import os
import traceback
from dataclasses import dataclass
from .pilglobals import PILGLOBALS

if PILGLOBALS.QT_Bindings == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets
if PILGLOBALS.QT_Bindings == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets

from .iothread import cls_IOThread


@dataclass
class controllerItem:
    id: int
    interfaceClass: object
    interfaceName: str
    isDisabled: bool
    interfaceParams: list[int | str]
    nextId: int
    status: int
    commObject: object
    readerThread: object
    writer: object
    devices: list[int]


class cls_controller(threading.Thread):

    STAT_RUN = 0
    STAT_PAUSE = 1
    STAT_STOP = 2

    CMD_PAUSE = -1
    CMD_RESUME = -2
    CMD_STOP = -3

    def __init__(self, sig_UpdateStatus, sig_ControllerTerminated, controllerItems):
        super().__init__()
        self.queue = queue.SimpleQueue()
        self.stopEvent = threading.Event()
        self.sig_UpdateStatus = sig_UpdateStatus
        self.sig_ControllerTerminated = sig_ControllerTerminated
        self.controllerItems = controllerItems

        #
        #     Create interface objects, set initial interface status, populate nextId
        #
        for i, item in enumerate(self.controllerItems):
            if i == len(self.controllerItems) - 1:
                item.nextId = self.controllerItems[0].id
            else:
                item.nextId = self.controllerItems[i + 1].id
            if item.isDisabled:
                item.status = cls_IOThread.STAT_DISABLED
                item.commobject = None
                item.write = None
            else:
                item.status = cls_IOThread.STAT_DISCONNECTED
                item.commObject = item.interfaceClass(
                    self.stopEvent,
                    self.queue,
                    item.id,
                    item.interfaceName,
                    item.interfaceParams,
                )
                print("commobject created for", item.interfaceName)
        self.updateStatus()

        #
        #     store writer
        #
        for i, item in enumerate(self.controllerItems):
            if self.controllerItems[item.nextId].commObject is not None:
                item.writer = self.controllerItems[item.nextId].commObject.writer
            else:
                item.writer = None

        print("controller: init passed")
        return

    def run(self):

        self.status = self.STAT_RUN
        self.e = None
        connected = False
        print("controller: start run")
        self.status = self.STAT_RUN
        for i in self.controllerItems:
            if not i.isDisabled:
                i.readerThread = threading.Thread(target=i.commObject.reader)
                i.readerThread.start()
        self.updateMessage("")
        exitError = False
        errMsgPrefix = ""
        try:

            while True:
                #
                # process commands issued from main
                #
                item = self.queue.get()
                if type(item) is not list:
                    if item == self.CMD_STOP:
                        self.status = self.STAT_STOP
                        break
                    if item == self.CMD_PAUSE:
                        self.status = self.STAT_PAUSE
                        self.updateMessage("Loop paused")
                        print("controller: pause")
                        continue
                    if item == self.CMD_RESUME:
                        self.status = self.STAT_RUN
                        print("controller: resume")
                        self.updateMessage("")
                        continue
                id = item[0]
                #
                # process frames
                #
                if item[1] >= 0:
                    # print("controller: processing ", self.controllerItems[id].devices)
                    if self.controllerItems[id].writer is not None:
                        #
                        # call writer of next interface to send frame
                        #
                        try:
                            self.controllerItems[id].writer(item[1])
                        except Exception as e:
                            e.add_note(
                                "controlthread: write Error for interface "
                                + self.controllerItems[id].interfaceName
                            )
                            raise e from e
                    else:
                        #
                        # next Interface is disabled: put data into queue with id of next interface
                        #
                        self.queue.put([self.controllerItems[id].nextId, item[1]])
                #
                # got error message from an io thread
                #
                elif item[1] == cls_IOThread.MSG_ERROR:
                    self.controllerItems[id].readerThread = None
                    self.e = item[2]
                    exitError = True
                    errMsgPrefix = (
                        "Error in IOThread " + self.controllerItems[id].interfaceName
                    )
                    break
                #
                #               got status change message
                #
                elif item[1] == cls_IOThread.MSG_STATUS:
                    self.controllerItems[id].status = item[2]
                    self.updateStatus()
        #
        # Exception error exit
        #
        except Exception as e:
            self.e = e
            exitError = True
            if errMsgPrefix == "":
                errMsgPrefix = "Controlthread Error"
        finally:
            pass
        #
        # stop all remaining io threads
        #
        self.stopEvent.set()
        for s in self.controllerItems:
            if not s.isDisabled:
                s.status = cls_IOThread.STAT_DISCONNECTED
                if s.readerThread is not None:
                    s.readerThread.join()
        self.stopEvent.clear()
        self.updateStatus()
        self.updateMessage("Loop stopped")
        print("controller: reader threads joined")
        self.status = self.STAT_STOP
        #
        # signal terminate on error
        #
        if exitError:
            self.sig_ControllerTerminated.emit(errMsgPrefix, self.e)
        return

    def pause(self):
        if self.status != self.STAT_RUN:
            print("Illegal status")
            return
        self.queue.put(self.CMD_PAUSE)
        print("controller pause")

    def stop(self):
        if self.status != self.STAT_RUN:
            print("Illegal status", self.status)
            return
        self.queue.put(self.CMD_STOP)
        print("controller stop")

    def resume(self):
        if self.status != self.STAT_PAUSE:
            print("Illegal status")
            return
        self.queue.put(self.CMD_RESUME)
        print("controller resume")

    def updateStatus(self):
        lst = []
        t = 0
        for s in self.controllerItems:
            lst.append(s.status)
            t += s.status
        if t:
            msg = "Waiting for connection(s) ..."
        else:
            msg = "Loop running ..."
        self.sig_UpdateStatus.emit(lst, msg)

    def updateMessage(self, msg):
        self.sig_UpdateStatus.emit(None, msg)


class cls_IndicatorWidget(QtWidgets.QWidget):

    def __init__(self, diameter, num):
        super().__init__()
        self.diameter = diameter
        self.lights = []
        self.hbox = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.hbox)
        self.num = num

        for i in range(self.num):
            w = cls_LightWidget(self.diameter)
            self.hbox.addWidget(w)
            self.lights.append(w)

    def updateStatus(self, stat):
        for i in range(self.num):
            self.lights[i].setState(stat[i])


class cls_LightWidget(QtWidgets.QWidget):

    def __init__(self, diameter):
        super().__init__()
        self.color = None
        self.diameter = diameter

    def minimumSizeHint(self):
        return QtCore.QSize(self.diameter + 2, self.diameter + 2)

    def setState(self, state):
        if state == cls_IOThread.STAT_DISABLED:
            self.color = QtCore.Qt.GlobalColor.black
        elif state == cls_IOThread.STAT_DISCONNECTED:
            self.color = QtCore.Qt.GlobalColor.red
        elif state == cls_IOThread.STAT_CONNECTING:
            self.color = QtCore.Qt.GlobalColor.yellow
        elif state == cls_IOThread.STAT_CONNECTED:
            self.color = QtCore.Qt.GlobalColor.green
        self.update()

    def paintEvent(self, e):
        with QtGui.QPainter(self) as painter:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setBrush(self.color)
            painter.drawEllipse(0, 0, self.diameter, self.diameter)
