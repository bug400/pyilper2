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
import serial.tools.list_ports
import shutil

from dataclasses import dataclass
from .pilglobals import PILGLOBALS

USE_8BITS = True
#
#  portable function to get mouse cursor coordinate
#
if PILGLOBALS.QT_Bindings == "PyQt5":

    def getEventPosition(ev):
        return ev.pos()


if PILGLOBALS.QT_Bindings == "PySide6":

    def getEventPosition(ev):
        return ev.position().toPoint()

#
# Application error class
#
class AppException(Exception):

   def __init__(self,msg):
        self.msg=msg



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
def buildconfigfilename(filename, configversion, instance, production):
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
        configpath = os.path.join(userhome, ".config", PILGLOBALS.StandardConfigDir)
    elif PILGLOBALS.isWindows:
        #
        # Windows
        #
        configpath = os.path.join(
            os.environ["HOMEDRIVE"],
            os.environ["HOMEPATH"],
            PILGLOBALS.StandardConfigDir,
        )
    elif PILGLOBALS.isMacos:
        #
        # Mac OS X
        #
        configpath = os.path.join(
            userhome, "Library", "Application Support", PILGLOBALS.StandardConfigDir
        )
    #
    else:
        #
        # Fallback
        #
        configpath = os.path.join(userhome, PILGLOBALS.StandardConfigDir)
    configfilename = os.path.join(configpath, fname)

    return configfilename, configpath


#
# move configfiles from %APPDATA%\pyilper to %HOMEDRIVE%%HOMEPATH%\pyilper_config
#
def moveWindowsConfig(silent):
    if not PILGLOBALS.isWindows:
        return
    oldConfigPath = os.path.join(os.environ["APPDATA"], "pyilper")
    newConfigPath = os.path.join(
        os.environ["HOMEDRIVE"], os.environ["HOMEPATH"], PILGLOBALS.StandardConfigDir
    )
    if not silent:
        print("Copy pyILPER configuration files from AppData to ", newConfigPath)
    if not os.path.isdir(oldConfigPath):
        if not silent:
            print(
                "Error: Directory " + oldConfigPath + " does not exist. Nothing to copy"
            )
        return
    if os.path.isdir(newConfigPath):
        if silent:
            return
        print(
            "Warning: Directory "
            + newConfigPath
            + " already exists. Files in that directory are overwritten!"
        )
        inp = input("Continue? (enter 'YES' uppercase): ")
        if inp != "YES":
            print("cancelled")
            return
    try:
        shutil.copytree(oldConfigPath, newConfigPath, dirs_exist_ok=True)
    except OSError as e:
        print("Error copying config files: " + e.strerror)
        return
    if not silent:
        print("pyILPER config files copied from AppData to ", newConfigPath)


#
#
#  check existence of a serial device
#
def checkSerialDeviceExists(device):
    if PILGLOBALS.Diagnostics:
        print("check for ", device)
        for p in serial.tools.list_ports.comports():
            print(
                "Device found: ",
                p.device,
                " ",
                p.description,
                " ",
                p.manufacturer,
                " ",
                p.product,
                " ",
                p.location,
                " ",
                p.interface,
            )
    for p in serial.tools.list_ports.grep(device):
        if p.device == device:
            return True
    return False


#
#  Interface specification dataclass
#
@dataclass
class cls_Interface_Spec:
    id: int
    name: str
    thread_class: object
    config_class: object
    hardware_class: int
    title: str
    hasAutoreconnect: bool = False


@dataclass
class cls_Tab_Spec:
    id: int
    mod: object
    tab_class: object
    name: str
