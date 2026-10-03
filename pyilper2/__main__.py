# -*- coding: utf-8 -*-
#
# pyILPER 2.0
#
# An emulator for virtual HP-IL devices for the PIL-Box
# derived from ILPER 1.4.5 for Windows
# Copyright (c) 2008-2013   Jean-Francois Garnier
# C++ version (c) 2013 Christoph Gießelink
# Python Version (c) 2026 Joachim Siebold
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
# Script to run pyilper as a module with python -m pyilper [options]
# Starting pyILPER with command line arguments is only possible if called as module
# Some maintenance functions which are called by a command line options are located here
#
# __main__.py: This file is executed, if pyILPER2 is called as a module
#
# Note: Calling pyILPER as a module is the o n l y reliable way to get access to command
# line parameters. Therefore all code that is executed without calling the main application
# is implemented here.
#
import sys
import os
import shutil
import argparse
from json import JSONDecodeError
from pathlib import Path
from .pyilpermain import main
from .pilglobals import PILGLOBALS
from .pilconfig import cls_pilconfig, PILCONFIG
from .pilcore import buildconfigfilename, decode_pyILPERVersion

# from pyilper2 import __version__, __isProduction__


#
# migrate config from version 1.9 (production) to 2.0
#
def migrateConfig(args):

    newName = PILGLOBALS.PackageName
    oldName = "pyilper"
    #
    #  ask for confirmation
    #
    print("\nW A R N I N G!")
    print("This overwrites the current configuration files of pyILPER 2.0")
    inp = input("Continue? (enter 'YES' uppercase): ")

    if inp != "YES":
        print("cancelled")
        return
    #
    # make backup copy of pyilper config file
    #
    try:
        filename = buildconfigfilename(
            PILGLOBALS.StandardConfigDir,
            "pyilper",
            PILGLOBALS.ConfigVersion,
            args.instance,
            PILGLOBALS.Production,
        )[0]
        if not Path(filename).exists():
            print("No pyilper 1.9 configuration found")
            return
        backupfilename = filename + ".bak"
        shutil.copy(filename, backupfilename)
    except OSError as e:
        print(
            "Error creating backup copy of pyILPER2 confuguration file: " + e.strerror
        )
        return
    #
    # copy files
    #
    count = 0
    for name in ["pyilper", "penconfig", "shortcutconfig"]:
        from_filename = buildconfigfilename("pyilper", name, "2", args.instance, True)[
            0
        ]
        if not os.path.isfile(from_filename):
            continue
        to_filename = buildconfigfilename(
            PILGLOBALS.StandardConfigDir,
            name,
            PILGLOBALS.ConfigVersion,
            args.instance,
            PILGLOBALS.Production,
        )[0]

        try:
            shutil.copy(from_filename, to_filename)
        except shutil.SameFileError as e:
            print(
                "Error copying file "
                + from_filename
                + " "
                + "source and destination file are identical"
            )
            return

        except OSError as e:
            print("Error copying file " + from_filename + ": " + e.strerror)
            try:
                shutil.copy(backupfilename, filename)
            except Exception:
                pass
            return

        print(from_filename)
        print("copied to:")
        print(to_filename)
        count += 1
    #
    # migrate pyilper configuration
    #
    try:
        PILCONFIG.open(
            PILGLOBALS.ConfigVersion,
            args.instance,
            PILGLOBALS.Production,
            False,
        )
        #
        # check version of old configuration must be of 1.9
        #
        oldversion = decode_pyILPERVersion(PILCONFIG.get("pyilper", "version", "0.0.0"))
        if oldversion == 0:
            print("no valid configuration files found for version 1.9.0")
            return
        if oldversion < 10900:
            print("cannot migrate pyilper configuration from versions < 1.9.0")
            return

        PILCONFIG.put(newName, "version", PILGLOBALS.Version)
        #
        # migrate tab configuration
        #
        tabconfig = PILCONFIG.get(oldName, "tabconfig", "")
        if tabconfig == "":
            print("no valid configuration files found for version 1.9.0")
            return
        newTabconfig = [[0, "Scope"], [1, "Interface1"], [9, "Probe1"]]
        for t in tabconfig:
            tabid = t[0]
            tabname = t[1]
            tabid += 1
            newTabconfig.append([tabid, tabname])
        newTabconfig.append([9, "Probe2"])
        PILCONFIG.put(newName, "tabconfig", newTabconfig)
        PILCONFIG.put(newName, "tabconfigchanged", True)
        PILCONFIG.put(newName, "active_tab", 0)
        #
        # migrate interface config
        #
        for oldkey in [
            "if_pilbox_device",
            "if_pilbox_baudrate",
            "if_pilbox_idyframe",
            "if_tcpip_port",
            "if_tcpip_remoteport",
            "if_tcpip_remotehost",
            "if_socket_serverport",
        ]:
            newkey = "Interface1_" + oldkey
            PILCONFIG.migrateKey(oldkey, newkey)
        #
        #       9600 baud not supported any more
        #
        baudrate = PILCONFIG.get("Interface1", "if_pilbox_baudrate", 115200)
        if baudrate == 9600:
            PILCONFIG.put("Interface1", "if_pilbox_baudrate", 115200)
        PILCONFIG.put("Interface1", "if_pilbox_controllermode", False)
        PILCONFIG.put("Interface1", "active", True)
        interfaceid = PILCONFIG.get(oldName, "mode", 0)
        PILCONFIG.put("Interface1", "interface_id", interfaceid)
        #
        # migrate remaining pyILPER config
        #
        PILCONFIG.put(newName, "autostart", True)

        for k in [
            "workdir",
            "usebom",
            "terminalcharsize",
            "directorycharsize",
            "helpposition",
            "hp2225b_screenwidth",
            "hp82162a_pixelsize",
            "lifutilspath",
            "papersize",
            "position",
        ]:
            oldkey = oldName + "_" + k
            newkey = newName + "_" + k
            PILCONFIG.migrateKey(oldkey, newkey)
        #
        # remove old keys
        #
        PILCONFIG.delKeys("pyilper")
        PILCONFIG.delKeys("if")
        PILCONFIG.save()
    #
    #   exception handling, restore previous pyilper2 config
    #
    except Exception as ex:
        print("Error migrating configuration " + repr(ex))
        try:
            shutil.copy(backupfilename, filename)
            print("previous pyilper2 configuration restored")
        except Exception:
            pass
        return

    print(
        count,
        "files copied and migrated. Restart pyILPER without the 'migrate' option now",
    )


#
# copy configuration data from devel to production and vice versa
# - a development/beta version of pyILPER copies the files of the
#   production version
# - a production version of pyILPER copies the files of the development/beta
#   version
#
def copyConfig(args):
    count = 0
    #
    #  get version numbers
    #
    from_config = cls_pilconfig()
    to_config = cls_pilconfig()
    try:
        from_config.open(
            PILGLOBALS.ConfigVersion, args.instance, not PILGLOBALS.Production, False
        )
        from_version = from_config.get(PILGLOBALS.PackageName, "version", "0.0.0")
        to_config.open(
            PILGLOBALS.ConfigVersion, args.instance, PILGLOBALS.Production, False
        )
        to_version = to_config.get(PILGLOBALS.PackageName, "version", "0.0.0")
    except Exception as e:
        print("Error reading pyILPER configuration file(s): ")
        return
    if from_version == "0.0.0":
        print("Error: there are no configuration files to copy")
        return
    #
    #  ask for confirmation
    #
    print("\nW A R N I N G!")
    print("This overwrites the configuration files")
    if PILGLOBALS.Production:
        print("of the production version: ", to_version)
    else:
        print("of the development/beta version: ", to_version)
    print("with the configuration files")
    if PILGLOBALS.Production:
        print("of the development/beta version: ", from_version)
    else:
        print("of the production version: ", from_version)
    inp = input("Continue? (enter 'YES' uppercase): ")
    if inp != "YES":
        print("cancelled")
        return
    #
    #  now copy configuration files
    #
    for name in ["pyilper", "penconfig", "shortcutconfig"]:
        from_filename = buildconfigfilename(
            PILGLOBALS.StandardConfigDir,
            name,
            PILGLOBALS.ConfigVersion,
            args.instance,
            not PILGLOBALS.Production,
        )[0]
        if not os.path.isfile(from_filename):
            continue
        to_filename = buildconfigfilename(
            PILGLOBALS.StandardConfigDir,
            name,
            PILGLOBALS.ConfigVersion,
            args.instance,
            PILGLOBALS.Production,
        )[0]
        try:
            shutil.copy(from_filename, to_filename)
        except shutil.SameFileError as e:
            print(
                "Error copying file "
                + from_filename
                + " "
                + "source and destination file are identical"
            )
            return
        except OSError as e:
            print("Error copying file " + from_filename + ": " + e.strerror)
            return
        print(from_filename)
        print("copied to:")
        print(to_filename)
        count += 1
    print(count, "files copied. Restart pyILPER without the 'cc' option now")


#
class ValidateScale(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values < 1.0 or values > 4.0:
            parser.error("Scale must between 1.0 and 4.0.")
        setattr(namespace, self.dest, values)


def start():
    parser = argparse.ArgumentParser(
        description="Start pyILPER with command line parameters",
        usage="python -m pyilper [options]",
    )
    parser.add_argument(
        "--instance",
        "-instance",
        default="",
        help="Start a pyILPER instance INSTANCE. This instance has an own configuration file.",
    )
    parser.add_argument(
        "--cc",
        "-cc",
        action="store_true",
        help="Copy configuration from development to production version and vice versa",
    )
    parser.add_argument(
        "--clean",
        "-clean",
        action="store_true",
        help="Start pyILPER with a config file which is reset to defaults",
    )
    parser.add_argument(
        "--use-system-browser",
        "--use-system-browser",
        action="store_true",
        help="Use default system browser for help system",
        dest="useSystemBrowser",
    )
    parser.add_argument("--diag", "-diag", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--scale",
        "-scale",
        type=float,
        action=ValidateScale,
        help="Force scaling for high-DPI displays. 1.0<=SCALE<=4.0",
    )
    parser.add_argument(
        "--migrate",
        "-migrate",
        action="store_true",
        help="Migrate pyILPER configuration from version 1.9",
    )

    parser.add_argument("--v", "-v", action="store_true", help="Show pyILPER version")
    args = parser.parse_args()
    #
    #  show version
    #
    if args.v:
        print("pyILPER ", PILGLOBALS.Version, end="")
        sys.exit(0)
    #
    #   run -cc and -migrate commands
    #
    if args.cc:
        copyConfig(args)
        sys.exit(1)
    if args.migrate:
        migrateConfig(args)
        sys.exit(1)
    #
    #  set scaling, if specified
    #
    if args.scale:
        os.putenv("QT_SCALE_FACTOR", str(args.scale))
    #
    #  set command line arguments to PILGLOBALS and run pyILPER
    #
    PILGLOBALS.setArgs(args)
    main()


if __name__ == "__main__":
    rc = 1
    start()
