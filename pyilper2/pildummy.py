from PySide6 import QtCore, QtWidgets

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


class cls_tabdummy(cls_tabgeneric):

    def __init__(self, parent, name):
        super().__init__(parent, name)

        self.guiobject = cls_DummyWidget(self, self.name)
        self.add_guiobject(self.guiobject)

        self.pildevice = cls_pildummy(self, self.guiobject)
        self.guiobject.set_pildevice(self.pildevice)

    def becomes_visible(self):
        return

    def becomes_invisible(self):
        return


class cls_DummyWidget(QtWidgets.QWidget):

    def __init__(self, parent, name):
        super().__init__()
        self.pildevice = None
        self.name = name

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(QtWidgets.QLabel("Dummy"))
        self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    def set_pildevice(self, pildevice):
        self.pildevice = pildevice


class cls_pildummy:

    def __init__(self, parent, guiobject):
        self.parent = parent
        self.guiobject = guiobject

    def process(self, frame):
        # print("processing", self.guiobject.name)
        return frame


def pildummy_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Dummy,
            PILGLOBALS.Tab_Type_Device,
            None,
            cls_tabdummy,
            "Dummy",
        )
    ]
