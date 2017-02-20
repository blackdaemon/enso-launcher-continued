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
#   enso
#
# ----------------------------------------------------------------------------

import logging


class EventResponderList(object):
    """
    Behaves like a dictionary with limited functionality.  When it become
    non-empty, an event handler is registered for a particular event
    and called whenever the event occurs.  When the it's empty,
    the event handler is unregistered and will not be called until
    it becomes non-empty again.
    """

    def __init__(self, eventManager, eventName, responderFunc):
        self.__eventManager = eventManager
        self.__eventName = eventName
        self.__responderFunc = responderFunc
        self.__isRegistered = False
        self.__items = {}

    def __setitem__(self, key, value):
        """
        if (not isinstance(item, slice) or
                not (item.start is None and item.stop is None)):
            raise NotImplementedError()
        """
        self.__items[key] = value
        self.__onItemsChanged()

    def __delitem__(self, key):
        del self.__items[key]
        self.__onItemsChanged()
        
    def __iter__(self):
        for key, item in self.__items.items():
            yield key, item

    def __onItemsChanged(self):
        if self.__items and (not self.__isRegistered):
            assert logging.debug(
                "Registering EventResponderList for onTimer event") or True
            self.__eventManager.registerResponder(
                self.__responderFunc,
                self.__eventName
            )
            self.__isRegistered = True
        elif self.__isRegistered and (not self.__items):
            assert logging.debug(
                "Removing EventResponderList for onTimer event") or True
            self.__eventManager.removeResponder(self.__responderFunc)
            self.__isRegistered = False

    def fromlist(self, lst):
        self.__items = dict((id(item), item) for item in lst)
        self.__onItemsChanged()

    def clear(self):
        self.__items.clear()
        self.__onItemsChanged()
