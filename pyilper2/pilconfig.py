#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pilconfig for pyILPER
#
# (c) 2015 Joachim Siebold
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
# pilconfig class -------------------------------------------
#
# Changelog
# XX.XX.XXXX jsi:
#
from .userconfig import cls_userconfig
from .pilglobals import PILGLOBALS


class cls_pilconfig:
    #
    #  initialize: create instance
    #
    def __init__(self):
        self.__config__ = {}
        self.__userconfig__ = None
        return

    #
    #  open: read in the configuration file into the dictionary
    #  if the configuration file does not exist, an empty file is created
    #  If clean is true do not read the config file
    #
    def open(self, configversion, instance, production, clean):
        self.__userconfig__ = cls_userconfig(
            "pyilper", configversion, instance, production
        )
        try:
            self.__config__ = self.__userconfig__.read(self.__config__, clean)
        except Exception as e:
            e.add_note("cannot get configuration from file")
            raise e from e

    #
    #  Get a key from the configuration dictionary. To initialize a key a default
    #  value can be specified
    #
    def get(self, name, param, default=None):
        pname = name + "_" + param
        try:
            p = self.__config__[pname]
        except KeyError as e:
            if default is None:
                e.add_note("configuration parameter not found: " + pname)
                raise e from e
            else:
                self.__config__[pname] = default
                p = default
        return p

    #
    #  Get a key, first a local key, if the value is -1 then get the global key
    #
    def get_dual(self, name, param):
        p = self.get(name, param)
        if p == -1:
            p = self.get(PILGLOBALS.PackageName, param)
        return p

    #
    #  Put a key into the configuration dictrionary
    #
    def put(self, name, param, value):
        pname = name + "_" + param
        self.__config__[pname] = value

    #
    #  Save the dictionary to the configuration file
    #
    def save(self):
        try:
            self.__userconfig__.write(self.__config__)
        except Exception as e:
            e.add_note("cannot save configuration")
            raise e from e

    #
    #  Get the keys of the configuration file
    #
    def getkeys(self):
        return self.__config__.keys()

    #
    #  remove an entry
    #
    def remove(self, key):
        try:
            del self.__config__[key]
        except KeyError:
            pass

    #
    #  migrate a key
    #
    def migrateKey(self, oldkey, newkey):
        if oldkey in self.__config__.keys():
            try:
                self.__config__[newkey] = self.__config__[oldkey]
                del self.__config__[oldkey]
            except KeyError:
                pass

    #
    #  debug print
    #
    def dump(self):
        print(self.__config__)
    #
    #  delete keys beginning with prefix (excluding a _)
    #
    def delEntries(self,prefix):
        for key in self.__config__:
            keyPrefix=key.split(sep="_")[0]
            if keyPrefix == prefix:
                print("remove",key)
                self.remove(key)


#
#  create config instance
#
PILCONFIG = cls_pilconfig()
