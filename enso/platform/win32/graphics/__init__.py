# Copyright (c) 2008, Humanized, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
    This is largely just a placeholder script that allows Python to
    interpret this directory as the Graphics package.

    Behind the scenes, however, it also internally performs a few
    tweaks to the namespace and defines a few functions that don't fit
    into any particular submodule of this package.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Future imports
from __future__ import with_statement

import logging

import ctypes
import win32con
import win32api
import win32gui
import winerror
import pywintypes

from TransparentWindow import TransparentWindow
from font_registry import FontRegistry
import enso.config


# Aliases to external names.
#from TransparentWindow import _getDesktopSize as getDesktopSize

class log_once():
    """ Decorator for logging the function result once. """
    _cache = {}

    def __init__(self, text):
        self.__text = text

    def __call__(self, func):
        def log_func(*args, **kwargs):
            result = func(*args, **kwargs)
            if not self._cache.get(result, None):
                logging.info(self.__text % result)
                self._cache[result] = True
            return result

        return log_func


def _get_workarea():
    """
    Get Windows desktop working area in pixels. Throws WindowError on error.
    """
    class RECT(ctypes.Structure):
        _fields_ = [('left',ctypes.c_ulong),
            ('top',ctypes.c_ulong),
            ('right',ctypes.c_ulong),
            ('bottom',ctypes.c_ulong)]
    r = RECT()
    if not ctypes.windll.user32.SystemParametersInfoA(
        win32con.SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
        raise ctypes.WinError()
    return map(int, (r.left, r.top, r.right, r.bottom))


def get_cursor_pos():
    """
    Safe version of win32gui.GetCursorPos()
    Use this function instead. Due to security restrictions, win32gui.GetCursorPos()
    throws access-denied exception when the workstation is locked.
    This functions returns 0, 0 coordinates in such case.
    """
    try:
        flags, hcursor, (mx, my) = win32gui.GetCursorInfo()
    except pywintypes.error, e:
        # This error occurs when workstation is locked
        if e.winerror == winerror.ERROR_ACCESS_DENIED:
            mx, my = 0, 0
        else:
            raise
    return mx, my


def get_cursor_info():
    """
    Safe version of win32gui.GetCursorInfo()
    Use this function instead. Due to security restrictions, win32gui.GetCursorPos()
    throws access-denied exception when the workstation is locked.
    This functions returns 0, 0 coordinates in such case.
    """
    try:
        flags, hcursor, (mx, my) = win32gui.GetCursorInfo()
    except pywintypes.error, e:
        # This error occurs when workstation is locked
        if e.winerror == winerror.ERROR_ACCESS_DENIED:
            flags = win32con.CURSOR_SHOWING
            hcursor = None
            mx, my = 0, 0
        else:
            raise
    return flags, hcursor, mx, my


def get_active_monitor():
    #for hMonitor, hdcMonitor, rect in win32api.EnumDisplayMonitors(None, None):
    #    print rect, win32api.GetMonitorInfo(hMonitor)
    #    #print win32api.GetMonitorInfo(hMonitor)
    return win32api.GetMonitorInfo(
        win32api.MonitorFromPoint(get_cursor_pos(), win32con.MONITOR_DEFAULTTONEAREST))
    #$monitor = win32api.GetMonitorInfo()


def get_primary_monitor():
    mx, my = get_cursor_pos()
    for hMonitor, hdcMonitor, rect in win32api.EnumDisplayMonitors(None, None):
        info = win32api.GetMonitorInfo(hMonitor)
        if info['Flags'] & win32con.MONITORINFOF_PRIMARY == win32con.MONITORINFOF_PRIMARY:
            return info


@log_once("Primary-desktop offset: %i/%ipx")
def getDesktopOffset():
    """ Return primary monitor desktop offset in pixels. """
    if enso.config.SHOW_ON_ACTIVE_MONITOR:
        left, top, _, _ = get_active_monitor()['Monitor']
    else:
        left, top, _, _ = win32gui.GetWindowRect(win32gui.GetDesktopWindow())
    #print "DESKTOP OFFSET:", left, top
    return left, top


@log_once("Primary-desktop size: %i/%ipx")
def getDesktopSize():
    """ Return primary monitor desktop size in pixels. """
    if enso.config.SHOW_ON_ACTIVE_MONITOR:
        left, top, right, bottom = get_active_monitor()['Monitor']
        width = abs(right-left)
        height = abs(bottom-top)
    else:
        left, top, right, bottom = win32gui.GetWindowRect(win32gui.GetDesktopWindow())
        width = right - left
        height = bottom - top
    #print "DESKTOP SIZE:", width, height
    return width, height

@log_once("Primary-workarea offset: %i/%ipx")
def getWorkareaOffset():
    """
    Return primary monitor workarea offset in pixels.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    left, top, _, _ = _get_workarea()
    return left, top


@log_once("Primary-workarea size: %i/%ipx")
def getWorkareaSize():
    """
    Return primary monitor workare size in pixels.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    left, top, right, bottom = _get_workarea()
    return right - left, bottom - top

def processWindowManagerPendingEvents():
    return None
