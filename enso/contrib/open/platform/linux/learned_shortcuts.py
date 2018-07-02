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

from watchdog.events import FileSystemEventHandler

from enso.contrib.open import (
    shortcuts,
    dirwatcher
)
from enso.contrib.open.platform.linux.utils import get_file_type

from os.path import splitext, basename, expanduser, isdir, join as pathjoin

SHORTCUT_CATEGORY = "learned"
my_documents_dir = expanduser('~/Documents')
LEARN_AS_DIR = pathjoin(my_documents_dir, u"Enso")

# Check if Learn-as dir exist and create it if not
if (not isdir(LEARN_AS_DIR)):
    os.makedirs(LEARN_AS_DIR)


def get_learned_shortcuts():
    logging.info("Loading learn-as shortcuts")
    result = []
    for f in os.listdir(LEARN_AS_DIR):
        name = splitext(basename(f).lower())[0]
        filepath = pathjoin(LEARN_AS_DIR, f)
        t = get_file_type(filepath)
        shortcut = shortcuts.Shortcut(name, t, filepath, shortcut_filename=filepath, category=SHORTCUT_CATEGORY)
        result.append(shortcut)
    #print result
    logging.info("Loaded %d shortcuts" % len(result))
    return result


def register_monitor_callback(callback_func):
    dirwatcher.register_monitor_callback(
        callback_func,
        ((LEARN_AS_DIR, False),)
    )
