import sys
import time
import threading
import traceback
from PySide6 import QtCore, QtWidgets


from .controlthread import cls_controller, controllerItem, cls_IndicatorWidget
from .pilbox import cls_pilbox
from .piltcpip import cls_piltcpip
from .pilacm import cls_pilacm
from .pilcore import AppException

class cls_RuntimeMessageBox(QtWidgets.QMessageBox):

    def __init__(self,width,height):
        super().__init__()
        self.width=width
        self.height=height

    def showEvent(self,e):
        super().showEvent(e)
        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)

    def resizeEvent(self,e):
        super().resizeEvent(e)
        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)
        


class cls_ui(QtWidgets.QMainWindow):
    """Docstring."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        widget = QtWidgets.QWidget()
        self.setCentralWidget(widget)
        layout = QtWidgets.QVBoxLayout(widget)
        but_start = QtWidgets.QPushButton("Start")
        but_start.clicked.connect(self.do_but_start)
        layout.addWidget(but_start)
        but_stop = QtWidgets.QPushButton("Stop")
        but_stop.clicked.connect(self.do_but_stop)
        layout.addWidget(but_stop)
        but_pause = QtWidgets.QPushButton("Pause")
        but_pause.clicked.connect(self.do_but_pause)
        layout.addWidget(but_pause)
        but_resume = QtWidgets.QPushButton("Resume")
        but_resume.clicked.connect(self.do_but_resume)
        layout.addWidget(but_resume)
        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setFixedWidth(300)
        self.indicator = None
        layout.addWidget(self.statusBar)
        self.setLayout(layout)

    def updateStatusLine(self, stat, msg):
        """Docstring."""
        if msg is not None:
            self.statusBar.showMessage(msg)
        if stat and self.indicator is not None:
            self.indicator.updateStatus(stat)

    def do_but_start(self):
        self.parent.controller_restart()

    def do_but_stop(self):
        self.parent.controller_stop()

    def do_but_pause(self):
        self.parent.controller_pause()

    def do_but_resume(self):
        self.parent.controller_resume()

    def closeEvent(self, event):
        event.accept()
        self.hide()
        self.parent.do_exit()

    def createIndicator(self, num):
        if self.indicator is not None:
            self.statusBar.removeWidget(self.indicator)
            self.indicator.deleteLater()
        self.indicator = cls_IndicatorWidget(10, num)
        self.statusBar.addPermanentWidget(self.indicator)
        self.indicator.show()


class cls_program(QtCore.QObject):

    sig_UpdateStatus = QtCore.Signal(list, str)  # must be class variable!!
    sig_ControllerTerminated = QtCore.Signal(str,Exception)  # must be class variable!!

    def __init__(self):
        super().__init__()

        #     absulutely needed: call super().__init__()
        self.sig_UpdateStatus.connect(self.updateStatusLine, QtCore.Qt.QueuedConnection)
        self.sig_ControllerTerminated.connect(
            self.controllerTerminated, QtCore.Qt.QueuedConnection
        )

        self.ui = cls_ui(self)
        self.ui.show()
        self.controllerItems = []
        i = controllerItem(
            0,
            cls_piltcpip,
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
            1, cls_pilbox, ["/dev/ttySTMG4", 0, 0, 1], 0, 0, None, None, None, [4, 5, 6]
        )
        self.controllerItems.append(i)
        i = controllerItem(
            2, cls_pilacm, ["/dev/ttySTMH7"], 0, 0, None, None, None, [7, 8, 9]
        )
        i= controllerItem(2,cls_pilbox,["/dev/ttySTMH7",0,1,1],0,0,None,None,None,[7,8,9])
        self.controllerItems.append(i)
        self.ui.createIndicator(len(self.controllerItems))
        self.controller_start()

    #
    #  Update status line signal handler
    #
    def updateStatusLine(self, stat, msg):
        self.ui.updateStatusLine(stat, msg)

    #
    #  controller terminated signal handler
    #
    def controllerTerminated(self,errMsgPrefix, ex):
        txt=""
        if hasattr(ex,"__notes__"):
            for line in reversed(ex.__notes__):
                if txt != "":
                    txt+="\ncaused by: "
                txt+=line
        if txt!="":
            txt+="\ncaused by: "
        if issubclass(ex.__class__, OSError):
            txt += type(ex).__name__ + ": " + ex.errno, ex.strerror
        elif ex.__class__ == AppException:
            txt += "AppError:" + ex.msg
        else:
            txt += type(ex).__name__
        txt=errMsgPrefix+": "+txt
        tb = ex.__traceback__
        tbTxt = ""
        for line in traceback.format_tb(tb):
            tbTxt += line
        msgBox = cls_RuntimeMessageBox(600,250)
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
        msgBox.setText(txt)
        msgBox.setDetailedText(tbTxt)
        msgBox.exec()

        self.controller = None

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

    def do_exit(self):
        self.controller_stop()
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    prog = cls_program()
    app.exec()


if __name__ == "__main__":
    main()
