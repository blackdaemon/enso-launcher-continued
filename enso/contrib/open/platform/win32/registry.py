# Author : Pavel Vitis "blackdaemon"
# Email  : blackdaemon@seznam.cz
#
# Copyright (c) 2010, Pavel Vitis <blackdaemon@seznam.cz>
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
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import with_statement
import win32api
import win32con
import os
from contextlib import contextmanager

try:
    import regex as re
except Exception, e:
    import re

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
    reghandle = win32api.RegConnectRegistry(machine, hive)
    yield reghandle


@contextmanager
def reg_open_key(reghandle, keyname, sam = win32con.KEY_READ):
    """
    With-statement handler.
    Use as:
        with reg_connect_registry(machine, hive) as reghandle:
            with reg_open_key(reghandle, key_name) as keyhandle:
                ...
    """
    try:
        keyhandle = win32api.RegOpenKeyEx(reghandle, keyname, 0, sam)
        yield keyhandle
    except Exception, e:
        raise
    else:
        win32api.RegCloseKey(keyhandle)


def get_value(hive, key_name, value_name, autoexpand=True):
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
    assert hive in (HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, HKEY_USERS, HKEY_CLASSES_ROOT),\
        "hive parameter has invalid value: %s" % str(hive)
    result = None
    key_name = key_name.replace("/", "\\")

    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name) as keyhandle:
            try:
                rval, rtype = win32api.RegQueryValueEx(keyhandle, value_name)
                result = [rtype, rval]
                if autoexpand and rtype == win32con.REG_EXPAND_SZ:
                    result.append(_expand_path_variables(rval))
            except Exception, e:
                return None

    return result


def walk_keys(hive, key_name, key_filter_regex=None, sam=win32con.KEY_READ):
    """
    >>> list(walk_keys(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows", r"^(H.*|Shell)"))
    ['Help', 'HTML Help', 'Shell']
    """
    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name, sam=sam) as keyhandle:
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


def walk_values(hive, key_name, value_filter_regex=None, valuetypes=None, autoexpand=False, sam=win32con.KEY_READ):
    """
    >>> list(walk_values(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\DrWatson", r"^(cr|dump)"))
    [('DumpSymbols', 0, 4), ('DumpAllThreads', 1, 4), ('CreateCrashDump', 1, 4), ('CrashDumpType', 1, 4)]

    >>> list(walk_values(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\DrWatson", valuetypes=(win32con.REG_EXPAND_SZ,)))
    [('WaveFile', '', 2)]
    """
    with reg_connect_registry(None, hive) as reghandle:
        with reg_open_key(reghandle, key_name, sam=sam) as keyhandle:
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
                    value = _expand_path_variables(value)
                yield name, value, value_type


if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: