from PySide6 import QtCore, QtWidgets
from .pilconfig import PILCONFIG


class cls_RuntimeMessageBox(QtWidgets.QMessageBox):

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def showEvent(self, e):
        super().showEvent(e)
        if self.width is not None:
            self.setFixedWidth(self.width)
        if self.height is not None:
            self.setFixedHeight(self.height)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.width is not None:
            self.setFixedWidth(self.width)
        if self.height is not None:
            self.setFixedHeight(self.height)


class cls_tabgeneric(QtWidgets.QWidget):

    def __init__(self, parent, name):
        super().__init__()
        self.name = name
        self.parent = parent
        self.width = 0
        self.height = 0
        self.guiobject = None
        self.pildevice = None
        self.widget_index = 1
        self.active = True
        #
        #       Build basic layout
        #
        #
        self.vbox = QtWidgets.QVBoxLayout()
        self.setLayout(self.vbox)
        #
        #       hbox1: container of GUI Object
        #
        self.hbox1 = QtWidgets.QHBoxLayout()
        self.hbox1.setContentsMargins(10, 10, 10, 10)
        #
        #       hbox2: container of control widgets
        #
        self.hbox2 = QtWidgets.QHBoxLayout()
        self.hbox2.setContentsMargins(10, 3, 10, 3)

        self.cbActive = QtWidgets.QCheckBox("Device enabled")
        self.cbActive.setChecked(self.active)
        self.cbActive.setEnabled(False)
        self.cbActive.stateChanged.connect(self.do_cbActive)
        self.hbox2.addWidget(self.cbActive)
        self.hbox2.addStretch(1)

        self.vbox.addLayout(self.hbox1)
        self.vbox.addLayout(self.hbox2)

    #
    #   add the gui object to hbox1
    #
    def add_guiobject(self, guiobject):
        self.guiobject = guiobject
        self.hbox1.addWidget(self.guiobject)

    #    insert a status widget
    #
    def add_statuswidget(self, statuswidget):
        self.hbox2.insertWidget(self.widget_index, statuswidget)
        self.hbox2.insertStretch(self.widget_index, 1)

    #
    #    action: toogle active checkbox, note: interfaces have not pildevice object
    #
    def do_cbActive(self):
        self.active = self.cbActive.isChecked()
        PILCONFIG.put(self.name, "active", self.active)
        if self.pildevice is not None:
            self.pildevice.setactive(self.active)
        self.toggle_active()
