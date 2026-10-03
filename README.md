pyILPER2
========

Abstract
--------
pyILPER version 2.x is the successor of pyILPER 1.x. Version 2.x allows you to use multiple interfaces (PIL-Box, TCP/IP, Socket) and includes a more flexible version of the scope.

Version 1.x of pyILPER is no longer being developed; only bug fixes are being made.

Since pyILPER 2 is a beta version, its use is recommended only for people with experience using version 1 of pyILPER.

This document provides a concise overview of the changes in pyILPER 2.0 compared to version 1.9. There are only a few, but important, differences from version 1.x

It is the result of a nearly two-year-long, comprehensive overhaul of the software.


Changes in Operating Requirements
---------------------------------

pyILPER2 requires now:

- Python >= 3.11 
- Pyside6 >= 6.8 
- pySerial >= 3.5 and LIFUTILS 2.0.1

Qt5 is not supported anymore.


pyILPER Loop
------------

pyILPER creates a virtual loop of emulated HP-IL devices, interfaces, and two scope probes. The loop can be started or stopped from the file menu. The loop has either the state "stopped", or "waiting for connections" or "running". In the pyILPER configuration window, you can configure the loop to start automatically,


Interfaces
----------

Interfaces can be configured at an arbitrary position in the loop in the "Virtual HP-IL devices configuration" window. Each interface has its onw tab, where it is configured. Please note that each additional interface will slow down the throughput of the loop considerably. As before, the interface types PIL-Box. TCP/IP and socket are available. The PIL-Box interface has an additional configuration option, that tells the box whether to operate in controller on or controller off mode.

The PIL-Box tty speed of 9600 baud and its special protocol used at this baudrate is not supported any more.

Interfaces have four states that are indicated by a status light in the status bar: "inactive" (black), "disconnected" (red), "waiting for connection" (yellow) and "connected" (green). The loop goes only into "running" state if all interfaces are connected.

After the loop has started, each active interfaces goes into "waiting for connection" state. It goes to "connected" state if either a read and write network connection (TCP/IP, Socket interface) was established or a PIL-Box serial device was found and initialized successfully.

A PIL-Box interface operates only in "autoreconnect" mode, that was introduced with pyILPER 1.9. 

A TCP/IP interface is connected only after the first frame has been sent to the remote host. Therefore, you should generate some traffic on the loop (e.g., RESTORE IO on the HP-71 or powering the HP-41 on and off) to bring the TCP/IP interfaces to the “connected” state.

An interface can be deactivated (bridged) if the loop is stopped.


Scope and Probes
----------------

As before, the scope is always the first tab that cannot be moved or deleted. By default, there are two probe devices, "Probe1" and "Probe2" which have no tab. The probes can be seen either in the "Virtual HP-IL device status" window or the "Virtual HP-IL device configuration". The position of the probes can be moved, but they can not be deleted. The probes are activated in the scope tab. Frames captured by "Probe1" are shown in uppercase letters and frames captured by "Probe2" are shown in lowercase letters.

In pyILPER 1.x the probes were always at a fixed position (after the interface and after the last device).

The scope now has a button to clear the display.

Devices
-------

New devices are now enabled by default.


Software Status
---------------

This is a development verision that is almost feature complete.


Installing and Running the software
-----------------------------------

- Download the zip file

- Create a Python virtual environment with the software listed above

- Unpack the zip file and go to the top-level directory of the unpacked package

Now run from the command line: 

     python -m pyilper2 -v

This show the program version.

The configuration of pyILPER2 is entirely separated from the configuration of version 1.x. You can migrate the configuration of your pyILPER 1.9 production version into a pyILPER 2.0 compatible format:

     python -m pyilper2 --migrate

Now run the program:

     pyilper -m pyilper2

If you did not have a pyilper 2.0 configuration before, a default configuration with one interface of type PIL-Box is created. pyILPER will show some quick start information about how to configure the program for first-time use. Follow the installation steps as described and start the loop from the file menu.


Configuration with Multiple Interfaces
--------------------------------------

If your pyILPER configuration contains several interfaces, there are a few things to keep in mind. It is recommended that you activate the pyILPER virtual loop in the following order:

- Connect all USB devices

- Start the loop. Check, whether all USB devices connect. If their status stays "connecting" then the serial device in the interface configuration does not exist.

- Start any programs for  virtual HP-IL over TCP/IP devices (e.g. IlVideo80.exe) and press their START button.

- Start the HP-IL controller last! Please follow the instructions above regarding TCP/IP connections.


Performance
-----------

The loop throughput of the pyILPER virtual loop of version 2 is the same as that of version 1 with an identical interface/devices configuration.

Each additional interface significantly slows down the virtual loop. Every frame sent by an interface takes a certain amount of time (travel time) to be fully received. This travel time adds up for each interface.  For example, if the throughput of a PIL-Box device is 2,000 frames/s, the travel time for each frame is 0.5 ms. If you have 4 interfaces of this type, the travel time sums up to 2 ms. This will reduce the maximum speed of the pyILPER virtual loop to approximately 500 frames/s, assuming all other overhead is negligible.

This is different with the (real) HP-IL loop. Here, the HP-IL chip built into each device in the loop can determine, after receiving just 3 bits of a frame, whether it can begin forwarding the frame to the next device. This reduces the time lag introduced by devices in the loop considerably.

Acknowledgements
----------------

Much code was taken from ILPER for Windows (Copyright (c) 2008-2013 
J-F Garnier, Visual C++ version by Christoph Gießelink 2016). 
The terminal emulator code was taken from the pyqterm console widget written
by Henning Schroeder. The virtual TCP/IP support of pyILPER was significantly
improved by Christoph Gießelink who also provided many other improvements. The virtual HP7470A plotter engine was derived from the HP2XX software (Heinz W. Werntges, Martin Kroeker). Parts of the HP82162A printer emulation were taken from Eric Smith's Nonpareil emulator.

