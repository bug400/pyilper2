
# Installing Python with the Python Install Manager on Windows

Index
-----

* [General](#general)
* [Installation and Setup](#installation-and-setup)
* [Maintenance of Python Versions](#maintenance-of-python-versions)
* [Working with multiple Python Versions](#working-with-multiple-python-versions)
* [Uninstall Python Install Manager and all Python versions](#uninstall-python-install-manager-and-all-python-versions)

## General

With the Python Install Manager, you can install and manage Python on Windows. This makes it easy to use newer versions of Python. Please note that Python interpreters newer than version 3.13 are only available via the Install Manager.

## Installation and Setup

Unfortunately, the initial setup of the Install Manager is not self-explanatory. Please follow the example below exactly:

- Install the Python Install Manager from the Microsoft Store
- If the download completed, run the Python Install Manager:

     Welcome to the Python installation manager configuration helper.
     
     Windows is not configured to allow paths longer than 260 characters.
     
     Python and some other apps can exceed this limit, but it requires changing a
     system-wide setting, which may need an administrator to approve, and will
     require a reboot. Some packages may fail to install without long path support enabled.

     Update setting now? [y/N] <b>n</b>
     
     The global shortcuts directory is not configured.
     
     Configuring this enables commands like python3.15.exe to run from your
     terminal, but is not needed for the python or py commands (for example, py
     -V:3.15).
     
     We can add the directory (C:\Users\achim\AppData\Local\Python\bin) to PATH now,
     but you will need to restart your terminal to use it. The entry will be removed
     if you run py uninstall --purge, or else you can remove it manually when
     uninstalling Python.

     Add commands directory to your PATH now? [y/N] <b>y</b>

     PATH has been updated, and will take effect after opening a new terminal.
     
     You do not have the latest Python runtime.
     
     Install the current latest version of CPython? If not, you can use 'py install
     default' later to install.
     
     Install CPython now? [Y/n] <b>y</b>

     Python install manager was successfully updated to 26.4.
     
     Please see https://github.com/python/pymanager/releases/tag/26.4 for all changes.
     
     The signature for https://www.python.org/ftp/python/index-windows.json was successfully verified.

     Installing Python 3.15.2.

     Downloading: ....................................................... 

     Extracting: ........................................................ 

     To see all available commands, run 'py help'
     
     
     Configuration checks completed.
     
     To run these checks again, launch Python install manager from your Start menu,
     or py install --configure from the terminal.
     
     
     Usage:

     ...
     
     View online help? [y/N] </b>n</b>

## Maintenance of Python versions

The Install Manager can manage different Python versions on the computer.

To list the installed versions, run:

     py list

To install a specific version of Python run:

     py install (Version)

To uninstall a specific version of Python run:

     py uninstall (Version)

## Working with multiple Python versions

It's easiest to create separate virtual environments for each installed version.
The default Python version, which is called with the python command, is always the most recently published version installed on the system. Other Python versions are invoked with the py command and a version tag.

Example: Python 3.15.2 and 3.14.10 are installed on your system. To create a virtual environment for 3.15.2 run:

     python -m venv test315

To create a virtual environment for 3.14.10 run:
     
     py -V:3.14.10 -m venv test314
     
## Uninstall Python Install Manager and all Python versions

To get rid of all Python versions, do:

     py uninstall --purge

This uninstalls all runtimes saved downloads, removes the global commands directory from PATH, and purges all shortcuts. It does not uninstall the Python Install Manager, which must be removed in the "Apps and Features" section in the "Settings" window.
