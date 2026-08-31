import sys
import time
import os
import threading
import traceback
import importlib
from json import JSONDecodeError
from PySide6 import QtCore, QtWidgets

from .pilwidgets import cls_RuntimeMessageBox, cls_Tabs, cls_PilConfigWindow
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG
from .shortcutconfig import SHORTCUTCONFIG
from .penconfig import PENCONFIG
from .controlthread import cls_controller, controllerItem, cls_IndicatorWidget
from .pilcore import AppException, decode_pyILPERVersion


class cls_ui(QtWidgets.QMainWindow):

    sig_UpdateStatus = QtCore.Signal(list, str)  # must be class variable!!
    sig_ControllerTerminated = QtCore.Signal(str, Exception)  # must be class variable!!

    def __init__(self, parent, version, instance):
        super().__init__()
        self.controller = None
        self.parent = parent
        self.name = PILGLOBALS.PackageName
        self.clean = PILGLOBALS.Clean
        self.instance = PILGLOBALS.Instance
        self.helpwin = None
        self.aboutwin = None
        self.devstatuswin = None
        self.lifutils_installed = False
        self.tabWidgetList = []

        #     absulutely needed: call super().__init__()
        self.sig_UpdateStatus.connect(self.updateStatusLine, QtCore.Qt.QueuedConnection)
        self.sig_ControllerTerminated.connect(
            self.showRuntimeError, QtCore.Qt.QueuedConnection
        )

        if instance == "":
            self.setWindowTitle("pyILPER " + version)
        else:
            self.setWindowTitle("pyILPER " + version + " : " + instance)
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
            PILCONFIG.get(self.name, "autostart", False)
            PILCONFIG.get(
                self.name,
                "tabconfig",
                [
                    [PILGLOBALS.Tab_Scope, "Scope"],
                    [PILGLOBALS.Tab_Interface, "Interface1"],
                    [PILGLOBALS.Tab_Dummy, "Dummy1"],
                    [PILGLOBALS.Tab_Dummy, "Dummy2"],
                    [PILGLOBALS.Tab_Interface, "Interface2"],
                    [PILGLOBALS.Tab_Dummy, "Dummy3"],
                ],
            )
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
                reply = QtWidgets.QMessageBox.warning(
                    self.ui,
                    "Warning",
                    "Your configuration files are of pyILPER version "
                    + PILCONFIG.get(self.name, "version")
                    + " which is newer than the version you are running. The program might crash or mishehave. Do you want to continue?",
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Cancel,
                )
                if reply == QtWidgets.QMessageBox.Cancel:
                    sys.exit(1)

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
            # Initterminal keyboard shortcuts
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
                    reply = QtWidgets.QMessageBox.critical(
                        self.ui,
                        "Error",
                        "Style "
                        + qtstyle
                        + " not available. Resetting to system default",
                        QtWidgets.QMessageBox.Ok,
                        QtWidgets.QMessageBox.Ok,
                    )

            #
            #       build GUI
            #
            self.menubar = self.menuBar()
            self.menubar.setNativeMenuBar(False)

            self.menuFile = self.menubar.addMenu("File")
            self.actionConfig = self.menuFile.addAction("pyILPER configuration")
            self.actionConfig.triggered.connect(self.pyilperConfig)
            self.actionDevConfig = self.menuFile.addAction(
                "Virtual HP-IL device configuration"
            )
            self.actionPenConfig = self.menuFile.addAction("Plotter pen configuration")
            self.actionShortcutConfig = self.menuFile.addAction(
                "Terminal keyboard shortcut configuration"
            )
            self.actionStart = self.menuFile.addAction("Start Loop")
            self.actionStart.triggered.connect(self.controller_restart)
            self.actionPause = self.menuFile.addAction("Pause Loop")
            self.actionPause.triggered.connect(self.controller_pause)
            self.actionResume = self.menuFile.addAction("Resume Loop")
            self.actionResume.triggered.connect(self.controller_resume)
            self.actionStop = self.menuFile.addAction("Stop Loop")
            self.actionStop.triggered.connect(self.controller_stop)
            self.actionExit = self.menuFile.addAction("Exit")
            self.actionExit.triggered.connect(self.app_exit)

            self.menuUtil = self.menubar.addMenu("Utilities")
            self.actionInit = self.menuUtil.addAction("Initialize LIF image file")
            self.actionFix = self.menuUtil.addAction("Fix Header of LIF image file")
            self.actionDevStatus = self.menuUtil.addAction(
                "Virtual HP-IL device status"
            )
            self.actionCopyPilimage = self.menuUtil.addAction(
                "Copy PILIMAGE.DAT to workdir"
            )
            self.actionInstallCheck = self.menuUtil.addAction(
                "Check LIFUTILS installation"
            )
            self.actionInit.setEnabled(False)
            self.actionFix.setEnabled(False)

            self.menuHelp = self.menubar.addMenu("Help")
            self.actionAbout = self.menuHelp.addAction("About")
            self.actionHelp = self.menuHelp.addAction("Manual")
            #
            # TODO: check lifutils, do we need that variable
            #
            # self.lifutils_installed= check_lifutils()[0]
            # if self.lifutils_installed:
            #    self.self.actionInit.setEnabled(False)
            #    self.actionFix.setEnabled(False)
            #
            # get tab classes and specifications from modules
            #
            self.tabSpecifications = {}
            self.tabModules = PILGLOBALS.TabModules
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
            # TODO: set scope fixed as first tab
            #
            self.tabWidget = cls_Tabs()
            self.setCentralWidget(self.tabWidget)
            for t in self.tabConfig:
                id = t[0]
                if id not in self.tabSpecifications.keys():
                    del self.tabConfig[id]
                    # TODO: remove config params of this entry
                    # pattern= t[1]+""_"
                    # PILCONFIG.delAll(pattern)
                    tabConfigChanged = True
                tabClass = self.tabSpecifications[id].tab_class
                tabType = self.tabSpecifications[id].type
                tabName = t[1]
                if tabType == PILGLOBALS.Tab_Type_Interface:
                    tab = tabClass(self, tabName, self.interfaceSpecifications)
                else:
                    tab = tabClass(self, tabName)
                self.tabWidget.addTab(tab, tabName)
                self.tabWidgetList.append(tab)
            #
            # store changed tabconfig, if unknown tab types were removed
            #
            if tabConfigChanged:
                lastTab = 0
                PILCONFIG.put(self.name, "tabconfigchanged", True)
                PILCONFIG.put(self.name, "tabconfig", self.tabConfig)
                # TODO output warning message
                PILCONFIG.put(self.name, "active_tab", 0)

            #
            # status bar and idicator widget
            #
            self.statusBar = QtWidgets.QStatusBar()
            #       self.statusBar.setFixedWidth(300)
            self.indicator = None
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
            self.setStatusBar(self.statusBar)

            #
            #  move window to last position
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
            # TODO: do autostart of loop if configured
            # TODO: show starter info if pyilper is run for the first time
            # TODO: show release notes if a new version of pyilper is run for the first time
        #
        #   catch any exception during initialization
        #
        except Exception as e:
            e.add_note("error during program initialization")
            self.showRuntimeError(None, e)
            sys.exit(1)

    def updateStatusLine(self, stat, msg):
        """Docstring."""
        if msg is not None:
            self.statusBar.showMessage(msg)
        if stat and self.indicator is not None:
            self.indicator.updateStatus(stat)

    #
    #  Start controller thread
    #
    def controller_start(self):
        #
        # TODO: error handling
        os.chdir(PILCONFIG.get(self.name, "workdir"))
        #
        self.controller = cls_controller(
            self, self.sig_UpdateStatus, self.sig_ControllerTerminated
        )
        ret = self.controller.setup(
            self.tabConfig,
            self.tabWidgetList,
            self.tabSpecifications,
            self.interfaceSpecifications,
        )
        #
        # No active interface found
        #
        if ret == 0:
            self.controller = None
            return
        #
        # TODO: enable the tab objects
        #
        for t in self.tabWidgetList:
            t.enable()
        self.t = threading.Thread(target=self.controller.run)
        self.t.start()
        #
        # trigger visible virtual device widget to enable refreshs
        #
        pilwidget = self.tabWidgetList[PILCONFIG.get(self.name, "active_tab")]
        pilwidget.becomes_visible()

    def controller_stop(self):
        if self.controller is None:
            return
        self.controller.stop()
        self.t.join()
        while self.t.is_alive():
            time.sleep(0.1)
        self.t = None
        #
        # TODO: disable registered tab objects
        #
        for t in self.tabWidgetList:
            t.disable()
        print("main: controller thread joined")
        self.controller = None

    def controller_pause(self):
        if self.controller is not None:
            self.controller.pause()

    def controller_resume(self):
        if self.controller is not None:
            self.controller.resume()

    def controller_restart(self):
        if self.controller is not None:
            print("illegal status")
            return
        self.controller_start()

    def pyilperConfig(self):
        (accept, needs_reconnect, needs_reconfigure) = cls_PilConfigWindow.getPilConfig(
            self, self.name
        )
        # print(f"return from config {accept} {needs_reconnect} {needs_reconfigure}")
        if accept:
            if needs_reconnect:  # TODO check if needed
                self.controller_stop()
                # TODO error handling
                PILCONFIG.save()
                return

            #
            # reconfigure the tabs while the thread is stopped
            #
            if needs_reconfigure:
                self.controller_pause()
                for obj in self.tabWidgetList:
                    obj.reconfigure()
                self.controller_resume()

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

    def closeEvent(self, event):
        event.accept()
        self.hide()
        self.app_exit()

    def createIndicator(self, num):
        if self.indicator is not None:
            self.statusBar.removeWidget(self.indicator)
            self.indicator.deleteLater()
        self.indicator = cls_IndicatorWidget(10, num)
        self.statusBar.addPermanentWidget(self.indicator)
        self.indicator.show()

    #
    #  controller terminated signal handler
    #
    def showRuntimeError(self, errMsgPrefix, ex):
        print("controller terminated signal")
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


def main():
    app = QtWidgets.QApplication(sys.argv)
    prog = cls_ui(app, "", "")
    app.exec()


if __name__ == "__main__":
    main()
