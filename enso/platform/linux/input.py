"""
Author : Guillaume "iXce" Seguin
Email  : guillaume@segu.in
Contributions from:
  Stuart "aquarius" Langridge, sil@kryogenix.org

Copyright (C) 2008, Guillaume Seguin <guillaume@segu.in>.
All rights reserved.

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

__updated__ = "2018-07-04"

import atexit
import logging
import os
from threading import Thread

import gobject
import gtk

from CharMaps import STANDARD_ALLOWED_KEYCODES as CASE_INSENSITIVE_KEYCODE_MAP
from Xlib import X
from shutilwhich import which
from utils import get_display, get_keycode, get_cmd_output, sanitize_char
from xprintidle import idle_time

from enso.utils import suppress


gtk.gdk.threads_init()

# Timer interval in seconds.
_TIMER_INTERVAL = 0.010

# Timer interval in milliseconds.
_TIMER_INTERVAL_IN_MS = int(_TIMER_INTERVAL * 1000)

# Input modes
QUASI_MODAL = 0
MODAL = 1

KEYCODE_CAPITAL = -1
KEYCODE_SPACE = -1
KEYCODE_LSHIFT = -1
KEYCODE_RSHIFT = -1
KEYCODE_LCONTROL = -1
KEYCODE_RCONTROL = -1
KEYCODE_LWIN = -1
KEYCODE_RWIN = -1
KEYCODE_RETURN = -1
KEYCODE_ESCAPE = -1
KEYCODE_TAB = -1
KEYCODE_BACK = -1
KEYCODE_DOWN = -1
KEYCODE_UP = -1
KEYCODE_LEFT = -1
KEYCODE_RIGHT = -1
KEYCODE_INSERT = -1
KEYCODE_HOME = -1
KEYCODE_END = -1
KEYCODE_DELETE = -1
KEYCODE_KP_ADD = -1
KEYCODE_KP_SUBTRACT = -1
KEYCODE_KP_MULTIPLY = -1
KEYCODE_KP_DIVIDE = -1
KEYCODE_KP_DECIMAL = -1
KEYCODE_KP_DELETE = -1
KEYCODE_KP_ENTER = -1
KEYCODE_KP_0 = -1
KEYCODE_KP_1 = -1
KEYCODE_KP_2 = -1
KEYCODE_KP_3 = -1
KEYCODE_KP_4 = -1
KEYCODE_KP_5 = -1
KEYCODE_KP_6 = -1
KEYCODE_KP_7 = -1
KEYCODE_KP_8 = -1
KEYCODE_KP_9 = -1

EVENT_KEY_UP = 0
EVENT_KEY_DOWN = 1
EVENT_KEY_QUASIMODE = 2

KEYCODE_QUASIMODE_START = 0
KEYCODE_QUASIMODE_END = 1
KEYCODE_QUASIMODE_CANCEL = 2
KEYCODE_QUASIMODE_CANCEL2 = 3

QUASIMODE_TRIGGER_KEYS = ["Caps_Lock"]

#CASE_INSENSITIVE_KEYCODE_MAP = {}


def fill_keymap():
    '''Fill keymap'''
    global EXTRA_KEYCODES
    EXTRA_KEYCODES = []
    special_keycodes = {}
    display = get_display()
    for i in range(0, 255):
        keyval = display.keycode_to_keysym(i, 0)
        if int(keyval) > 0x110000:
            continue
        if keyval == gtk.keysyms.Return:
            special_keycodes["KEYCODE_RETURN"] = i
        elif keyval == gtk.keysyms.Escape:
            special_keycodes["KEYCODE_ESCAPE"] = i
        elif keyval == gtk.keysyms.Tab:
            special_keycodes["KEYCODE_TAB"] = i
        elif keyval == gtk.keysyms.BackSpace:
            special_keycodes["KEYCODE_BACK"] = i
        elif keyval == gtk.keysyms.Up:
            special_keycodes["KEYCODE_UP"] = i
        elif keyval == gtk.keysyms.Down:
            special_keycodes["KEYCODE_DOWN"] = i
        elif keyval == gtk.keysyms.Left:
            special_keycodes["KEYCODE_LEFT"] = i
        elif keyval == gtk.keysyms.Right:
            special_keycodes["KEYCODE_RIGHT"] = i
        elif keyval == gtk.keysyms.Insert:
            special_keycodes["KEYCODE_INSERT"] = i
        elif keyval == gtk.keysyms.Home:
            special_keycodes["KEYCODE_HOME"] = i
        elif keyval == gtk.keysyms.End:
            special_keycodes["KEYCODE_END"] = i
        elif keyval == gtk.keysyms.Delete:
            special_keycodes["KEYCODE_DELETE"] = i
        elif keyval == gtk.keysyms.KP_Add:
            special_keycodes["KEYCODE_KP_ADD"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "+"
        elif keyval == gtk.keysyms.KP_Subtract:
            special_keycodes["KEYCODE_KP_SUBTRACT"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "-"
        elif keyval == gtk.keysyms.KP_Multiply:
            special_keycodes["KEYCODE_KP_MULTIPLY"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "*"
        elif keyval == gtk.keysyms.KP_Divide:
            special_keycodes["KEYCODE_KP_DIVIDE"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "/"
        elif keyval == gtk.keysyms.KP_Decimal:
            special_keycodes["KEYCODE_KP_DECIMAL"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "."
        elif keyval == gtk.keysyms.KP_Delete:
            special_keycodes["KEYCODE_KP_DELETE"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "."
        elif keyval in (gtk.keysyms.KP_0, gtk.keysyms.KP_Insert):
            special_keycodes["KEYCODE_KP_0"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "0"
        elif keyval in (gtk.keysyms.KP_1, gtk.keysyms.KP_End):
            special_keycodes["KEYCODE_KP_1"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "1"
        elif keyval in (gtk.keysyms.KP_2, gtk.keysyms.KP_Down):
            special_keycodes["KEYCODE_KP_2"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "2"
        elif keyval in (gtk.keysyms.KP_3, gtk.keysyms.KP_Page_Down):
            special_keycodes["KEYCODE_KP_3"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "3"
        elif keyval in (gtk.keysyms.KP_4, gtk.keysyms.KP_Left):
            special_keycodes["KEYCODE_KP_4"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "4"
        elif keyval == gtk.keysyms.KP_5:
            special_keycodes["KEYCODE_KP_5"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "5"
        elif keyval in (gtk.keysyms.KP_6, gtk.keysyms.KP_Right):
            special_keycodes["KEYCODE_KP_6"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "6"
        elif keyval in (gtk.keysyms.KP_7, gtk.keysyms.KP_Home):
            special_keycodes["KEYCODE_KP_7"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "7"
        elif keyval in (gtk.keysyms.KP_8, gtk.keysyms.KP_Up):
            special_keycodes["KEYCODE_KP_8"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "8"
        elif keyval in (gtk.keysyms.KP_9, gtk.keysyms.KP_Page_Up):
            special_keycodes["KEYCODE_KP_9"] = i
            CASE_INSENSITIVE_KEYCODE_MAP[i] = "9"
        elif keyval == gtk.keysyms.KP_Enter:
            special_keycodes["KEYCODE_KP_ENTER"] = i
        else:
            char = unichr(int(keyval))
            if len(char) > 0 and ord(char) > 0:
                CASE_INSENSITIVE_KEYCODE_MAP[i] = str(char)
    global_vars = globals()
    for i in special_keycodes:
        global_vars[i] = special_keycodes[i]
        EXTRA_KEYCODES.append(special_keycodes[i])

fill_keymap()


class _KeyListener (Thread):
    '''Keyboard input handling thread'''

    __parent = None
    __callback = None

    __display = None

    __terminate = False
    __restart = False

    __capture = False

    __lock = False

    __caps_lock = None
    __num_lock_mod = None
    __key_mod = None

    def __init__(self, parent, callback):
        '''Initialize object'''
        Thread.__init__(self)
        self.__parent = parent
        self.__callback = callback

    def run(self):
        '''Main keyboard event loop'''
        def make_event(event_type, keycode=None):
            return {
                "event": event_type,
                "keycode": keycode,
            }
        self.__display = get_display()
        self.__display.set_error_handler(self.error_handler)
        '''Outter loop, used for configuration handling'''
        while not self.__terminate:
            trigger_key, trigger_keycode = self.grab(QUASIMODE_TRIGGER_KEYS)
            events = [X.KeyPress]
            if not self.__parent.getModality():
                events += [X.KeyRelease]
            self.__restart = False
            '''Inner loop, used for event processing'''
            while not self.__restart:
                event = self.__display.next_event()
                self.__lock = True
                with gtk.gdk.lock:
                    if hasattr(event, "detail") and \
                       event.detail == trigger_keycode and \
                       event.type in events:
                        if self.__parent.getModality():
                            continue
                        elif event.type == X.KeyPress:
                            self.__callback(make_event("quasimodeStart"))
                            self.__capture = True
                        elif event.type == X.KeyRelease:
                            self.__callback(make_event("quasimodeEnd"))
                            self.__capture = False
                    elif not self.__parent.getModality() and self.__capture \
                            and event.type in events:
                        modifiers_mask = gtk.gdk.MODIFIER_MASK
                        if self.__key_mod:
                            mod_str = self.__key_mod.upper()
                            mod = eval("gtk.gdk.%s_MASK" % mod_str)
                            modifiers_mask &= ~mod
                        state = event.state & modifiers_mask
                        keyval = self.__display.keycode_to_keysym(event.detail,
                                                                  state)
                        if not keyval and self.__num_lock_mod:
                            # print "numlock mod"
                            mod_str = self.__num_lock_mod.upper()
                            mod = eval("gtk.gdk.%s_MASK" % mod_str)
                            modifiers_mask &= ~mod
                            state = event.state & modifiers_mask
                            keyval = \
                                self.__display.keycode_to_keysym(event.detail,
                                                                 state)
                        # print keyval, event.detail
                        # FIXME: Handling of numpad "5" key, converting it to
                        # normal "5" key
                        if keyval == 65437:
                            keyval, event.detail = 53, 14
                        if event.detail in EXTRA_KEYCODES \
                           or sanitize_char(keyval):
                            if event.type == X.KeyPress:
                                self.__callback(make_event("keyDown",
                                                           event.detail))
                            else:
                                self.__callback(make_event("keyUp",
                                                           event.detail))

                self.__lock = False
            self.ungrab(QUASIMODE_TRIGGER_KEYS)

    def unlock(self):
        '''Unlock GDK threading lock'''
        if self.__lock:
            gtk.gdk.threads_leave()

    def stop(self):
        '''Halt thread: restart inner loop and kill outter loop'''
        self.__restart = True
        self.__terminate = True

    def restart(self):
        '''Restart inner loop to use latest options'''
        self.__restart = True

    def error_handler(self, error, *args):
        '''Catch Xlib errors'''
        logging.critical("X protocol error caught : %s" % error)
        self.__parent.stop()

    def grab(self, keys):
        '''Grab specific keys'''
        root_window = self.__display.screen().root
        keycode = 0
        xset_cmd = which("xset")
        xmodmap_cmd = which("xmodmap")
        if not xset_cmd:
            logging.warn(
                "xset not found, you might experience some bad key-repeat problems")
        for key in keys:
            keycode = get_keycode(key)
            if not keycode:
                continue
            if xset_cmd:
                # FIXME: revert on exit
                os.system("%s -r %d" % (xset_cmd, keycode))
            if xmodmap_cmd:
                cmd_status, cmd_stdout = get_cmd_output(
                    "%s -pm" % xmodmap_cmd)
                if cmd_status == 0 and cmd_stdout:
                    lines = cmd_stdout.splitlines()
                else:
                    lines = []
                lock_line = [l.strip().split()
                             for l in lines if l.startswith("lock")]
                num_line = [l.strip().split()
                            for l in lines if "Num_Lock" in l]
                key_line = [l.strip().split() for l in lines if key in l]
                if lock_line:
                    parts = lock_line[0]
                    if len(parts) > 1:
                        self.__caps_lock = parts[1]
                if num_line:
                    parts = num_line[0]
                    if len(parts) > 1:
                        self.__num_lock_mod = parts[0]
                if key_line:
                    parts = key_line[0]
                    if len(parts) > 1:
                        self.__key_mod = parts[0]
            if key == "Caps_Lock":
                if not self.__caps_lock:
                    logging.debug("Caps Lock already disabled!")
                else:
                    self.disable_caps_lock()
                    atexit.register(self.enable_caps_lock)
            ownev = not self.__parent.getModality()
            root_window.grab_key(keycode, X.AnyModifier, ownev,
                                 X.GrabModeAsync, X.GrabModeAsync)
            return key, keycode
        logging.critical("Couldn't find quasimode key")
        self.__parent.stop()
        return None, None

    def ungrab(self, keys):
        '''Ungrab specific keys'''
        root_window = self.__display.screen().root
        for keycode in keys:
            root_window.ungrab_key(keycode, 0)

    def disable_caps_lock(self):
        '''Disable Caps Lock'''
        if self.__caps_lock:
            assert logging.debug("Using xmodmap to disable Caps Lock") or True
            os.system('xmodmap -e "clear Lock"')

    def enable_caps_lock(self):
        '''Enable Caps Lock'''
        if self.__caps_lock:
            assert logging.debug("Using xmodmap to enable Caps Lock") or True
            os.system('xmodmap -e "add Lock = %s"' % self.__caps_lock)


class InputManager (object):
    '''Input event manager object'''

    __mouseEventsEnabled = False
    __qmKeycodes = [0, 0, 0, 0]
    __isModal = False
    __inQuasimode = False

    __keyListener = None

    def __init__(self):
        '''Initialize object'''
        pass

    def __timerCallback(self):
        '''Handle gobject timeout'''
        with gtk.gdk.lock:
            try:
                self.onTick(_TIMER_INTERVAL_IN_MS)
            except KeyboardInterrupt:
                gtk.main_quit()
                return False
            finally:
                return True  # Return true to keep the timeout running

    def __keyCallback(self, info):
        '''Handle callbacks from KeyListener'''
        if info["event"] == "quasimodeStart":
            self.onKeypress(EVENT_KEY_QUASIMODE,
                            KEYCODE_QUASIMODE_START)
        elif info["event"] == "quasimodeEnd":
            self.onKeypress(EVENT_KEY_QUASIMODE,
                            KEYCODE_QUASIMODE_END)
        elif info["event"] == "someKey":
            self.onSomeKey()
        elif info["event"] in ["keyUp", "keyDown"]:
            keycode = info["keycode"]
            if info["event"] == "keyUp":
                eventType = EVENT_KEY_UP
            else:
                eventType = EVENT_KEY_DOWN
            self.onKeypress(eventType, keycode)
        else:
            logging.warn("Don't know what to do with event: %s" % info)

    def run(self):
        '''Main input events processing loop'''
        logging.info("Entering InputManager.run ()")

        timeout_source = gobject.timeout_add(_TIMER_INTERVAL_IN_MS,
                                             self.__timerCallback)

        self.__keyListener = _KeyListener(self, self.__keyCallback)
        self.__keyListener.start()

        try:
            try:
                self.onInit()
                gtk.main()
            except KeyboardInterrupt as e:
                logging.error(e)
            except IOError as e:
                logging.error(e)
            except Exception as e:
                logging.error(e)
        finally:
            self.__keyListener.stop()
            gobject.source_remove(timeout_source)

        logging.info("Exiting InputManager.run ()")
        exit(1)

    def stop(self):
        '''Stop main loop by exiting from gtk mainloop'''
        with suppress(Exception):
            self.__keyListener.unlock()
            gtk.main_quit()

    def enableMouseEvents(self, isEnabled):
        # TODO: Implementation needed.
        self.__mouseEventsEnabled = isEnabled

    def onKeypress(self, eventType, vkCode):
        pass

    def onSomeKey(self):
        pass

    def onSomeMouseButton(self):
        pass

    def onExitRequested(self):
        pass

    def onMouseMove(self, x, y):
        pass

    def getQuasimodeKeycode(self, quasimodeKeycode):
        return self.__qmKeycodes[quasimodeKeycode]

    def setQuasimodeKeycode(self, quasimodeKeycode, keycode):
        # TODO: Implementation needed.
        self.__qmKeycodes[quasimodeKeycode] = keycode

    def setModality(self, isModal):
        # TODO: Implementation needed.
        if self.__isModal != isModal:
            self.__isModal = isModal
            if self.__keyListener:
                self.__keyListener.restart()

    def getModality(self):
        return self.__isModal

    def getIdleTime(self):
        return idle_time()
        
    def setCapsLockMode(self, caps_lock_enabled):
        if caps_lock_enabled:
            self.__keyListener.enable_caps_lock()
        else:
            self.__keyListener.disable_caps_lock()

    def onTick(self, msPassed):
        pass

    def onInit(self):
        pass
