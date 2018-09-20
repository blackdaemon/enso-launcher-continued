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

"""
TODO:
    - Resolve duplicate names in gtk_bookmarks (use part of directory on duplicated entries)
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from __future__ import with_statement
import logging
import os

import gio
from gtk.gdk import lock as gtk_lock

from enso.contrib.open import (
    shortcuts,
    dirwatcher
)


SHORTCUT_CATEGORY = "gtk-bookmark"

# Default legacy bookmarks file location for GTK-2
BOOKMARKS_DIR = os.path.expanduser("~")
BOOKMARKS_FILE = ".gtk-bookmarks"

# New bookmarks file location for GTK-3 
if os.path.isfile(os.path.expanduser("~/.config/gtk-3.0/bookmarks")):
    BOOKMARKS_DIR = os.path.expanduser("~/.config/gtk-3.0")
    BOOKMARKS_FILE = "bookmarks"

BOOKMARKS_PATH = os.path.join(BOOKMARKS_DIR, BOOKMARKS_FILE)


def get_bookmarks():
    logging.info("Loading gtk-bookmarks")
    basename = os.path.basename
    places = []
    with open(BOOKMARKS_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            items = line.strip().split(" ", 1)
            uri = items[0]
            with gtk_lock:
                gfile = gio.File(uri)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
                if len(items) > 1:
                    title = items[1].rstrip()
                else:
                    disp = gfile.get_parse_name()
                    title = basename(disp)
                locpath = gfile.get_path()
                new_uri = gfile.get_uri()
            if locpath:
                shortcut = shortcuts.Shortcut(
                    "%s [places]" % title, shortcuts.SHORTCUT_TYPE_FOLDER, locpath, category=SHORTCUT_CATEGORY)
            else:
                shortcut = shortcuts.Shortcut(
                    "%s [places]" % title, shortcuts.SHORTCUT_TYPE_URL, new_uri, category=SHORTCUT_CATEGORY)
            #print shortcut
            places.append(shortcut)
    logging.info("Loaded %d gtk-bookmarks" % len(places))
    return places


def register_monitor_callback(callback_func):
    dirwatcher.register_monitor_callback(
        callback_func,
        ((BOOKMARKS_DIR, False),)
    )
