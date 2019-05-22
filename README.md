Enso Readme
===========

Enso is an extensible, cross-platform quasimodal linguistic
command-line interface written in Python.

Building Enso
-------------

To build Enso, you need:
  * Python 2.6 or above
    This can be found at http://www.python.org.

  * Following additional modules should be installed using 'pip' or 'easyinstall':
    ccy
    httplib2
    iniparse
    ujson (or json)
    netifaces
    pygeoip
    pyparsing
    python-dateutil
    shutilwhich
    urllib3
    watchdog
    backports.functools_lru_cache
    
  * Optionally also:
    psyco (improves performance significantly, but is avaliable only for Python <= 2.6)
    
  
You'll also need the appropriate prerequisites for your particular
platform.  Please consult one of the following files:

  README.osx    (Mac OS X)
  README.win32  (Microsoft Windows)
  README.linux  (Linux and other Un*x-based platforms)

Once you've read this file, just run 'scons' from the root directory
of the source tree.

Running Enso
------------

To run Enso, just excecute the following from the root directory of
the source tree:

  python scripts/run_enso.py

Installing Enso System-Wide
---------------------------

Enso has a distutils-based install script that can be used to install
Enso system-wide, but it currently only works on Linux (see issue 19).

To use it, just run

  python setup.py install

  
