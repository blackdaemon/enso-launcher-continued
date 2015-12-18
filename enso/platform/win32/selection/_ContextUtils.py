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
    A collection of utility functions used in the various modules of
    the context system.  In general, if you find a utility function
    which is defined in more than one context module, consider moving
    it here.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import time
import logging
import os
import win32api
import win32con
import win32gui
import win32clipboard
import win32process
import ctypes
import pywintypes
from ctypes import windll, wintypes

from enso.utils.decorators import finalizeWrapper

# ----------------------------------------------------------------------------
# Public constants
# ----------------------------------------------------------------------------

# Max time to wait for clipboard to change after issuing a
# shortcut-key command to an application.
STANDARD_WAIT_TIME = 250

# Amount of time to wait between attempts to open the clipboard, in
# ms.
CLIPBOARD_OPEN_WAIT_INTERVAL = 10

# Total amount of time we can wait for the clipboard to become
# available for opening, in ms.
# The larger we make this, the rarer the clipboard will
# be unopenable, but with increased wait times for users. However,
# it should also be remembered that if some application has
# ownership of the clipboard, they should release it very soon,
# and if the system is very busy, this may understandably take
# a lot of time.
CLIPBOARD_OPEN_WAIT_AMOUNT = 1000

# The following three constants are obtained programatically.
# Since this code is executed the first time that ContextUtils is
# imported, and it is imported in __init__.py, these constants
# should always be available for other modules to import.

# Clipboard format code for ThornSoft's CF_CLIPBOARD_VIEWER_IGNORE
# format.  For more information, see
# http://www.thornsoft.com/developer_ignore.htm.
CF_CLIPBOARD_VIEWER_IGNORE = win32clipboard.RegisterClipboardFormat(
    "Clipboard Viewer Ignore"
    )

# Clipboard formats for HTML and RTF are, annoyingly, not constant
# numbers; Windows reserves the right to vary them between runs;
# but we can fetch their current values as follows:
CF_HTML = win32clipboard.RegisterClipboardFormat("HTML Format")
CF_RTF  = win32clipboard.RegisterClipboardFormat("Rich Text Format")


# Keyboard event types.  According to MSDN documentation:
# "KEYEVENTF_KEYUP
#    If specified, the key is being released. If not specified, the
#    key is being depressed."
KEYEVENTF_KEYDOWN = 0
KEYEVENTF_KEYUP = win32con.KEYEVENTF_KEYUP
KEYEVENTF_EXTENDEDKEY = win32con.KEYEVENTF_EXTENDEDKEY

VK_LBRACKET = 0xDB
VK_RBRACKET = 0xDD

KEY_MAPPING = { "F1" : win32con.VK_F1,
                "F2" : win32con.VK_F2,
                "F3" : win32con.VK_F3,
                "F4" : win32con.VK_F4,
                "F5" : win32con.VK_F5,
                "F6" : win32con.VK_F6,
                "F7" : win32con.VK_F7,
                "F8" : win32con.VK_F8,
                "F9" : win32con.VK_F9,
                "F10": win32con.VK_F10,
                "F11": win32con.VK_F11,
                "F12": win32con.VK_F12,
                "CD" : win32con.VK_LCONTROL,
                "CU" : win32con.VK_LCONTROL,
                "SD" : win32con.VK_LSHIFT,
                "SU" : win32con.VK_LSHIFT,
                "AD" : win32con.VK_MENU,
                "AU" : win32con.VK_MENU,
                "ID" : win32con.VK_LWIN,
                "IU" : win32con.VK_LWIN,
                "LA": win32con.VK_LEFT,
                "RA": win32con.VK_RIGHT,
                "ESC": win32con.VK_ESCAPE,
                "INS": win32con.VK_INSERT,
                "DEL": win32con.VK_DELETE,
                "[": VK_LBRACKET,
                "]": VK_RBRACKET,
                "LBRACKET": VK_LBRACKET,
                "RBRACKET": VK_RBRACKET
              }

# List of keys that need to have the win32con.KEYEVENTF_EXTENDEDKEY flag set
KEYS_EXTENDED = [
    win32con.VK_UP,
    win32con.VK_DOWN,
    win32con.VK_LEFT,
    win32con.VK_RIGHT,
    win32con.VK_HOME,
    win32con.VK_END,
    win32con.VK_PRIOR, # PgUp
    win32con.VK_NEXT,  # PgDn
    win32con.VK_INSERT,
    win32con.VK_DELETE
]

# ----------------------------------------------------------------------------
# Private Module Variables
# ----------------------------------------------------------------------------

_contextUtilsHasTheClipboardOpen = False


# ----------------------------------------------------------------------------
# Private Functions
# ----------------------------------------------------------------------------

def _hasTheClipboardOpen():
    """
    Returns true if clipboard is currently held open by this module.
    This should be used only for debugging, and is only accurate if the
    clipboard was only opened and closed using the safeOpenClipboard
    and safeCloseClipboard functions defined below.
    """

    return _contextUtilsHasTheClipboardOpen


def _keyboardEvent( vkCode, eventType ):
    """
    Causes Windows to generate an event for key vkCode, of type eventType.
    """

    # win32all does not provide access to MapVirtualKey, so we have to use
    # ctypes to access the DLL directly, and have to append "A" to the name
    # since the function is implemented in Unicode and ANSI versions.

    # This gives a hardware scancode for the virtual key.
    scanCode = ctypes.windll.user32.MapVirtualKeyA( vkCode, 0 )

    # Some keys needs the 'extended-key' attribute
    if vkCode in KEYS_EXTENDED:
        eventType |= KEYEVENTF_EXTENDEDKEY

    # This creates the keyboard event (this function is the one called
    # by keyboard driver interupt handlers, so it's as low-level as it gets)
    win32api.keybd_event( vkCode, scanCode, eventType, 0 )


# ----------------------------------------------------------------------------
# Public Functions
# ----------------------------------------------------------------------------

def safeOpenClipboard():
    """
    Replacement for win32clipboard.OpenClipboard() that repeatedly
    tries to open the clipboard over a short period of time, in case
    another application already has the clipboard open.
    Also maintains the module-level clipboard state variable.
    Raises a ClipboardUnopenableError if it fails.
    """

    # Preconditions:
    assert( not _hasTheClipboardOpen() )

    totalTime = 0
    success = False

    while not success:
        try:
            win32clipboard.OpenClipboard( 0 )
            success = True
        except pywintypes.error: #IGNORE:E1101
            if totalTime < CLIPBOARD_OPEN_WAIT_AMOUNT:
                sleepForMs( CLIPBOARD_OPEN_WAIT_INTERVAL )
                totalTime += CLIPBOARD_OPEN_WAIT_INTERVAL
            else:
                # We failed to open the clipboard in the specified
                # time.
                success = False
                break
    if success:
        global _contextUtilsHasTheClipboardOpen
        _contextUtilsHasTheClipboardOpen = True
    else:
        raise ClipboardUnopenableError()

    # Postconditions:
    assert( _hasTheClipboardOpen() )



def safeCloseClipboard():
    """
    Replacement for win32clipboard.CloseClipboard() that turns the
    fatal error into a warning if the clipboard was already closed.
    Also maintains the module-level clipboard state variable.
    """

    # Postconditions:
    assert( _hasTheClipboardOpen() )

    try:
        win32clipboard.CloseClipboard()
    except pywintypes.error: #IGNORE:E1101
        logging.warn( "Attempted to close clipboard when not open." )
    global _contextUtilsHasTheClipboardOpen
    _contextUtilsHasTheClipboardOpen = False

    # Postconditions:
    assert( not _hasTheClipboardOpen() )



def clipboardDependent( function ):
    """
    A decorator which opens the clipboard before executing the wrapped
    function, then closes it when the wrapped function is done,
    whether or not the wrapped function throws an exception.
    """

    def wrapperFunc( *args, **kwargs ):
        # If safeOpenClipboard() raises an exception, this function will do
        # nothing but allow it to be raised. (We shouldn't attempt to close
        # the clipboard if we couldn't open it in the first place.)
        safeOpenClipboard()
        try:
            result = function( *args, **kwargs )
        finally:
            # If function raises an exception, the finally clause
            # will be executed and then the exception will be re-raised.
            safeCloseClipboard()
        return result

    return finalizeWrapper( function,
                            wrapperFunc,
                            "clipboardDependent" )


@clipboardDependent
def clearClipboard():
    """
    Opens the clipboard, empties it, and then closes it.  Also sets
    the CF_CLIPBOARD_VIEWER_IGNORE format so that clipboard viewers
    will ignore this alteration of the clipboard.
    """

    win32clipboard.EmptyClipboard()
    setClipboardDataViewerIgnore()


def setClipboardDataViewerIgnore():
    """
    Adds ThornSoft's CF_CLIPBOARD_VIEWER_IGNORE format to the
    clipboard.  Assumes that the clipboard is open and in a state
    where data can be added to it.
    """

    # Note the string we pass in is not altered before going to C
    # and then the Windows Clipboard, so we must explicitly null-
    # terminate it lest Bad Things happen.
    win32clipboard.SetClipboardData(
        CF_CLIPBOARD_VIEWER_IGNORE,
        "HumanizedEnso\0"
        )


def sleepForMs( ms ):
    """
    Sleeps for the given number of milliseconds
    """

    time.sleep( ms / 1000.0 )


def interpretFormatCode( format ):
    """
    LONGTERM TODO: This is kept around for debugging but can be deleted from
    production code.

    Given a format code (of the kind returned from the windows clipboard
    functions), returns a string describing the meaning of that
    format code.
    """

    formatCodeDictionary = {
        win32con.CF_BITMAP:
            "Bitmap Handle",
        win32con.CF_DIB:
            "Bitmap info structure and bits",
        win32con.CF_DIF:
            "Software Arts' Data Interchange Format",
        win32con.CF_DSPBITMAP:
            "Private bitmap display format",
        win32con.CF_DSPENHMETAFILE:
            "Private enhanced metafile display format",
        win32con.CF_DSPMETAFILEPICT:
            "Private metafile-picture display format",
        win32con.CF_DSPTEXT:
            "Private text display format",
        win32con.CF_ENHMETAFILE:
            "Handle to enhanced metafile",
        win32con.CF_HDROP:
            "HDROP dropped files",
        win32con.CF_LOCALE:
            "Handle to locale information associated with text",
        win32con.CF_METAFILEPICT:
            "Handle to metafile picture format",
        win32con.CF_OEMTEXT:
            "OEM Text",
        win32con.CF_OWNERDISPLAY:
            "Clipboard owner display message",
        win32con.CF_PALETTE:
            "Handle to a color palette",
        win32con.CF_PENDATA:
            "Microsoft Pen Computing data",
        win32con.CF_RIFF:
            "RIFF (Audio data)",
        win32con.CF_SYLK:
            "Microsoft Symbolic Link Format",
        win32con.CF_TEXT:
            "Plain Text",
        win32con.CF_TIFF:
            "TIFF (Tagged Image File Format)",
        win32con.CF_UNICODETEXT:
            "Unicode Text",
        win32con.CF_WAVE:
            "Audio data in wav format"
        }

    # Formats above 0xC000 are dynamically registered by other
    # programs; formats below that correspond to named constants.

    if format >= 0xC000:
        return win32clipboard.GetClipboardFormatName( format )
    elif format in formatCodeDictionary:
        return formatCodeDictionary[ format ]
    else:
        return "Unknown data format."


def typeCommandKey( key, wait=0 ):
    """
    Given a character literal, simulates holding the Control key down
    and typing that character. Useful for simulating menu shortcut keys.
    Optionally wait between keypresses number of milliseconds.
    """

    _keyboardEvent( win32con.VK_LCONTROL, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    if isinstance(key, basestring):
        if key in KEY_MAPPING:
            key_code = KEY_MAPPING[key]
        else:
            key_code = ord(key.upper())
    else:
        key_code = key

    _keyboardEvent( key_code, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( key_code, KEYEVENTF_KEYUP )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( win32con.VK_LCONTROL, KEYEVENTF_KEYUP )
    logging.info( "I am in typeCommandKey and I just typed " + key )


def typeAltKey( key, wait=0 ):
    """
    Given a character literal, simulates holding the Alt key down
    and typing that character.
    Optionally wait between keypresses number of milliseconds.
    """

    _keyboardEvent( win32con.VK_MENU, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    if isinstance(key, basestring):
        if key in KEY_MAPPING:
            key_code = KEY_MAPPING[key]
        else:
            key_code = ord(key.upper())
    else:
        key_code = key

    if wait:
        sleepForMs(wait)

    _keyboardEvent( key_code, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( key_code, KEYEVENTF_KEYUP )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( win32con.VK_MENU, KEYEVENTF_KEYUP )


def typeShiftKey( key, wait=0 ):
    """
    Given a character literal, simulates holding the Shift key down
    and typing that character.
    Optionally wait between keypresses number of milliseconds.
    """

    _keyboardEvent( win32con.VK_LSHIFT, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    if isinstance(key, basestring):
        if key in KEY_MAPPING:
            key_code = KEY_MAPPING[key]
        else:
            key_code = ord(key.upper())
    else:
        key_code = key

    if wait:
        sleepForMs(wait)

    _keyboardEvent( key_code, KEYEVENTF_KEYDOWN )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( key_code, KEYEVENTF_KEYUP )

    if wait:
        sleepForMs(wait)

    _keyboardEvent( win32con.VK_LSHIFT, KEYEVENTF_KEYUP )


def tapKey( keyCode ):
    """
    Given a virtual key code, simulates tapping that key.
    """

    _keyboardEvent( keyCode, KEYEVENTF_KEYDOWN )
    _keyboardEvent( keyCode, KEYEVENTF_KEYUP )


def typeSequence( keys ):
    """
    Enables scripting of keystrokes. Useful for any case that a series
    of keystrokes is required to accomplish the given task.

    The argument is a space-separated string of keys, which can include
    literal alphanumeric keys as well as codes for special keys and
    codes for pauses.  Codes for pauses are the character W followed
    by a numeric literal describing the number of seconds to wait
    (which can be fractional).  Codes for special keys include "F1"
    through "F12" for the function keys, "SD" for shift down, "SU"
    for shift up, "LA" and "RA" for left and right arrow keys, and
    "ESC" for escape.  "AD" and "AU" correspond to alt down and alt
    up, respectively.  "ID" and "IU" correspond to windows down and
    windows up, respectively.  "CD" and "CU" correspond to control down
    and control up, respectively.
    "W###" means wait specified number of milliseconds between keypresses,
    i.e. "W100" means to wait 100ms.

    LONGTERM TODO add a doctest here
    """

    # LONGTERM TODO: Develop a decent scripting language that includes
    # keydown, keyup, keypress, and pauses.

    keys = keys.split( " " )

    for key in keys:
        key = key.upper()

        # "W###" means wait given number of milliseconds
        if len(key) > 1 and key[0] == "W" and key[1:].isdigit():
            sleepForMs( int(key[1:]) )
            continue

        # These keys require particular calls to the underlying
        # keybd_event function, and therefore don't use our keyboard
        # event wrapper.
        if key in ["SD", "AD", "ID", "CD"]:
            win32api.keybd_event( KEY_MAPPING[key], 0, KEYEVENTF_KEYDOWN, 0 )
            continue
        if key in ["SU", "AU", "IU", "CU"]:
            win32api.keybd_event( KEY_MAPPING[key], 0, KEYEVENTF_KEYUP, 0 )
            continue

        # Any one-character code means tap and release that literal key.
        if key in KEY_MAPPING:
            key_code = KEY_MAPPING[key]
        else:
            key_code = ord(key.upper())
        _keyboardEvent( key_code, KEYEVENTF_KEYDOWN )
        _keyboardEvent( key_code, KEYEVENTF_KEYUP )


def typeText( text ):
    """
    Enables scripting of keystrokes. Useful for any case that a series
    of keystrokes is required to accomplish the given task.

    The argument is a space-separated string of keys, which can include
    literal alphanumeric keys as well as codes for special keys and
    codes for pauses.  Codes for pauses are the character W followed
    by a numeric literal describing the number of seconds to wait
    (which can be fractional).  Codes for special keys include "F1"
    through "F12" for the function keys, "SD" for shift down, "SU"
    for shift up, "LA" and "RA" for left and right arrow keys, and
    "ESC" for escape.  "AD" and "AU" correspond to alt down and alt
    up, respectively.  "ID" and "IU" correspond to windows down and
    windows up, respectively.  "CD" and "CU" correspond to control down
    and control up, respectively.
    "W###" means wait specified number of milliseconds between keypresses,
    i.e. "W100" means to wait 100ms.

    LONGTERM TODO add a doctest here
    """

    for char in text:
        key_code = ord(char)
        _keyboardEvent( key_code, KEYEVENTF_KEYDOWN )
        _keyboardEvent( key_code, KEYEVENTF_KEYUP )


def getForegroundClassNameUnicode(hwnd=None):
    """
    Returns a unicode string containing the class name of the specified
    application window.
    If hwnd parameter is None, frontmost window will be queried.
    """

    if hwnd is None:
        hwnd = win32gui.GetForegroundWindow()

    # Maximum number of chars we'll accept for the class name; the
    # rest will be truncated if it's longer than this.
    MAX_LENGTH = 1024

    classNameBuf = ctypes.create_unicode_buffer( MAX_LENGTH )
    retval = ctypes.windll.User32.GetClassNameW(
        hwnd,
        classNameBuf,
        len( classNameBuf )
        )
    if retval == 0:
        raise ctypes.WinError()
    return classNameBuf.value


def getWindowClassName(hwnd=None):
    """
    Returns a unicode string containing the class name of the specified
    application window.
    If hwnd parameter is None, frontmost window will be queried.
    """
    return getForegroundClassNameUnicode(hwnd)


def getWindowProcessName(hwnd=None):
    """
    Returns a unicode string containing the process name of the specified
    application window (executable path).
    If hwnd parameter is None, frontmost window will be queried.
    """
    if hwnd is None:
        hwnd = win32gui.GetForegroundWindow()

    # Get PID so we can get process handle
    _, process_id = win32process.GetWindowThreadProcessId(hwnd)

    # Get process handle
    process_handle = win32api.OpenProcess(
        win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
        False,
        process_id)
    if not process_handle:
        return None

    MAX_PATH = 260
    MAX_BUFFER = 32767
    
    # Following is preffered way of getting process filename on Windows Vista/7
    try:
        kernel32_dll = windll.LoadLibrary("kernel32")

        _QueryFullProcessImageName = kernel32_dll.QueryFullProcessImageNameW
        PDWORD = wintypes.POINTER(wintypes.DWORD)
        _QueryFullProcessImageName.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, PDWORD]
        _QueryFullProcessImageName.restype = wintypes.BOOL
    except Exception, e:
        _QueryFullProcessImageName = None

    # http://msdn.microsoft.com/en-us/library/aa365247.aspx#maxpath
    if _QueryFullProcessImageName:
        pexe = None
        try:
            # Initial buffer size should be enough for most situations
            buffer_size = MAX_PATH
            while buffer_size <= MAX_BUFFER:
                bufflen = wintypes.DWORD(buffer_size)
                ubuffer = ctypes.create_unicode_buffer("", bufflen.value)
                success = _QueryFullProcessImageName(
                    long(process_handle), 0, ctypes.byref(ubuffer), ctypes.byref(bufflen))
                if success:
                    # Buffer was big enough
                    if bufflen.value < buffer_size:
                        pexe = ubuffer.value
                        break
                    # Buffer was exact size or not big enough, try again with bigger size
                    else:
                        buffer_size += 1024
                else:
                    raise Exception(win32api.FormatMessage(win32api.GetLastError()))
        except Exception, e:
            logging.error("Error getting process filename using QueryFullProcessImageName(): %s", e)

        return pexe
    
    
    # Following is preffered way of getting process filename on Windows XP and above
    try:
        psapi_dll = windll.LoadLibrary("psapi")

        _GetProcessImageFileName = psapi_dll.GetProcessImageFileNameW
        _GetProcessImageFileName.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD]
        _GetProcessImageFileName.restype = wintypes.DWORD
    except Exception, e:
        _GetProcessImageFileName = None

    if _GetProcessImageFileName:
        pexe = None
        try:
            # Initial buffer size should be enough for most situations
            buffer_size = MAX_PATH
            while buffer_size <= MAX_BUFFER:
                ubuffer = ctypes.create_unicode_buffer("", buffer_size)
                length_copied = _GetProcessImageFileName(
                    long(process_handle), ctypes.byref(ubuffer), buffer_size)
                if length_copied > 0:
                    # Buffer was big enough
                    if length_copied < buffer_size:
                        pexe = ubuffer.value
                        break
                    # Buffer was exact size or not big enough, try again with bigger size
                    else:
                        buffer_size += 1024
                else:
                    raise Exception(win32api.FormatMessage(win32api.GetLastError()))
        except Exception, e:
            logging.error("Error getting process filename using GetProcessImageFileName(): %s", e)
    
        return pexe
    
    try:
        pexe = win32process.GetModuleFileNameEx(process_handle, 0)
    except Exception, e:
        logging.error("Error getting process filename using GetModuleFileNameEx(): %s", e)

    return pexe


# ----------------------------------------------------------------------------
# Exception
# ----------------------------------------------------------------------------

class ClipboardUnopenableError( Exception ):
    """
    Exception raised if the clipboard was unable to be opened after
    multiple attempts.
    """

    pass
