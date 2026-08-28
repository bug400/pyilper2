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
from .pilconfig import PILCONFIG
from .iothread import cls_IOThread


@dataclass
class controllerItem:
    isDisabled: bool
    interfaceItemId: int
    nextInterfaceItemId: int
    tabIndex: int
    name: str
    status: int
    commObject: object
    readerThread: object
    writer: object
    deviceProcessors: list[object]


class cls_controller(threading.Thread):

    STAT_RUN = 0
    STAT_PAUSE = 1
    STAT_STOP = 2

    CMD_PAUSE = -1
    CMD_RESUME = -2
    CMD_STOP = -3

    CONTROLLER_ID = -1

    def __init__(self, parent, sig_UpdateStatus, sig_ControllerTerminated):
        super().__init__()
        self.parent = parent
        self.controllerItems = {}
        self.queue = queue.SimpleQueue()
        self.stopEvent = threading.Event()
        self.sig_UpdateStatus = sig_UpdateStatus
        self.sig_ControllerTerminated = sig_ControllerTerminated
        self.status = self.STAT_STOP

    #
    #   create the controllerItems data structure to control interface and device processing
    #
    def setup(
        self, tabConfig, tabWidgetList, tabSpecifications, interfaceSpecifications
    ):
        self.tabWidgetList = tabWidgetList
        #
        # First pass, create Item list
        #
        firstInterfaceIndex = -1
        interfaceIndex = -1
        activeInterfaces = 0
        deviceProcessors = []
        tabIndex = 0
        for t in tabConfig:
            id = t[0]
            tabType = tabSpecifications[id].type
            tabName = t[1]
            if tabType == PILGLOBALS.Tab_Type_Interface:
                interfaceIndex += 1
                isDisabled = not PILCONFIG.get(tabName, "active")
                interfaceTypeId = PILCONFIG.get(tabName, "interface_id")
                interfaceName = interfaceSpecifications[interfaceTypeId].interfaceName
                interfaceConfigName = (
                    tabName
                    + "_"
                    + interfaceSpecifications[interfaceTypeId].configPrefix
                )

                if not isDisabled:
                    if interfaceIndex == 0:
                        firstInterfaceIndex = tabIndex
                    activeInterfaces += 1

                    interfaceClass = interfaceSpecifications[
                        interfaceTypeId
                    ].interfaceClass

                    commObject = interfaceClass(
                        self,
                        self.stopEvent,
                        self.queue,
                        interfaceIndex,
                        interfaceConfigName,
                        interfaceName,
                    )
                    readerThread = getattr(
                        commObject,
                        interfaceSpecifications[interfaceTypeId].readerMethodName,
                    )
                    writer = getattr(
                        commObject,
                        interfaceSpecifications[interfaceTypeId].writerMethodName,
                    )
                    item = controllerItem(
                        isDisabled,
                        interfaceIndex,
                        0,
                        tabIndex,
                        interfaceName,
                        cls_IOThread.STAT_DISCONNECTED,
                        commObject,
                        readerThread,
                        writer,
                        deviceProcessors,
                    )

                else:
                    item = controllerItem(
                        isDisabled,
                        interfaceIndex,
                        0,
                        tabIndex,
                        interfaceName,
                        cls_IOThread.STAT_DISABLED,
                        None,
                        None,
                        None,
                        deviceProcessors,
                    )
                self.controllerItems[interfaceIndex] = item
            tabIndex += 1
        #
        # return, if we have no active interfaces
        #
        self.parent.createIndicator(interfaceIndex + 1)

        #
        # Pass 2, add pildevice process methods and add index of writer interface
        #
        for i in self.controllerItems.keys():
            if self.controllerItems[i].isDisabled:
                continue
            tidx = self.controllerItems[i].tabIndex + 1
            nextInterfaceItemId = i + 1
            while True:
                if tidx >= len(tabConfig):
                    tidx = 0
                if nextInterfaceItemId >= len(self.controllerItems.keys()):
                    nextInterfaceItemId = 0
                id = tabConfig[tidx][0]
                tabType = tabSpecifications[id].type
                tabName = tabConfig[tidx][1]
                isActive = PILCONFIG.get(tabName, "active")
                if tabType == PILGLOBALS.Tab_Type_Device and isActive:
                    self.controllerItems[i].deviceProcessors.append(
                        tabWidgetList[tidx].pildevice.process
                    )
                if tabType == PILGLOBALS.Tab_Type_Scope:
                    pass
                if tabType == PILGLOBALS.Tab_Type_Probe:
                    pass
                if tabType == PILGLOBALS.Tab_Type_Interface:
                    if isActive:
                        self.controllerItems[i].nextInterfaceItemId = (
                            nextInterfaceItemId
                        )
                        break
                    else:
                        nextInterfaceItemId += 1
                tidx += 1
        print(self.controllerItems)

        return activeInterfaces

    def run(self):

        self.status = self.STAT_RUN
        self.e = None
        connected = False
        print("controller: start run")
        self.status = self.STAT_RUN
        for i in self.controllerItems.keys():
            if not self.controllerItems[i].isDisabled:
                self.controllerItems[i].readerThread = threading.Thread(
                    target=self.controllerItems[i].commObject.reader
                )
                self.controllerItems[i].readerThread.start()
        exitError = False
        self.updateStatus(exitError)
        errMsgPrefix = ""
        try:

            while True:
                #
                # process commands issued from main
                #
                item = self.queue.get()
                id = item[0]
                #
                # process frames, item[1] is data and always >=0
                #
                if item[1] >= 0:
                    frame = item[1]
                    for processMethod in self.controllerItems[id].deviceProcessors:
                        frame = processMethod(frame)
                    writerId = self.controllerItems[id].nextInterfaceItemId

                    #
                    # call writer of next interface to send frame
                    #
                    try:
                        self.controllerItems[writerId].writer(frame)
                    except Exception as e:
                        e.add_note(
                            "controlthread: write Error for interface "
                            + self.controllerItems[writerId].interfaceName
                        )
                        raise e from e

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
                # got status change message
                #
                elif item[1] == cls_IOThread.MSG_STATUS:
                    self.controllerItems[id].status = item[2]
                    self.updateStatus(exitError)
                #
                # Commands sent from main applications
                #
                elif id == self.CONTROLLER_ID and item[1] == self.CMD_STOP:
                    self.status = self.STAT_STOP
                    break
                elif id == self.CONTROLLER_ID and item[1] == self.CMD_PAUSE:
                    self.status = self.STAT_PAUSE
                    self.updateStatus(exitError)
                    print("controller: pause")
                    continue
                elif id == self.CONTROLLER_ID and item[1] == self.CMD_RESUME:
                    self.status = self.STAT_RUN
                    print("controller: resume")
                    self.updateStatus(exitError)
                    continue
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
        for i in self.controllerItems.keys():
            if not self.controllerItems[i].isDisabled:
                self.controllerItems[i].status = cls_IOThread.STAT_DISCONNECTED
                if self.controllerItems[i].readerThread is not None:
                    self.controllerItems[i].readerThread.join()
        self.stopEvent.clear()
        self.status = self.STAT_STOP
        self.updateStatus(exitError)
        print("controller: reader threads joined")

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
        self.queue.put([self.CONTROLLER_ID, self.CMD_PAUSE])
        print("controller pause")

    def stop(self):
        if self.status != self.STAT_RUN:
            print("Illegal status", self.status)
            return
        self.queue.put([self.CONTROLLER_ID, self.CMD_STOP])
        print("controller stop")

    def resume(self):
        if self.status != self.STAT_PAUSE:
            print("Illegal status")
            return
        self.queue.put([self.CONTROLLER_ID, self.CMD_RESUME])
        print("controller resume")

    #
    #   Update status information in the status bar of the GUI
    #
    def updateStatus(self, exitError):
        #
        #       update status of interfaces
        #
        lst = []
        allConnected = True
        for i in self.controllerItems.keys():
            interfaceStatus = self.controllerItems[i].status
            lst.append(interfaceStatus)
            if (
                interfaceStatus != cls_IOThread.STAT_DISABLED
                and interfaceStatus != cls_IOThread.STAT_CONNECTED
            ):
                allConnected = False
        #
        #       create status message
        #
        if self.status == self.STAT_RUN:
            if allConnected:
                msg = "Loop running ..."
            else:
                msg = "Waiting for connection(s) ..."
        elif self.status == self.STAT_PAUSE:
            msg = "Loop suspended ..."
        else:
            if exitError:
                msg = "Loop stopped after error"
            else:
                msg = "Loop stopped"
        self.sig_UpdateStatus.emit(lst, msg)


class cls_IndicatorWidget(QtWidgets.QWidget):

    def __init__(self, diameter, num):
        super().__init__()
        self.hide()
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
        if self.color is None:
            return
        with QtGui.QPainter(self) as painter:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setBrush(self.color)
            painter.drawEllipse(0, 0, self.diameter, self.diameter)
