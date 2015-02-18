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

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Imports
import os
import logging
import glob
import subprocess

import gio

from enso.contrib.open import interfaces
from enso.contrib.open import shortcuts
from enso.contrib.open.interfaces import AbstractOpenCommand, ShortcutAlreadyExistsError
from enso.contrib.open.shortcuts import ShortcutsDict
from enso.contrib.open.utils import Timer

from enso.contrib.open.platform.linux import recent
from enso.contrib.open.platform.linux import learned_shortcuts
from enso.contrib.open.platform.linux import applications
from enso.contrib.open.platform.linux import gtk_bookmarks


class OpenCommandImpl( AbstractOpenCommand ):

    def __init__(self, use_categories = True):
        #self.shortcut_dict = None
        self.use_categories = use_categories
        super(OpenCommandImpl, self).__init__()

            
    def _get_learn_as_dir(self):
        return learned_shortcuts.LEARN_AS_DIR

    def _reload_shortcuts(self, shortcuts_dict):
        shortcuts_dict.update_by_category(applications.SHORTCUT_CATEGORY, dict((s.name, s) for s in applications.get_applications()))
        def update_applications():
            shortcuts_dict.update_by_category(applications.SHORTCUT_CATEGORY, dict((s.name, s) for s in applications.get_applications()))
        applications.register_update_callback(update_applications)

        """
        shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        def update_recent_documents():
            shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        recent.register_update_callback(update_recent_documents)
        """
        
        shortcuts_dict.update_by_category(gtk_bookmarks.SHORTCUT_CATEGORY, dict((s.name, s) for s in gtk_bookmarks.get_bookmarks()))
        def update_gtk_bookmarks():
            shortcuts_dict.update_by_category(gtk_bookmarks.SHORTCUT_CATEGORY, dict((s.name, s) for s in gtk_bookmarks.get_bookmarks()))
        gtk_bookmarks.register_update_callback(update_gtk_bookmarks)

        shortcuts_dict.update_by_category(learned_shortcuts.SHORTCUT_CATEGORY, dict((s.name, s) for s in learned_shortcuts.get_learned_shortcuts()))
        def update_learned_shortcuts():
            shortcuts_dict.update_by_category(learned_shortcuts.SHORTCUT_CATEGORY, dict((s.name, s) for s in learned_shortcuts.get_learned_shortcuts()))
        learned_shortcuts.register_update_callback(update_learned_shortcuts)
       

    def _is_application(self, shortcut):
        return shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE

    def _save_shortcut(self, shortcut_name, file):
        shortcut_file_path = os.path.join(self._get_learn_as_dir(), shortcut_name)

        if os.path.isfile(shortcut_file_path):
            raise ShortcutAlreadyExistsError()

        os.symlink(file, shortcut_file_path)

        return shortcuts.Shortcut(
            shortcut_name, self._get_shortcut_type(file), shortcut_file_path)

    def _remove_shortcut(self, shortcut):
        if not os.path.isfile(shortcut.file):
            return
        os.remove(shortcut.file)

    def _get_shortcut_type(self, file):
        raise NotImplementedError()

    def _run_shortcut(self, shortcut):
        if shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE:
            try:
                app = applications.applications_dict.get(shortcut.target, None)
                if app:
                    app.launch(None)
            except Exception, e:
                logging.error(e)
        else:
            try:
                program = "/usr/bin/open"
                params = shortcut.target
                command_run = subprocess.call([program, params])
                if command_run != 0:
                    program = "gnome-open"
                    command_run = subprocess.call([program, params])
            except Exception, e:
                logging.error(e)
                try:
                    os.system('gnome-open "%s"' % shortcut.target)
                except Exception, e:
                    logging.error(e)

    def _open_with_shortcut(self, shortcut, files):
        raise NotImplementedError()


class RecentCommandImpl( OpenCommandImpl ):

    def __init__(self, use_categories = True):
        super(RecentCommandImpl, self).__init__(use_categories)

    def _reload_shortcuts(self, shortcuts_dict):
        shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        def update_recent_documents():
            shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        recent.register_update_callback(update_recent_documents)

    def _get_shortcut_type(self, file):
        raise NotImplementedError()


# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: