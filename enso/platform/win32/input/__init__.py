# A placeholder.  Just import the InputManager class.

from types import MethodType
import win32api

from InputManager import *
from CharMaps import STANDARD_ALLOWED_KEYCODES as CASE_INSENSITIVE_KEYCODE_MAP

INJECT_METHODS = not hasattr(InputManager, "getIdleTime")

"""
Following section is a terrible hack
Remove it after the idle time measurement is implemented in the C++ sources and compiled.
"""
_idle_time = 0

def _getIdleTime(self):
    global _idle_time
    return _idle_time
    # Following is unreliable. It does not work if some application is sending phantom input events
    # (like joystick movements). For instance Tobii Eye Tracker or vJoy.
    # Unfortunately, this also means that activity is not detected if user uses only a joystick (playing game?)
    #return (win32api.GetTickCount() - win32api.GetLastInputInfo())


_originalOnTick = InputManager.onTick
_originalOnMouseMove = InputManager.onMouseMove
_originalOnSomeMouseButton = InputManager.onSomeMouseButton
_originalOnSomeKey = InputManager.onSomeKey
_originalOnKeypress = InputManager.onKeypress

# HACK: Remove this after it is implemented in C++ sources
def _onTick(self, msPassed):
    global _idle_time
    _idle_time += msPassed
    return _originalOnTick(self, msPassed)


# HACK: Remove this after it is implemented in C++ sources
def _onMouseMove(self, x, y):
    global _idle_time
    _idle_time = 0
    return _originalOnMouseMove(self, x, y)


# HACK: Remove this after it is implemented in C++ sources
def _onSomeMouseButton(self):
    global _idle_time
    _idle_time = 0
    return _originalOnSomeMouseButton(self)


# HACK: Remove this after it is implemented in C++ sources
def _onSomeKey(self):
    global _idle_time
    _idle_time = 0
    return _originalOnSomeKey(self)


# HACK: Remove this after it is implemented in C++ sources
def _onKeypress(self, eventtype, keycode):
    global _idle_time
    _idle_time = 0
    return _originalOnKeypress(self, eventtype, keycode)

if INJECT_METHODS:
    # HACK: Remove this after it is implemented in C++ sources
    # Inject new getIdleTime function into InputManager object
    InputManager.getIdleTime = MethodType(_getIdleTime, None, InputManager)
    # Replace original onTick method with new one
    InputManager.onTick = MethodType(_onTick, None, InputManager)
    # Replace original onMouseMove method with new one
    InputManager.onMouseMove = MethodType(_onMouseMove, None, InputManager)
    # Replace original onSomeMouseButton method with new one
    InputManager.onSomeMouseButton = MethodType(_onSomeMouseButton, None, InputManager)
    # Replace original onSomeKey method with new one
    InputManager.onSomeKey = MethodType(_onSomeKey, None, InputManager)
    # Replace original onKeyPress method with new one
    InputManager.onKeypress = MethodType(_onKeypress, None, InputManager)
