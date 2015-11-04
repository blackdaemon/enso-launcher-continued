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

import os
import gio
from gtk.gdk import lock as gtk_lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from enso.contrib.open import shortcuts

SHORTCUT_CATEGORY_DESKTOP = "desktop"
SHORTCUT_CATEGORY_LAUNCHPANEL = "launch-panel"
DESKTOP_DIR = os.path.expanduser("~/Desktop")
LAUNCH_PANEL_DIR = os.path.expanduser("~/.gnome2/panel2.d/default/launchers")


class FileChangedEventHandler( FileSystemEventHandler ):
    
    def __init__(self):
        super(FileChangedEventHandler, self).__init__()
        self.update_callback_func = None
        #self.update_commands_delayed = DelayedExecution(1.0, self.update_commands)

    def on_moved(self, event):
        super(FileChangedEventHandler, self).on_moved(event)
        what = 'directory' if event.is_directory else 'file'
        print "Moved %s: from %s to %s" % (what, event.src_path, event.dest_path)
        self.call_callback(event)
    
    def on_created(self, event):
        super(FileChangedEventHandler, self).on_created(event)
        what = 'directory' if event.is_directory else 'file'
        print "Created %s: %s" % (what, event.src_path)
        self.call_callback(event)
    
    def on_deleted(self, event):
        super(FileChangedEventHandler, self).on_deleted(event)
        what = 'directory' if event.is_directory else 'file'
        print "Deleted %s: %s" % (what, event.src_path)
        self.call_callback(event)
    
    def on_modified(self, event):
        super(FileChangedEventHandler, self).on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        print "Modified %s: %s" % (what, event.src_path)
        self.call_callback(event)

    def call_callback(self, event):
        print "Recently changed learned-shortcuts list was updated"
        if self.update_callback_func:
            try:
                print "Calling update callback func..."
                self.update_callback_func()
            except Exception, e:
                print e
        else:
            print "No calling update callback func was defined, that's fine"


file_changed_event_handler = FileChangedEventHandler()


def get_shortcut_type(filepath):
    return shortcuts.SHORTCUT_TYPE_EXECUTABLE


def lookup_exec_path(exename):
    "Return path for @exename in $PATH or None"
    PATH = os.environ.get("PATH") or os.defpath
    for execdir in PATH.split(os.pathsep):
        exepath = os.path.join(execdir, exename)
        if os.access(exepath, os.R_OK|os.X_OK) and os.path.isfile(exepath):
            return exepath


def _get_runnable_shortcuts_from_dir(directory, category):
    result = []
    splitext = os.path.splitext
    pathjoin = os.path.join
    get_app_info = gio.unix.desktop_app_info_new_from_filename
    for f in os.listdir(directory):
        if splitext(f)[1] != ".desktop":
            continue
        f = pathjoin(directory, f)
        with gtk_lock:
            try:
                #print f
                ds = get_app_info(f)
            except RuntimeError as e:
                print f, e
                continue
            #cmdline = ds.get_commandline()
            name = ds.get_name().lower()
            t = get_shortcut_type(ds.get_executable())
        shortcut = shortcuts.Shortcut(name, t, f, f, category)
        result.append(shortcut)
    return result


def get_desktop_shortcuts():
    return _get_runnable_shortcuts_from_dir(DESKTOP_DIR, SHORTCUT_CATEGORY_DESKTOP)

def get_launch_panel_shortcuts():
    return _get_runnable_shortcuts_from_dir(LAUNCH_PANEL_DIR, SHORTCUT_CATEGORY_LAUNCHPANEL)


def register_update_callback(callback_func):
    assert callback_func is None or callable(callback_func), "callback_func must be callable entity or None"
    file_changed_event_handler.update_callback_func = callback_func


# Set up the directory watcher for shortcuts directory 
dir_monitor = Observer()
dir_monitor.schedule(file_changed_event_handler, DESKTOP_DIR, recursive=False)
dir_monitor.schedule(file_changed_event_handler, LAUNCH_PANEL_DIR, recursive=False)
dir_monitor.start()
