import sys
import os
import time
import pythoncom
import logging
from win32com.shell import shell, shellcon

import enso.config
from enso.messages import displayMessage
from enso.platform.win32.taskbar.tray_icon import SysTrayIcon

ENSO_DIR = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), ".."))
ENSO_EXECUTABLE = os.path.join(ENSO_DIR, "Enso.lnk")


def tray_on_enso_quit(systray):
    enso.config.SYSTRAY_ICON.change_tooltip("Closing Enso...")
    if not enso.config.CMDLINE_OPTIONS.quiet:
        displayMessage(u"<p>Closing Enso...</p><caption>Enso</caption>")
    #import win32gui
    #win32gui.PostQuitMessage(0)
    time.sleep(1)
    sys.exit(0)


def tray_on_enso_about(systray):
    _ = systray
    quasimode_key_name = {
        "KEYCODE_LSHIFT":"Left Shift",
        "KEYCODE_RSHIFT":"Right Shift",
        "KEYCODE_LCONTROL":"Left Ctrl",
        "KEYCODE_RCONTROL":"Right Ctrl",
        "KEYCODE_LWIN":"Left Win",
        "KEYCODE_RWIN":"Right Win",
        "KEYCODE_CAPITAL":"CapsLock"
        }[enso.config.QUASIMODE_START_KEY]
    displayMessage(
        "%s<p> </p><caption>Hold down the <command>%s</command> key to invoke Enso</caption>"
        % (enso.config.ABOUT_MSG_XML, quasimode_key_name),
        primaryWaitTime=2000)


def tray_on_enso_help(systray):
    _ = systray
    pass


def tray_on_enso_exec_at_startup(systray, get_state = False):
    _ = systray
    startup_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    assert os.path.isdir(startup_dir)

    link_file = os.path.join(startup_dir, "Enso.lnk")

    if get_state:
        return os.path.isfile(link_file)
    else:
        if not os.path.isfile(link_file):
            try:
                pythoncom.CoInitialize()
            except:
                # already initialized.
                pass

            shortcut = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IShellLink
            )

            shortcut.SetPath(ENSO_EXECUTABLE)
            enso_root_dir = os.path.dirname(ENSO_EXECUTABLE)
            shortcut.SetWorkingDirectory(enso_root_dir)
            shortcut.SetIconLocation(os.path.join(enso_root_dir, "Enso.ico"), 0)

            shortcut.QueryInterface( pythoncom.IID_IPersistFile ).Save(
                link_file, 0 )
            try:
                pythoncom.CoUnInitialize()
            except:
                pass

            displayMessage(u"<p><command>Enso</command> will be automatically executed at system startup</p><caption>enso</caption>")
        else:
            os.remove(link_file)
            displayMessage(u"<p><command>Enso</command> will not start at system startup</p><caption>enso</caption>")


def systray(enso_config):
    """
    Tray-icon handling code. This function have to be executed
    in separate thread
    """

    icon_filename = "Enso.ico"
    startup_dir = os.path.dirname(sys.argv[0])
    enso_icon = os.path.realpath(os.path.join(startup_dir, icon_filename))
    if not os.path.isfile(enso_icon):
        enso_icon = os.path.realpath(os.path.join(startup_dir, "..", icon_filename))
    assert logging.debug("Icon path: %s", enso_icon) or True

    trayicon = SysTrayIcon(
            enso_icon,
            "Enso open-source",
            None,
            on_quit = tray_on_enso_quit)

    trayicon.on_about = tray_on_enso_about
    trayicon.on_doubleclick = tray_on_enso_about
    trayicon.on_leftclick = trayicon.on_rightclick
    trayicon.add_menu_item("&Start automatically at login", tray_on_enso_exec_at_startup)
    enso_config.SYSTRAY_ICON = trayicon
    trayicon.main_thread()


# vim:set tabstop=4 shiftwidth=4 expandtab:
