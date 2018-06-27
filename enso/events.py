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

# ----------------------------------------------------------------------------
#
#   enso.events
#
# ----------------------------------------------------------------------------

"""
    The central event clearinghouse.

    Wraps the InputManager to provide event handling for the user
    interface.  User interface code, and indeed any client Python
    code, can register event responders of several types (listed
    below).  These responders can be added and removed in real time,
    allowing the user interface to respond to events differently based
    on system state; for example, a timer event handler that draws the
    quasimode might be removed when not in the quasimode, to reduce
    overhead when timer events occur and improve system performance.

    The event manager implemented here does not implement a main event
    loop; that is implemented the InputManager.  Calling the
    run method of the event manager enters a main event loop that
    calls the various on<event>() methods when events occur.  These
    methods in turn call any responder functions registered for the
    appropriate type of event.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import logging
import time

from enso import input
from enso.utils import call_once_for_given_args


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

# A list of all possible types of events that event responders can be
# registered for.
EVENT_TYPES = [
    "key",
    "timer",
    # LONGTERM TODO: Is "click" ever used?  Doesn't seem to be...
    "click",
    "dismissal",
    "traymenu",
    "idle",
#    "session_lock",  # TODO: Implement session lock detection
#    "session_unlock",  # TODO: Implement session unlock detection
#    "screensaver_start",  # TODO: Implement screensaver-start detection
#    "screensaver_stop",  # TODO: Implement screensaver-stop detection
    "init",
    "mousemove",
    "somekey"
]

# "idle" event will be triggered on user inactivity
IDLE_TIMEOUT_10M = 10 * 60
IDLE_TIMEOUT_5M = 5 * 60
IDLE_TIMEOUT_1M = 1 * 60
IDLE_TIMEOUT_30S = 30
IDLE_TIMEOUT_20S = 20
IDLE_TIMEOUT_10S = 10
IDLE_TIMEOUT_5S = 5

# Default timeout is 5 minutes (legacy)
IDLE_TIMEOUT = IDLE_TIMEOUT_5M

# Scale of timeouts from largest to smallest. Used internally.
_IDLE_TIMEOUT_SCALE = list(
    reversed(sorted(globals()[v] for v in globals().keys() if v.startswith("IDLE_TIMEOUT_")))
)


class EventResponderFuncWrapper(object):
    """
    Event responder function wrapper
    It serves only one purpose: to provide is_running() function to the responder functions
    so that the function execution can be tracked and synchronized.
    """

    def __init__(self, func):
        self.__func = func
        self.__is_running = False

    def is_running(self):
        return self.__is_running

    def get_function(self):
        return self.__func

    def __call__(self, *args, **kwargs):
        self.__is_running = True
        try:
            return self.__func(*args, **kwargs)
        finally:
            self.__is_running = False

    def __repr__(self):
        return repr(self.__func)

    def __str__(self):
        return str(self.__func)

    """ Mandatory functions for a wrapper """

    def __getattr__(self, attr):
        return getattr(self.__func, attr)

    """ Mandatory functions for a wrapper """

    def __cmp__(self, other):
        if self.__func > other:
            return 1
        elif self.__func < other:
            return -1
        elif self.__func == other:
            return 0

    """ Mandatory functions for a wrapper """

    def __eq__(self, other):
        return self.__func == other

    """ Mandatory functions for a wrapper """
    @property
    def __lt__(self, other):
        raise AttributeError()

    @property
    def __le__(self, other):
        raise AttributeError()

    @property
    def __ne__(self, other):
        raise AttributeError()

    @property
    def __gt__(self, other):
        raise AttributeError()

    @property
    def __ge__(self, other):
        raise AttributeError()


# ----------------------------------------------------------------------------
# EventManager class
# ----------------------------------------------------------------------------

class EventManager(input.InputManager):
    """
    This class is the event-handling singleton, inheriting from the
    input manager class.  It creates a dictionary of event responders,
    and overrides the input manager's on<eventtype>() methods to call
    every registered responder for <eventtype>.
    """

    __instance = None

    @classmethod
    def get(cls, reload_=False):
        if not cls.__instance:
            cls.__instance = cls()
        elif reload_:
            del cls.__instance
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        """
        Initializes the event manager, creates an internal dictionary
        of responders.
        """
        input.InputManager.__init__(self)  # @UndefinedVariable

        # Copy the core event types to the dynamic event types list,
        # which can be extended with the createEventType() method.
        self._dynamicEventTypes = EVENT_TYPES[:]

        self.__responders = {}
        for evt in self._dynamicEventTypes:
            self.__responders[evt] = []

        self.__idlingStage = 0

    def createEventType(self, typeName):
        """
        Creates a new event type to be responded to.

        Implemented to allow for 'startQuasimode' and 'endQuasimode'
        event types to be registered; it seems to be the logical way
        for all event types to be dealt with.
        """
        assert typeName not in self._dynamicEventTypes,\
            "dynamic-event-type '%s' has been already created." % typeName
        self.__responders[typeName] = []
        self._dynamicEventTypes.append(typeName)

    def triggerEvent(self, eventType, *args, **kwargs):
        """
        Used to (artificially or really) trigger an event type.
        """
        assert eventType in self._dynamicEventTypes,\
            "dynamic-event-type '%s' is uknown" % eventType
        perf = []

        # Act on copy of the responders list, as the responder function might
        # change the original list (by calling registerResponder or removeReponder)
        # while we are iterating over it
        for func in self.__responders[eventType][:]:
            started = time.time()
            try:
                sub_perf = func(*args, **kwargs)
            except Exception as e:
                logging.error(e)
            else:
                if isinstance(sub_perf, list):
                    perf.extend(sub_perf)
                elapsed = time.time() - started
                perf.append((func, args, kwargs, elapsed))
        return perf

    def getResponders(self, eventType):
        """
        Returns a list of all responders of the given type.
        """
        assert eventType in self._dynamicEventTypes,\
            "dynamic-event-type '%s' is uknown" % eventType
        return self.__responders[eventType]

    def registerResponder(self, responderFunc, eventType):
        """
        Registers a responder for event type eventType.
        """
        assert eventType in self._dynamicEventTypes,\
            "dynamic-event-type '%s' is uknown" % eventType
        assert responderFunc not in self.getResponders(eventType),\
            "responder-function '%s' for event-type '%s' is already registered in the responder" \
            % (responderFunc.__name__, eventType)

        responderList = self.__responders[eventType]
        assert logging.debug("Added a responder function!") or True

        # If this is a dismissal responder and we don't currently have
        # any registered, enable mouse events so we're actually
        # notified of dismissals via mouse input.
        if eventType in ["dismissal", "mousemove"]:
            self.enableMouseEvents(True)  # IGNORE:E1101

        # Wrap the responder-function to provide is_running() function
        responderList.append(EventResponderFuncWrapper(responderFunc))

    def removeResponder(self, responderFunc, sync=False):
        """
        Removes responderFunc from the internal responder dictionary.

        NOTE: Removes responderFunc from responding to ALL types of events.
        """
        def removeResponderFunc(responderList, responderFunc, sync):
            # Update original list
            responderList.remove(responderFunc)
            assert logging.debug(
                "Removed a responder function %s!", responderFunc.__name__) or True
            if sync:
                try:
                    assert logging.debug(
                        "Syncing %s responder wrapper", responderFunc) or True
                    while responderFunc.is_running():
                        # This is mandatory, otherwise the performance goes down
                        time.sleep(0.01)
                except Exception:
                    logging.error(
                        "Error calling is_running() function for responder-wrapper %s",
                        responderFunc
                    )

        for eventType in self.__responders.keys():
            # Save the original list...
            responderList = self.__responders[eventType]
            # ...and iterate over its copy
            for responderWrapper in self.__responders[eventType][:]:
                # Unregister responder-function
                if responderWrapper == responderFunc:
                    removeResponderFunc(responderList, responderWrapper, sync)
                    break

        if eventType in ["dismissal", "mousemove"]:
            # If we're removing our only dismissal responder,
            # disable mouse events since we only need to know
            # about them for the purposes of dismissal events.
            numMouseResponders = len(self.__responders["mousemove"])
            numDismissResponders = len(self.__responders["dismissal"])
            if (numMouseResponders + numDismissResponders) == 0:
                self.enableMouseEvents(False)  # IGNORE:E1101

    def run(self):
        """
        Runs the main event loop.
        """
        input.InputManager.run(self)  # @UndefinedVariable

    # ----------------------------------------------------------------------
    # Functions for transferring the existing event handlers to the more
    # robust registerResponder method outlined above.
    # ----------------------------------------------------------------------

    def _onIdle(self, idle_seconds):
        """
        High-level event handler called whenever we haven't received
        any useful input events for IDLE_TIMEOUT seconds.
        """
        @call_once_for_given_args
        def report_function_call_deprecation(func):
            logging.warning(
                    "\"idle\" event handling function without an argument is deprecated (function {}() in module {})!".format(
                        func.get_function().__name__, func.get_function().__module__)
            )

        for func in self.__responders["idle"]:
            try:
                func(idle_seconds)
            except TypeError as e:
                report_function_call_deprecation(func)
                # Call legacy onidle handler only on default interval of 5 minutes
                if idle_seconds == IDLE_TIMEOUT:
                    func()

    def onInit(self):
        """
        Low-level event handler called as soon as the event manager
        starts running.
        """
        for func in self.__responders["init"]:
            func()

    def onExitRequested(self):
        """
        Called when another process wants us to exit gracefully.
        """
        logging.info("Exit request received.")
        self.stop()  # IGNORE:E1101

    def onTick(self, msPassed):
        """
        Low-level event handler called at a regular interval.  The
        number of milliseconds passed since the last onTick() call is
        passed in, although this value may not be 100% accurate.
        """
        super(EventManager, self).onTick(msPassed)

        for timeout in _IDLE_TIMEOUT_SCALE:
            if self.getIdleTime() >= timeout * 1000:
                if self.__idlingStage < timeout:
                    self.__idlingStage = timeout
                    try:
                        self._onIdle(timeout)
                    except Exception as e:
                        logging.error(e)
                break
        else:
            if self.__idlingStage > 0:
                self.__idlingStage = 0

        for func in self.__responders["timer"]:
            func(msPassed)

    def onTrayMenuItem(self, menuId):
        """
        Low-level event handler called whenever the user selects a
        menu item on the popup menu of the Tray Icon.
        """
        self._onDismissalEvent()
        for func in self.__responders["traymenu"]:
            func(menuId)

    def _onDismissalEvent(self):
        """
        High-level event handler called whenever a keypress, mouse
        movement, or mouse button click is made.
        """
        self.__idlingStage = 0

        for func in self.__responders["dismissal"]:
            func()

    def onKeypress(self, eventType, keyCode):
        """
        Low-level event handler called whenever a quasimodal keypress
        is made.
        """
        super(EventManager, self).onKeypress(eventType, keyCode)
        self._onDismissalEvent()
        for func in self.__responders["key"]:
            func(eventType, keyCode)

        # The following message may be used by system tests.
        #logging.debug( "onKeypress: %s, %s" % (eventType, keyCode) )

    def onMouseMove(self, x, y):
        """
        Low-level event handler that deals with any mouse movement
        event.  The absolute position of the mouse cursor on-screen is
        passed in.
        """
        super(EventManager, self).onMouseMove(x, y)
        self._onDismissalEvent()
        for func in self.__responders["mousemove"]:
            func(x, y)

    def onSomeMouseButton(self):
        """
        Low-level event handler called whenever any mouse button is
        pressed.
        """
        super(EventManager, self).onSomeMouseButton()
        self._onDismissalEvent()

    def onSomeKey(self):
        """
        Low-level event handler called whenever a non-quasimodal
        keypress is made.
        """
        super(EventManager, self).onSomeKey()
        for func in self.__responders["somekey"]:
            func()
        self._onDismissalEvent()
