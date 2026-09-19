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
# pyilpermain.py: main pyILPER gui and callbacks
#

import sys
import time
import os
import threading
import traceback
import importlib
import shutil
import re
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from PySide6 import QtCore, QtWidgets, QtGui

from .pilwidgets import (
    cls_RuntimeMessageBox,
    cls_Tabs,
    cls_PilConfigWindow,
    cls_DeviceConfigWindow,
    cls_DevStatusWindow,
    cls_AboutWindow,
    cls_HelpWindow,
)
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG
from .shortcutconfig import SHORTCUTCONFIG, cls_ShortcutConfigWindow
from .penconfig import PENCONFIG, cls_PenConfigWindow
from .controlthread import cls_controller, controllerItem, cls_IndicatorWidget
from .pilcore import AppException, decode_pyILPERVersion
from .pildevbase import cls_pilqueue
from .iothread import cls_IOThread
from .lifexec import check_lifutils, cls_liffix, cls_lifinit, cls_installcheck


@dataclass
class deviceInfo:
    tabId: int
    tabType: int
    tabName: str
    pildevice: object


class cls_ui(QtWidgets.QMainWindow):

    sig_UpdateStatus = QtCore.Signal(int, list, bool)  # must be class variable!!
    sig_ControllerTerminated = QtCore.Signal(str, Exception)  # must be class variable!!
    sig_UpdateInterfaceActive = QtCore.Signal(int, bool)

    #   def __init__(self, parent, version, instance):
    def __init__(self, parent):
        super().__init__()
        self.controller = None
        self.controllerThread = None

        self.name = PILGLOBALS.PackageName
        self.clean = PILGLOBALS.Clean
        self.instance = PILGLOBALS.Instance
        self.helpwin = None
        self.aboutwin = None
        self.devstatuswin = None
        self.lifutils_installed = False
        self.isEnabled = False
        self.tabWidgetList = []
        self.deviceInfoList = []
        self.validConfigNameList = []
        self.scopeQueue = cls_pilqueue()

        #     absolutely needed: call super().__init__() to make this work!
        self.sig_UpdateStatus.connect(self.updateStatus, QtCore.Qt.QueuedConnection)
        self.sig_ControllerTerminated.connect(
            self.controllerErrorHandler, QtCore.Qt.QueuedConnection
        )
        self.sig_UpdateInterfaceActive.connect(
            self.updateInterfaceActive, QtCore.Qt.QueuedConnection
        )

        if PILGLOBALS.Instance == "":
            self.setWindowTitle("pyILPER " + PILGLOBALS.Version)
        else:
            self.setWindowTitle(
                "pyILPER " + PILGLOBALS.Version + " : " + PILGLOBALS.Instance
            )
        #
        #       Init configuration, catch any errors in the following init code
        #
        try:
            PILCONFIG.open(
                PILGLOBALS.ConfigVersion,
                self.instance,
                PILGLOBALS.Production,
                self.clean,
            )
            PILCONFIG.get(self.name, "active_tab", 0)
            PILCONFIG.get(self.name, "tabconfigchanged", False)
            PILCONFIG.get(self.name, "workdir", os.path.expanduser("~"))
            PILCONFIG.get(self.name, "position", "")
            PILCONFIG.get(self.name, "version", "0.0.0")
            PILCONFIG.get(self.name, "helpposition", "")
            PILCONFIG.get(self.name, "papersize", 0)
            PILCONFIG.get(self.name, "lifutilspath", "")
            PILCONFIG.get(self.name, "terminalcharsize", 15)
            PILCONFIG.get(self.name, "directorycharsize", 13)
            PILCONFIG.get(self.name, "hp82162a_pixelsize", 1)
            PILCONFIG.get(self.name, "hp2225b_screenwidth", 640)
            PILCONFIG.get(self.name, "usebom", False)
            PILCONFIG.get(self.name, "qtstyle", "Default")
            PILCONFIG.get(self.name, "autostart", True)
            PILCONFIG.get(
                self.name,
                "tabconfig",
                [
                    [PILGLOBALS.Tab_Scope, "Scope"],
                    [PILGLOBALS.Tab_Interface, "Interface1"],
                    [PILGLOBALS.Tab_Probe, "Probe1"],
                    [PILGLOBALS.Tab_Printer, "Printer1"],
                    [PILGLOBALS.Tab_Terminal, "Terminal"],
                    [PILGLOBALS.Tab_Plotter, "Plotter"],
                    [PILGLOBALS.Tab_Drive, "Drive1"],
                    [PILGLOBALS.Tab_Drive, "Drive2"],
                    [PILGLOBALS.Tab_Probe, "Probe2"],
                ],
            )
            #
            # If the tab config was changed set lastTab to 0
            #
            tabConfigChanged = PILCONFIG.get(self.name, "tabconfigchanged")
            if tabConfigChanged:
                lastTab = 0
                PILCONFIG.put(self.name, "tabconfigchanged", False)
                PILCONFIG.put(self.name, "active_tab", 0)
            else:
                lastTab = PILCONFIG.get(self.name, "active_tab")

            self.tabConfig = PILCONFIG.get(self.name, "tabconfig")
            tabConfigChanged = False
            #
            # version check, warn user if the configuration files are of a newer
            # version
            #
            oldversion = decode_pyILPERVersion(PILCONFIG.get(self.name, "version"))
            thisversion = decode_pyILPERVersion(PILGLOBALS.Version)
            if thisversion < oldversion:
                reply = self.showWarningWithCancel(
                    "Your configuration files are of pyILPER version "
                    + +PILCONFIG.get(self.name, "version")
                    + " which is newer than the version you are running. The program might crash or mishehave. Do you want to continue?"
                )
                if reply == QtWidgets.QMessageBox.Cancel:
                    sys.exit(1)
            PILCONFIG.put(self.name, "version", PILGLOBALS.Version)
            #
            # Init pen configuration
            #
            PENCONFIG.open(
                PILGLOBALS.ConfigVersion,
                self.instance,
                PILGLOBALS.Production,
                self.clean,
            )

            #
            # Init terminal keyboard shortcuts
            #
            SHORTCUTCONFIG.open(
                PILGLOBALS.ConfigVersion,
                self.instance,
                PILGLOBALS.Production,
                self.clean,
            )
            #
            # check Qt Style, if available, otherwise reset to "Default"
            #
            qtstyle = PILCONFIG.get(self.name, "qtstyle")
            if qtstyle != "Default":
                styleFound = False
                for availableStyle in QtWidgets.QStyleFactory.keys():
                    if qtstyle == availableStyle:
                        QtWidgets.QApplication.setStyle(qtstyle)
                        styleFound = True
                        break
                if not styleFound:
                    PILCONFIG.put(self.name, "qtstyle", "Default")
                    self.showError(
                        "Style "
                        + qtstyle
                        + " not available. Resetting to system default",
                    )
            #
            # change working directory
            #
            self.oldWorkdir = ""
            self.changeWorkdir()

            #
            # build GUI
            #
            self.menubar = self.menuBar()
            self.menubar.setNativeMenuBar(False)

            self.menuFile = self.menubar.addMenu("File")
            self.actionConfig = self.menuFile.addAction("pyILPER configuration")
            self.actionConfig.triggered.connect(self.pyilperConfig)
            self.actionDevConfig = self.menuFile.addAction(
                "Virtual HP-IL device configuration"
            )
            self.actionDevConfig.triggered.connect(self.devConfig)
            self.actionPenConfig = self.menuFile.addAction("Plotter pen configuration")
            self.actionPenConfig.triggered.connect(self.penConfig)
            self.actionShortcutConfig = self.menuFile.addAction(
                "Terminal keyboard shortcut configuration"
            )
            self.actionShortcutConfig.triggered.connect(self.shortcutConfig)
            self.actionStart = self.menuFile.addAction("Start Loop")
            self.actionStart.triggered.connect(self.controller_start)
            self.actionStop = self.menuFile.addAction("Stop Loop")
            self.actionStop.triggered.connect(self.controller_stop)
            self.actionStop.setEnabled(False)
            self.actionExit = self.menuFile.addAction("Exit")
            self.actionExit.triggered.connect(self.app_exit)

            self.menuUtil = self.menubar.addMenu("Utilities")
            self.actionInit = self.menuUtil.addAction("Initialize LIF image file")
            self.actionInit.triggered.connect(self.initLif)
            self.actionFix = self.menuUtil.addAction("Fix Header of LIF image file")
            self.actionFix.triggered.connect(self.fixLif)
            self.actionDevStatus = self.menuUtil.addAction(
                "Virtual HP-IL device status"
            )
            self.actionDevStatus.triggered.connect(self.devStatus)
            self.actionCopyPilimage = self.menuUtil.addAction(
                "Copy PILIMAGE.DAT to workdir"
            )
            self.actionCopyPilimage.triggered.connect(self.copyPilImage)
            self.actionInstallCheck = self.menuUtil.addAction(
                "Check LIFUTILS installation"
            )
            self.actionInstallCheck.triggered.connect(self.installCheck)
            self.actionInit.setEnabled(False)
            self.actionFix.setEnabled(False)

            self.menuHelp = self.menubar.addMenu("Help")
            self.actionAbout = self.menuHelp.addAction("About")
            self.actionAbout.triggered.connect(self.about)
            self.actionHelp = self.menuHelp.addAction("Manual")
            self.actionHelp.triggered.connect(self.help)
            #
            # check lifutils, do we need that variable
            #
            self.lifutils_installed = check_lifutils()[0]
            if self.lifutils_installed:
                self.actionInit.setEnabled(True)
                self.actionFix.setEnabled(True)
            #
            # get tab classes and specifications from modules
            #
            self.tabSpecifications = {}
            self.tabModules = PILGLOBALS.TabModules
            #
            # add extra tab modules
            #
            extraTabModules = os.environ.get("PYILPER2_EXTRA_TABS")
            if extraTabModules is not None:
                for m in extraTabModules.split(","):
                    self.tabModules.append(m)

            for m in self.tabModules:
                #
                # retrieve tab module object
                #
                mod = importlib.import_module("." + m, "pyilper2")
                #
                # get tab specification
                #
                get_spec = getattr(mod, m + "_spec")
                specList = get_spec()
                for spec in specList:
                    self.tabSpecifications[spec.id] = spec
            #
            # Get interface classes from modules
            #
            self.interfaceSpecifications = {}
            self.interfaceModules = PILGLOBALS.InterfaceModules
            #
            # add extra interface modules
            #
            extraInterfaceModules = os.environ.get("PYILPER2_EXTRA_INTERFACES")
            if extraInterfaceModules is not None:
                for m in extraInterfaceModules.split(","):
                    self.interfaceModules.append(m)

            for m in self.interfaceModules:
                #
                # retrieve interface module object
                #
                mod = importlib.import_module("." + m, "pyilper2")
                #
                # get interface specification
                #
                get_spec = getattr(mod, m + "_spec")
                specList = get_spec()
                for spec in specList:
                    self.interfaceSpecifications[spec.id] = spec
            #
            # Add device tabs, Scope is fixed the first tab, remove unknown tab types
            #
            self.tabWidget = cls_Tabs()
            self.setCentralWidget(self.tabWidget)
            self.validConfigNameList.append(self.name)
            numInterfaces = 0
            self.interfaceStatus = []
            #
            # Build data structures for tab/device management and add tab objects to the main tab Widget
            # tabWidgetList: list of the tab objects; note: some devices (probes) have no tab object
            # validConfigNameList: list of tab names which have configuration entries in PILCONFIG, used to remove entries for non existing items
            # deviceInfoList: Datestructures with various informations about devices (note: the Scope is not a device)
            #
            # For interfaces the initial interface status is created (disconnected/deactivated interface)
            #
            for t in self.tabConfig:
                id = t[0]
                #
                # remove entry with an unknown tab id
                #
                if id not in self.tabSpecifications.keys():
                    print(f"deleting tab with non existing id {id}")
                    del self.tabConfig[id]
                    tabConfigChanged = True
                    continue
                #
                # now build data structures
                #
                tabClass = self.tabSpecifications[id].tab_class
                tabType = self.tabSpecifications[id].type
                tabName = t[1]

                self.tab = None
                if tabType == PILGLOBALS.Tab_Type_Scope:
                    self.tab = tabClass(self, tabName, self.scopeQueue)
                    self.tabWidget.addTab(self.tab, tabName)
                    self.tabWidgetList.append(self.tab)
                    self.validConfigNameList.append(tabName)
                elif tabType == PILGLOBALS.Tab_Type_Probe:
                    self.tab = tabClass(self, tabName, self.scopeQueue)
                    dInfo = deviceInfo(id, tabType, tabName, self.tab.pildevice)
                    self.deviceInfoList.append(dInfo)
                    self.tabWidgetList[0].registerProbe(tabName, self.tab.pildevice)
                elif tabType == PILGLOBALS.Tab_Type_Interface:
                    self.tab = tabClass(
                        self,
                        tabName,
                        self.interfaceSpecifications,
                        self.sig_UpdateInterfaceActive,
                        numInterfaces,
                    )
                    self.tabWidget.addTab(self.tab, tabName)
                    self.tabWidgetList.append(self.tab)
                    dInfo = deviceInfo(id, tabType, tabName, self.tab.pildevice)
                    self.deviceInfoList.append(dInfo)
                    self.validConfigNameList.append(tabName)
                    if self.tab.get_active():
                        self.interfaceStatus.append(cls_IOThread.STAT_DISCONNECTED)
                    else:
                        self.interfaceStatus.append(cls_IOThread.STAT_DISABLED)
                    numInterfaces += 1
                elif tabType == PILGLOBALS.Tab_Type_Device:
                    self.tab = tabClass(self, tabName)
                    self.tabWidget.addTab(self.tab, tabName)
                    self.tabWidgetList.append(self.tab)
                    dInfo = deviceInfo(id, tabType, tabName, self.tab.pildevice)
                    self.deviceInfoList.append(dInfo)
                    self.validConfigNameList.append(tabName)
                else:
                    self.showError("Illegal Tab Type found")
                    sys.exit(1)
            #
            # remove entries in configuration which do not exist in validConfigNameList
            #
            removeKeys = []
            for key in PILCONFIG.getkeys():
                keyPrefix = key.split(sep="_")[0]
                if not keyPrefix in self.validConfigNameList:
                    removeKeys.append(key)
            for key in removeKeys:
                print(f"remove {key}")
                PILCONFIG.remove(key)
            if removeKeys:
                self.tabConfigChanged = True

            #
            # store changed tabconfig, if tabs of non existing tab types were removed
            #
            if tabConfigChanged:
                lastTab = 0
                PILCONFIG.put(self.name, "tabconfigchanged", True)
                PILCONFIG.put(self.name, "tabconfig", self.tabConfig)
                PILCONFIG.put(self.name, "active_tab", 0)

            #
            # status bar and idicator widget
            #
            self.statusBar = QtWidgets.QStatusBar()
            self.indicator = cls_IndicatorWidget(10, numInterfaces)
            self.statusBar.addPermanentWidget(self.indicator)
            self.indicator.show()
            self.indicator.updateStatus(self.interfaceStatus)
            self.statusBar.showMessage("Loop stopped")

            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
            self.setStatusBar(self.statusBar)

            #
            #  move main window to last position
            #
            position = PILCONFIG.get(self.name, "position")
            if position != "":
                self.move(QtCore.QPoint(position[0], position[1]))
            if len(position) == 4:
                self.resize(position[2], position[3])
            #
            # go to last active tab (if tabconfig did not change)
            #
            self.tabWidget.setCurrentIndex(lastTab)
            #
            #  show and raise gui
            #
            self.show()
            self.raise_()

        #
        # catch any exception during initialization
        #
        except Exception as e:
            e.add_note("error during program initialization")
            self.showRuntimeError(None, e)
            sys.exit(1)
        #
        # if we run pyILPER for the first time (oldversion =0.0.0), show startup info
        #
        if PILCONFIG.get(self.name, "position") == "":
            self.startupInfo()
        else:
            #
            # if we run a new version for the first time, show release notes
            #
            if thisversion > oldversion:
                self.releaseInfo(PILGLOBALS.Version)
        #
        #
        # Do autostart of loop if configured
        #
        if PILCONFIG.get(self.name, "autostart"):
            self.controller_start()

    #
    # This signal callback updates the interface status if the active checkbox of an interface is checked/unchecked.
    # Note: this is only possible, if the controlthread is n o t running
    #
    def updateInterfaceActive(self, interfaceNumber, active):
        if active:
            self.interfaceStatus[interfaceNumber] = cls_IOThread.STAT_DISCONNECTED
        else:
            self.interfaceStatus[interfaceNumber] = cls_IOThread.STAT_DISABLED
        self.indicator.updateStatus(self.interfaceStatus)
        return

    #
    # This signal callback updates the interface status and the loop status if the controlthread is running
    # The handler also controls the activation of the loop start/loop stop actions in the file menu
    #
    def updateStatus(self, controllerStatus, interfaceStatus, exitError):

        #
        # update interface indicators
        #
        self.indicator.updateStatus(interfaceStatus)
        #
        # check, if all interfaces are connected, then the loop is running
        #
        allConnected = True
        for i in interfaceStatus:
            if i != cls_IOThread.STAT_DISABLED and i != cls_IOThread.STAT_CONNECTED:
                allConnected = False
        #
        # create the appropriate status message
        #
        msg = ""
        if controllerStatus == cls_controller.STAT_RUN:
            if allConnected:
                msg = "Loop running ..."
            else:
                msg = "Waiting for connection(s) ..."
            self.actionStart.setEnabled(False)
            self.actionStop.setEnabled(True)
        else:
            if exitError:
                msg = "Loop stopped after error"
            else:
                msg = "Loop stopped"
            self.actionStart.setEnabled(True)
            self.actionStop.setEnabled(False)
        self.statusBar.showMessage(msg)

    #
    #  Start controller thread, enable the tab objects and trigger the visible tab to enable refreshs
    #
    def controller_start(self):

        try:
            self.controller = cls_controller(
                self, self.sig_UpdateStatus, self.sig_ControllerTerminated
            )
            ret = self.controller.setup(
                self.deviceInfoList,
                self.interfaceSpecifications,
            )
            #
            # No active interface found
            #
            if ret == 0:
                self.showInfo("No active Interfaces found")
                self.controller = None
                return
            #
            # Enable the tab objects, change workdir first
            #
            self.changeWorkdir()
            self.isEnabled = True
            for tab in self.tabWidgetList:
                tab.enable()
            self.controllerThread = threading.Thread(target=self.controller.run)
            self.controllerThread.start()
            #
            # trigger visible virtual device widget to enable refreshs
            #
            pilwidget = self.tabWidgetList[PILCONFIG.get(self.name, "active_tab")]
            pilwidget.becomes_visible()

        except Exception as e:
            e.add_note("controller initialization failed")
            self.showException(e)
            self.controller = None

    #
    # Stop the controller thread, disable all tabs
    #
    def controller_stop(self):
        if self.controller is None:
            return
        self.controller.stop()
        if self.controllerThread is not None:
            self.controllerThread.join()
            while self.controllerThread.is_alive():
                time.sleep(0.1)
            self.controllerThread = None
        #
        # Disable registered tab objects
        #
        for tab in self.tabWidgetList:
            tab.disable()
        self.isEnabled = False
        print("main: controller thread joined")
        self.controller = None

    #
    # pyILPER system configuration callback
    #
    def pyilperConfig(self):
        (accept, needs_reconfigure) = cls_PilConfigWindow.getPilConfig(self, self.name)
        if accept:
            #
            # reconfigure the tabs while the thread is suspended
            # Note: controller_pause and controller_resume do nothing, if
            # self.controller is None
            #
            if needs_reconfigure:
                self.controller_pause()
                for obj in self.tabWidgetList:
                    obj.reconfigure()
                self.controller_resume()

    #
    # pyILPER device configuration callback
    #
    def devConfig(self):

        if not cls_DeviceConfigWindow.getDeviceConfig(self, self.tabSpecifications):
            return
        try:
            PILCONFIG.save()
        except Exception as e:
            e.add_note("Device configuration not saved")
            self.showException(e)

    #
    # plotter pen configuration callback
    #
    def penConfig(self):
        if not cls_PenConfigWindow.getPenConfig():
            return
        try:
            PENCONFIG.save()
        except Exception as e:
            e.add_note("Plotter pen configuration not saved")
            self.showException(e)

    #
    # terminal keyboard shortcut configuration callback
    #
    def shortcutConfig(self):
        if not cls_ShortcutConfigWindow.getShortcutConfig():
            return
        try:
            SHORTCUTCONFIG.save()
        except Exception as e:
            e.add_note("Kayboard shortcut configuration not saved")
            self.showException(e)

    #
    # callback init LIF data file

    def initLif(self):
        workdir = PILCONFIG.get(self.name, "workdir")
        cls_lifinit.execute(workdir)

    #
    #  callback fix LIF data file
    #
    def fixLif(self):
        workdir = PILCONFIG.get(self.name, "workdir")
        cls_liffix.execute(workdir)

    #
    #  callback check LIFUTILS installation
    #
    def installCheck(self):
        cls_installcheck.execute()

    #
    # callback show HP-IL device status
    #
    def devStatus(self):
        if self.devstatuswin is None:
            self.devstatuswin = cls_DevStatusWindow(self, self.deviceInfoList)
        self.devstatuswin.show()
        self.devstatuswin.raise_()

    #
    #  callback copy PILIMAGE.DAT to working directory
    #
    def copyPilImage(self):

        srcfile = os.path.join(
            os.path.dirname(PILGLOBALS.PackageDir),
            "lifimage",
            "PILIMAGE.DAT",
        )
        srcfile = re.sub("//", "/", srcfile, count=1)
        dstpath = PILCONFIG.get(self.name, "workdir")
        if os.access(os.path.join(dstpath, "PILIMAGE.DAT"), os.W_OK):
            if (
                self.showWarningWithCancel(
                    "File PILIMAGE.DAT already exists. Do you really want to overwrite that file?"
                )
                == QtWidgets.QMessageBox.Cancel
            ):
                return
        try:
            shutil.copy(srcfile, dstpath)
        except shutil.SameFileError:
            self.showError("Source and destination files are identical")
            return
        except OSError as e:
            e.add_note(f"Cannot copy file ${srcfile}")
            self.showException(e)
            return

    #
    # callback show about window
    #
    def about(self):
        if self.aboutwin is None:
            self.aboutwin = cls_AboutWindow(PILGLOBALS.Version)
            self.aboutwin.show()
            self.aboutwin.raise_()

    #
    # Exit Application
    #
    def app_exit(self):
        #
        # Shut down controller
        #
        self.controller_stop()
        #
        # Store position of main window
        #
        pos_x = self.pos().x()
        pos_y = self.pos().y()
        if pos_x < 50:
            pos_x = 50
        if pos_y < 50:
            pos_y = 50
        width = self.width()
        height = self.height()
        position = [pos_x, pos_y, width, height]
        PILCONFIG.put(self.name, "position", position)
        #
        # Store position of help window
        #
        if self.helpwin is not None:
            helpposition = [
                self.helpwin.pos().x(),
                self.helpwin.pos().y(),
                self.helpwin.width(),
                self.helpwin.height(),
            ]
            PILCONFIG.put(self.name, "helpposition", helpposition)
        #
        # close all floating windows and store their positions
        #
        self.tabWidget.closeFloatingWindows()
        #
        # store configuration
        #
        try:
            PILCONFIG.save()
        except Exception as e:
            e.add_note(
                "Error during application shutdown. Configuration will not be saved."
            )
            self.showRuntimeError(None, e)
        QtWidgets.QApplication.quit()

    #
    # change working directory, if changed
    #
    def changeWorkdir(self):
        workdir = PILCONFIG.get(self.name, "workdir")
        if self.oldWorkdir != workdir:
            try:
                os.chdir(PILCONFIG.get(self.name, "workdir"))
            except Exception as e:
                e.add_note("Cannot change to working directory")
                self.showException(e)
            self.oldWorkdir = workdir

    #
    # this catches the window close event
    #
    def closeEvent(self, event):
        event.accept()
        self.hide()
        self.app_exit()

    #
    #  controller terminated signal handler, show detailed error messages and disable devices
    #
    def controllerErrorHandler(self, errMsgPrefix, ex):
        self.showRuntimeError(errMsgPrefix, ex)
        #
        # Disable registered tab objects
        #
        for tab in self.tabWidgetList:
            tab.disable()
        self.isEnabled = False
        self.controller = None

    #
    # show runtime error with traceback in message box
    #
    def showRuntimeError(self, errMsgPrefix, ex):
        txt = ""
        if hasattr(ex, "__notes__"):
            for line in reversed(ex.__notes__):
                if txt != "":
                    txt += "\ncaused by: "
                txt += line
        if txt != "":
            txt += "\ncaused by: "
        if issubclass(ex.__class__, OSError):
            if ex.strerror is not None:
                txt += type(ex).__name__ + ": " + ex.strerror
            else:
                txt += type(ex).__name__
        elif ex.__class__ == AppException:
            txt += "AppError:" + ex.msg
        elif ex.__class__ == JSONDecodeError:
            txt += f"JSON decode error: {ex.msg} at {ex.lineno}:{ex.colno}"
        else:
            txt += type(ex).__name__
        if errMsgPrefix is not None:
            txt = errMsgPrefix + ": " + txt
        tb = ex.__traceback__
        tbTxt = ""
        for line in traceback.format_tb(tb):
            tbTxt += line
        msgBox = cls_RuntimeMessageBox(600, None)
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
        msgBox.setText(txt)
        msgBox.setDetailedText(tbTxt)
        msgBox.exec()
        msgBox.destroy()

    #
    # show warning message
    #
    def showWarning(self, txt):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
        msgBox.setText(txt)
        msgBox.exec()
        msgBox.destroy()

    #
    # show warning message with cancel button
    #
    def showWarningWithCancel(self, txt):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msgBox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel
        )
        msgBox.setText(txt)
        ret = msgBox.exec()
        msgBox.destroy()
        return ret

    #
    # show info message
    #
    def showInfo(self, txt):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
        msgBox.setText(txt)
        msgBox.exec()
        msgBox.destroy()

    #
    # Show short error message
    #
    def showError(self, txt):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
        msgBox.setText(txt)
        msgBox.exec()
        msgBox.destroy()

    #
    # Show detailed error message (exception)
    #
    def showException(self, ex):
        self.showRuntimeError(None, ex)

    #
    # callback show help window
    #
    def help(self):
        self.showHelp("", "index.html")

    #
    # show release information window
    #
    def releaseInfo(self, version):
        self.showHelp("", "releasenotes.html")

    #
    # show startup info
    #
    def startupInfo(self):
        self.showHelp("", "startup.html")

    #
    #  show help windows for a certain document
    #
    def showHelp(self, subdir, document):
        if subdir == "":
            docPath = Path(PILGLOBALS.PackageDir).parent / "Manual" / document
        else:
            docPath = Path(PILGLOBALS.PackageDir).parent / "Manual" / subdir / document
        #
        # use internal browser
        #
        if PILGLOBALS.Has_Webengine:
            if self.helpwin is None:
                try:
                    self.helpwin = cls_HelpWindow()
                except Exception as e:
                    e.add_note(f"Cannot load help page {docPath}")
                    self.showException(e)
                    return

                helpposition = PILCONFIG.get(self.name, "helpposition")
                if helpposition != "":
                    self.helpwin.move(QtCore.QPoint(helpposition[0], helpposition[1]))
                    self.helpwin.resize(helpposition[2], helpposition[3])
                else:
                    self.helpwin.resize(720, 700)
            self.helpwin.loadDocument(docPath)
            self.helpwin.show()
            self.helpwin.raise_()
        #
        # use system browser
        #
        else:
            ret = QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(str(docPath.resolve()))
            )
            if not ret:
                self.showError(
                    "Cannot launch system default browser to display a pyILPER help page"
                )


def main():
    app = QtWidgets.QApplication(sys.argv)
    prog = cls_ui(app)
    app.exec()


if __name__ == "__main__":
    main()
