import logging
import os
import sys

from defaults import *


ENSORC_PATH = os.path.expanduser(os.path.join("~", ".ensorc"))
ENSORC_LOADED = False


def load_ensorc():
    global ENSORC_PATH, ENSORC_LOADED

    if (not os.path.isfile(ENSORC_PATH) and sys.platform.startswith("win") and
            os.path.isfile(ENSORC_PATH + ".lnk")):
        # Extract real .ensorc path from .ensorc.lnk file on Windows
        # platform
        try:
            import pythoncom  # @UnresolvedImport
            from win32com.shell import shell, shellcon  # @UnresolvedImport @UnusedImport
            link = pythoncom.CoCreateInstance(  # @UndefinedVariable
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,  # @UndefinedVariable
                shell.IID_IShellLink
            )
            link.QueryInterface(pythoncom.IID_IPersistFile).Load(  # @UndefinedVariable
                ENSORC_PATH + ".lnk")  # @UndefinedVariable
            path = link.GetPath(shell.SLGP_UNCPRIORITY)
            if path and path[0]:
                ENSORC_PATH = path[0]
        except Exception as e:
            logging.error("Error parsing .ensorc.lnk file: %s", e)

    if os.path.isfile(ENSORC_PATH):
        logging.info("Loading '%s'." % ENSORC_PATH)
        contents = open(ENSORC_PATH, "r").read()
        compiled_contents = compile(contents + "\n", ENSORC_PATH, "exec")
        try:
            exec compiled_contents in {}, {}
        except Exception as e:
            logging.error("Error parsing user config from %s: %s", ENSORC_PATH, str(e))
        else:
            ENSORC_LOADED = True
    else:
        logging.warning(".ensorc file can't be read!")
