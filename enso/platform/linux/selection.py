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

from __future__ import with_statement

import logging

from time import sleep, time, clock

import Xlib
import Xlib.ext.xtest
from utils import *

import dbus
import dbus.mainloop.glib
from gio import File
from enso.platform.linux.weaklib import DbusWeakCallback


gtk.gdk.threads_init()

"""
Class to handle Nautilus file-selection notifications in Linux Gnome desktop
"""
class NautilusFileSelection(object):
    def __init__(self):
        self.paths = []
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)    
        callback = DbusWeakCallback(self._on_selection_change)
        # Register signal receiver for SelectionChanged event in Nautilus windows
        callback.token = dbus.Bus().add_signal_receiver(
            callback,
            "SelectionChanged",
            dbus_interface="se.kaizer.FileSelection",
            byte_arrays=True)
        
    def _on_selection_change(self, selection, window_id):
        # File selection changed (user clicked on file/directory or selected
        # a group of files/directories.
        # Update internal variable
        self.paths = filter(None, [File(uri).get_path() for uri in selection])

nautilus_file_selection = NautilusFileSelection()


GET_TIMEOUT = 1.5
PASTE_STATE = Xlib.X.ShiftMask
PASTE_KEY = "^V"

def get_clipboard_text_cb (clipboard, text, userdata):
    '''Callback for clipboard fetch handling'''
    global selection_text
    selection_text = text

def get_focused_window (display):
    '''Get the currently focussed window'''
    input_focus = display.get_input_focus ()
    window = Xlib.X.NONE
    if input_focus != None and input_focus.focus:
        window = input_focus.focus
    return window

def make_key (keycode, state, window, display):
    '''Build a data dict for a KeyPress/KeyRelease event'''
    root = display.screen ().root
    event_data = {
        "time": int (time ()),
        "root": root,
        "window": window,
        "same_screen": True,
        "child": Xlib.X.NONE,
        "root_x": 0,
        "root_y": 0,
        "event_x": 0,
        "event_y": 0,
        "state": state,
        "detail": keycode,
                 }
    return event_data

def fake_key_up (key, window, display):
    '''Fake a keyboard press event'''
    event = Xlib.protocol.event.KeyPress (**key)
    window.send_event (event, propagate = True)
    display.sync ()

def fake_key_down (key, window, display):
    '''Fake a keyboard release event'''
    event = Xlib.protocol.event.KeyRelease (**key)
    window.send_event (event, propagate = True)
    display.sync ()

def fake_key_updown (key, window, display):
    '''Fake a keyboard press/release events pair'''
    fake_key_up (key, window, display)
    fake_key_down (key, window, display)

def fake_paste (display = None):
    '''Fake a "paste" keyboard event'''
    if not display:
        display = get_display ()
    window = get_focused_window (display)
    state = PASTE_STATE
    k = PASTE_KEY
    ctrl = False
    if k.startswith("^"):
        k = k[1:]
        ctrl = True
    keycode = get_keycode (key = k, display = display)
    key = make_key (keycode, state, window, display)
    ctrl_keycode = get_keycode (key = "Control_L", display = display)
    ctrl_key = make_key (ctrl_keycode, state, window, display)
    if ctrl: 
        Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, ctrl_keycode)
    Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, keycode)
    Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, keycode)
    Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, ctrl_keycode)
    display.sync()

    
def get ():
    '''Fetch text from X PRIMARY selection'''
    global selection_text, nautilus_file_selection
    
    selection_text = None
    clipboard = gtk.clipboard_get (gtk.gdk.SELECTION_PRIMARY)
    clipboard.request_text (get_clipboard_text_cb)
    # Iterate until we actually received something, or we timed out waiting
    start = clock ()
    while not selection_text and (clock () - start) < GET_TIMEOUT:
        gtk.main_iteration(False)
    if not selection_text:
        selection_text = ""
    files = []
    # Get file list from Nautilus window (if available)
    focus = get_focused_window(get_display())
    wmclass = focus.get_wm_class()
    if wmclass is None: #or wmname is None:
        focus = focus.query_tree().parent
        wmclass = focus.get_wm_class()
    wmname = focus.get_wm_name()
    #print wmclass, wmname
    #TODO: Implement file selection from other Linux file managers
    if nautilus_file_selection and nautilus_file_selection.paths and wmclass[0] == 'nautilus':
        files = nautilus_file_selection.paths
    selection = {
                    "text": selection_text,
                    "files": files,
                }
    return selection

def set (seldict):
    '''Paste data into X CLIPBOARD selection'''
    if "text" in seldict:
        clipboard = gtk.clipboard_get (selection = "CLIPBOARD")
        clipboard.set_text (seldict["text"])
        primary = gtk.clipboard_get (selection = "PRIMARY")
        primary.set_text (seldict["text"])
        fake_paste()
        return True
    return False

