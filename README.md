pyILPER2
========

Abstract
--------
pyILPER version 2.x is the successor of pyILPER 1.x. Version 1.x is no longer being developed; only bug fixes are being made.

This document provides a concise overview of the changes in pyILPER 2.0 compared to version 1.9. There are only a few, but important, differences from version 1.x

It is the result of a nearly two-year-long, comprehensive overhaul of the software.


Operating Requirements
----------------------

Python >= 3.11, Pyside6 >= 6.8, pySerial >= 3.5 and LIFUTILS 2.0.2. Qt5 is not supported anymore.


pyILPER Loop
------------

pyILPER creates a virtual loop of emulated HP-IL devices, interfaces, and two scope probes. The loop can be started or stopped from the file menu. The loop has the states "stopped", "waiting for connections" or "running". You can configure the loop to start automatically when pyILPER is called in the pyILPER configuration window.


Interfaces
----------

Interfaces can be configured at an arbitrary position in the loop in the "Virtual HP-IL devices configuration" window. They are now configured in their tab. Please note that <b>each additional interface will slow down the throughput of the loop considerably</b>. As before, the interface types PIL-Box. TCP/IP and socket are available. The PIL-Box interface has an additional configuration option, that tells the box whether to operate in controller on or controller off mode.

The PIL-Box tty speed of 9600 baud is not supported any more.

Interfaces have four states that are indicated by a status indicator in the status bar: "inactive" (black), "disconnected" (red), "waiting for connection" (yellow) and "connected" (green). The loop goes only into "running" state if all interfaces are connected.

After the loop has started, each active interfaces goes into "waiting for connection" state. It goes to "connected" state if either a read and write network connection (TCP/IP, Socket interface) was established or a PIL-Box serial device was found and initialized successfully.

Note: a TCP/IP interface is connected only after the first frame has been sent to the remote host. Therefore, you should generate some traffic on the loop (e.g., RESTORE IO on the HP-71 or powering the HP-41 on and off) to set the TCP/IP interfaces to the “connected” state.

An interface can be deactivated (bridged) if the loop is stopped.


Scope and Probes
----------------

As before, the scope is always the first tab that cannot be moved or deleted. By default, there are two probe devices, "Probe1" and "Probe2" which have no tab. The probes can be seen either in the "Virtual HP-IL device status" window or the "Virtual HP-IL device configuration". The position of the probes can be moved, but they can not be deleted. The probes are activated in the scope tab. Frames captured by "Probe1" are shown in uppercase letters and frames captured by "Probe2" are shown in lowercase letters.


Devices
-------

There were no functional changes to the devices.


Software Status
---------------

This is a development verision that is almost feature complete with the exception of an updated online help.

Most system functions have been tested on Linux. On Windows and macOS only smoke tests were run.


Installing and Running the software
-----------------------------------

- Download the zip file

- Create a Python virtual environment with the software listed above

- Unpack the zip file and go to the top-level directory of the package

- run 

     python -m pyilper2 -v

This show the program version.

The configuration of pyILPER2 is entirely separated from the configuration of version 1.x. You can migrate the configuration of your pyILPER 1.9 production version into a pyILPER 2.0 compatible format:

     python -m pyilper2 --migrate

Now run the program:

     pyilper -m pyiper2

If you did not have a pyilper 2.0 configuration before, a default configuration with one Interface of type PIL-Box is created. pyILPER will start with an error message, that the serial device of the PIL-Box has not been configured. Enter the device name in der Interface tab and start the loop from the file menu.

Configuration with Multiple Interfaces
--------------------------------------

If your pyILPER configuration contains several interfaces, there are a few thins to keep in mind:

- Connect all USB devices

- Start the loop. Check, whether all USB devices connect. If their status stays "connecting" then the serial device in the interface configuration does not exist.

- start the TCP/IP virtual HP-IL devices and make them running.

- start the HP-IL controller last! Please follow the instructions above regarding TCP/IP connections.

