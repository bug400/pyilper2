# pyILPER Installation Instructions for Version 2.0

Index
-----
* [Overview](#overview)
* [Requirements](#requirements)
* [Installation with pip from PyPi](#installation-with-pip-from-pypi)
     * [Get a Python interpreter for your system](#get-a-python-interpreter-for-your-system)
     * [Create a virtual Python environment for pyILPER version 2](#create-a-virtual-python-environment-for-pyilper-version-2)
     * [Activate the virtual Python environment](#activate-the-virtual-python-environment)
     * [Install pyILPER version 2 and its runtime components from PyPi](#install-pyilper-version-2-and-its-runtime-components-from-pypi)
     * [Launch pyILPER](#launch-pyilper)
     * [Create desktop shortcuts](#create-desktop-shortcuts)
     * [Sample Installation on Windows](#sample-installation-on-windows)
     * [Sample Installation on macOS](#sample-installation-on-macos)
     * [Sample Installation on Linux](#sample-installation-on-linux)
* [Alternative Installation Methods](#alternative-installation-methods)
     * [Offline Installation with pip](#offline-installation-with-pip)
     * [Installation of releases published on GitHub](#installation-of-releases-published-on-github)
     * [Installation of development versions](#installation-of-development-versions)
* [Post Installation Steps](#post-installation-steps)
     * [Installation of the LIFUTILS](#installation-of-the-lifutils)
     * [Migrate configuration files of earlier versions of pyILPER](#migrate-configuration-files-of-earlier-versions-of-pyilper)
     * [Get the configuration files of a development version](#get-the-configuration-files-of-a-development-version)
     * [pyILPER Setup](#pyilper-setup)
     * [pyILPER Documentation](#pyilper-documentation)
* [Virtual Environment Maintenance](#virtual-environment-maintenance)

## Overview

This document describes in detail the installation of pyILPER and its required Python components. 

First, the system requirements are described; then, the installation process using pip—the standard method for using pyilper—is explained. 
In addition, the installation from release or development ZIP files is demonstrated.
Next, the steps to be performed after installation are described. Finally, the process of maintaining a virtual environment with pip is demonstrated.

## Requirements

To run pyILPER Version 2.x, you need:

* Python version 3.11 or higher. Version 3.13 is currently recommended.
* Qt version 6.8 or higher with the PySide6 language bindings (Qt version 5.x is not supported)
* The Python bindings for  Qt Webengine
* pySerial  3.5 or higher
* [LIFUTILS](https://github.com/bug400/lifutils/releases) (the most recent version)

pyILPER version 2.x has only been tested on a larger scale with the versions of Python and Python packages listed as recommended.

Minimum version means that earlier versions will definitely not work.

More recent macOS versions and Windows 11 already provide a USB serial driver for the PIL-Box.

Linux does not need to install any driver software.


## Installation with pip from PyPi

The installation of pyILPER version 2.x and the required runtime software from PyPi requires the following steps:

### Get a Python interpreter for your system

* Windows: download and install the [Python Install Manager](PYTHON_INSTALL_MANAGER.md) from the Microsoft Store 
* macOS: download and install the universal installer from the [www.python.org](https://www.python.org) website
* Linux: install it from system repositories if not already installed on your system

### Create a virtual Python environment for pyILPER version 2

A virtual environment is a directory tree that contains a dedicated Python runtime version with pyILPER version 2.x
and all the necessary libraries and software components to run this software for the current user. This environment must be "activated" (see below), and it works isolated from the 
system-wide Python components or other virtual Python environments.

Installing pyILPER in a virtual environment does not affect your system configuration.

Note: you can also easily install pyILPER version 2.x in a virtual environment where pyILPER version 1.x is already installed.

A virtual environment can be removed by simply removing its directory tree. This does not affect the configuration files of any pyILPER version.

See [this guide](https://docs.python.org/3/library/venv.html#how-venvs-work) if you want to know more about virtual Python environments.

### Activate the virtual Python environment

To use a virtual Python environment, an activation script must be called. An activated environment is indicated
in the prompt string. 

- Windows: <path to the virtual environment directory>\scripts\activate
- macOS, Linux: source <path to the virtual environment>\bin\activate

### Install pyILPER version 2 and its runtime components from PyPi

This step fetches pyILPER version 2 and the necessary runtime components (Qt6, PySide6 language bindings, and pySerial)
from the [Python Package Index (PyPi)](https://pypi.org), which is the official third-party software repository for Python. 

     python -m pip install pyilper2

You can also install additional software in the environment from the Python Package Index.

See [Virtual Environment Maintenance](#virtual-environment-maintenance) on how to update an existing pyILPER2 version.

<b>Warning: always call the Python interpreter "python3" if you create a virtual environment and "python" after the environment has been activated!!!</b>

### Launch pyILPER

The recommended way to start pyILPER version 2 from a command line is:

      python -m pyilper2 <optional command line parameters>
      
You can use optional command line parameters here, and you will see all diagnostics and runtime error messages that may occur.
      
In some system environments, error messages may appear regarding the activation of graphics acceleration. These messages can usually be ignored. If pyilper terminates at this point, run the program using the following command:

     python -m pyilper2 --use-system-browser

The shortcut command:

     pyilper2

does not accept any command line parameters and does not show any runtime errors on Windows. Use this command to create desktop shortcuts.

To start pyILPER version 2.x from an unzipped source directory use:

     python start.py <optional command line parameters>


### Create desktop shortcuts

You can launch pyILPER version 2.x without activating the Python environment:

     (Virtual environment directory)/bin/python -m pyilper2 <optional command line parameters> (Linux, macOS)
     
     (Virtual environment directory)/scripts/pythonw -m pyilper2 <optional command line parameters> (Windows)

Use this command to create desktop shortcuts.

On macOS use the Automator application to create a desktop shortcut. Use the "run shell script" action and enter the full path to the pyilper script in the bin directory of the virtual environment. Save it as a program and drag it to the desktop. See [this guide](https://www.hpmuseum.org/forum/thread-3824-post-150519.html#pid150519) for details, but enter your proper pyILPER path.



### Sample Installation on Windows

Note: use the "Command Line" instead of the "Terminal (PowerShell)" application to enter the commands below. Using the "Activate.ps1" PowerShell script requires issuing the PowerShell command:

     PS C:> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

To install the Python interpreter, open the Microsoft Store, enter the search term "Python" and select the recommended version (see above) for installation. Python is installed for the current user.

Note: Python version 3.13 is the last version that can be installed from the Microsoft Store. Newer versions must be installed using the [Python Install Manager](PYTHON_INSTALL_MANAGER.md).

Example: create a virtual environment "pytest" in the home directory of the current user, install and start pyILPER version 2.x:


     C:\>cd %USERPROFILE%                                    (change to users home directory)
     
     C:\Users\bug400>python3 -m venv pytest                  (create environment %USERPROFILE%\py313, use python3 to call the interpreter here!!!)

     C:\Users\bug400>pytest\scripts\activate                 (activate the environment, the environment name becomes component of the prompt string)
     
     (pytest) C:\Users\bug400>python -m pip install pyilper2 (install pyILPER version 2,x with the required runtime dependecies)
     Collecting pyilper2
       Obtaining dependency information for pyilper2 from https://files.pythonhosted.org/packages/3e/
     
     ...
     
     Installing collected packages: pyserial, shiboken6, PySide6-Essentials, PySide6-Addons, pyside6, pyilper2
     Successfully installed PySide6-Addons-6.8.1 PySide6-Essentials-6.8.1 pyilper-2.0.0 pyserial-3.5 pyside6-6.8.1 shiboken6-6.8.1
     
     [notice] A new release of pip is available: 23.2.1 -> 23.3.2
     [notice] To update, run: python.exe -m pip install --upgrade pip
     
     (pytest) C:\Users\bug400>python -m pyilper2 -v           (display version number of pyILPER version 2.x)



If the Python interpreter is run for the first time, a window opens and requests firewall permissions. To grant permissions for Python applications, administrator privileges are needed.


### Sample Installation on macOS

Install Python for macOS from the [Python website](https://www.python.org/). Choose the recommended Python version (see above), download and install the macOS 64-bit universal installer. You need administrator privileges for that.

See [Using Python on a Mac](https://docs.python.org/3/using/mac.html) for further details.

Example: create a virtual environment "pytest" in the home directory of the current user, install and start pyILPER version 2.x:

     node1-mac:~ bug400$ python3 -m venv pytest                  (create virtual environment ~/py313)
     node1-mac:~ bug400$ source pytest/bin/activate              (activate virtual environment ~/py313)
     (pytest) node1-mac:~ bug400$ python -m pip install pyilper2 (install pyILPER and required runtime components)
     Collecting pyilper2
       Obtaining dependency information for pyilper2 from https://files.pythonhosted.org/packages/3e

     ...

     Using cached shiboken6-6.8.1-cp38-abi3-macosx_11_0_universal2.whl (406 kB)
     Installing collected packages: pyserial, shiboken6, PySide6-Essentials, PySide6-Addons, pyside6, pyilper2
     Successfully installed PySide6-Addons-6.8.1 PySide6-Essentials-6.8.1 pyilper-2.0.0 pyserial-3.5 pyside6-6.8.1 shiboken6-6.8.1
     
     [notice] A new release of pip is available: 23.2.1 -> 23.3.2
     [notice] To update, run: pip install --upgrade pip
     (pytest) node1-mac:~ bug400$ python -m pyilper2 -v           (display version number of pyILPER version 2.x)
     

### Sample Installation on Linux

Generally, it is recommended to use the Python Interpreter and the Qt software provided by the Linux distribution. 
The [pyILPER Releases page](https://github.com/bug400/pyilper2/releases/) also provides an installation package for the current Debian release. Installing this package will add the necessary dependencies to the system and create a menu entry to start the program. This package might also be installable on Linux distributions that were derived from the DEBIAN release in question (Ubuntu, Raspberry Pi OS).

See the release comments, which version of DEBIAN is currently supported. To install the .deb file, issue the 
following command as root in the directory containing the installer file:

    apt install ./pyilper2_X.Y.Z_all.deb 

This will also install additional software components, which are necessary to run pyILPER. 

**Note:** This command installs the software package from a downloaded file, not from a repository. To obtain a new version of the software, you must download the corresponding deb package and install it using the command above. The previous program version will then be overwritten.

If pyilper was installed as a Debian package, there is no need to create a virtual Python environment. After installing the .deb package, you can check the pyILPER version:

    python -m pyilper2 -v

from the command line. If no error messages are displayed, the installation was successful.


For non-DEBIAN Linux systems, you should try to install the [required components](#requirements) from
the distribution repositories.

If you would like to install pyILPER from PyPI, follow the macOS installation instructions. Please note that there may be problems with incompatible system libraries.

## Alternative Installation Methods

### Offline Installation with pip

To perform an offline installation of pyILPER, you have to download and install the pyILPER wheel file from PyPi:

* Open the [PyPi Website](https://pypi.org)
* Search for pyilper2
* Select pyilper2 from the project list
* Check the Release files tab
* Download the whl file for the pyILPER release you want to install
* Active your Python environment
* Install the whl file

     python -m pip install  pyilper2-2.X.Y-py3-none-any.whl

### Installation of releases published on GitHub

To install pyILPER version 2.x this way, the above mentioned system requirements must be installed on your computer.

Download the latest pyILPER version 2.x source code zip-file from the [pyILPER Releases page](https://github.com/bug400/pyilper2/releases/) and unzip it in an arbitrary location. You get the pyILPER version 2.x directory pyilper2-x.y.z, where x.y.z is the version number.

Now you can start pyILPER with:

      python <Path to the pyILPER version 2.x directory>/start.py <optional parameters> (Linux, macOS)
      or
      pythonw <Path to the pyILPER version 2.x directory>/start.py <optional parameters> (Windows)


Note: it depends on your operating system configuration whether the Python interpreter is invoked as "python" or "python3".


### Installation of development versions

Beta versions of pyILPER version 2.x are published on the [release page](https://github.com/bug400/pyilper2/releases). Download the source code zip file and proceed as described below.

To use development versions of pyILPER version 2.x download the pyilper2-master.zip file from the GitHub [front page of pyILPER](https://github.com/bug400/pyilper2) ("Download ZIP" button). 

Unzip the downloaded file to an arbitrary location in your file system.

Start pyILPER as described in the previous chapter.

Note:

* Development versions are work in progress and were tested roughly. They are not tested on all platforms.  They may crash and may ruin your data at worst.
* Beta versions are tested more thoroughly on all supported platforms. They are intended for public testing but should not be used for production.
* The beta or development versions do not affect the configuration of an already installed production version because different naming conventions are used for the configuration files.

To obtain more recent development versions of pyILPER version 2.x download the pyilper2-master.zip file again. If you are familiar with a Git client, you can synchronize a local pyilper2 repository with the remote GitHub repository.

## Post Installation Steps

### Installation of the LIFUTILS

In order to use the file and disk management functions and the virtual HP7470A plotter,
an up-to-date version of the [LIFUTILS](https://github.com/bug400/lifutils/releases)
must be installed. See the [Installation Instructions](https://github.com/bug400/lifutils/blob/master/INSTALL.md) for further details.


### Migrate configuration files of earlier versions of pyILPER

You can migrate the pyILPER configuration of a production version 1.9.x to pyILPER 2.0.

Run the following command once:

     python -m pyilper2 --migrate
     
Note: it is not possible to migrate from a pyILPER version prior to 1.9. In this case, you must first install version 1.9 and run it once. This will update older configuration files to version 1.9.


### Get the configuration files of a development version

If you were using a development version of pyILPER 2.x, you can copy the configuration files to the production version.

Run the following command once:

     python -m pyilper2 -cc

     
### pyILPER Setup

If pyILPER version 2.x is started for the first time, the built-in help window opens and explains the first steps for getting started. Leave the help window open and follow the instructions to complete the necessary configuration steps.


### pyILPER Documentation

See the online documentation, which can be launched from the Help menu.

If the user manual is not available in pyILPER due to missing language bindings, you can also display it with your web browser. Search for the pyILPER version 2.x installation in the virtual environment (usually below the site-packages directory) and open the file pyilper2/Manual/index.html.


## Virtual Environment Maintenance

Generally, it is recommended to check whether a new version of pyILPER version 2.x exists and to upgrade that package only.

Note: To upgrade the Python interpreter itself, it is safest to uninstall the old interpreter and install the new interpreter. If there is a major update of the Python interpreter (e.g. from 3.14 to 3.15), then you must recreate the virtual environment.

To do virtual environment maintenance, you have to activate it first:

     <path to venv directory>/scripts/activate (Windows)
     or
     source <path to venv directory>/bin/activate (macOS, Linux)


Deactivate an environment:

     deactivate

Check for packages that can be updated:

     python -m pip list --outdated

Update pyILPER version 2.x:

     python -m pip install --upgrade pyilper2


Further maintenance commands:

List installed packages:

     python -m pip list

Install a package:

     python -m pip install <packagename>

Show details of a package:

     python -m pip show <packagename>

Remove a package:

     python -m pip uninstall <packagename>

Check for new versions of a package

     python -m pip list -o

Upgrade a package (pip itself can be upgraded with pip)

     python -m pip install --upgrade <packagename>

Clear package cache (saves space on disk):

     python -m pip cache  purge

Remove an environment:

     Delete the entire directory tree of the environment

