from PySide6 import QtCore, QtWidgets

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


class cls_tabscope(cls_tabgeneric):

    def __init__(self, parent, name):
        super().__init__(parent, name)

        self.guiobject = cls_ScopeWidget(self, self.name)
        self.add_guiobject(self.guiobject)

        self.pildevice = cls_pilscope(self, self.guiobject)
        self.guiobject.set_pildevice(self.pildevice)


class cls_ScopeWidget(QtWidgets.QWidget):

    def __init__(self, parent, name):
        super().__init__()
        self.pildevice = None
        self.name = name

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(QtWidgets.QLabel("Scope"))
        self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    def set_pildevice(self, pildevice):
        self.pildevice = pildevice


class cls_pilscope:

    def __init__(self, parent, guiobject):
        self.parent = parent
        self.guiobject = guiobject

    def process(self, frame):
        print("process", self.guiobject.name)
        return frame


def pilscope_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Scope, PILGLOBALS.Tab_Type_Scope, None, cls_tabscope, "Scope"
        )
    ]
