import sys
import time
import threading
import traceback
import importlib
from PySide6 import QtCore, QtWidgets
from .pilwidgets import cls_RuntimeMessageBox

from .pilconfig import PILCONFIG
from .pilglobals import PILGLOBALS
from .controlthread import cls_controller, controllerItem, cls_IndicatorWidget
from .pilbox import cls_pilbox
from .piltcpip import cls_piltcpip
from .acmbox import cls_acmbox
from .usbbox import cls_usbbox
from .pilcore import AppException


from .pildummy import cls_tabdummy


class cls_ui(QtWidgets.QMainWindow):

    sig_UpdateStatus = QtCore.Signal(list, str)  # must be class variable!!
    sig_ControllerTerminated = QtCore.Signal(str, Exception)  # must be class variable!!

    def __init__(self, parent, version, instance):
        super().__init__()
        self.controller = None
        self.parent = parent
        self.name = "pyilper2"
        self.clean = PILGLOBALS.Clean
        self.instance = PILGLOBALS.Instance
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
            PILCONFIG.get(self.name, "position", "")
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

            self.tabConfig = PILCONFIG.get(self.name, "tabconfig")

            #
            #       build GUI
            #
            self.menubar = self.menuBar()
            self.menubar.setNativeMenuBar(False)
            self.menuFile = self.menubar.addMenu("File")
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
                print(specList)
                for spec in specList:
                    self.interfaceSpecifications[spec.id] = spec
            #
            # Add device tabs
            #
            self.tabWidget = QtWidgets.QTabWidget()
            self.setCentralWidget(self.tabWidget)
            for t in self.tabConfig:
                id = t[0]
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

            self.statusBar = QtWidgets.QStatusBar()
            #       self.statusBar.setFixedWidth(300)
            self.indicator = None
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
            self.setStatusBar(self.statusBar)

            #
            # controller configuration
            #
            self.controllerItems = []
            self.setupController()
            self.createIndicator(len(self.controllerItems))
            #
            #  move window to last position
            #
            position = PILCONFIG.get(self.name, "position")
            if position != "":
                self.move(QtCore.QPoint(position[0], position[1]))
            if len(position) == 4:
                self.resize(position[2], position[3])
            #
            #  show and raise gui
            #
            self.show()
            self.raise_()
        #
        #   catch any exception
        #
        except Exception as e:
            e.add_note("error during program initialization")
            self.showRuntimeError(None, e)
            QtWidgets.QApplication.quit()

    def setupController(self):
        i = controllerItem(
            0,
            cls_piltcpip,
            "TCP/IP",
            False,
            [60001, "localhost", 60000],
            0,
            0,
            None,
            None,
            None,
            [1, 2, 3],
        )
        self.controllerItems.append(i)
        i = controllerItem(
            1,
            cls_pilbox,
            "PIL-Box 1",
            True,
            ["/dev/ttySTMG4", 0, 0, 1],
            0,
            0,
            None,
            None,
            None,
            [4, 5, 6],
        )
        self.controllerItems.append(i)
        i = controllerItem(
            2,
            cls_acmbox,
            "ACM-Box",
            False,
            ["/dev/ttySTM32"],
            0,
            0,
            None,
            None,
            None,
            [7, 8, 9],
        )
        self.controllerItems.append(i)
        i = controllerItem(
            2,
            cls_pilbox,
            "Pil-Box",
            False,
            ["/dev/ttySTM32", 0, 0, 1],
            0,
            0,
            None,
            None,
            None,
            [7, 8, 9],
        )
        # self.controllerItems.append(i)
        i = controllerItem(
            2,
            cls_acmbox,
            "Fast ACM-Box",
            False,
            ["/dev/ttySTMH7", 0, 1, 1],
            0,
            0,
            None,
            None,
            None,
            [7, 8, 9],
        )
        # self.controllerItems.append(i)
        i = controllerItem(
            2,
            cls_usbbox,
            "Fast USB-Box",
            False,
            [0x0483, 0x5740],
            0,
            0,
            None,
            None,
            None,
            [7, 8, 9],
        )
        # self.controllerItems.append(i)
        #
        #       controller
        #
        # self.controller_start()

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
        self.controller = cls_controller(
            self.sig_UpdateStatus, self.sig_ControllerTerminated, self.controllerItems
        )
        self.t = threading.Thread(target=self.controller.run)
        self.t.start()

    def controller_stop(self):
        if self.controller is None:
            return
        self.controller.stop()
        self.t.join()
        while self.t.is_alive():
            time.sleep(0.1)
        self.t = None
        print("main: controller thread joined")
        self.controller = None

    def controller_pause(self):
        self.controller.pause()

    def controller_resume(self):
        self.controller.resume()

    def controller_restart(self):
        if self.controller is not None:
            print("illegal status")
            return
        self.controller_start()

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
