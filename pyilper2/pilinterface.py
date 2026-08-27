from PySide6 import QtCore, QtWidgets

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


class cls_tabinterface(cls_tabgeneric):

    def __init__(self, parent, name, interfaceSpecifications):
        super().__init__(parent, name)
        self.parent = parent
        self.name = name

        PILCONFIG.put(self.name, "interface_id", PILGLOBALS.DefaultInterface)
        self.guiobject = cls_InterfaceWidget(self, self.name, interfaceSpecifications)
        self.add_guiobject(self.guiobject)
        self.pildevice = None


class cls_InterfaceWidget(QtWidgets.QWidget):

    def __init__(self, parent, name, interfaceSpecifications):
        super().__init__()
        self.pildevice = None
        self.interfaceSpecifications = interfaceSpecifications

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(QtWidgets.QLabel("Interface"))
        for id in self.interfaceSpecifications.keys():
            print(self.interfaceSpecifications[id])
            self.vbox.addWidget(
                QtWidgets.QLabel(self.interfaceSpecifications[id].interfaceName)
            )
        self.vbox.addStretch(1)
        self.setLayout(self.vbox)


def pilinterface_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Interface,
            PILGLOBALS.Tab_Type_Interface,
            None,
            cls_tabinterface,
            "Interface",
        )
    ]
