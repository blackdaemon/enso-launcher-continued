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

from __future__ import with_statement
import ctypes
import logging
import os
import sqlite3
import unicodedata
from ctypes import wintypes
from itertools import chain
from xml.sax.saxutils import escape as xml_escape

import pythoncom
import win32api
import win32con
import win32file
import winerror
from win32com.shell import shell, shellcon

import enso.providers
from enso.contrib.open import interfaces
from enso.contrib.open.interfaces import (
    AbstractOpenCommand,
    ShortcutAlreadyExistsError,
)
from enso.contrib.open.platform.win32 import (
    filesystem,
    registry,
    utils,
    win_shortcuts,
)
from enso.contrib.open.shortcuts import *  # IGNORE:W0401
from enso.contrib.open.utils import Timer
from enso.contrib.scriptotron.ensoapi import EnsoApi
from enso.utils.decorators import suppress


try:
    import regex as re
except ImportError:
    import re

if utils.platform_windows_vista() or utils.platform_windows_7():
    from enso.contrib.open.platform.win32 import control_panel_vista_win7 as control_panel
else:
    from enso.contrib.open.platform.win32 import control_panel_2000_xp as control_panel

logger = logging.getLogger(__name__)

EXECUTABLE_EXTS = ['.exe', '.com', '.cmd', '.bat', '.py', '.pyw']
EXECUTABLE_EXTS.extend(
    [ext for ext
        in os.environ['PATHEXT'].lower().split(os.pathsep)
        if ext not in EXECUTABLE_EXTS])
EXECUTABLE_EXTS = set(EXECUTABLE_EXTS)

ensoapi = EnsoApi()

directory_watcher = None

def get_special_folder_path(folder_id):
    return unicode(shell.SHGetFolderPath(0, folder_id, 0, 0))
    return unicode(
        shell.SHGetPathFromIDList(
            shell.SHGetFolderLocation(0, folder_id)
        ) #.decode("iso-8859-2")
    )

LEARN_AS_DIR = os.path.join(
    get_special_folder_path(shellcon.CSIDL_PERSONAL),
    u"Enso's Learn As Open Commands")

# Check if Learn-as dir exist and create it if not
if (not os.path.isdir(LEARN_AS_DIR)):
    os.makedirs(LEARN_AS_DIR)

RECYCLE_BIN_LINK = os.path.join(LEARN_AS_DIR, "recycle bin.lnk")

# Shortcuts in Start-Menu/Quick-Links that are ignored
startmenu_ignored_links = re.compile(
    r"(\buninstall|\bread ?me|\bfaq|\bf\.a\.q|\bhelp|\bcopying$|\bauthors$|\bwebsite$|"
    "\blicense$|\bchangelog$|\brelease ?notes$)",
    re.IGNORECASE)

GAMEEXPLORER_DIR = os.path.join(
            get_special_folder_path(shellcon.CSIDL_LOCAL_APPDATA),
            "Microsoft", "Windows", "GameExplorer")


def load_cached_shortcuts():
    #TODO: Move shortcuts caching to platform independent interface? (AbstractOpenCommandImpl)
    rows = []
    conn = None
    #cursor = None
    try:
        conn = sqlite3.connect(
            os.path.expanduser("~/enso-open-shortcuts.db"),
            timeout = 0.5)
        logging.info("connected " + repr(conn))
        rows = conn.execute(
            "select name, type, target, shortcut_filename from shortcut"
            ).fetchall()
    except Exception, e:
        logging.error(e)
        raise
    finally:
        #if cursor:
        #    cursor.close()
        #    del cursor
        if conn:
            conn.close()
            #del conn

    if rows:
        return ShortcutsDict(((r[0], Shortcut(r[0], r[1], r[2], r[3])) for r in rows))


def save_shortcuts_cache(shortcuts_dict):
    #TODO: Move shortcuts caching to platform independent interface? (AbstractOpenCommandImpl)
    conn = None
    #cursor = None
    try:
        conn = sqlite3.connect(
            #":memory:",
            os.path.expanduser("~/enso-open-shortcuts.db"),
            isolation_level = 'DEFERRED',
            timeout = 0.5)
        logging.info("connected " + repr(conn))
        try:
            conn.execute("delete from shortcut")
        except sqlite3.OperationalError, e:
            conn.execute(
                "create table shortcut(name text, type text, target text, shortcut_filename text, flags integer)")
        conn.executemany(
            "insert into shortcut (name, type, target, shortcut_filename, flags) values (?, ?, ?, ?, ?)",
                ((s.name, s.type, s.target, s.shortcut_filename, s.flags)
                for s in shortcuts_dict.itervalues())
            )
    except Exception, e:
        logging.error(e)
        if conn:
            conn.rollback()
    else:
        conn.commit()
    finally:
        #if cursor:
        #    cursor.close()
        #    del cursor
        if conn:
            conn.close()
            #del conn



# TODO: Refactor get_file_type, it's too complex, solves too many cases, ...
# ...is unreliable, split url/file detection: url should be detected outside of this
def get_file_type(target):
    # Stripping \0 is needed for the text copied from Lotus Notes
    target = target.strip(" \t\r\n\0")
    # Before deciding whether to examine given text using URL regular expressions
    # do some simple checks for the probability that the text represents a
    # file path
    
    # FIXME: the file existence check must be also based on PATH search,
    # probably use "is_runnable" instead
    if not os.path.exists(target) and interfaces.is_valid_url(target):
            return SHORTCUT_TYPE_URL

    file_path = target
    file_name, file_ext = os.path.splitext(file_path)
    file_ext = file_ext.lower()

    if file_ext == ".url":
        return SHORTCUT_TYPE_URL

    if file_ext == ".lnk":
        sl = win_shortcuts.PyShellLink(file_path)
        file_path = sl.get_target()
        if file_path and os.path.exists(file_path):
            file_name, file_ext = os.path.splitext(file_path)
            file_ext = file_ext.lower()
        elif target.startswith(("http://", "https://", "hcp://")):
            return SHORTCUT_TYPE_URL
        else:
            return SHORTCUT_TYPE_DOCUMENT

    if os.path.isdir(file_path):
        return SHORTCUT_TYPE_FOLDER

    if (os.path.isfile(file_path) and ext in EXECUTABLE_EXTS):
        return SHORTCUT_TYPE_EXECUTABLE

    #TODO: Finish this
    #if ext in (".", ""):
    #    for ext in EXECUTABLE_EXTS:
    #        if os.path.isfile(os.path.extsep)
    return SHORTCUT_TYPE_DOCUMENT


def dirwalk(top, max_depth=None):
    """ Custom directory walking generator. It introduces max_depth parameter.
    max_depth=0 means traversing only specified directory
    max_dept=None means unlimited depth
    This is adapted version from os.py in standard libraries.
    Top-down walking logic has been removed as it is not useful here.
    """
    from os import listdir
    # Speed optimization
    from os.path import join, isdir, islink

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        names = listdir(top)
    except:
        return

    dirs, nondirs = [], []
    for name in names:
        if isdir(join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    yield top, dirs, nondirs

    if max_depth is None or max_depth > 0:
        depth = None if max_depth is None else max_depth-1
        for name in dirs:
            path = join(top, name)
            if not islink(path):
                for x in dirwalk(path, depth):
                    yield x


def get_shortcuts_from_dir(directory, re_ignored=None, max_depth=None, collect_dirs=False, category=None):
    assert max_depth is None or max_depth >= 0

    if not os.path.isdir(directory):
        return

    # Speed optimization
    splitext = os.path.splitext
    pathjoin = os.path.join
    isfile = os.path.isfile
    isdir = os.path.isdir
    basename = os.path.basename

    """
    with Timer("os.listdir %s" % directory):
        for filename in os.listdir(directory):
            pass
    with Timer("os.walk %s" % directory):
    for dirpath, _, filenames in os.walk(directory):
            pass
    with Timer("os.listdir %s" % directory):
        for filename in os.listdir(directory):
            pass
        """

    for shortcut_dirpath, shortcut_directories, shortcut_filenames in dirwalk(directory, max_depth):
        if collect_dirs:
            for shortcut_directory in shortcut_directories:
                if re_ignored and re_ignored.search(shortcut_directory):
                    continue
                target = pathjoin(shortcut_dirpath, shortcut_directory)
                try:
                    #old_name = shortcut_name
                    shortcut_name = unicodedata.normalize(
                        'NFKD', unicode(shortcut_directory)).encode('ascii', 'ignore')
                    #if shortcut_name != old_name:
                    #    print "NORMALIZED:", old_name, shortcut_name
                except Exception, e: #IGNORE:W0703
                    logging.error(u"%s; directory:%s", e, target) #dirpath)
                else:
                    try:
                        yield Shortcut(
                            shortcut_name.lower(), SHORTCUT_TYPE_FOLDER, target, target)
                    except AssertionError, e:
                        logging.error(e)

        for shortcut_filename in shortcut_filenames:
            target = None

            shortcut_filepath = pathjoin(shortcut_dirpath, shortcut_filename)

            if re_ignored and re_ignored.search(shortcut_filepath):
                continue

            shortcut_name, shortcut_ext = splitext(shortcut_filename)
            shortcut_ext = shortcut_ext.lower()

            if filesystem.is_symlink(shortcut_filepath):
                try:
                    shortcut_filepath = filesystem.trace_symlink_target(
                        shortcut_filepath)
                    shortcut_filename = basename(shortcut_filepath)
                except WindowsError as e:
                    logging.error(
                        "Unresolvable symbolic link; target file does not exists: \"%s\"" % shortcut_filepath)
                    continue

            # rdp is remote-desktop shortcut
            #if not shortcut_ext in (".lnk", ".url", ".rdp"):
            #    continue
            #print shortcut_name, shortcut_ext
            shortcut_type = SHORTCUT_TYPE_DOCUMENT

            if shortcut_ext == ".lnk":
                shell_link = win_shortcuts.PyShellLink(shortcut_filepath)
                #FIXME: Maybe extracting of path could be done lazily in the Shortcut object itself
                #bottom-line here is: we need to extract it to get the type
                #type could be also get lazily, but the advantage is then void
                target = shell_link.get_target()
                if target:
                    #print type(target)
                    if isinstance(target, str):
                        target = target.encode("string_escape")
                    else:
                        print target.replace("\\", "\\\\")
                    if isdir(target):
                        shortcut_type = SHORTCUT_TYPE_FOLDER
                    elif isfile(target):
                        target_ext = splitext(target)[1].lower()
                        if target_ext in EXECUTABLE_EXTS | set([".ahk"]):
                            shortcut_type = SHORTCUT_TYPE_EXECUTABLE
                        elif target_ext == ".url":
                            shortcut_type = SHORTCUT_TYPE_URL
                        else:
                            shortcut_type = SHORTCUT_TYPE_DOCUMENT
                        #shortcut_type = get_file_type(target)
                    elif target.startswith(("http://", "https://", "hcp://")):
                        shortcut_type = SHORTCUT_TYPE_URL
                else:
                    #shortcut_type = SHORTCUT_TYPE_DOCUMENT
                    continue
            elif shortcut_ext == ".url":
                url_link = win_shortcuts.PyInternetShortcut(shortcut_filepath)
                target = url_link.get_target()
                shortcut_type = SHORTCUT_TYPE_URL
            elif shortcut_ext == ".rdp":
                target = shortcut_filepath
                shortcut_type = SHORTCUT_TYPE_DOCUMENT
            elif shortcut_ext == ".vmcx":
                target = shortcut_filepath
                shortcut_type = SHORTCUT_TYPE_DOCUMENT
            else:
                continue

            #shortcuts.append((shortcut_type, shortcut_name.lower(), os.path.join(dirpath, filename)))
            shortcut_path = shortcut_filepath
            try:
                #old_name = shortcut_name
                shortcut_name = unicodedata.normalize('NFKD', unicode(shortcut_name)).encode(
                    'ascii', 'ignore').lower()
                if category:
                    if callable(category):
                        shortcut_name = "%s (%s)" % (
                            shortcut_name, category(shortcut_name, shortcut_type, target, shortcut_path))
                    else:
                        shortcut_name = "%s (%s)" % (shortcut_name, category)
                #if shortcut_name != old_name:
                #    print "NORMALIZED:", old_name, shortcut_name
            except Exception, e: #IGNORE:W0703
                logging.error(
                    u"%s; shortcut_name:%s; dirpath:%s", e, shortcut_name, shortcut_path)
            else:
                try:
                    yield Shortcut(
                        shortcut_name, shortcut_type, target, shortcut_path)
                except AssertionError, e:
                    logging.error(e)
                #really_processed += 1
    #print "Total files to process:", total_files_processed, ", really processed:", really_processed
    #return shortcuts


def get_special_folders(use_categories=True):
    #TODO:Use sublasses here (something like SpecialShortcut, or FixedShortcut)
    with suppress():
        yield Shortcut(
                "desktop folder",
                SHORTCUT_TYPE_FOLDER,
                get_special_folder_path(shellcon.CSIDL_DESKTOPDIRECTORY)
            )

    with suppress():
        yield Shortcut(
                "my documents folder",
                SHORTCUT_TYPE_FOLDER,
                get_special_folder_path(shellcon.CSIDL_PERSONAL)
            )

    with suppress():
        yield Shortcut(
                "my pictures folder",
                SHORTCUT_TYPE_FOLDER,
                get_special_folder_path(shellcon.CSIDL_MYPICTURES)
            )

    with suppress():
        yield Shortcut(
                "my videos folder",
                SHORTCUT_TYPE_FOLDER,
                get_special_folder_path(shellcon.CSIDL_MYVIDEO)
            )

    with suppress():
        yield Shortcut(
                "my music folder",
                SHORTCUT_TYPE_FOLDER,
                get_special_folder_path(shellcon.CSIDL_MYMUSIC)
            )

    if not os.path.isfile(RECYCLE_BIN_LINK):
        recycle_shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        recycle_shortcut.SetPath("")
        recycle_shortcut.SetWorkingDirectory("")
        recycle_shortcut.SetIDList(
            ['\x1f\x00@\xf0_d\x81P\x1b\x10\x9f\x08\x00\xaa\x00/\x95N'])
        recycle_shortcut.QueryInterface( pythoncom.IID_IPersistFile ).Save(
            RECYCLE_BIN_LINK, 0 )
    yield Shortcut(
            "recycle bin",
            SHORTCUT_TYPE_FOLDER,
            RECYCLE_BIN_LINK
            )


def get_control_panel_applets(use_categories=True):
    return control_panel.get_control_panel_applets(use_categories)


def get_gameexplorer_entries(use_categories=True):
    """ Generator for enumerating the list of games in the GameExplorer
    of Windows Vista/7.
    Should yield 0 results for Windows XP.
    """
    # Enumerate first from registry, as the .lnk shortcuts do not have
    # meaningful titles
    gameux_key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameUX"
    try:
        # Ending with -1003 is the correct key (at least experimentation shows)
        gamelist_key = registry.walk_keys(
            win32con.HKEY_LOCAL_MACHINE,
            gameux_key,
            r"-1003$").next()
    except:
        # Nothing here (No games installed, or not Windows Vista/7)
        return

    # Go through games records
    for key in registry.walk_keys(registry.HKEY_LOCAL_MACHINE,
        "%s\\%s" % (gameux_key, gamelist_key),
        r"^{.*}$"):
        game_key = "%s\\%s\\%s" % (gameux_key, gamelist_key, key)

        try:
            target = registry.get_value(
                registry.HKEY_LOCAL_MACHINE, game_key, "AppExePath", True)[1]
            title = registry.get_value(
                registry.HKEY_LOCAL_MACHINE, game_key, "Title", True)[1]
        except:
            continue

        # Obtain the game .lnk shortcut from known directory
        game_dir = os.path.join(GAMEEXPLORER_DIR, key, "PlayTasks", "0")
        links = os.listdir(game_dir)
        shortcut_filename = None
        if links:
            for link in links:
                if os.path.basename(link).lower() == "play.lnk":
                    shortcut_filename = os.path.join(game_dir, link)
                    break
            if not shortcut_filename:
                shortcut_filename = os.path.join(game_dir, links[0])

        # Output shortcut
        try:
            title = title.lower()
            yield Shortcut(
                (u"%s (games)" % title) if use_categories else title,
                SHORTCUT_TYPE_VIRTUAL, # Virtual shortcut, so it's undeletable
                target,
                shortcut_filename)
        except AssertionError, e:
            logging.error(e)


def run_shortcut(shortcut):
    try:
        if shortcut.type == SHORTCUT_TYPE_CONTROL_PANEL:
            target = shortcut.target
            # os.startfile does not work with .cpl files,
            # ShellExecute have to be used.
            #FIXME: Replace with regexp, there will be probably more such things
            if target.startswith("mshelp://") or target.startswith("ms-help://"):
                params = None
                work_dir = None
            else:
                target, params = utils.splitcmdline(target)
                target = os.path.normpath(
                    utils.expand_win_path_variables(target))
                params = " ".join(
                    (
                        ('"%s"' % p if ' ' in p else p) for p in
                            (utils.expand_win_path_variables(p) for p in params)
                    )
                )
                # Fix params if there is special Control Panel syntax like:
                # shell32.dll,Control_RunDLL C:\Windows\system32\FlashPlayerCPLApp.cpl,@0
                # where utils.splitcmdline erroneously separate last part before , as:
                # shell32.dll,Control_RunDLL C:\Windows\system32\FlashPlayerCPLApp.cpl ,@0
                if ".cpl" in params:
                    params = re.sub(r"(.*) (,@[0-9]+)$", "\\1\\2", params)
                work_dir = os.path.dirname(target)
            logger.info(
                "Executing '%s%s'", target, " " + params if params else "")
            try:
                _ = win32api.ShellExecute(
                    0,
                    'open',
                    target,
                    params,
                    work_dir if work_dir else None,
                    win32con.SW_SHOWDEFAULT)
            except Exception, e: #IGNORE:W0703
                logger.error(e)
                try:
                    os.startfile(target)
                except WindowsError, e:
                    logger.error("%d: %s", e.errno, e)
        elif shortcut.type == SHORTCUT_TYPE_FOLDER:
            try:
                os.startfile(shortcut.target)
            except WindowsError, e:
                logger.error("%d: %s", e.errno, e)
        else:
            target = os.path.normpath(
                utils.expand_win_path_variables(shortcut.shortcut_filename))
            logger.info("Executing '%s'", target)

            try:
                os.startfile(target)
            except WindowsError, e:
                # TODO: Why am I getting 'bad command' error on Win7 instead of
                # 'not found' error?
                if e.errno in (winerror.ERROR_FILE_NOT_FOUND, winerror.ERROR_BAD_COMMAND):
                    ensoapi.display_message(
                        u"File has not been found. Please adjust the shortcut properties.")
                    logger.error("%d: %s", e.errno, e)
                    try:
                        _ = win32api.ShellExecute(
                            0,
                            'properties',
                            target,
                            None,
                            None,
                            win32con.SW_SHOWDEFAULT)
                    except Exception, e: #IGNORE:W0703
                        logger.error(e)
                elif e.errno == winerror.ERROR_NO_ASSOCIATION:
                    # No application is associated with the specified file.
                    # Open system "Open with..." dialog:
                    try:
                        _ = win32api.ShellExecute(
                            0,
                            'open',
                            "rundll32.exe",
                            "shell32.dll,OpenAs_RunDLL %s" % target,
                            None,
                            win32con.SW_SHOWDEFAULT)
                    except Exception, e: #IGNORE:W0703
                        logger.error(e)
                else:
                    logger.error("%d: %s", e.errno, e)
        return True
    except Exception, e: #IGNORE:W0703
        logger.error(e)
        return False


def open_with_shortcut(shortcut, targets):
    # User did not select any application. Offer system "Open with..." dialog
    if not shortcut:
        for file_name in targets:
            try:
                _ = win32api.ShellExecute(
                    0,
                    'open',
                    "rundll32.exe",
                    "shell32.dll,OpenAs_RunDLL %s" % file_name,
                    None,
                    win32con.SW_SHOWDEFAULT)
            except Exception, e: #IGNORE:W0703
                logger.error(e)
        return

    executable = utils.expand_win_path_variables(shortcut.target)
    workdir = os.path.dirname(executable)
    _, ext = os.path.splitext(executable)
    # If it is a shortcut, extract the executable info
    # for to be able to pass the command-line parameters
    if ext.lower() == ".lnk":
        sl = win_shortcuts.PyShellLink(executable)
        executable = sl.get_target()
        workdir = sl.get_working_dir()
        if not workdir:
            workdir = os.path.dirname(executable)
    #print executable, workdir

    params = u" ".join((u'"%s"' % file_name for file_name in targets))
    #print params

    try:
        win32api.ShellExecute(
            0,
            'open',
            "\"" + executable + "\"",
            params,
            workdir,
            win32con.SW_SHOWDEFAULT)
    except Exception, e: #IGNORE:W0703
        logger.error(e)



class OpenCommandImpl( AbstractOpenCommand ):

    def __init__(self, use_categories = True):
        self.shortcut_dict = None
        self.use_categories = use_categories
        super(OpenCommandImpl, self).__init__()

    def __reload_dir(self, directory, added_files, removed_files, modified_files, re_ignored=None, max_depth=None, collect_dirs=False):
        """ This is called from the directory-watcher service when the contents
        of a monitored directory changes
        """
        with Timer("Updated shortcut list by directory: %s" % directory):
            with suppress():
                # Need to initialize this here because it's called from
                # the directory-watcher in a new thread.
                pythoncom.CoInitialize()

            # Reload directory contents, the list of changes passed from
            # the directory-watcher is not always reliable
            if directory == GAMEEXPLORER_DIR:
                # Special handling for GameExplorer items
                updated_dict = dict(
                    (s.name, s) for s in get_gameexplorer_entries(self.use_categories))
            else:
                # TODO: Add categories reload here
                updated_dict = dict(
                    (s.name, s) for s
                    in get_shortcuts_from_dir(
                        directory, re_ignored, max_depth, collect_dirs))
            # Update shortcuts related to this directory only
            self.shortcut_dict.update_by_dir(directory, updated_dict)

    def _reload_shortcuts(self, shortcuts_dict):
        with suppress():
            # Need to initialize this here because it's called from
            # the directory-watcher in a new thread.
            pythoncom.CoInitialize()

        try:
            shortcuts_dict.update(load_cached_shortcuts())
            logging.info("Loaded shortcuts from cache")
        except Exception as e:
            logging.error(e)

        desktop_dir = get_special_folder_path(shellcon.CSIDL_DESKTOPDIRECTORY)
        common_desktop_dir = get_special_folder_path(
            shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)
        quick_launch_dir = os.path.join(
            get_special_folder_path(shellcon.CSIDL_APPDATA),
            "Microsoft",
            "Internet Explorer",
            "Quick Launch")
        start_menu_dir = get_special_folder_path(shellcon.CSIDL_STARTMENU)
        common_start_menu_dir = get_special_folder_path(
            shellcon.CSIDL_COMMON_STARTMENU)
        virtualmachines_dir = os.path.join(
            get_special_folder_path(shellcon.CSIDL_PROFILE),
            "Virtual Machines")
        recent_documents_dir = get_special_folder_path(shellcon.CSIDL_RECENT)

        """
        shortcuts = chain(
            get_shortcuts_from_dir(desktop_dir),
            get_shortcuts_from_dir(quick_launch_dir, startmenu_ignored_links),
            get_shortcuts_from_dir(start_menu_dir, startmenu_ignored_links),
            get_shortcuts_from_dir(common_start_menu_dir, startmenu_ignored_links),
            get_gameexplorer_entries(),
            iter(get_control_panel_applets()),
            get_special_folders(),
            get_shortcuts_from_dir(LEARN_AS_DIR)
        )
        """
        shortcuts = []
        import cProfile
        cProfile.runctx(
            'list(get_shortcuts_from_dir(desktop_dir))', globals(), locals())
        with Timer("Loaded common-desktop shortcuts"):
            shortcuts.extend(get_shortcuts_from_dir(common_desktop_dir,
                max_depth=0, collect_dirs=True
                #,category="desktop" if self.use_categories else None
                ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    common_desktop_dir,
                    self.__reload_dir,
                    (None, 0, True))
        with Timer("Loaded user-desktop shortcuts"):
            shortcuts.extend(get_shortcuts_from_dir(desktop_dir,
                max_depth=0, collect_dirs=True
                #,category="desktop" if self.use_categories else None
                ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    desktop_dir,
                    self.__reload_dir,
                    (None, 0, True))
        with Timer("Loaded quick-launch shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(quick_launch_dir, startmenu_ignored_links,
                    max_depth=0, collect_dirs=True
                    #,category="quicklaunch" if self.use_categories else None
                    ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    quick_launch_dir,
                    self.__reload_dir,
                    (startmenu_ignored_links, 0, True))

        pathsplit = os.path.split
        _, start_menu_name = pathsplit(start_menu_dir)
        _, common_start_menu_name = pathsplit(common_start_menu_dir)
        def get_startmenu_category(name, type, target, filename):
            # Get the last sub-menu name
            _, category = pathsplit(pathsplit(filename)[0])
            # We are on the top of the start-menu
            if category in (start_menu_name, common_start_menu_name):
                return "startmenu"
            # We are in some of the sub-menus, return the sub-menu name
            category = unicodedata.normalize('NFKD', unicode(category)
                ).encode('ascii', 'ignore').lower()
            return "startmenu %s" % category

        with Timer("Loaded user-start-menu shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(start_menu_dir, startmenu_ignored_links,
                    category=get_startmenu_category if self.use_categories else None))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    start_menu_dir,
                    self.__reload_dir,
                    (startmenu_ignored_links,))
        with Timer("Loaded common-start-menu shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(common_start_menu_dir,
                    startmenu_ignored_links,
                    category=get_startmenu_category if self.use_categories else None))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    common_start_menu_dir,
                    self.__reload_dir,
                    (startmenu_ignored_links,))
        with Timer("Loaded Virtual PC machines"):
            shortcuts.extend(
                get_shortcuts_from_dir(virtualmachines_dir,
                    category="virtual machine" if self.use_categories else None))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    virtualmachines_dir,
                    self.__reload_dir)
        with Timer("Loaded control-panel applets"):
            cps = get_control_panel_applets(self.use_categories)
            shortcuts.extend(cps)
        with Timer("Loaded special folders shortcuts"):
            shortcuts.extend(get_special_folders(self.use_categories))
        if os.path.isdir(GAMEEXPLORER_DIR):
            with Timer("Loaded gameexplorer entries"):
                shortcuts.extend(get_gameexplorer_entries(self.use_categories))
                directory_watcher.manager.register_handler(
                    GAMEEXPLORER_DIR,
                    self.__reload_dir)
        with Timer("Loaded Enso learn-as shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(LEARN_AS_DIR,
                    max_depth=0
                    #,category="learned" if self.use_categories else None
                    ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    LEARN_AS_DIR,
                    self.__reload_dir,
                    (None, 0))

        """
        with Timer("Loaded recent documents shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(recent_documents_dir,
                    max_depth=0
                    ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    recent_documents_dir,
                    self.__reload_dir,
                    (None, 0))
        """

        shortcuts_dict.update(ShortcutsDict(((s.name, s) for s in shortcuts)))

        try:
            save_shortcuts_cache(shortcuts_dict)
            logging.info("Updated shortcuts cache")
        except Exception, e:
            logging.error(e)

    def _is_application(self, shortcut):
        return shortcut.type == SHORTCUT_TYPE_EXECUTABLE

    def _is_runnable(self, shortcut):
        raise NotImplementedError()
        
    def _save_shortcut(self, name, target):
        # Shortcut actual file goes to "Enso Learn As" directory. This is typically
        # different for each platform.
        shortcut_file_path = os.path.join(self._get_learn_as_dir(), name)

        if self._is_url(target):
            shortcut_file_path = shortcut_file_path + ".url"
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()
            s = win_shortcuts.PyInternetShortcut()
            s.set_url(target)
            s.save(shortcut_file_path)
        else:
            shortcut_file_path = shortcut_file_path + ".lnk"
            if os.path.isfile(shortcut_file_path):
                raise ShortcutAlreadyExistsError()

            if os.path.splitext(target)[1] == ".lnk":
                try:
                    win32file.CreateSymbolicLink(
                        shortcut_file_path,
                        target,
                        win32file.SYMBOLIC_LINK_FLAG_DIRECTORY if os.path.isdir(target) else 0 )
                except Exception, e:
                    s = win_shortcuts.PyShellLink()
                    s.set_path(target)
                    s.set_working_dir(os.path.dirname(target))
                    s.set_icon_location(target, 0)
                    s.save(shortcut_file_path)
            else:
                s = win_shortcuts.PyShellLink()
                s.set_path(target)
                s.set_working_dir(os.path.dirname(target))
                s.set_icon_location(target, 0)
                s.save(shortcut_file_path)
        return Shortcut(
            name, self._get_shortcut_type(target), target, shortcut_file_path)

    def _remove_shortcut(self, shortcut):
        assert 0 == shortcut.flags & SHORTCUT_FLAG_CANTUNLEARN
        assert os.path.isfile(shortcut.shortcut_filename)
        os.remove(shortcut.shortcut_filename)

    def _get_shortcut_type(self, target):
        return get_file_type(target)

    def _run_shortcut(self, shortcut):
        return run_shortcut(shortcut)

    def _open_with_shortcut(self, shortcut, targets):
        return open_with_shortcut(shortcut, targets)

    def _get_learn_as_dir(self):
        return LEARN_AS_DIR



class RecentCommandImpl( AbstractOpenCommand ):

    def __init__(self, use_categories = True):
        print "RecentCommandIMpl.__init__()"
        self.shortcut_dict = None
        self.use_categories = use_categories
        super(RecentCommandImpl, self).__init__()

    def _create_category(self, shortcut_name, shortcut_type, target, shortcut_path):
        pass

    def __reload_dir(self, directory, added_files, removed_files, modified_files, re_ignored=None, max_depth=None, collect_dirs=False):
        """ This is called from the directory-watcher service when the contents
        of a monitored directory changes
        """
        with Timer("Updated shortcut list by directory: %s" % directory):
            with suppress():
                # Need to initialize this here because it's Called From
                # The Directory-watcher In A New Thread.
                pythoncom.CoInitialize()
            # Reload directory contents, the list of changes passed from
            # the directory-watcher is not always reliable
            # TODO: Add categories reload here
            updated_dict = dict(
                (s.name, s) for s
                in get_shortcuts_from_dir(
                    directory, re_ignored, max_depth, collect_dirs, category=self._create_category))
            # Update shortcuts related to this directory only
            self.shortcut_dict.update_by_dir(directory, updated_dict)

    def _reload_shortcuts(self):
        with suppress():
            # Need to initialize this here because it's called from
            # the directory-watcher in a new thread.
            pythoncom.CoInitialize()

        recent_documents_dir = get_special_folder_path(shellcon.CSIDL_RECENT)

        """
        shortcuts = chain(
            get_shortcuts_from_dir(desktop_dir),
            get_shortcuts_from_dir(quick_launch_dir, startmenu_ignored_links),
            get_shortcuts_from_dir(start_menu_dir, startmenu_ignored_links),
            get_shortcuts_from_dir(common_start_menu_dir, startmenu_ignored_links),
            get_gameexplorer_entries(),
            iter(get_control_panel_applets()),
            get_special_folders(),
            get_shortcuts_from_dir(LEARN_AS_DIR)
        )
        """
        shortcuts = []
        with Timer("Loaded recent documents shortcuts"):
            shortcuts.extend(
                get_shortcuts_from_dir(recent_documents_dir,
                    max_depth=0,
                    category=self._create_category
                    ))
            if directory_watcher:
                directory_watcher.manager.register_handler(
                    recent_documents_dir,
                    self.__reload_dir,
                    (None, 0))

        self.shortcut_dict = ShortcutsDict(((s.name, s) for s in shortcuts))

        return self.shortcut_dict

    def _is_application(self, shortcut):
        return shortcut.type == SHORTCUT_TYPE_EXECUTABLE

    def _get_shortcut_type(self, target):
        return get_file_type(target)

    def _run_shortcut(self, shortcut):
        return run_shortcut(shortcut)

    def _open_with_shortcut(self, shortcut, targets):
        return open_with_shortcut(shortcut, targets)



# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: