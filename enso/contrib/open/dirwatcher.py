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
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


_dir_monitor = None
_dir_specs = {}


class _FileChangedEventHandler(FileSystemEventHandler):

    def __init__(self):
        super(_FileChangedEventHandler, self).__init__()
        self.update_callback_func = None
        self.update_callback_args = None
        self.update_callback_kwargs = None
        self.events = []
        #self.update_commands_delayed = DelayedExecution(1.0, self.update_commands)

    def on_moved(self, event):
        super(_FileChangedEventHandler, self).on_moved(event)
        what = 'directory' if event.is_directory else 'file'
        print "Moved %s: from %s to %s" % (what, event.src_path, event.dest_path)
        self.call_callback(event.dest_path)

    def on_created(self, event):
        super(_FileChangedEventHandler, self).on_created(event)
        what = 'directory' if event.is_directory else 'file'
        print "Created %s: %s" % (what, event.src_path)
        self.call_callback(event.src_path)

    def on_deleted(self, event):
        super(_FileChangedEventHandler, self).on_deleted(event)
        what = 'directory' if event.is_directory else 'file'
        print "Deleted %s: %s" % (what, event.src_path)
        self.call_callback(event.src_path)

    def on_modified(self, event):
        # TODO: Implement also filtering?
        super(_FileChangedEventHandler, self).on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        print "Modified %s: %s" % (what, event.src_path)
        self.events.append((event, time.time()))
        if len(self.events) % 10 == 0:
            evts = self.events[:]
            delays = [abs(e[1] - evts[i+1][1]) for i, e in enumerate(evts) if i < len(evts)-1]
            maximum = max(delays)
            if maximum > 30:
                maximum = 0
                del self.events[:] 
            print "Delays between events: %ds-%ds" % (min(delays), maximum)
        self.call_callback(event.src_path)

    def call_callback(self, directory):
        if self.update_callback_func:
            try:
                assert logging.debug("Calling update callback func...") or True
                self.update_callback_func(directory, *self.update_callback_args, **self.update_callback_kwargs)
            except Exception as e:
                logging.error("Error calling watchdog-update-callback function: %s", e)
        else:
            assert logging.debug("No calling update callback func was defined, that's fine") or True


def register_monitor_callback(callback_func, directories, *args, **kwargs):
    """
    """
    assert callback_func is None or callable(callback_func), "callback_func must be callable entity or None"
    assert directories
    assert hash(directories)

    global _dir_monitor, _dir_specs

    _id = hash(directories)
    handler = _dir_specs.setdefault(_id, _FileChangedEventHandler())
    if (handler.update_callback_func != callback_func or
        directories != handler.directories):
        handler.update_callback_func = directories
        handler.update_callback_func = callback_func
        handler.update_callback_args = args
        handler.update_callback_kwargs = kwargs

    if _dir_monitor is None:
        # Set up the directory watcher for shortcuts directory
        _dir_monitor = Observer()
        _dir_monitor.start()

    for directory, recursive in directories:
        try:
            _dir_monitor.schedule(handler, directory, recursive=recursive)
        except Exception as e:
            logging.error("Error scheduling directory monitor for %s: %s", directory, str(e))
