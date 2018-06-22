# A placeholder.  Just import the InputManager class.

from types import MethodType
import win32api

from InputManager import *
from CharMaps import STANDARD_ALLOWED_KEYCODES as CASE_INSENSITIVE_KEYCODE_MAP


def getIdleTime(self):
    return (win32api.GetTickCount() - win32api.GetLastInputInfo())

# this assigns the method to the class definition
InputManager.getIdleTime = MethodType(getIdleTime, None, InputManager)
