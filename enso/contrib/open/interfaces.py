# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:

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

__updated__ = "2017-02-23"

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import os
import threading
import urlparse
from abc import ABCMeta, abstractmethod
from xml.sax.saxutils import escape as xml_escape

try:
    import regex as re
except Exception, e:
    import re

import enso.messages
from enso.contrib.open import shortcuts
from enso.contrib.open import utils
from enso.utils.decorators import timed_execution

def display_message(msg):
    enso.messages.displayMessage("<p>%s</p>" % msg)


class ShortcutAlreadyExistsError(Exception):
    pass


# TODO: This is not a good set of URL regexps! Do more unit-testing
_RE_URL_FINDERS = [
    re.compile(r"""
        (   # hostname / IP address
            [0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}     # IP address
            |    # or
            (
                ((news|telnet|nttp|file|http|ftp|https)://)    # Protocol
                |
                (www|ftp)[-A-Za-z0-9]*\.
            )[-A-Za-z0-9\.]+                                   # Rest of hostname / IP
        )
        (:[0-9]*)?/[-A-Za-z0-9_\$\.\+\!\*\(\),;:@&=\?/~\#\%]*[^]'\.}>\),\\"]"
        """, re.VERBOSE),
    re.compile(
        "([0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|(((news|telnet|nttp|file|http|ftp|https)://)|(www|ftp)[-A-Za-z0-9]*\\.)[-A-Za-z0-9\\.]+)(:[0-9]*)?"),
    re.compile("(~/|/|\\./)([-A-Za-z0-9_\\$\\.\\+\\!\\*\\(\\),;:@&=\\?/~\\#\\%]|\\\\)+"),
    re.compile(r"(mailto:)?[-_\.\d\w]+@[-_\.\d\w]+", re.IGNORECASE),
]


def is_valid_url(text):
    """
    >>> is_valid_url("mailto:aks12kjACd.ka-0a_0@alsksk.com")
    True
    >>> is_valid_url("<aks12kjACd.ka-0a_0@alsksk.com>")
    True
    """
    return any(urltest.search(text, re.I) for urltest in _RE_URL_FINDERS)


def is_url2(text):
    """If @text is an URL, return a cleaned-up URL, else return None"""
    text = text.strip()
    components = list(urlparse.urlparse(text))
    domain = "".join(components[1:])
    dotparts = domain.rsplit(".")

    # 1. Domain name part is one word (without spaces)
    # 2. Urlparse parses a scheme (http://), else we apply heuristics
    if len(domain.split()) == 1 and (components[0] or ("." in domain and
                                                       len(dotparts) >= 2 and len(dotparts[-1]) >= 2 and
                                                       any(char.isalpha() for char in domain) and
                                                       all(part[:1].isalnum() for part in dotparts))):
        if not components[0]:
            url = "http://" + "".join(components[1:])
        else:
            url = text
        name = ("".join(components[1:3])).strip("/")
        if name:
            return url


class IOpenCommand(object):
    """
    Open command interface
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        super(IOpenCommand, self).__init__()

    @abstractmethod
    def get_shortcuts(self, force_reload=False):
        """ Return ShortcutDictionary of Shortcut objects """
        return None

    @abstractmethod
    def is_runnable(self, shortcut_name):
        """
        Return True if the shortcut represents runnable file that could
        open another files.
        This is used to identify correct shortcuts for 'open with' command.
        """
        return None

    @abstractmethod
    def add_shortcut(self, shortcut_name, target):
        """ Register shortcut """
        return

    @abstractmethod
    def remove_shortcut(self, shortcut_name):
        """
        Unregister shortcut.
        Undo functionality should be implemented here.
        """
        return

    @abstractmethod
    def undo_remove_shortcut(self):
        """ Undo of last unregistering shortcut """
        return

    @abstractmethod
    def run_shortcut(self, shortcut_name):
        """ Run the program/document represented by shortcut """
        return

    @abstractmethod
    def open_with_shortcut(self, shortcut_name, targets):
        """
        Open target(s) (file(s)) with the application represented
        by runnable shortcut.
        """
        return


class AbstractOpenCommand(IOpenCommand):
    """
    Implements platform independent Open command functionality.
    Platform implementations should subclass this class and override
    all abstract methods.
    """

    def __init__(self):
        super(AbstractOpenCommand, self).__init__()

        def reloader_thread(self):
            with timed_execution("Refreshed \"open\" command shortcuts dict"):
                self._reload_shortcuts(self.shortcut_dict)
                """
                if not isinstance(shortcuts, dict):
                    shortcuts = dict(shortcuts)
                self.shortcuts_map.update(shortcuts)
                """

        # Reload shortcuts dictionary in the thread
        self._unlearn_open_undo = []
        self.shortcut_dict = shortcuts.ShortcutsDict()
        t = threading.Thread(target=reloader_thread, args=(self,))
        # t.setDaemon(True)
        t.start()

    def get_shortcuts(self, force_reload=False):
        """ Return ShortcutsDict of all collected Shortcut objects """
        if force_reload or self.shortcut_dict is None:
            with timed_execution("Reloading shortcuts dict"):
                if self.shortcut_dict is None:
                    self.shortcut_dict = shortcuts.ShortcutsDict()
                self._reload_shortcuts(self.shortcut_dict)
        return self.shortcut_dict

    def is_runnable(self, shortcut_name):
        """
        Return True if the shortcut represents runnable file that could
        open another files.
        This is used to identify correct shortcuts for 'open with' command.
        """
        return self._is_runnable(
            self.shortcut_dict[shortcut_name])

    def add_shortcut(self, shortcut_name, target):
        """ Register shortcut """
        # Cleanup name
        shortcut_name = shortcut_name.replace(":", "").replace("?", "").replace("\\", "")

        try:
            shortcut = self._save_shortcut(
                shortcut_name, target)
        except ShortcutAlreadyExistsError:
            return None

        self.shortcut_dict[shortcut_name] = shortcut

        return shortcut

    def remove_shortcut(self, shortcut_name):
        """
        Unregister shortcut.
        Undo functionality is implemented here.
        """
        shortcut = self.shortcut_dict[shortcut_name]
        if shortcut.flags & shortcuts.SHORTCUT_FLAG_CANTUNLEARN:
            raise Exception("Shortcut can't be unlearned: %s" % shortcut.target)
        try:
            removed = self._remove_shortcut(shortcut)
        except Exception as e:
            raise
        else:
            if removed:
                self._unlearn_open_undo.append(shortcut)
                del self.shortcut_dict[shortcut_name]
            else:
                raise Exception("Shortcut can't be unlearned: %s" % shortcut.target)

    def undo_remove_shortcut(self):
        if len(self._unlearn_open_undo) > 0:
            shortcut = self._unlearn_open_undo.pop()
            return self.add_shortcut(shortcut.name, shortcut.target)
        else:
            return None

    def run_shortcut(self, shortcut_name):
        """ Run the program/document represented by shortcut """
        self._run_shortcut(self.shortcut_dict[shortcut_name])

    def open_with_shortcut(self, shortcut_name, targets):
        """ Open target(s) (file(s)) with the application represented
        by runnable shortcut
        """
        # User did not select any application. Offer system "Open with..." dialog
        if not shortcut_name:
            self._open_with_shortcut(None, targets)
            return

        display_message(
            u"Opening selected %s with <command>%s</command>..."
            % ("files" if len(targets) > 1 else "file" if os.path.isfile(targets[0]) else "folder",
                xml_escape(shortcut_name))
        )

        self._open_with_shortcut(self.shortcut_dict[shortcut_name], targets)
        # print file, application

    def _is_url(self, text):
        return is_valid_url(text)

    @abstractmethod
    def _reload_shortcuts(self, shortcuts_dict):
        """ Update dictionary of application/document shortcuts.
        Items in the dictionary must be of shortcuts.Shortcut type.

        Example:
            from enso.contrib.open import shortcuts
            shortcuts_dict['internet explorer'] = shortcuts.Shortcut(
                'internet explorer',
                shortcuts.SHORTCUT_TYPE_EXECUTABLE,
                'iexplore.exe')
        """
        return

    @abstractmethod
    def _get_learn_as_dir(self):
        """ Return directory for storing of "Enso learn as" shortcuts.
        Implement this in platform specific class.
        """
        return None

    @abstractmethod
    def _save_shortcut(self, name, target):
        """ Register shortcut """
        return

    @abstractmethod
    def _remove_shortcut(self, shortcut):
        """ Unregister shortcut """
        return

    @abstractmethod
    def _run_shortcut(self, shortcut):
        """ Run the program/document represented by shortcut """
        return

    @abstractmethod
    def _get_shortcut_type(self, file_name):
        return None

    @abstractmethod
    def _is_runnable(self, shortcut):
        """ Return True if the shortcut represents runnable file that could
        open another files.
        This is used to identify correct shortcuts for 'open with' command.
        """
        return None

    @abstractmethod
    def _open_with_shortcut(self, name, file_names):
        """ Open target(s) (file(s)) with the application represented
        by runnable shortcut.
        """
        return
