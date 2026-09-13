from PySide6 import QtCore, QtWidgets
import serial.tools.list_ports

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


#
# generic interface configuration class
#
class cls_ConfigInterfaceGeneric(QtWidgets.QFrame):

    buttonCheckedSignal = QtCore.Signal()

    def __init__(self, parent, name, id, interfaceSpecifications):
        super().__init__()
        self.parent = parent
        self.name = name
        self.id = id
        self.interfaceSpecifications = interfaceSpecifications
        #
        # config name of interface
        #
        self.configName = (
            self.name + "_" + self.interfaceSpecifications[self.id].configPrefix
        )
        self.interfaceName = self.interfaceSpecifications[self.id].interfaceName

        self.isChecked = False
        self.vb = QtWidgets.QVBoxLayout(self)
        self.radBut = QtWidgets.QRadioButton()
        self.radBut.setText(self.interfaceName)
        self.radBut.clicked.connect(self.do_checked)
        self.vb.addWidget(self.radBut)

    def do_checked(self):
        PILCONFIG.put(self.name, "interface_id", self.id)
        self.setActive(True)
        self.parent.do_uncheckOthers(self.id)

    def setUnchecked(self):
        self.radbud.setChecked(False)
        self.setActive(False)


#
# Get TTy  Dialog class ------------------------------------------------------
#


class cls_TtyWindow(QtWidgets.QDialog):

    def __init__(self, tty):
        super().__init__()

        self.oldTty = tty
        self.setWindowTitle("Select serial device")
        self.vlayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.vlayout)

        self.label = QtWidgets.QLabel()
        self.label.setText("Select or enter serial port")
        #     self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.vlayout.addWidget(self.label)

        pattern = ""
        if PILGLOBALS.isWindows:
            pattern = "COM\\d+"
        if PILGLOBALS.isLinux:
            pattern = "(ttyACM\\d+)|(ttyUSB\\d+)"
        if PILGLOBALS.isMacos:
            pattern = "(cu.usbserial-*)|(cu.usbmodem\\d+)"

        self.__ComboBox__ = QtWidgets.QComboBox()
        self.__ComboBox__.setEditable(True)
        self.vlayout.addWidget(self.__ComboBox__)

        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.addWidget(QtWidgets.QLabel("Description"), 0, 0)
        self.gridLayout.addWidget(QtWidgets.QLabel("UID"), 1, 0)
        self.gridLayout.addWidget(QtWidgets.QLabel("Manufacturer"), 2, 0)
        self.gridLayout.addWidget(QtWidgets.QLabel("Serial Number"), 3, 0)
        self.gridLayout.addWidget(QtWidgets.QLabel("Product"), 4, 0)
        self.gridLayout.addWidget(QtWidgets.QLabel("Interface"), 5, 0)
        self.description = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.description, 0, 1)
        self.uid = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.uid, 1, 1)
        self.manufacturer = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.manufacturer, 2, 1)
        self.serialNumber = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.serialNumber, 3, 1)
        self.product = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.product, 4, 1)
        self.interface = QtWidgets.QLabel("")
        self.gridLayout.addWidget(self.interface, 5, 1)
        self.gridLayout.addWidget(
            QtWidgets.QLabel("Information above may be incomplete or nil"), 6, 0, 1, 2
        )

        self.vlayout.addLayout(self.gridLayout)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.accepted.connect(self.do_ok)
        self.buttonBox.rejected.connect(self.do_cancel)
        self.hlayout = QtWidgets.QHBoxLayout()
        self.hlayout.addWidget(self.buttonBox)
        self.vlayout.addWidget(self.buttonBox)

        self.portInfo = {}
        for port in serial.tools.list_ports.grep(pattern):
            self.__ComboBox__.addItem(port.device)
            self.portInfo[port.device] = port

        self.__device__ = ""

        idx = self.__ComboBox__.findText(self.oldTty, QtCore.Qt.MatchExactly)
        if idx >= 0:
            self.__ComboBox__.setCurrentIndex(idx)
        self.setDeviceInfo(self.__ComboBox__.currentText())
        self.__ComboBox__.activated[int].connect(self.combobox_choosen)
        self.__ComboBox__.editTextChanged.connect(self.combobox_textchanged)

    def setDeviceInfo(self, device):
        self.description.setText("")
        self.uid.setText("")
        self.manufacturer.setText("")
        self.serialNumber.setText("")
        self.product.setText("")
        self.interface.setText("")
        if device in self.portInfo.keys():
            self.description.setText(self.portInfo[device].description)
            if (
                self.portInfo[device].vid is not None
                and self.portInfo[device].pid is not None
            ):
                self.uid.setText(
                    hex(self.portInfo[device].vid)
                    + ":"
                    + hex(self.portInfo[device].pid)
                )
            self.manufacturer.setText(self.portInfo[device].manufacturer)
            self.serialNumber.setText(self.portInfo[device].serial_number)
            self.product.setText(self.portInfo[device].product)
            self.interface.setText(self.portInfo[device].interface)

    def do_ok(self):
        if self.__device__ == "":
            self.__device__ = self.__ComboBox__.currentText()
            if self.__device__ == "":
                return
        super().accept()

    def do_cancel(self):
        super().reject()

    def combobox_textchanged(self, device):
        self.__device__ = device
        self.setDeviceInfo(self.__device__)

    def combobox_choosen(self, idx):
        self.__device__ = self.__ComboBox__.itemText(idx)
        self.setDeviceInfo(self.__device__)

    def getDevice(self):
        return self.__device__

    @staticmethod
    def getTtyDevice(tty_device):
        dialog = cls_TtyWindow(tty_device)
        dialog.resize(200, 100)
        result = dialog.exec()
        if result == QtWidgets.QDialog.Accepted:
            return dialog.getDevice()
        else:
            return ""


#
# Main interface GUI Tab object
#
class cls_tabinterface(cls_tabgeneric):

    def __init__(
        self,
        mainUI,
        name,
        interfaceSpecifications,
        sig_UpdateInterfaceActive,
        interfaceNumber,
    ):
        super().__init__(mainUI, name)
        self.sig_UpdateInterfaceActive = sig_UpdateInterfaceActive
        self.interfaceNumber = interfaceNumber

        self.guiobject = cls_InterfaceWidget(
            self.mainUI, self.name, interfaceSpecifications
        )
        self.add_guiobject(self.guiobject)
        self.pildevice = None
        self.cbActive.setEnabled(True)

    def enable(self):
        self.setEnabled(False)

    def disable(self):
        self.setEnabled(True)

    def toggle_active(self):
        self.sig_UpdateInterfaceActive.emit(self.interfaceNumber, self.active)
        return

    def becomes_visible(self):
        return

    def becomes_invisible(self):
        return


#
# Interface GUI object, inserted into the GUI Tab object
#
class cls_InterfaceWidget(QtWidgets.QWidget):

    def __init__(self, mainUI, name, interfaceSpecifications):
        super().__init__()
        self.mainUI = mainUI
        self.name = name
        self.pildevice = None
        self.interfaceSpecifications = interfaceSpecifications
        self.interfaceConfigWidgets = {}
        self.selectedInterfaceId = PILCONFIG.get(
            self.name, "interface_id", PILGLOBALS.DefaultInterface
        )
        if self.selectedInterfaceId not in interfaceSpecifications.keys():
            self.mainUI.showWarning(
                f"Interface with Id {self.selectedInterfaceId} not found. Resetting to PIL-Box interface."
            )
            self.selectedInterfaceId = PILGLOBALS.DefaultInterface
        self.vbox = QtWidgets.QVBoxLayout()
        self.hbox = QtWidgets.QHBoxLayout()
        self.gbox = QtWidgets.QGroupBox()
        self.gbox.setFlat(True)
        self.gbox.setTitle("Communication configuration")
        self.vboxgbox = QtWidgets.QVBoxLayout()
        self.gbox.setLayout(self.vboxgbox)
        self.hbox.addWidget(self.gbox)
        self.hbox.addStretch(1)
        self.vbox.addLayout(self.hbox)

        for id in self.interfaceSpecifications.keys():
            #    self.vbox.addWidget(
            #        QtWidgets.QLabel(self.interfaceSpecifications[id].interfaceName)
            #    )

            w = self.interfaceSpecifications[id].configClass(
                self,
                self.name,
                id,
                self.interfaceSpecifications,
            )

            self.interfaceConfigWidgets[id] = w
            if id == self.selectedInterfaceId:
                w.setActive(True)
            else:
                w.setActive(False)
            self.vboxgbox.addWidget(w)

        self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    def do_uncheckOthers(self, id):
        for i, w in self.interfaceConfigWidgets.items():
            if i != id:
                w.setActive(False)


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
