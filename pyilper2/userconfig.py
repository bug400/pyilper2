#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pyILPER 2
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
# userconfig class ---------------------------------------------------------
#
# Changelog
# XX.XX.XXXX jsi:

import json
import os
from .pilcore import buildconfigfilename


class cls_userconfig:

    def __init__(self, filename, configversion, instance, production):
        #
        #  determine config file name
        #
        self.__configfile__, self.__configpath__ = buildconfigfilename(
            filename, configversion, instance, production
        )

    #
    #  read configuration, if no configuration exists or the clean flag is set write default configuration
    #
    def read(self, default, clean):
        if not os.path.isfile(self.__configfile__) or clean:
            if not os.path.exists(self.__configpath__):
                os.makedirs(self.__configpath__)
            self.write(default)
            return default
        f = None
        try:
            f = open(self.__configfile__, "r")
            config = json.load(f)
        except Exception as e:
            raise e from e
        finally:
            if f is not None:
                f.close()
        return config

    #
    #  Store configuration, create file if it does not exist
    #
    def write(self, config):
        f = None
        try:
            f = open(self.__configfile__, "w")
            json.dump(config, f, sort_keys=True, indent=3)
        except Exception as e:
            raise e from e
        finally:
            if f is not None:
                f.close()
