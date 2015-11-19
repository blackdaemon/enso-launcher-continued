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

import gio
from gtk import recent_manager_get_default

from enso.contrib.open import shortcuts
from enso.platform.linux.weaklib import gobject_connect_weakly

SHORTCUT_CATEGORY = "recent"


recent_manager = recent_manager_get_default()

class RecentChangedSignalReceiver( object ):
    def __init__(self):
        self.update_callback_func = None
        
    def recent_changed(self, *args):
        print "Recently changed documents list was updated"
        if self.update_callback_func:
            try:
                print "Calling update callback func..."
                self.update_callback_func()
            except Exception, e:
                print e
        else:
            print "No calling update callback func was defined, that's fine"

recent_changed_signal_receiver = RecentChangedSignalReceiver()

        
def get_recent_documents(max_days=None, for_application_named=None):
    items = recent_manager.get_items()
    item_leaves = []
    for item in items:
        if for_application_named and for_application_named.lower() not in set(a.lower() for a in item.get_applications()):
            continue
        day_age = item.get_age()
        if max_days >= 0 and day_age > max_days:
            continue
        if not item.exists():
            continue
        uri = item.get_uri()
        name = item.get_short_name()
        if item.is_local():
            leaf = gio.File(uri).get_path()
        else:
            leaf = uri
        #print leaf, item.get_mime_type()
        type = shortcuts.SHORTCUT_TYPE_DOCUMENT
        shortcut = shortcuts.Shortcut(name, type, leaf, category=SHORTCUT_CATEGORY)
        item_leaves.append(shortcut)
    return item_leaves

def register_update_callback(callback_func):
    assert callback_func is None or callable(callback_func), "callback_func must be callable entity or None"
    recent_changed_signal_receiver.update_callback_func = callback_func
    
gobject_connect_weakly(recent_manager, "changed", recent_changed_signal_receiver.recent_changed)
