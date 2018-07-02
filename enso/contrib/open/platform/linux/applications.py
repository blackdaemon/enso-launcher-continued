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

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Future imports
from __future__ import with_statement

import logging
import os
from distutils.spawn import find_executable

from gio import app_info_get_all  # @UnresolvedImport Keep PyLint and PyDev happy
from gio.unix import desktop_app_info_set_desktop_env
from gtk.gdk import lock as gtk_lock
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from enso.contrib.open import (
    shortcuts,
    dirwatcher
)
from enso.platform.linux import DESKTOP_ENVIRONMENT


SHORTCUT_CATEGORY = "application"

applications_dict = {}


def get_applications():
    logging.info("open-command: Loading application shortcuts")
    # Add this to the default
    whitelist = set([
        # if you set/reset default handler for folders it is useful
        "nautilus-folder-handler.desktop",
        # we think that these are useful to show
        "eog.desktop",
        "evince.desktop",
        "gnome-about.desktop",
        "gstreamer-properties.desktop",
        "notification-properties.desktop",
    ])
    blacklist = set([
        "nautilus-home.desktop",
    ])

    result = []
    if DESKTOP_ENVIRONMENT:
        desktop_app_info_set_desktop_env(DESKTOP_ENVIRONMENT)
    isabs = os.path.isabs
    isfile = os.path.isfile
    islink = os.path.islink
    with gtk_lock:
        for item in app_info_get_all():
            id_ = item.get_id()
            if id_ in whitelist or (item.should_show() and id_ not in blacklist):
                name = item.get_name().lower()
                filepath = item.get_executable()
                #print filepath,";",item.get_commandline(),";",item.get_description()
                # Need to check for existence of the file, as sometimes the app does not disappear from the list if not ptoperly uninstalled
                if filepath and filepath.strip() != "":
                    if isabs(filepath):
                        if not (isfile(filepath) or islink(filepath)):
                            continue
                    else:
                        if not find_executable(filepath):
                            continue
                    applications_dict[name] = item
                    s_type = shortcuts.SHORTCUT_TYPE_EXECUTABLE  # get_shortcut_type(filepath)
                    shortcut = shortcuts.Shortcut(name, s_type, filepath.strip(), category=SHORTCUT_CATEGORY)
                    result.append(shortcut)

    #print "\n".join(sorted(str(s) for s in result))
    logging.info("open-command: Loaded %d application shortcuts" % len(result))
    return result


def register_monitor_callback(callback_func):
    dirwatcher.register_monitor_callback(
        callback_func,
        (
            ("/usr/share/applications", False),
            ("/usr/local/share/applications", False),
            (os.path.expanduser("~/.local/share/applications"), False),
        )
    )
