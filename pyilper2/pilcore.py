#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# pyILPER 2.0
# Copyright (c) 2026 J. Siebold
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
# pyILPER support functions and classes -----------------------------------------------
#
# Changelog
# XX.XX.2026 jsi:
# - derived from version 1.9
#
import re
import os
import shutil

from dataclasses import dataclass
from .pilglobals import PILGLOBALS

USE_8BITS = True

"""
def getEventPosition(ev):
    return ev.position().toPoint()
"""

#
# A note on pyILPER error handling in the thread code.
# - All exceptions are bubbled up to the topmost thread code and handled there
# - If appropriate, exceptions are caught on a higher level. In this case
#  the required clean up actions are taken, a note is added to the exception
#  that describes the error on that level, and the exception is re-raised:
#
# try:
#    code where an arbitrary exception might occur
# except Exception as e:
#    do necessary cleanup
#    e.add_note("Message that describes the error at this application level")
#    raise e from e
#
# On the topmost level the exception object has a complete traceback and
# a stack of error messages. Then, the exception is  sent to the GUI
# application to show an error message and the thread and its descendants
# are terminated gracefully.
#


#
# Application error class
# This class is used to raise an application exception in the case
# of a malfunction detected by Python user code and not by the
# Python runtime system.
#
class AppException(Exception):

    def __init__(self, msg):
        self.msg = msg


#
# decode version number of lifutils or emu7470
#
def decode_version(version_number):
    if version_number == 0:
        return "(unknown)"
    version = str(version_number)
    major = int(version[0])
    minor = int(version[1:3])
    subversion = int(version[3:5])
    return "{:d}.{:d}.{:d}".format(major, minor, subversion)


#
# decode version number of pyilper as a list
#
def decode_pyILPERVersion(version_string):
    #
    #  parse the pyILPER version string as a list:
    #  major version, minor version, subversion, a/b, devel-version
    #  only major version, minor version and subersion are returned as a
    #  single integer. Returns 0 if no valid release information was found.
    #
    #  Fixed DEPRECATED escape sequence \. using raw string
    reg = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)(?:(b)([0-9]+)?)?.*$")
    ret = reg.findall(version_string)
    try:
        major = int(ret[0][0])
        minor = int(ret[0][1])
        subversion = int(ret[0][2])
        return major * 10000 + minor * 100 + subversion
    except ValueError:
        return 0
    except IndexError:
        return 0


#
#  assemble file name of config file
#
def buildconfigfilename(configdir, filename, configversion, instance, production):
    #
    #  determine config file name
    #
    fname = filename + instance + configversion
    if not production:
        fname += "d"
    #
    #  determine path (os dependend)
    #
    userhome = os.path.expanduser("~")

    if PILGLOBALS.isLinux:
        #
        # LINUX
        #
        configpath = os.path.join(userhome, ".config", configdir)
    elif PILGLOBALS.isWindows:
        #
        # Windows
        #
        configpath = os.path.join(
            os.environ["HOMEDRIVE"],
            os.environ["HOMEPATH"],
            configdir,
        )
    elif PILGLOBALS.isMacos:
        #
        # Mac OS X
        #
        configpath = os.path.join(userhome, "Library", "Application Support", configdir)
    #
    else:
        #
        # Fallback
        #
        configpath = os.path.join(userhome, configdir)
    configfilename = os.path.join(configpath, fname)

    # print(configfilename, configdir)
    return configfilename, configpath


#
#  Interface specification dataclass
#
@dataclass
class cls_Interface_Spec:
    id: int
    configPrefix: str
    interfaceClass: object
    readerMethodName: str
    writerMethodName: str
    configClass: object
    interfaceName: str


@dataclass
class cls_Tab_Spec:
    id: int
    type: int
    mod: object
    tab_class: object
    name: str
