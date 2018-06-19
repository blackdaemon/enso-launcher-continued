# Copyright (c) 2008, Humanized, Inc.
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
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso
#
# ----------------------------------------------------------------------------
__updated__ = "2018-06-19"

import logging
import os
import re
import time
import types
from os.path import basename

import enso.config
import enso.system
from enso.commands.manager import CommandAlreadyRegisteredError
from enso.contrib.scriptotron import (
    adapters,
    cmdretriever,
    concurrency,
    ensoapi,
)
from enso.contrib.scriptotron.events import EventResponderList
from enso.contrib.scriptotron.tracebacks import TracebackCommand, safetyNetted
from enso.messages import MessageManager, displayMessage as display_xml_message
from enso.platform import PlatformUnsupportedError
from enso.utils import do_once

# This may no longer be required (it was for backward compat)
SCRIPTS_FILE_NAME = os.path.expanduser("~/.ensocommands")
# IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
# IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
_SCRIPTS_FOLDER_NAME = enso.system.SPECIALFOLDER_ENSOCOMMANDS  # @UndefinedVariable

# String to search for in the file to determine if it contains any command definitions
COMMAND_FILE_CHECK = re.compile(
    r"^def %s[a-zA-Z0-9_]" % cmdretriever.SCRIPT_PREFIX,
    re.MULTILINE)


class ScriptCommandTracker(object):

    def __init__(self, commandManager, eventManager):
        self._cmdExprs = []
        self._cmdMgr = commandManager
        self._genMgr = concurrency.GeneratorManager(eventManager)
        self._quasimodeStartEvents = EventResponderList(
            eventManager,
            "startQuasimode",
            self._onQuasimodeStart
        )
        self._textModifiedEvents = EventResponderList(
            eventManager,
            "textModified",
            self._onTextModified
        )

    @safetyNetted
    def _callHandler(self, handler, *args, **kwargs):
        assert logging.debug("calling handler %s", handler.__name__) or True
        result = handler(*args, **kwargs)
        if isinstance(result, types.GeneratorType):
            self._genMgr.add(result)

    def _onQuasimodeStart(self):
        perf = []
        for cmdName, handler in self._quasimodeStartEvents:
            _ = cmdName
            started = time.time()
            self._callHandler(handler)
            elapsed = time.time() - started
            perf.append((handler, [], [], elapsed))
        return perf

    def _onTextModified(self, keyCode, oldText, newText, quasimodeId=0):
        perf = []
        for cmdName, handler in self._textModifiedEvents:
            if not newText.startswith(cmdName + " "):
                continue
            oldText = oldText[len(cmdName) + 1:]
            newText = newText[len(cmdName) + 1:]
            started = time.time()
            try:
                self._callHandler(
                    handler, keyCode, oldText, newText, quasimodeId=quasimodeId)
            except Exception:
                logging.error(
                    "onTextModified handler is missing quasimodeId parameter: %s" % cmdName)
                self._callHandler(handler, keyCode, oldText, newText)
            elapsed = time.time() - started
            perf.append((handler, [], [], elapsed))
        return perf

    def _registerCommand(self, cmdObj, cmdExpr):
        try:
            self._cmdMgr.registerCommand(cmdExpr, cmdObj)
            self._cmdExprs.append(cmdExpr)
        except CommandAlreadyRegisteredError:
            logging.warn("Command already registered: %s" % cmdExpr)

    def registerNewCommands(self, commandInfoList):
        for info in commandInfoList:
            if hasattr(info["func"], "on_quasimode_start"):
                self._quasimodeStartEvents[info["cmdName"]] = info[
                    "func"].on_quasimode_start
            if hasattr(info["func"], "on_text_modified"):
                self._textModifiedEvents[info["cmdName"]] = info[
                    "func"].on_text_modified
            cmd = adapters.makeCommandFromInfo(
                info,
                ensoapi.EnsoApi(),
                self._genMgr
            )
            self._registerCommand(cmd, info["cmdExpr"])

    def clearCommands(self, commandInfoList=None):
        if commandInfoList:
            for info in commandInfoList:
                if hasattr(info["func"], "on_quasimode_start"):
                    del self._quasimodeStartEvents[info["cmdName"]]
                if hasattr(info["func"], "on_text_modified"):
                    del self._textModifiedEvents[info["cmdName"]]
                # Both below can fail and it should be tolerated
                try:
                    self._cmdMgr.unregisterCommand(info["cmdExpr"])
                except RuntimeError:
                    logging.warn("Error unregistering command '%s'" % info["cmdExpr"])
                try:
                    del self._cmdExprs[self._cmdExprs.index(info["cmdExpr"])]
                except Exception:
                    logging.warn("Error deleting command '%s'" % info["cmdExpr"])
                # FIXME: remove generator from _genMgr
        else:
            for cmdExpr in self._cmdExprs:
                try:
                    self._cmdMgr.unregisterCommand(cmdExpr)
                except RuntimeError as e:
                    print e, cmdExpr
            self._cmdExprs = []
            self._quasimodeStartEvents[:] = []
            self._genMgr.reset()


class ScriptTracker(object):

    def __init__(self, eventManager, commandManager):
        self._firstRun = True
        self._scriptCmdTracker = ScriptCommandTracker(commandManager,
                                                      eventManager)
        self._scriptFilename = SCRIPTS_FILE_NAME
        self._scriptFolder = getScriptsFolderName()
        self._lastMods = {}
        self._registerDependencies()
        self._commandsInFile = {}
        # Call it now, otherwise there is a delay on first quasimode invocation
        self._updateScripts()

        eventManager.registerResponder(
            self._updateScripts,
            "startQuasimode"
        )

        commandManager.registerCommand(TracebackCommand.NAME,
                                       TracebackCommand())

    @classmethod
    def install(cls, eventManager, commandManager):
        cls(eventManager, commandManager)

    @staticmethod
    @safetyNetted
    def _getGlobalsFromSourceCode(text, filename):
        allGlobals = {}
        code = compile(text + "\n", filename, "exec")
        try:
            exec code in allGlobals
        except PlatformUnsupportedError:
            logging.warning(
                "Command '%s' is not supported on this platform."
                % basename(filename)
            )
            return None
        return allGlobals

    def _getCommandFiles(self):
        try:
            # Get all *.py files, except those not valid for current platform, example:
            # example.windows.py, example.linux.py, example.osx.py
            commandFiles = [
                os.path.join(self._scriptFolder, x)
                for x in os.listdir(self._scriptFolder)
                if x.endswith(".py")
            ]
        except:
            commandFiles = []
        return commandFiles

    def _reloadPyScripts(self, files=None):
        if files:
            for file_name in files:
                cmd_infos = self._commandsInFile.get(file_name, None)
                if cmd_infos:
                    self._scriptCmdTracker.clearCommands(cmd_infos)
        else:
            self._scriptCmdTracker.clearCommands()
        commandFiles = [self._scriptFilename]
        if files:
            commandFiles = commandFiles + files
            print "Files to reload: ", commandFiles
        else:
            commandFiles = commandFiles + self._getCommandFiles()

        assert logging.debug(commandFiles) or True

        for file_name in commandFiles:
            try:
                with open(file_name, "r") as fd:
                    file_contents = fd.read().replace('\r\n', '\n') + "\n"
            except IOError as e:
                if file_name == SCRIPTS_FILE_NAME:
                    do_once(
                        logging.warning,
                        "Legacy script file %s not found" % SCRIPTS_FILE_NAME
                    )
                else:
                    logging.error(e)
                continue
            except Exception as e:
                logging.error(e)
                continue

            # Do not bother to parse files which does not contain command definitions
            if not COMMAND_FILE_CHECK.search(file_contents):
                logging.warning(
                    "Skipping file %s as it does not contain any command definitions",
                    file_name)
                continue

            allGlobals = self._getGlobalsFromSourceCode(
                file_contents,
                file_name
            )

            if allGlobals is not None:
                infos = cmdretriever.getCommandsFromObjects(allGlobals)
                self._scriptCmdTracker.registerNewCommands(infos)
                self._registerDependencies(allGlobals)
                self._commandsInFile[file_name] = infos
                logging.info(
                    "Scriptotron registered commands from '%s': [%s]" %
                    (basename(file_name), ", ".join(info["cmdName"] for info in infos))
                )

    def _registerDependencies(self, allGlobals=None):
        baseDeps = [self._scriptFilename] + self._getCommandFiles()

        if allGlobals:
            # Find any other files that the script may have executed
            # via execfile().
            extraDeps = [
                obj.func_code.co_filename
                for obj in allGlobals.values()
                if ((hasattr(obj, "__module__")) and
                    (obj.__module__ is None) and
                    (hasattr(obj, "func_code")))
            ]
        else:
            extraDeps = []

        self._fileDependencies = list(set(baseDeps + extraDeps))

    def _updateScripts(self):
        filesToReload = {}
        for fileName in self._fileDependencies:
            if os.path.isfile(fileName):
                lastMod = os.path.getmtime(fileName)
                if lastMod != self._lastMods.get(fileName, 0):
                    self._lastMods[fileName] = lastMod
                    filesToReload[fileName] = lastMod

        for fileName in self._getCommandFiles():
            if fileName not in self._fileDependencies:
                self._fileDependencies.append(fileName)
                self._lastMods[fileName] = os.path.getmtime(fileName)
                filesToReload[fileName] = lastMod

        if filesToReload:
            if not self._firstRun:
                display_xml_message(
                    u"<p>Reloading commands, please wait...</p><caption>enso</caption>")
            # TODO: This can be enabled after issues in clearCommands are
            # solved...
            self._reloadPyScripts(filesToReload.keys())
            # self._reloadPyScripts()
            if not self._firstRun:
                # Force primary-message to disappear
                MessageManager.get().finishPrimaryMessage()
                # Display mini message with result
                display_xml_message(
                    u"<p>Commands have been reloaded.</p><caption>enso</caption>",
                    primaryMsg=False, miniMsg=True, miniWaitTime=10)
            if self._firstRun:
                self._firstRun = False


def getScriptsFolderName():
    if hasattr(enso.config, "SCRIPTS_FOLDER_NAME"):
        if os.path.isdir(enso.config.SCRIPTS_FOLDER_NAME):  # IGNORE:E1101
            return enso.config.SCRIPTS_FOLDER_NAME  # IGNORE:E1101
        else:
            raise Exception("enso.config.SCRIPTS_FOLDER_NAME is not valid folder: \"%s\""
                            % enso.config.SCRIPTS_FOLDER_NAME)  # IGNORE:E1101
    else:
        if not os.path.isdir(_SCRIPTS_FOLDER_NAME):
            os.makedirs(_SCRIPTS_FOLDER_NAME)
        return _SCRIPTS_FOLDER_NAME
