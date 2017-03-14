"""
Author : Guillaume "iXce" Seguin
Email  : guillaume@segu.in

Copyright (C) 2008, Guillaume Seguin <guillaume@segu.in>.
All rights reserved.

Author : Pavel Vitis "blackdaemon"
Email  : pavelvitis@gmail.com


Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  3. Neither the name of Enso nor the names of its contributors may
     be used to endorse or promote products derived from this
     software without specific prior written permission.

THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os

from gtk.gdk import keyval_from_name
from Xlib.display import Display


def get_display():
    # TODO: Can multiple displays exist?
    global _DISPLAYS
    # Cache the Display object as creating it is expensive
    # and this function is called from many places
    try:
        display_id = os.environ["DISPLAY"]
        return _DISPLAYS[display_id]
    except (NameError, KeyError) as e:
        if isinstance(e, NameError):
            _DISPLAYS = {}
        return _DISPLAYS.setdefault(display_id, Display(display_id))


def get_keycode(key, display=None):
    '''Helper function to get a keycode from raw key name'''
    if not display:
        display = get_display()
    keysym = keyval_from_name(key)
    keycode = display.keysym_to_keycode(keysym)
    return keycode


def sanitize_char(keyval):
    '''Sanitize a single character keyval by attempting to convert it'''
    char = unichr(int(keyval))
    if len(char) > 0 and ord(char) > 0 and ord(char) < 65000:
        # print keyval, char
        return char
    return None


def get_cmd_output(cmd, cwd=None):
    """Return (status, output) of executing cmd in a shell."""
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    if cwd:
        if not os.path.isdir(cwd):
            raise Exception("cwd is not an existing directory: %s" % cwd)
        cmd = "cd \"%s\"; %s" % (cwd, cmd)
    pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None:
        sts = 0
    if text and text[-1] == '\n':
        text = text[:-1]
    return sts, text
