# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Imports
import os
import logging
import glob

from enso.contrib.open import interfaces
from enso.contrib.open import shortcuts
from enso.contrib.open.interfaces import AbstractOpenCommand, ShortcutAlreadyExistsError
from enso.contrib.open.shortcuts_dict import ShortcutsDict


my_documents_dir = os.path.expanduser('~/Documents')
LEARN_AS_DIR = os.path.join(my_documents_dir, u"Enso's Learn As Open Commands")

# Check if Learn-as dir exist and create it if not
if (not os.path.isdir(LEARN_AS_DIR)):
    os.makedirs(LEARN_AS_DIR)


def get_shortcut_type(filepath):
    raise NotImplementedError()


def get_shortcuts():
    result = []
    for file in os.listdir(LEARN_AS_DIR):
        name = os.path.basename(file).lower()
        filepath = os.path.join(LEARN_AS_DIR, file)
        type = get_shortcut_type(filepath)
        shortcut = shortcuts.Shortcut(name, type, filepath)
        result.append(shortcut)
    return result


def get_applications():
    applications = glob.glob('/Applications/*.app')
    result = []
    for file in applications:
        name = os.path.splitext(os.path.basename(file))[0].lower()
        filepath = os.path.join(LEARN_AS_DIR, file)
        type = get_shortcut_type(filepath)
        shortcut = shortcuts.Shortcut(name, type, filepath)
        result.append(shortcut)
    return result


class OpenCommandImpl( AbstractOpenCommand ):

    def __init__(self):
        super(OpenCommandImpl, self).__init__()

    def _get_learn_as_dir(self):
        return LEARN_AS_DIR

    def _reload_shortcuts(self):
        shortcuts = []
        shortcuts.extend(get_shortcuts())
        shortcuts.extend(get_applications())
        return ShortcutsDict(((s.name, s) for s in shortcuts))

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
        try:
            os.system('/usr/bin/open "%s"' % shortcut.file)
        except Exception, e:
            logging.error(e)

    def _open_with_shortcut(self, shortcut, files):
        raise NotImplementedError()


# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: