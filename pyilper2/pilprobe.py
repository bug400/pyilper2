from PySide6 import QtCore, QtWidgets
import threading

from .pilwidgets import cls_tabgeneric
from .pilcore import cls_Tab_Spec
from .pilglobals import PILGLOBALS
from .pilconfig import PILCONFIG


class cls_tabprobe(cls_tabgeneric):

    def __init__(self, parent, name, queue):
        super().__init__(parent, name)
        self.queue = queue

        self.id = int("".join([char for char in name[::-1] if char.isdigit()])[::-1])

        self.pildevice = cls_pilprobe(self.queue, self.id)


class cls_pilprobe:

    def __init__(self, queue, id):
        self.id = id
        self.queue = queue
        self.__isactive__ = False  # device active in loop
        self.__isactive_lock__ = threading.Lock()

    def process(self, frame):
        if self.getactive():
            self.queue.putItem([self.id, frame])
        return frame

    def setactive(self, active):
        self.__isactive_lock__.acquire()
        self.__isactive__ = active
        self.__isactive_lock__.release()

    #
    # get decive active status
    #
    def getactive(self):
        self.__isactive_lock__.acquire()
        active = self.__isactive__
        self.__isactive_lock__.release()
        return active


def pilprobe_spec():
    return [
        cls_Tab_Spec(
            PILGLOBALS.Tab_Probe,
            PILGLOBALS.Tab_Type_Probe,
            None,
            cls_tabprobe,
            "Probe",
        )
    ]
