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

# Future imports
from __future__ import division, with_statement

__updated__ = "2017-02-23"

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import glob
import logging
import os
import subprocess

import gio
import gtk
import xdg
from gtk.gdk import lock as gtk_lock

from enso.contrib.open import interfaces, shortcuts
from enso.contrib.open.interfaces import (
    AbstractOpenCommand,
    ShortcutAlreadyExistsError,
)
from enso.contrib.open.platform.linux import (
    applications,
    desktop,
    gtk_bookmarks,
    learned_shortcuts,
)
from enso.contrib.open.platform.linux.desktop_launch import (
    create_desktop_info,
    launch_app_info,
    spawn_app,
)
from enso.contrib.open.platform.linux.utils import get_file_type
from enso.contrib.open.shortcuts import ShortcutsDict
from enso.contrib.open.utils import Timer
from enso.utils.decorators import suppress


# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Imports


# from enso.contrib.open.platform.linux import recent
# from enso.contrib.open.platform.linux.windows import DesktopWindowsDirectory, windows_list

"""
def limit_windows_by_title_fuzzy_search(title, win_list, first_hit=False):
    import re, operator
    if not title or len(title.rstrip()) == 0:
        return win_list
    title = title.lower()
    keywords = re.split(r" |\t|\r|\n|-|:|", title)
    new_list = []
    scores = []
    for window in win_list:
        score = 0
        points_multiplier = 1
        window_title = window.get_name().lower()
        for keyword in keywords:
            keyword = re.sub("[^a-zA-Z0-9]", "", keyword)
            pos = window_title.find(keyword)
            if pos >= 0:
                score += (100 - (pos / (len(window_title) / 100.0))) * points_multiplier
            points_multiplier /= 2
        scores.append((window, score))
    new_list = [window for (window,score) in
        sorted(
            ((window,score) for (window,score) in scores if score > 0),
            key=operator.itemgetter(0),
            reverse=False)
        ]
    print "||| ".join(window.get_name() for window in new_list)
    return new_list
"""


class OpenCommandImpl(AbstractOpenCommand):

    def __init__(self, use_categories=True):
        # self.shortcut_dict = None
        self.use_categories = use_categories
        super(OpenCommandImpl, self).__init__()

    def _get_learn_as_dir(self):
        return learned_shortcuts.LEARN_AS_DIR

    def _reload_shortcuts(self, shortcuts_dict):
        def update_applications():
            shortcuts_dict.update_by_category(
                applications.SHORTCUT_CATEGORY, dict((s.name, s) for s in applications.get_applications()))
        update_applications()

        def update_desktop_shortcuts():
            shortcuts_dict.update_by_category(
                desktop.SHORTCUT_CATEGORY_DESKTOP, dict((s.name, s) for s in desktop.get_desktop_shortcuts()))
        update_desktop_shortcuts()

        def update_launch_panel_shortcuts():
            shortcuts_dict.update_by_category(
                desktop.SHORTCUT_CATEGORY_LAUNCHPANEL, dict((s.name, s) for s in desktop.get_launch_panel_shortcuts()))
        update_launch_panel_shortcuts()

        """
        shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        def update_recent_documents():
            shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        recent.register_update_callback(update_recent_documents)
        """

        def update_gtk_bookmarks():
            shortcuts_dict.update_by_category(
                gtk_bookmarks.SHORTCUT_CATEGORY, dict((s.name, s) for s in gtk_bookmarks.get_bookmarks()))
        update_gtk_bookmarks()

        def update_learned_shortcuts():
            shortcuts_dict.update_by_category(learned_shortcuts.SHORTCUT_CATEGORY, dict(
                (s.name, s) for s in learned_shortcuts.get_learned_shortcuts()))
        update_learned_shortcuts()

        applications.register_update_callback(update_applications)
        desktop.register_update_callback(update_desktop_shortcuts)
        desktop.register_update_callback(update_launch_panel_shortcuts)
        gtk_bookmarks.register_update_callback(update_gtk_bookmarks)
        learned_shortcuts.register_update_callback(update_learned_shortcuts)

    def _is_runnable(self, shortcut):
        return shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE

    def _is_application(self, shortcut):
        return shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE

    def _save_shortcut(self, shortcut_name, text):
        target = text
        file_type = self._get_shortcut_type(target)

        if file_type == shortcuts.SHORTCUT_TYPE_EXECUTABLE:
            shortcut_file_path = os.path.join(
                self._get_learn_as_dir(),
                shortcut_name + (".desktop")
            )
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            dsk = xdg.DesktopEntry.DesktopEntry(shortcut_file_path)
            dsk.set("Version", "1.0")
            dsk.set("Name", shortcut_name)
            dsk.set("Type", "Application")
            dsk.set("Icon", "application-x-executable")
            dsk.set("Exec", target)
            dsk.set("Terminal", "0")
            dsk.set("Path", os.path.abspath(os.path.dirname(target)))
            dsk.write(trusted=True)
            with suppress():
                subprocess.Popen(["gnome-desktop-item-edit", shortcut_file_path])
        elif file_type == shortcuts.SHORTCUT_TYPE_FOLDER:
            shortcut_file_path = os.path.join(
                self._get_learn_as_dir(),
                shortcut_name + (".desktop")
            )
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            dsk = xdg.DesktopEntry.DesktopEntry(shortcut_file_path)
            dsk.set("Version", "1.0")
            dsk.set("Name", shortcut_name)
            dsk.set("Type", "Application")
            dsk.set("Icon", "gtk-directory")
            dsk.set("Exec", "xdg-open \"%s\"" % os.path.abspath(target))
            dsk.set("Terminal", "0")
            dsk.set("Path", os.path.abspath(target))
            file_type = shortcuts.SHORTCUT_TYPE_EXECUTABLE
            dsk.write(trusted=True)
            with suppress():
                subprocess.Popen(["gnome-desktop-item-edit", shortcut_file_path])
        elif file_type == shortcuts.SHORTCUT_TYPE_URL:
            shortcut_file_path = os.path.join(
                self._get_learn_as_dir(),
                shortcut_name + (".desktop")
            )
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            dsk = xdg.DesktopEntry.DesktopEntry(shortcut_file_path)
            dsk.set("Version", "1.0")
            dsk.set("Name", shortcut_name)
            dsk.set("Icon", "applications-internet")
            dsk.set("URL", target)
            dsk.set("Type", "Link")
            dsk.write(trusted=True)
            with suppress():
                subprocess.Popen(["gnome-desktop-item-edit", shortcut_file_path])
        else:
            """
            #FIXME: This is probably not a good idea to create Application type .desktop entry for a document
            shortcut_file_path = os.path.join(
                self._get_learn_as_dir(),
                shortcut_name + (".desktop")
                )
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            dsk = xdg.DesktopEntry.DesktopEntry(shortcut_file_path)
            dsk.set("Version", "1.0")
            dsk.set("Name", shortcut_name)
            dsk.set("Type", "Application")
            dsk.set("Icon", "gtk-directory")
            dsk.set("Exec", "xdg-open \"%s\"" % os.path.abspath(target))
            dsk.set("Terminal", "0")
            dsk.set("Path", os.path.abspath(target))
            file_type = shortcuts.SHORTCUT_TYPE_EXECUTABLE
            dsk.write(trusted=True)
            with suppress():
                subprocess.Popen(["gnome-desktop-item-edit", shortcut_file_path])
            """
            # This would be better, but problem is that on load, it's determined ax executable instead of a document.
            shortcut_file_path = os.path.join(
                self._get_learn_as_dir(),
                shortcut_name
            )
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            os.symlink(target, shortcut_file_path)

        return shortcuts.Shortcut(
            shortcut_name, file_type, shortcut_file_path, shortcut_file_path, category=learned_shortcuts.SHORTCUT_CATEGORY
        )

        """
        os.symlink(file, shortcut_file_path)

        return shortcuts.Shortcut(
            shortcut_name, self._get_shortcut_type(file), shortcut_file_path)
        """

    def _remove_shortcut(self, shortcut):
        if not os.path.isfile(shortcut.shortcut_filename):
            return False
        try:
            os.remove(shortcut.shortcut_filename)
        except Exception as e:
            logging.error(e)
            return False
        else:
            return True

    def _get_shortcut_type(self, text):
        return get_file_type(text)

    def _run_shortcut(self, shortcut):
        if shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE:
            try:
                # Desktop and launch-panel shortcuts should have precedence over applications, so try to
                # get .desktop shortcut first...
                app = None
                if os.path.isfile(shortcut.target) and os.path.splitext(shortcut.target)[1] == ".desktop":
                    # with gtk_lock:
                    app = gio.unix.desktop_app_info_new_from_filename(shortcut.target)
                # ...and then stored application object if .desktop does not exists
                if not app:
                    app = applications.applications_dict.get(shortcut.name, None)
                if app:
                    """
                    # LONGTERM TODO: Finish switching to already open app window by title search(?)
                    try:
                        win_list = windows_list.get_windows_by_app(app)
                        if len(win_list) > 1:
                            win_list = limit_windows_by_title_fuzzy_search(shortcut.name, win_list, True)
                        for window in reversed(win_list):
                            if DesktopWindowsDirectory.raise_window(window.get_xid()):
                                return
                    except Exception as e:
                        print e
                    print shortcut.category
                    """
                    launch_app_info(app, timestamp=gtk.get_current_event_time(), desktop_file=shortcut.target)
                    # app.launch([], gtk.gdk.AppLaunchContext())
            except Exception as e:
                logging.error(e)
        else:
            try:
                _ = subprocess.Popen(["xdg-open", shortcut.target])
                # FIXME: How to figure out that Popen failed?
                if False:
                    # FIXME: subprocess.call is waiting for process to finish, that is not what we want
                    _ = subprocess.Popen(["/usr/bin/open", shortcut.target])
            except Exception, e:
                logging.error(e)
                try:
                    os.system('gnome-open "%s"' % shortcut.target)
                except Exception, e:
                    logging.error(e)

    def _open_with_shortcut(self, shortcut, files):
        assert shortcut.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE

        try:
            # Desktop and launch-panel shortcuts should have precedence over applications, so try to
            # get .desktop shortcut first...
            app = None
            if os.path.isfile(shortcut.target) and os.path.splitext(shortcut.target)[1] == ".desktop":
                # with gtk_lock:
                app = gio.unix.desktop_app_info_new_from_filename(shortcut.target)
            # ...and then stored application object if .desktop does not exists
            if not app:
                app = applications.applications_dict.get(shortcut.name, None)
            if app:
                # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
                gfiles = [gio.File(filepath) for filepath in files]  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
                launch_app_info(app, gfiles=gfiles)
                # app.launch([], gtk.gdk.AppLaunchContext())
        except Exception, e:
            logging.error(e)


class RecentCommandImpl(OpenCommandImpl):

    def __init__(self, use_categories=True):
        super(RecentCommandImpl, self).__init__(use_categories)

    def _reload_shortcuts(self, shortcuts_dict):
        # TODO: This is big problem with GTK threading, sometimes it lags a lot. Problem is described here:
        # https://bugzilla.gnome.org/show_bug.cgi?id=488507
        # and here:
        # http://stackoverflow.com/questions/9275677/platform-dependent-performance-issues-when-selecting-a-large-number-of-files-wit
        """
        def update_recent_documents():
            shortcuts_dict.update_by_category(recent.SHORTCUT_CATEGORY, dict((s.name, s) for s in recent.get_recent_documents(30)))
        update_recent_documents()
        recent.register_update_callback(update_recent_documents)
        """
        logging.warn(
            "The functionality of listing the recent items in 'open' command has been disabled due to performance issues in Linux GTK recent-files manager.")

    def _get_shortcut_type(self, target):
        raise NotImplementedError()
