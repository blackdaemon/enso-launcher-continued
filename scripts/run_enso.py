#! /usr/bin/env python
# vim:set tabstop=4 shiftwidth=4 expandtab:
# -*- coding: utf-8 -*-

__updated__ = "2019-05-03"

import atexit

atexit_register = atexit.register
atexit_functions = []

def my_atexit_register(func, *args, **kwargs):
    global atexit_functions
    atexit_functions.append((func, args, kwargs))
    atexit_register(func, *args, **kwargs)

def run_all_exitfunctions():
    global atexit_functions
    for func, args, kwargs in atexit_functions:
        try:
            print "Running exit function: ", func.__name__
            func(*args, **kwargs)
        except:
            pass
    
atexit.register = my_atexit_register
atexit.run_all_exitfunctions = run_all_exitfunctions 

import logging
import os
import socket
import sys
import threading

import click

import enso.config
import enso.version

from enso._version_local import VERSION

_ = enso.version  # Keep pyLint happy
ENSO_DIR = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), ".."))


# Disable IPV6 address lookup
# http://stackoverflow.com/questions/2014534/force-python-mechanize-urllib2-to-only-use-a-requests
# FIXME: Resolve this based on current location and user configuration
# FIXME: Move this somewhere else
# This hack will force IPV4 DNS lookups only.
origGetAddrInfo = socket.getaddrinfo


def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
    return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)

# replace the original socket.getaddrinfo by our version
#socket.getaddrinfo = getAddrInfoWrapper


def change_color_scheme(color):
    """Change Enso color scheme"""
    if not hasattr(enso.config, "COLOR_SCHEMES"):
        print "No COLOR_SCHEMES setting found in config.py. Color scheme will not be changed."
        return
    if color not in enso.config.COLOR_SCHEMES:
        print "Unknown color scheme '%s'. Leaving defaults." % color
        return
    from enso.quasimode import layout
    scheme = enso.config.COLOR_SCHEMES[color]
    layout.WHITE = scheme[0]
    layout.DESIGNER_GREEN = scheme[1]
    layout.DARK_GREEN = scheme[2]
    layout.BLACK = scheme[3]
    layout.DESCRIPTION_BACKGROUND_COLOR = layout.COLOR_DESIGNER_GREEN + "cc"
    layout.MAIN_BACKGROUND_COLOR = layout.COLOR_BLACK + "d8"


class LoggingDebugFilter(logging.Filter):

    def filter(self, record):
        """
        Determine if the specified record is to be logged.

        Is the specified record to be logged? Returns 0 for no, nonzero for
        yes. If deemed appropriate, the record may be modified in-place.
        """
        res = logging.Filter.filter(self, record)
        if res == 0:
            return res
        if record.module == "inotify_buffer" and record.funcName == "run":
            return 0
        return res


class LogLevelFilter(logging.Filter, object):
    """Filters (lets through) all messages with level <= LEVEL"""
    # http://stackoverflow.com/a/24956305/408556

    def __init__(self, name, passlevel, reject):
        super(LogLevelFilter, self).__init__(name)
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        passed = super(LogLevelFilter, self).filter(record)
        if self.reject:
            return passed and (record.levelno > self.passlevel)
        else:
            return passed and (record.levelno <= self.passlevel)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-l', '--log-level', default="ERROR",
              type=click.Choice(['CRITICAL', 'ERROR', 'INFO', 'WARNING', 'DEBUG']),
              show_default=True, help='Log level.')
@click.option('-n', '--no-splash', is_flag=True, help='Do not show splash window.')
@click.option('-c', '--no-console', is_flag=True, help='Do not show console window.')
@click.option('-q', '--quiet', is_flag=True,
              help='No information windows are shown on startup/shutdown.')
@click.option('-i', '--ignore-config', is_flag=True, help='Ignore .ensorc file.')
@click.option('-k', '--hotkey',
              type=click.Choice(['CAPITAL', 'LSHIFT', 'RSHIFT', 'LCONTROL',
                                 'RCONTROL', 'LWIN', 'RWIN']),
              help="Override the hotkey to invoke Enso interface set in .ensorc.")
@click.option("--commands-dir",
              help="Override name of the subdirectory in user home directory that stores custom commands (used for development)")
@click.option("--color-scheme",
              type=click.Choice(enso.config.COLOR_SCHEMES.keys()[1:]),
              help="Override default color scheme (used for development).")
@click.option("-t", "--no-tray-icon", is_flag=True, help="Hide tray icon (only on Windows)")
@click.version_option(version=VERSION)
def main(log_level, no_splash, no_console, quiet, ignore_config, hotkey,
         commands_dir, color_scheme, no_tray_icon):
    """
    Enso: Linguistic command-line launcher
    """
    if not ignore_config:
        # Load custom user config first
        enso.config.load_ensorc()
    else:
        logging.info("Ignoring your .ensorc startup script")

    enso.config.CMDLINE_OPTIONS = {
        'log_level': log_level,
        'no_splash': no_splash,
        'no_console': no_console,
        'quiet': quiet,
        'ignore_config': ignore_config,
        'hotkey': hotkey,
        'commands_dir': commands_dir,
        'color_scheme': color_scheme,
        'no_tray_icon': no_tray_icon,
    }

    logformat = "%(levelname)-9s%(asctime)s %(pathname)s[%(funcName)s:%(lineno)d]: %(message)s"
    loglevel = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
    }.get(log_level, logging.NOTSET)

    if not no_console:
        MIN_LEVEL = loglevel
        STDOUT_MAX_LEVEL = logging.WARNING
        stdout_hdlr = logging.StreamHandler(sys.stdout)
        stdout_hdlr.addFilter(LogLevelFilter('', STDOUT_MAX_LEVEL, False))
        stdout_hdlr.setFormatter(logging.Formatter(logformat))
        stdout_hdlr.setLevel(MIN_LEVEL)

        stderr_hdlr = logging.StreamHandler(sys.stderr)
        stderr_hdlr.addFilter(LogLevelFilter('', STDOUT_MAX_LEVEL, True))
        stderr_hdlr.setFormatter(logging.Formatter(logformat))
        stderr_hdlr.setLevel(MIN_LEVEL)

        rootLogger = logging.getLogger()
        rootLogger.addHandler(stdout_hdlr)
        rootLogger.addHandler(stderr_hdlr)
        rootLogger.setLevel(MIN_LEVEL)
    else:
        click.echo("Logging into '%s'" % os.path.join(ENSO_DIR, "enso.log"))
        sys.stdout = open("stdout.log", "w", 0)  # NullDevice()
        sys.stderr = open("stderr.log", "w", 0)  # NullDevice()
        logging.basicConfig(
            filename=os.path.join(ENSO_DIR, "enso.log"),
            level=loglevel,
            format=logformat)

    if loglevel == logging.DEBUG:
        pass
        assert logging.debug("default options set:" + repr(enso.config.CMDLINE_OPTIONS)) or True
        assert logging.debug("command-line args:" + repr(enso.config.CMDLINE_OPTIONS)) or True

    if hotkey:
        #contents += "enso.config.QUASIMODE_START_KEY = \"KEYCODE_%s\"\n" % opts.hotkey
        enso.config.QUASIMODE_START_KEY = "KEYCODE_%s" % hotkey
        logging.info("Enso hotkey has been set to %s" % hotkey)

    # Can't display message at this phase as on Linux the gtk loop is not active yet
    # at this point and that causes screen artifacts. Will be displayed in the init
    # handler instead (initialized in enso.run()
    # if not opts.quiet and opts.show_splash:
    #    displayMessage("<p><command>Enso</command> is starting...</p>")
    enso.config.SHOW_SPLASH = not quiet and not no_splash

    if sys.platform.startswith("win"):
        # Add tray-icon support for win32 platform
        if not no_tray_icon:
            # tray-icon code must be run in separate thread otherwise it blocks
            # current thread (using PumpMessages() )
            try:
                import enso.platform.win32.taskbar as taskbar
                threading.Thread(
                    target=taskbar.systray, args=(enso.config,)).start()
            except Exception as e:
                logging.error("Error initializing taskbar systray icon: %s", e)

    if commands_dir:
        logging.info(
            "Default commands directory changed to \"%s\"" % commands_dir)
        enso.config.SCRIPTS_FOLDER_NAME = commands_dir

    if color_scheme:
        logging.info("Changing color scheme to %s" % color_scheme)
        change_color_scheme(color_scheme)

    try:
        # Use Psyco optimization if available
        # Last Psyco available is for Python 2.6 (Win32) and Python 2.7 (Linux, unofficial build from github)
        # There is no Psyco support for Python > 2.7
        import psyco  # @UnresolvedImport
        psyco.profile()
        # psyco.log()
    except Exception as e:
        """
        try:
            from enso.thirdparty import psyco  # @UnresolvedImport
            psyco.profile()
            # psyco.log()
        except Exception as e:
            logging.error(e)
        else:
            logging.info(
                "Using Psyco optimization; Psyco for Python 2.7 (experimental)")
        """
        pass
    else:
        logging.info("Using Psyco optimization; Psyco for Python <= 2.6")

    l = logging.getLogger()
    if l.isEnabledFor(logging.DEBUG):
        try:
            l.addFilter(LoggingDebugFilter())
        except:
            pass

    # Execute main Enso loop
    enso.run()
    
    import time
    time.sleep(10)
    
    import traceback
    
    thread_names = dict([(t.ident, t.name) for t in threading.enumerate()])
    for thread_id, frame in sys._current_frames().iteritems():
        print("Thread %s:" % thread_names.get(thread_id, thread_id))
        traceback.print_stack(frame)
        print()
    
    return 0


if __name__ == "__main__":
    #sys.exit(main(sys.argv))
    main()
