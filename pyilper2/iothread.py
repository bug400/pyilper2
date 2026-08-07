#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pyILPER 1.2.1 for Linux
#
# An emulator for virtual HP-IL devices for the PIL-Box
# derived from ILPER 1.4.5 for Windows
# Copyright (c) 2008-2013   Jean-Francois Garnier
# C++ version (c) 2013 Christoph Gießelink
# Python Version (c) 2015 Joachim Siebold
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
# IO Thread virtual class  ---------------------------------------------
#
# Changelog
#
# XX.XX.2026 jsi
# - first version

import threading


class IOThreadException(Exception):
    def __init__(self, msg):
        self.msg = msg


class cls_IOThread(threading.Thread):

    STAT_DISCONNECTED = 2
    STAT_CONNECTING = 1
    STAT_CONNECTED = 0

    MSG_ERROR = -1
    MSG_STATUS = -2

    def __init__(self, stopEvent, queue, id):
        super().__init__()
        self.__stopEvent__ = stopEvent
        self.__queue__ = queue
        self.__id__ = id
        self.__status__ = self.STAT_DISCONNECTED
        self.__statLock__ = threading.Lock()

    def setStatus(self, stat):
        with self.__statLock__:
            self.__status__ = stat
        self.__queue__.put([self.__id__, self.MSG_STATUS, stat])

    def getStatus(self):
        with self.__statLock__:
            return self.__status__
