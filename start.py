#!/usr/bin/env python

""" start.py: run pyilper2 as a module located in the current directory """
import runpy
ret=runpy.run_module("pyilper2",run_name="__main__",alter_sys=True)
