#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import logging

import enso.config
from enso.messages import displayMessage
from optparse import OptionParser


ENSO_DIR = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), ".."))

options = None


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


def process_options(argv):
    version = '1.0'
    usageStr = "%prog [options]\n\n"
    parser = OptionParser(usage=usageStr, version="%prog " + version)

    parser.add_option("-l", "--log-level", action="store", dest="loglevel", default="ERROR", help="logging level (CRITICAL, ERROR, INFO, WARNING, DEBUG)")
    parser.add_option("-n", "--no-splash", action="store_false", dest="show_splash", default=True, help="Do not show splash window")
    parser.add_option("-c", "--no-console", action="store_false", dest="show_console", default=True, help="Hide console window")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="No information windows are shown on startup/shutdown")
    parser.add_option("-k", "--hotkey", action="store", dest="hotkey", default="default", help="Hotkey used to invoke Enso. Possible values are: CAPITAL, LSHIFT, RSHIFT, LCONTROL, RCONTROL, LWIN, RWIN")
    parser.add_option("", "--ignore-ensorc", action="store_true", dest="ignore_ensorc", default=False, help="Ignore .ensorc file")

    # Hidden options useful for development
    parser.add_option("", "--commands-dir", action="store", dest="commands_dir", default="default", help="Used to override name of the subdirectory in user home directory that stores custom commands (used for development)")
    parser.add_option("", "--color-scheme", action="store", dest="color_scheme", default="default", help="Used to override default color scheme (used for development)")

    if sys.platform.startswith("win"):
        # Add tray-icon support for win32 platform
        parser.add_option("-t", "--no-tray", action="store_false", dest="show_tray_icon", default=True, help="Hide tray icon")

    opts, args = parser.parse_args(argv)
    return opts, args


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


class LogLevelFilter( logging.Filter, object ):
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




def main(argv = None):
    global options

    opts, args = process_options(argv[1:])
    options = opts

    enso.config.CMDLINE_OPTIONS = options


    logformat = "%(levelname)-9s%(asctime)s %(pathname)s[%(funcName)s:%(lineno)d]: %(message)s"
    loglevel = {
        'CRITICAL' : logging.CRITICAL,
        'ERROR' : logging.ERROR,
        'WARNING' : logging.WARNING,
        'INFO' : logging.INFO,
        'DEBUG' : logging.DEBUG,
        }.get(opts.loglevel, logging.NOTSET)

    if opts.show_console:
        print "Showing console"
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
        print "Hiding console"
        print "Logging into '%s'" % os.path.join(ENSO_DIR, "enso.log")
        sys.stdout = open("stdout.log", "w", 0) #NullDevice()
        sys.stderr = open("stderr.log", "w", 0) #NullDevice()
        logging.basicConfig(
            filename=os.path.join(ENSO_DIR, "enso.log"),
            level=loglevel,
            format=logformat)

    if loglevel == logging.DEBUG:
        pass
        assert logging.debug("default options set:" + repr(opts)) or True
        assert logging.debug("command-line args:" + repr(args)) or True


    if not opts.ignore_ensorc:
        ensorc_path = os.path.expanduser(os.path.join("~",".ensorc"))
        if (not os.path.isfile(ensorc_path) and sys.platform.startswith("win")
            and os.path.isfile(ensorc_path+".lnk")):
            # Extract real .ensorc path from .ensorc.lnk file on Windows platform
            try:
                import pythoncom
                from win32com.shell import shell, shellcon
                link = pythoncom.CoCreateInstance(
                    shell.CLSID_ShellLink,
                    None,
                    pythoncom.CLSCTX_INPROC_SERVER,
                    shell.IID_IShellLink
                )
                link.QueryInterface(pythoncom.IID_IPersistFile).Load(ensorc_path+".lnk")
                path = link.GetPath(shell.SLGP_UNCPRIORITY)
                if path and path[0]:
                    ensorc_path = path[0]
            except Exception, e:
                logging.error("Error parsing .ensorc.lnk file: %s", e)

        if os.path.isfile(ensorc_path):
            logging.info( "Loading '%s'." % ensorc_path )
            contents = open( ensorc_path, "r" ).read()
            compiledContents = compile( contents + "\n", ensorc_path, "exec" )
            exec compiledContents in {}, {}
        else:
            logging.warning(".ensorc file can't be read!")
    else:
        logging.info("Ignoring your .ensorc startup script")

    if opts.hotkey in ("default", "CAPITAL", "LSHIFT", "RSHIFT", "LCONTROL", "RCONTROL", "LWIN", "RWIN"):
        if opts.hotkey != "default":
            #contents += "enso.config.QUASIMODE_START_KEY = \"KEYCODE_%s\"\n" % opts.hotkey
            enso.config.QUASIMODE_START_KEY = "KEYCODE_%s" % opts.hotkey
            logging.info("Enso hotkey has been set to %s" % opts.hotkey)
    else:
        logging.error("Invalid hotkey spec: %s" % opts.hotkey)

    # Can't display message at this phase as on Linux the gtk loop is not active yet
    # at this point and that causes screen artefacts.
    #if not opts.quiet and opts.show_splash:
    #    displayMessage("<p><command>Enso</command> is starting...</p>")
    
    if sys.platform.startswith("win"):
        # Add tray-icon support for win32 platform
        if opts.show_tray_icon:
            # tray-icon code must be run in separate thread otherwise it blocks
            # current thread (using PumpMessages() )
            try:
                import enso.platform.win32.taskbar as taskbar
                threading.Thread(target = taskbar.systray, args = (enso.config,)).start()
            except Exception, e:
                logging.error("Error initializing taskbar systray icon: %s", e)

    if opts.commands_dir != "default":
        logging.info("Default commands directory changed to \"%s\"" % opts.commands_dir)
        enso.config.SCRIPTS_FOLDER_NAME = opts.commands_dir

    if opts.color_scheme != "default":
        logging.info("Changing color scheme to %s" % opts.color_scheme)
        change_color_scheme(opts.color_scheme)

    try:
        # Use Psyco optimization if available
        # Last Psyco available is for Python 2.6 (Win32) and Python 2.7 (Linux, unofficial build from github)
        # There is no Psyco support for Python > 2.7
        import psyco
        logging.info("Using Psyco optimization")
        psyco.profile()
        #psyco.log()
    except:
        pass

    l = logging.getLogger()
    if l.isEnabledFor(logging.DEBUG):
        try:
            l.addFilter(LoggingDebugFilter())
        except:
            pass
        
    # Execute main Enso loop
    enso.run()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# vim:set tabstop=4 shiftwidth=4 expandtab:
