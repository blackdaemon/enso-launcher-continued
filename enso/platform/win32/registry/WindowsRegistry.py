from __future__ import with_statement
import win32api
import win32con
import os
import re
from contextlib import contextmanager


HKEY_LOCAL_MACHINE = win32con.HKEY_LOCAL_MACHINE
HKEY_CURRENT_USER = win32con.HKEY_CURRENT_USER
HKEY_USERS = win32con.HKEY_USERS
HKEY_CLASSES_ROOT = win32con.HKEY_CLASSES_ROOT


def _expand_path_variables(file_path):
    re_env = re.compile(r'%\w+%')

    def expander(mo):
        return os.environ.get(mo.group()[1:-1], 'UNKNOWN')

    return re_env.sub(expander, file_path)


@contextmanager
def reg_connect_registry(machine, hive):
    """
    With-statement handler.
    Use as:
        with reg_connect_registry(machine, hive) as reghandle:
            ...
    """
    # here goes __enter__ stuff
    reghandle = win32api.RegConnectRegistry(machine, hive)
    yield reghandle
    # here goes __exit__ stuff


"""
class reg_connect_registry(object):
    ""
    With-statement handler.
    Use as:
        with reg_connect_registry(machine, hive) as reghandle:
            ...
    ""
    def __init__(self, machine, hive):
        self._machine = machine
        self._hive  = hive

    def __enter__(self):
        self._reghandle = win32api.RegConnectRegistry(
            self._machine,
            self._hive)
        return self._reghandle

    def __exit__(self, type, value, traceback):
        #print "exit:", type, value
        #print traceback
        pass
"""

@contextmanager
def reg_open_key(reghandle, keyname):
    """
    With-statement handler.
    Use as:
        with reg_connect_registry(machine, hive) as reghandle:
            with reg_open_key(reghandle, key_name) as keyhandle:
                ...
    """
    try:
        keyhandle = win32api.RegOpenKeyEx(reghandle, keyname)
        yield keyhandle
    except Exception, e:
        raise
    finally:
        if keyhandle:
            win32api.RegCloseKey(keyhandle)

"""
class reg_open_key(object):
    ""
    With-statement handler.
    Use as:
        with reg_connect_registry(machine, hive) as reghandle:
            with reg_open_key(reghandle, key_name) as keyhandle:
                ...
    ""
    def __init__(self, reghandle, keyname):
        self._reghandle = reghandle
        self._keyname  = keyname

    def __enter__(self):
        self._keyhandle = win32api.RegOpenKeyEx(
            self._reghandle,
            self._keyname)
        return self._keyhandle

    def __exit__(self, type, value, traceback):
        if self._keyhandle:
            win32api.RegCloseKey(self._keyhandle)
            self._keyhandle = None
        #print "exit:", type, value
        #print traceback
"""


def get_value(hive, key_name, value_name):
    """
    >>> get_value(
    ...    HKEY_LOCAL_MACHINE,
    ...    "SOFTWARE/Microsoft/Windows/CurrentVersion/Explorer/StartMenu",
    ...    "Type")
    [1, 'group']

    >>> get_value(
    ...    HKEY_CURRENT_USER,
    ...    "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CLSID\\{645FF040-5081-101B-9F08-00AA002F954E}\\DefaultIcon",
    ...    "Full")
    [2, '%SystemRoot%\\\\System32\\\\shell32.dll,32', 'C:\\\\WINDOWS\\\\System32\\\\shell32.dll,32']
    """
    assert hive in (HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, HKEY_USERS, HKEY_CLASSES_ROOT)
    result = None
    key_name = key_name.replace("/", "\\")

    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name) as keyhandle:
            try:
                rval, rtype = win32api.RegQueryValueEx(keyhandle, value_name)
                result = [rtype, rval]
                if rtype == win32con.REG_EXPAND_SZ:
                    result.append(_expand_path_variables(rval))
            except Exception, e:
                print e
                return None

    return result


def walk_keys(hive, key_name, key_filter_regex = None):
    """
    >>> list(walk_keys(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows", r"^(H.*|Shell)"))
    ['Help', 'HTML Help', 'Shell']
    """
    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name) as keyhandle:
            index = 0
            while True:
                try:
                    key = win32api.RegEnumKey(keyhandle, index)
                except Exception, e:
                    if e[0] == 259: # No more items available
                        break
                    raise e
                index += 1
                if key_filter_regex and not re.search(
                    key_filter_regex, key, re.IGNORECASE):
                    continue
                yield key


def walk_values(hive, key_name, value_filter_regex = None, valuetypes = None, autoexpand = False):
    """
    >>> list(walk_values(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\DrWatson", r"^(cr|dump)"))
    [('DumpSymbols', 0, 4), ('DumpAllThreads', 1, 4), ('CreateCrashDump', 1, 4), ('CrashDumpType', 1, 4)]

    >>> list(walk_values(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\DrWatson", valuetypes=(win32con.REG_EXPAND_SZ,)))
    [('WaveFile', '', 2)]
    """
    def expand_path_variables(file_path):
        re_env = re.compile(r'%\w+%')

        def expander(mo):
            return os.environ.get(mo.group()[1:-1], 'UNKNOWN')

        return os.path.expandvars(re_env.sub(expander, file_path))

    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name) as keyhandle:
            index = 0
            while True:
                try:
                    name, value, value_type = win32api.RegEnumValue(keyhandle, index)
                except Exception, e:
                    if e[0] == 259: # No more items available
                        break
                    raise e
                index += 1
                if value_filter_regex and not re.search(
                    value_filter_regex, name, re.IGNORECASE):
                    continue
                if valuetypes and not value_type in valuetypes:
                    continue
                if autoexpand and value_type == win32con.REG_EXPAND_SZ:
                    value = expand_path_variables(value)
                yield name, value, value_type


if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: