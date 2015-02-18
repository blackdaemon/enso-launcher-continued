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

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from enso.contrib.open import shortcuts
from enso.platform.linux import utils 
from enso.platform.linux.weaklib import gobject_connect_weakly

SHORTCUT_CATEGORY = "gtk-bookmark"
BOOKMARKS_DIR = "~"
BOOKMARKS_FILE = ".gtk-bookmarks"


class FileChangedEventHandler( FileSystemEventHandler ):
    
    def __init__(self):
        super(FileChangedEventHandler, self).__init__()
        self.update_callback_func = None
        #self.update_commands_delayed = DelayedExecution(1.0, self.update_commands)

    def on_moved(self, event):
        super(FileChangedEventHandler, self).on_moved(event)
        #what = 'directory' if event.is_directory else 'file'
        #print "Moved %s: from %s to %s" % (what, event.src_path, event.dest_path)
        bookmarks_filename = os.path.expanduser(os.path.join(BOOKMARKS_DIR, BOOKMARKS_FILE)) 
        if not event.is_directory and event.dest_path == bookmarks_filename:
            self.call_callback(event)
    
    def on_created(self, event):
        super(FileChangedEventHandler, self).on_created(event)
        #what = 'directory' if event.is_directory else 'file'
        #print "Created %s: %s" % (what, event.src_path)
        #self.call_callback(event)
    
    def on_deleted(self, event):
        super(FileChangedEventHandler, self).on_deleted(event)
        #what = 'directory' if event.is_directory else 'file'
        #print "Deleted %s: %s" % (what, event.src_path)
        #self.call_callback(event)
    
    def on_modified(self, event):
        super(FileChangedEventHandler, self).on_modified(event)
        #what = 'directory' if event.is_directory else 'file'
        #print "Modified %s: %s" % (what, event.src_path)

    def call_callback(self, event):
        print "Recently changed applications list was updated"
        if self.update_callback_func:
            try:
                print "Calling update callback func..."
                self.update_callback_func()
            except Exception, e:
                print e
        else:
            print "No calling update callback func was defined, that's fine"


file_changed_event_handler = FileChangedEventHandler()


def get_bookmarks():
    print "Loading gtk-bookmarks"
    basename = os.path.basename
    places = []
    with open(os.path.expanduser(os.path.join(BOOKMARKS_DIR, BOOKMARKS_FILE))) as f:
        for line in f:
            if not line.strip():
                continue
            items = line.strip().split(" ", 1)
            uri = items[0]
            gfile = gio.File(uri)
            if len(items) > 1:
                title = items[1].rstrip()
            else:
                disp = gfile.get_parse_name()
                title = basename(disp)
            locpath = gfile.get_path()
            if locpath:
                shortcut = shortcuts.Shortcut(
                    "%s [places]" % title, shortcuts.SHORTCUT_TYPE_FOLDER, locpath, category=SHORTCUT_CATEGORY)
            else:
                shortcut = shortcuts.Shortcut(
                    "%s [places]" % title, shortcuts.SHORTCUT_TYPE_URL, gfile.get_uri(), category=SHORTCUT_CATEGORY)
            places.append(shortcut)
    return places


def register_update_callback(callback_func):
    assert callback_func is None or callable(callback_func), "callback_func must be callable entity or None"
    file_changed_event_handler.update_callback_func = callback_func


# Set up the directory watcher for shortcuts directory 
dir_monitor = Observer()
dir_monitor.schedule(file_changed_event_handler, os.path.expanduser(BOOKMARKS_DIR))
dir_monitor.start()
