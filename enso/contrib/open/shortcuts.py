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

import time
import os
import logging

SHORTCUT_TYPE_EXECUTABLE = 'x' # .exe, .com, .cmd, .bat, .py
SHORTCUT_TYPE_FOLDER = 'f'
SHORTCUT_TYPE_URL = 'u'
SHORTCUT_TYPE_CONTROL_PANEL = 'c' # control-panel applets and .msc
SHORTCUT_TYPE_DOCUMENT = 'd' # All other shortcuts
SHORTCUT_TYPE_VIRTUAL = 'v' # Virtual folders/links in Vista/Win7

SHORTCUT_FLAG_CANTUNLEARN = 1


_SHORTCUT_TYPES = (
    SHORTCUT_TYPE_EXECUTABLE
    ,SHORTCUT_TYPE_FOLDER
    ,SHORTCUT_TYPE_URL
    ,SHORTCUT_TYPE_CONTROL_PANEL
    ,SHORTCUT_TYPE_DOCUMENT
    ,SHORTCUT_TYPE_VIRTUAL
    )
_SHORTCUT_TYPES_WITH_MANDATORY_TARGET = (
    SHORTCUT_TYPE_EXECUTABLE
    ,SHORTCUT_TYPE_URL
    ,SHORTCUT_TYPE_DOCUMENT
    )


class Shortcut( object ):
    def __init__(self, name, type, target, shortcut_filename=None, category=None):
        assert name, "Name must not be empty"
        assert type in _SHORTCUT_TYPES, "Type must be valid type: %s (name=%s)" % (type, name)
        assert target if type in _SHORTCUT_TYPES_WITH_MANDATORY_TARGET else True, \
            "Target can't be empty for given type: %s (name=%s)" % (type, name)
        #assert shortcut_filename if type not in (SHORTCUT_TYPE_CONTROL_PANEL, SHORTCUT_TYPE_FOLDER, SHORTCUT_TYPE_VIRTUAL) else True, \
        #    "Shortcut_filename must not be empty if type is not 'c' or 'f' (name=%s)" % name

        self.name = name
        self.type = type
        self.target = target
        self.shortcut_filename = shortcut_filename
        self.category = category

        #TODO:Implement special shortcuts (not learned, not unlearnable) as a subclasses
        self.flags = 0
        if not shortcut_filename or type in SHORTCUT_TYPE_CONTROL_PANEL:
            self.flags |= SHORTCUT_FLAG_CANTUNLEARN


class ShortcutsDict( dict ):
    """
    Dictionary object that provides additional attribute 'updated_on'
    holding timestamp of last dict update.

    Events that update 'updated_on' attribute:
    1. Instantiation
    2. Setting item as d[k] = item, only when item is different
       (i.e. d.get(k, None) != item)
    3. Deleting item as del d[k]
    4. Updating dictionary by d.update(nd)

    This class is proxy class to native dict object.
    """

    def __init__(self, *args, **kwargs):
        super(ShortcutsDict, self).__init__(*args, **kwargs)
        self.updated_on = time.time()

    def __setitem__(self, item, value):
        old_value = self.get(item, None)
        super(ShortcutsDict, self).__setitem__(item, value)
        if old_value != value:
            self.updated_on = time.time()
        assert logging.debug("dict item inserted") or True

    def __delitem__(self, item):
        super(ShortcutsDict, self).__delitem__(item)
        self.updated_on = time.time()
        assert logging.debug("dict item deleted: %s", item) or True

    def update(self, *args, **kwargs):
        try:
            super(ShortcutsDict, self).update(*args, **kwargs)
        finally:
            if args or kwargs:
                self.updated_on = time.time()
            assert logging.debug("dict updated") or True

    def update_by_dir(self, directory, new_dict):
        delitem = super(ShortcutsDict, self).__delitem__
        directory = os.path.normpath(directory).lower()
        for key, shortcut in super(ShortcutsDict, self).items():
            if not shortcut.type in (SHORTCUT_TYPE_EXECUTABLE, SHORTCUT_TYPE_DOCUMENT, SHORTCUT_TYPE_FOLDER):
                continue
            if shortcut.shortcut_filename:
                shortcut_directory = shortcut.shortcut_filename.lower()
            else:
                shortcut_directory = shortcut.target
            if shortcut_directory.startswith(directory):
                #print key, "-->", shortcut.shortcut_filename
                if key not in new_dict:
                    delitem(key)
        try:
            super(ShortcutsDict, self).update(new_dict)
        finally:
            self.updated_on = time.time()

    def update_by_category(self, category, new_dict):
        delitem = super(ShortcutsDict, self).__delitem__
        for key, shortcut in super(ShortcutsDict, self).items():
            if shortcut.category != category:
                continue
            if not shortcut.type in (SHORTCUT_TYPE_EXECUTABLE, SHORTCUT_TYPE_DOCUMENT, SHORTCUT_TYPE_FOLDER, SHORTCUT_TYPE_URL):
                continue
            #print key, "-->", shortcut.shortcut_filename
            if key not in new_dict:
                delitem(key)
        try:
            super(ShortcutsDict, self).update(new_dict)
        finally:
            self.updated_on = time.time()

"""
class ShortcutsDict(object):

    def __init__(self, init_list = None):
        if init_list:
            self.data = dict(init_list)
        else:
            self.data = {}
        self.updated_on = time.time()

    def __setitem__(self, item, value):
        _value = self.data.get(item, None)
        if _value != value:
            self.updated_on = time.time()
            self.data[item] = value
            logging.debug("dict item inserted")

    def __delitem__(self, item):
        self.updated_on = time.time()
        del self.data[item]
        logging.debug("dict item deleted: %s" % item)

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)

    def get(self, key, default = None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def has_key(self, key):
        return self.data.has_key(key)

    def update(self, d):
        self.data.update(d)
        self.updated_on = time.time()
        logging.debug("dict updated")

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def iterkeys(self):
        return self.data.iterkeys()

    def itervalues(self):
        return self.data.itervalues()

    def pop(self, key):
        return self.data.pop(key)

    def get_keys_cached(self, hash):
        return self.keys()
"""

class ShortcutsManager( object ):

    instance = None

    @classmethod
    def get(cls):
        if cls.instance is None:
            cls.instance = ShortcutsManager()
        return cls.instance

    def __init__(self):
        pass


# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: