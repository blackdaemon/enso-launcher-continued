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

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from __future__ import with_statement

import ctypes
import logging
import os
import sqlite3
import subprocess
import unicodedata

from ctypes import wintypes
from itertools import chain
from xml.sax.saxutils import escape as xml_escape
from os import listdir
from os.path import (
    basename,
    dirname,
    exists,
    expanduser,
    isdir,
    isfile,
    islink,
    join as pathjoin,
    normpath,
    pathsep,
    splitext,
)

import pythoncom
import win32api
import win32con
import win32file
import win32process
import winerror
from win32com.shell import shell, shellcon

import enso.providers
from enso.contrib.open import dirwatcher
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
from enso.utils.decorators import (
    timed_execution,
    timed,
    synchronized,
    debounce
)
from enso.utils import suppress
from enso.contrib.scriptotron.ensoapi import EnsoApi
from enso.contrib.open.platform.win32.decorators import initialize_pythoncom
from enso.system import dirwalk

try:
    import regex as re
except ImportError:
    import re

if utils.platform_windows_vista() or utils.platform_windows_7():
    from enso.contrib.open.platform.win32 import control_panel_vista_win7 as control_panel
else:
    from enso.contrib.open.platform.win32 import control_panel_2000_xp as control_panel

__updated__ = "2019-05-21"

logger = logging.getLogger(__name__)

REPORT_UNRESOLVABLE_TARGETS = False

# Debouncing time of shortcuts refreshes in seconds
SHORTCUTS_REFRESH_DEBOUNCE_TIME = 4

EXECUTABLE_EXTS = ['.exe', '.com', '.cmd', '.bat', '.py', '.pyw']
EXECUTABLE_EXTS.extend(
    [ext for ext
        in os.environ['PATHEXT'].lower().split(pathsep)
        if ext not in EXECUTABLE_EXTS])
EXECUTABLE_EXTS = set(EXECUTABLE_EXTS)

ensoapi = EnsoApi()


def get_special_folder_path(folder_id):
    return unicode(shell.SHGetFolderPath(0, folder_id, 0, 0))
    return unicode(
        shell.SHGetPathFromIDList(
            shell.SHGetFolderLocation(0, folder_id)
        )  # .decode("iso-8859-2")
    )

LEARN_AS_DIR = pathjoin(
    get_special_folder_path(shellcon.CSIDL_PERSONAL),
    u"Enso's Learn As Open Commands")

# Check if Learn-as dir exist and create it if not
if (not isdir(LEARN_AS_DIR)):
    os.makedirs(LEARN_AS_DIR)

RECYCLE_BIN_LINK = pathjoin(LEARN_AS_DIR, "recycle bin.lnk")

# Shortcuts in Start-Menu/Quick-Links that are ignored
startmenu_ignored_links = re.compile(
    r"(\buninstall|\bread ?me|\bfaq|\bf\.a\.q|\bhelp|\bcopying$|\bauthors$|\bwebsite$|"
    "\blicense$|\bchangelog$|\brelease ?notes$)",
    re.IGNORECASE)

GAMEEXPLORER_DIR = pathjoin(
    get_special_folder_path(shellcon.CSIDL_LOCAL_APPDATA),
    "Microsoft", "Windows", "GameExplorer")


def load_cached_shortcuts():
    # TODO: Move shortcuts caching to platform independent interface?
    # (AbstractOpenCommandImpl)
    rows = []
    conn = None
    #cursor = None
    try:
        conn = sqlite3.connect(
            expanduser("~/enso-open-shortcuts.db"),
            timeout=0.5
        )
        logging.info("connected " + repr(conn))
        rows = conn.execute(
            "select name, type, target, shortcut_filename from shortcut"
        ).fetchall()
    except Exception as e:
        logging.error(e)
        raise
    finally:
        # if cursor:
        #    cursor.close()
        #    del cursor
        if conn:
            conn.close()
            #del conn

    if rows:
        return ShortcutsDict(((r[0], Shortcut(r[0], r[1], r[2], r[3])) for r in rows))


def save_shortcuts_cache(shortcuts_dict):
    # TODO: Move shortcuts caching to platform independent interface?
    # (AbstractOpenCommandImpl)
    conn = None
    #cursor = None
    try:
        conn = sqlite3.connect(
            #":memory:",
            expanduser("~/enso-open-shortcuts.db"),
            isolation_level='DEFERRED',
            timeout=0.5
        )
        logging.info("connected " + repr(conn))
        try:
            conn.execute("delete from shortcut")
        except sqlite3.OperationalError as e:
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
        # if cursor:
        #    cursor.close()
        #    del cursor
        if conn:
            conn.close()
            #del conn


def safe_isdir(text):
    """ Ignore type error for badly encoded strings
    If TypeError is thrown, it returns False
    """
    try:
        return isdir(text)
    except TypeError:
        return False


def safe_isfile(text):
    """ Ignore type error for badly encoded strings
    If TypeError is thrown, it returns False
    """
    try:
        return isfile(text)
    except TypeError:
        return False


def get_file_type(target):
    # TODO: Refactor get_file_type, it's too complex, solves too many cases, ...
    # ...is unreliable, split url/file detection: url should be detected outside of this

    # Stripping \0 is needed for the text copied from Lotus Notes
    target = target.strip(" \t\r\n\0")
    # Before deciding whether to examine given text using URL regular expressions
    # do some simple checks for the probability that the text represents a
    # file path

    # FIXME: the file existence check must be also based on PATH search,
    # probably use "is_runnable" instead
    if not exists(target) and interfaces.is_valid_url(target):
        return SHORTCUT_TYPE_URL

    file_path = target
    file_name, file_ext = splitext(file_path)
    file_ext = file_ext.lower()

    if file_ext == ".url":
        return SHORTCUT_TYPE_URL

    if file_ext == ".lnk":
        sl = win_shortcuts.PyShellLink(file_path)
        file_path = sl.get_target()
        if file_path and exists(file_path):
            file_name, file_ext = splitext(file_path)
            file_ext = file_ext.lower()
        elif target.startswith(("http://", "https://", "hcp://")):
            return SHORTCUT_TYPE_URL
        else:
            return SHORTCUT_TYPE_DOCUMENT

    if isdir(file_path):
        return SHORTCUT_TYPE_FOLDER

    if (isfile(file_path) and ext in EXECUTABLE_EXTS):
        return SHORTCUT_TYPE_EXECUTABLE

    # TODO: Finish this
    # if ext in (".", ""):
    #    for ext in EXECUTABLE_EXTS:
    #        if os.path.isfile(os.path.extsep)
    return SHORTCUT_TYPE_DOCUMENT


<<<<<<< HEAD
=======
def dirwalk(top, max_depth=None):
    """ Custom directory walking generator. It introduces max_depth parameter.
    max_depth=0 means traversing only specified directory
    max_dept=None means unlimited depth
    This is adapted version from os.py in standard libraries.
    Top-down walking logic has been removed as it is not useful here.
    """

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
    _isdir = isdir
    _pathjoin = pathjoin
    _islink = islink

    for name in names:
        if _isdir(_pathjoin(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    yield top, dirs, nondirs

    if max_depth is None or max_depth > 0:
        depth = None if max_depth is None else max_depth - 1
        for name in dirs:
            path = _pathjoin(top, name)
            if not _islink(path):
                for x in dirwalk(path, depth):
                    yield x


>>>>>>> branch 'master' of https://github.com/blackdaemon/enso-launcher-continued.git
def get_shortcut_type_and_target(shortcut_filepath, shortcut_ext):
    """ Determine the shortcut type and its target (real file it points to).
    If it can't determine the type, it returns None, None.
    """
    shortcut_type, target = None, None

    if shortcut_ext == ".lnk":
        shell_link = win_shortcuts.PyShellLink(shortcut_filepath)
        # FIXME: Maybe extracting of path could be done lazily in the Shortcut object itself
        # bottom-line here is: we need to extract it to get the type
        # type could be also get lazily, but the advantage is then void
        target = shell_link.get_target()
        if target:
        # print type(target)
            if isinstance(target, str):
                target = target.encode("string_escape") #else:
            #    print target.replace("\\", "\\\\")
            if safe_isdir(target):
                shortcut_type = SHORTCUT_TYPE_FOLDER
            elif safe_isfile(target):
                target_ext = splitext(target)[1].lower()
                if target_ext in EXECUTABLE_EXTS | set([".ahk"]):
                    shortcut_type = SHORTCUT_TYPE_EXECUTABLE
                elif target_ext == ".url":
                    shortcut_type = SHORTCUT_TYPE_URL
                else:
                    shortcut_type = SHORTCUT_TYPE_DOCUMENT #shortcut_type = get_file_type(target)
            elif target.startswith(("http://", "https://", "hcp://")):
                shortcut_type = SHORTCUT_TYPE_URL
        else:
            target = shortcut_filepath
            shortcut_type = SHORTCUT_TYPE_DOCUMENT
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

    return shortcut_type, target


def get_shortcuts_from_dir(directory, re_ignored=None, max_depth=None, collect_dirs=False, category=None, flags=0):
    assert max_depth is None or max_depth >= 0

    if not isdir(directory):
        return

    """
    with timed_execution("listdir %s" % directory):
        for filename in listdir(directory):
            pass
    with timed_execution("os.walk %s" % directory):
    for dirpath, _, filenames in os.walk(directory):
            pass
    with timed_execution("listdir %s" % directory):
        for filename in listdir(directory):
            pass
        """

    _pathjoin = pathjoin
    _splitext = splitext
    _basename = basename
    _is_symlink = filesystem.is_symlink
    _trace_symlink_target = filesystem.trace_symlink_target

<<<<<<< HEAD
    for shortcut_dirpath, shortcut_directories, shortcut_filenames in dirwalk(directory, max_depth=max_depth):
=======
    for shortcut_dirpath, shortcut_directories, shortcut_filenames in dirwalk(directory, max_depth):
>>>>>>> branch 'master' of https://github.com/blackdaemon/enso-launcher-continued.git
        if collect_dirs:
            for shortcut_directory in shortcut_directories:
                if re_ignored and re_ignored.search(shortcut_directory):
                    continue
                target = _pathjoin(shortcut_dirpath, shortcut_directory)
                try:
                    #old_name = shortcut_name
                    shortcut_name = unicodedata.normalize(
                        'NFKD', unicode(shortcut_directory)).encode('ascii', 'ignore')
                    # if shortcut_name != old_name:
                    #    print "NORMALIZED:", old_name, shortcut_name
                except Exception as e:  # IGNORE:W0703
                    logging.error(u"%s; directory:%s", e, target)  # dirpath)
                else:
                    try:
                        yield Shortcut(
                            shortcut_name.lower(),
                            SHORTCUT_TYPE_FOLDER,
                            target,
                            target,
                            category=category,
                            flags=flags
                        )
                    except AssertionError as e:
                        logging.error(e)

        for shortcut_filename in shortcut_filenames:
            shortcut_filepath = _pathjoin(shortcut_dirpath, shortcut_filename)

            if re_ignored and re_ignored.search(shortcut_filepath):
                continue

            shortcut_name, shortcut_ext = _splitext(shortcut_filename)
            shortcut_ext = shortcut_ext.lower()

            try:
                if _is_symlink(shortcut_filepath):
                    try:
                        shortcut_filepath = _trace_symlink_target(
                            shortcut_filepath)
                        shortcut_filename = _basename(shortcut_filepath)
                    except WindowsError as e:
                        if REPORT_UNRESOLVABLE_TARGETS:
                            logging.warning(
                                u"Unresolvable symbolic link; target file does not exists: \"%s\"" % shortcut_filepath)
                        continue
            except Exception as e:
                logging.error(u"Error determining if the target is a symlink: %s", str(e))
                continue

            try:
                shortcut_type, target = get_shortcut_type_and_target(shortcut_filepath, shortcut_ext)
                if shortcut_type is None:
                    continue
            except Exception as e:
                logging.error(u"Error determining the shortcut type: %s", str(e))
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
                # if shortcut_name != old_name:
                #    print "NORMALIZED:", old_name, shortcut_name
            except Exception as e:
                logging.error(
                    u"%s; shortcut_name:%s; dirpath:%s", e, shortcut_name, shortcut_path)
            else:
                try:
                    yield Shortcut(
                        shortcut_name,
                        shortcut_type,
                        target,
                        shortcut_path,
                        category=category,
                        flags=flags
                    )
                except AssertionError as e:
                    logging.error(e)
                #really_processed += 1
    # print "Total files to process:", total_files_processed, ", really processed:", really_processed
    # return shortcuts


def get_special_folders(use_categories=True):
    # TODO: Use subclasses here (something like SpecialShortcut, or
    # FixedShortcut)
    with suppress(Exception):
        yield Shortcut(
            "desktop folder",
            SHORTCUT_TYPE_FOLDER,
            get_special_folder_path(shellcon.CSIDL_DESKTOPDIRECTORY)
        )

    with suppress(Exception):
        yield Shortcut(
            "my documents folder",
            SHORTCUT_TYPE_FOLDER,
            get_special_folder_path(shellcon.CSIDL_PERSONAL)
        )

    with suppress(Exception):
        yield Shortcut(
            "my pictures folder",
            SHORTCUT_TYPE_FOLDER,
            get_special_folder_path(shellcon.CSIDL_MYPICTURES)
        )

    with suppress(Exception):
        yield Shortcut(
            "my videos folder",
            SHORTCUT_TYPE_FOLDER,
            get_special_folder_path(shellcon.CSIDL_MYVIDEO)
        )

    with suppress(Exception):
        yield Shortcut(
            "my music folder",
            SHORTCUT_TYPE_FOLDER,
            get_special_folder_path(shellcon.CSIDL_MYMUSIC)
        )

    if not isfile(RECYCLE_BIN_LINK):
        recycle_shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        recycle_shortcut.SetPath("")
        recycle_shortcut.SetWorkingDirectory("")
        recycle_shortcut.SetIDList(
            ['\x1f\x00@\xf0_d\x81P\x1b\x10\x9f\x08\x00\xaa\x00/\x95N'])
        recycle_shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(
            RECYCLE_BIN_LINK, 0)
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
        game_dir = pathjoin(GAMEEXPLORER_DIR, key, "PlayTasks", "0")
        links = listdir(game_dir)
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
                SHORTCUT_TYPE_VIRTUAL,  # Virtual shortcut, so it's undeletable
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
            # FIXME: Replace with regexp, there will be probably more such
            # things
            if target.startswith("mshelp://") or target.startswith("ms-help://"):
                params = None
                work_dir = None
            else:
                target, params = utils.splitcmdline(target)
                target = normpath(
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
                # shell32.dll,Control_RunDLL
                # C:\Windows\system32\FlashPlayerCPLApp.cpl ,@0
                if ".cpl" in params:
                    params = re.sub(r"(.*) (,@[0-9]+)$", "\\1\\2", params)
                work_dir = dirname(target)
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
            except Exception as e:  # IGNORE:W0703
                logger.error(e)
                try:
                    os.startfile(target)
                except WindowsError as e:
                    logger.error("%d: %s", e.errno, e)
        elif shortcut.type == SHORTCUT_TYPE_FOLDER:
            try:
                os.startfile(shortcut.target)
            except WindowsError as e:
                logger.error("%d: %s", e.errno, e)
        else:
            target = normpath(
                utils.expand_win_path_variables(shortcut.shortcut_filename))
            logger.info("Executing '%s'", target)

            try:
                os.startfile(target)
                """
                subprocess.Popen(
                    target,
                    shell=True,
                    #stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    close_fds=True,
                    creationflags=win32process.DETACHED_PROCESS | win32process.CREATE_NEW_PROCESS_GROUP
                )
                """
            except WindowsError as e:
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
                    except Exception as e:  # IGNORE:W0703
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
                    except Exception as e:  # IGNORE:W0703
                        logger.error(e)
                else:
                    logger.error("%d: %s", e.errno, e)
        return True
    except Exception as e:  # IGNORE:W0703
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
            except Exception as e:  # IGNORE:W0703
                logger.error(e)
        return

    executable = utils.expand_win_path_variables(shortcut.target)
    workdir = dirname(executable)
    _, ext = splitext(executable)
    # If it is a shortcut, extract the executable info
    # for to be able to pass the command-line parameters
    if ext.lower() == ".lnk":
        sl = win_shortcuts.PyShellLink(executable)
        executable = sl.get_target()
        workdir = sl.get_working_dir()
        if not workdir:
            workdir = dirname(executable)
    # print executable, workdir

    params = u" ".join((u'"%s"' % file_name for file_name in targets))
    # print params

    try:
        win32api.ShellExecute(
            0,
            'open',
            "\"" + executable + "\"",
            params,
            workdir,
            win32con.SW_SHOWDEFAULT)
    except Exception as e:  # IGNORE:W0703
        logger.error(e)


class OpenCommandImpl(AbstractOpenCommand):

    def __init__(self, use_categories=True):
        self.shortcut_dict = None
        self.use_categories = use_categories
        super(OpenCommandImpl, self).__init__()

    @initialize_pythoncom
    def _reload_shortcuts(self, shortcuts_dict):
        try:
            shortcuts_dict.update(load_cached_shortcuts())
            logging.info("Loaded shortcuts from cache")
        except Exception as e:
            logging.error(e)

        desktop_dir = get_special_folder_path(shellcon.CSIDL_DESKTOPDIRECTORY)
        common_desktop_dir = get_special_folder_path(
            shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)
        quick_launch_dir = pathjoin(
            get_special_folder_path(shellcon.CSIDL_APPDATA),
            "Microsoft",
            "Internet Explorer",
            "Quick Launch")
        user_pinned_dir = pathjoin(
            get_special_folder_path(shellcon.CSIDL_APPDATA),
            "Microsoft",
            "Internet Explorer",
            "Quick Launch",
            "User Pinned")
        start_menu_dir = get_special_folder_path(shellcon.CSIDL_STARTMENU)
        common_start_menu_dir = get_special_folder_path(
            shellcon.CSIDL_COMMON_STARTMENU)
        virtualmachines_dir = pathjoin(
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

        """
        import cProfile
        cProfile.runctx(
            'list(get_shortcuts_from_dir(desktop_dir))', globals(), locals())
        """

        @timed_execution("Loaded common-desktop shortcuts", mute_on_false=True)
        @synchronized()
        def reload_commom_desktop_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
                not isdir(p) and basename(p) not in ('desktop.ini',)
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            #with timed_execution("Loaded common-desktop shortcuts"):
            shortcuts_dict.update_by_dir(
                common_desktop_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(common_desktop_dir,
                    max_depth=0, collect_dirs=True
                    #,category="desktop" if self.use_categories else None
                ))
            )
            return True

        reload_commom_desktop_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_commom_desktop_shortcuts),
            ((common_desktop_dir, False),),
        )

        @timed_execution("Loaded user-desktop shortcuts", mute_on_false=True)
        @synchronized()
        @initialize_pythoncom
        def reload_user_desktop_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
                not isdir(p) and basename(p) not in ('desktop.ini',)
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            shortcuts_dict.update_by_dir(
                desktop_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    desktop_dir,
                    max_depth=0, collect_dirs=True
                    #,category="desktop" if self.use_categories else None
                ))
            )
            return True

        reload_user_desktop_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_user_desktop_shortcuts),
            ((desktop_dir, False),),
        )

        @timed_execution("Loaded quick-launch shortcuts", mute_on_false=True)
        @synchronized()
        @initialize_pythoncom
        def reload_quick_launch_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
<<<<<<< HEAD
                isfile(p) #and basename(p) not in ('desktop.ini',)
                and splitext(p)[1] == '.lnk'
=======
                not isdir(p) and basename(p) not in ('desktop.ini',)
>>>>>>> branch 'master' of https://github.com/blackdaemon/enso-launcher-continued.git
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            shortcuts_dict.update_by_dir(
                quick_launch_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    quick_launch_dir,
                    startmenu_ignored_links,
                    # max_depth=2 will handle also "User Pinned/[TaskBar|StartMenu]" subdirs
                    max_depth=2, collect_dirs=True
                    #,category="quicklaunch" if self.use_categories else None
                ))
            )
            return True

        reload_quick_launch_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_quick_launch_shortcuts),
            ((quick_launch_dir, True),),
        )

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

        @timed_execution("Loaded user-start-menu shortcuts", mute_on_false=True)
        @synchronized()
        @initialize_pythoncom
        def reload_user_start_menu_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
                not isdir(p) and basename(p) not in ('desktop.ini',)
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            shortcuts_dict.update_by_dir(
                start_menu_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    start_menu_dir,
                    startmenu_ignored_links,
                    category=get_startmenu_category if self.use_categories else None
                ))
            )
            return True

        reload_user_start_menu_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_user_start_menu_shortcuts),
            ((start_menu_dir, False),),
        )

        @timed_execution("Loaded common-start-menu shortcuts", mute_on_false=True)
        @synchronized()
        @initialize_pythoncom
        def reload_common_start_menu_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
                not isdir(p) and basename(p) not in ('desktop.ini',)
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            shortcuts_dict.update_by_dir(
                common_start_menu_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    common_start_menu_dir,
                    startmenu_ignored_links,
                    category=get_startmenu_category if self.use_categories else None
                ))
            )
            return True

        reload_common_start_menu_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_common_start_menu_shortcuts),
            ((common_start_menu_dir, False),),
        )

        @timed_execution("Loaded Virtual PC machines")
        @synchronized()
        @initialize_pythoncom
        def reload_virtual_pc_machines(path=None):
            shortcuts_dict.update_by_dir(
                virtualmachines_dir,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    virtualmachines_dir,
                    category="virtual machine" if self.use_categories else None
                ))
            )
        reload_virtual_pc_machines()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_virtual_pc_machines),
            ((virtualmachines_dir, False),)
        )

        with timed_execution("Loaded control-panel applets"):
            shortcuts_dict.update(
                dict(
                    (s.name, s) for s in
                    get_control_panel_applets(self.use_categories)
                )
            )

        with timed_execution("Loaded special folders shortcuts"):
            shortcuts_dict.update(
                dict(
                    (s.name, s) for s in
                    get_special_folders(self.use_categories)
                )
            )

        if os.path.isdir(GAMEEXPLORER_DIR):
            @timed_execution("Loaded gameexplorer entries")
            @synchronized()
            @initialize_pythoncom
            def reload_gameexplorer_shortcuts(path=None):
                shortcuts_dict.update(
                    dict(
                        (s.name, s) for s in
                        get_gameexplorer_entries(self.use_categories)
                    )
                )
            reload_gameexplorer_shortcuts()
            dirwatcher.register_monitor_callback(
                debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_gameexplorer_shortcuts),
                ((GAMEEXPLORER_DIR, False),)
            )

        @timed_execution("Loaded Enso learn-as shortcuts", mute_on_false=True)
        @synchronized()
        @initialize_pythoncom
        def reload_enso_learned_shortcuts(path=None, all_calls_params=[]):
            # Get unique list of changed paths
            # ('all_calls_params' arg is provided by the @debounce decorator)
            changed_paths = set(chain.from_iterable(args for (args, kwargs) in all_calls_params))
            # Act only on file changes and exclude certain files
            if changed_paths and not any(
                not isdir(p) and basename(p) not in ('desktop.ini',)
                for p in changed_paths
            ):
                print "Skipping changed path(s): ", changed_paths
                return False
            shortcuts_dict.update_by_dir(
                LEARN_AS_DIR,
                dict((s.name, s) for s in
                get_shortcuts_from_dir(
                    LEARN_AS_DIR,
                    max_depth=0,
                    #,category="learned" if self.use_categories else None
                    flags=SHORTCUT_FLAG_LEARNED
                ))
            )
            return True

        reload_enso_learned_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_enso_learned_shortcuts),
            ((LEARN_AS_DIR, False),),
        )

        try:
            save_shortcuts_cache(shortcuts_dict)
            logging.info("Updated shortcuts cache")
        except Exception as e:
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
                        win32file.SYMBOLIC_LINK_FLAG_DIRECTORY if os.path.isdir(target) else 0)
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


class RecentCommandImpl(AbstractOpenCommand):

    def __init__(self, use_categories=True):
        self.shortcut_dict = None
        self.use_categories = use_categories
        super(RecentCommandImpl, self).__init__()

    def _create_category(self, shortcut_name, shortcut_type, target, shortcut_path):
        pass

    def _reload_shortcuts(self):
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
        self.shortcut_dict = ShortcutsDict()

        @timed("Loaded recent documents shortcuts")
        @synchronized()
        @initialize_pythoncom
        def reload_recent_shortcuts(path=None):
            _ = path
            self.shortcut_dict.update(
                get_shortcuts_from_dir(recent_documents_dir,
                                       max_depth=0,
                                       category=self._create_category
                )
            )

        reload_recent_shortcuts()
        dirwatcher.register_monitor_callback(
            debounce(SHORTCUTS_REFRESH_DEBOUNCE_TIME)(reload_recent_shortcuts),
            ((recent_documents_dir, False),)
        )


        return self.shortcut_dict

    def _is_application(self, shortcut):
        return shortcut.type == SHORTCUT_TYPE_EXECUTABLE

    def _get_shortcut_type(self, target):
        return get_file_type(target)

    def _run_shortcut(self, shortcut):
        return run_shortcut(shortcut)

    def _open_with_shortcut(self, shortcut, targets):
        return open_with_shortcut(shortcut, targets)
