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

import logging
import os
import types

from enso.commands.manager import CommandAlreadyRegisteredError
from enso.contrib.scriptotron.tracebacks import TracebackCommand
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.events import EventResponderList
from enso.contrib.scriptotron import adapters
from enso.contrib.scriptotron import cmdretriever
from enso.contrib.scriptotron import ensoapi
from enso.contrib.scriptotron import concurrency

import enso.config
import enso.system

# This may no longer be required (it was for backward compat)
SCRIPTS_FILE_NAME = "~/.ensocommands"
_SCRIPTS_FOLDER_NAME = enso.system.SPECIALFOLDER_ENSOCOMMANDS

    
class ScriptCommandTracker:
    def __init__( self, commandManager, eventManager ):
        self._cmdExprs = []
        self._cmdMgr = commandManager
        self._genMgr = concurrency.GeneratorManager( eventManager )
        self._qmStartEvents = EventResponderList(
            eventManager,
            "startQuasimode",
            self._onQuasimodeStart
            )

    @safetyNetted
    def _callHandler( self, handler ):
        result = handler()
        if isinstance( result, types.GeneratorType ):
            self._genMgr.add( result )

    def _onQuasimodeStart( self ):
        for handler in self._qmStartEvents:
            self._callHandler( handler )

    def clearCommands( self ):
        for cmdExpr in self._cmdExprs:
            self._cmdMgr.unregisterCommand( cmdExpr )
        self._cmdExprs = []
        self._qmStartEvents[:] = []
        self._genMgr.reset()

    def _registerCommand( self, cmdObj, cmdExpr ):
        try:
            self._cmdMgr.registerCommand( cmdExpr, cmdObj )
            self._cmdExprs.append( cmdExpr )
        except CommandAlreadyRegisteredError:
            logging.warn( "Command already registered: %s" % cmdExpr )

    def registerNewCommands( self, commandInfoList ):
        for info in commandInfoList:
            if hasattr( info["func"], "on_quasimode_start" ):
                self._qmStartEvents.append( info["func"].on_quasimode_start )
            cmd = adapters.makeCommandFromInfo(
                info,
                ensoapi.EnsoApi(),
                self._genMgr
                )
            self._registerCommand( cmd, info["cmdExpr"] )

class ScriptTracker:
    def __init__( self, eventManager, commandManager ):
        self._scriptCmdTracker = ScriptCommandTracker( commandManager,
                                                       eventManager )
        self._scriptFilename = SCRIPTS_FILE_NAME
        self._scriptFolder = getScriptsFolderName()
        self._lastMods = {}
        self._registerDependencies()

        eventManager.registerResponder(
            self._updateScripts,
            "startQuasimode"
            )

        commandManager.registerCommand( TracebackCommand.NAME,
                                        TracebackCommand() )

    @classmethod
    def install( cls, eventManager, commandManager ):
        cls( eventManager, commandManager )

    @safetyNetted
    def _getGlobalsFromSourceCode( self, text, filename ):
        allGlobals = {}
        code = compile( text, filename, "exec" )
        exec code in allGlobals
        return allGlobals
    
    def _getCommandFiles( self ):
        try:
            commandFiles = [
              os.path.join(self._scriptFolder,x)
              for x in os.listdir(self._scriptFolder)
              if x.endswith(".py")
            ]
        except:
            commandFiles = []
        return commandFiles

    def _reloadPyScripts( self ):
        self._scriptCmdTracker.clearCommands()
        commandFiles = [self._scriptFilename] + self._getCommandFiles()
        print commandFiles
        for f in commandFiles:
            try:
                text = open( f, "r" ).read()
            except:
                continue

            allGlobals = self._getGlobalsFromSourceCode(
                text,
                f
                )

            if allGlobals is not None:
                infos = cmdretriever.getCommandsFromObjects( allGlobals )
                self._scriptCmdTracker.registerNewCommands( infos )
                self._registerDependencies( allGlobals )

    def _registerDependencies( self, allGlobals = None ):
        baseDeps = [ self._scriptFilename ] + self._getCommandFiles()

        if allGlobals:
            # Find any other files that the script may have executed
            # via execfile().
            extraDeps = [
                obj.func_code.co_filename
                for obj in allGlobals.values()
                if ( (hasattr(obj, "__module__")) and
                     (obj.__module__ is None) and 
                     (hasattr(obj, "func_code")) )
                ]
        else:
            extraDeps = []

        self._fileDependencies = list( set(baseDeps + extraDeps) )

    def _updateScripts( self ):
        shouldReload = False
        for fileName in self._fileDependencies:
            if os.path.exists( fileName ):
                lastMod = os.stat( fileName ).st_mtime
                if lastMod != self._lastMods.get(fileName):
                    self._lastMods[fileName] = lastMod
                    shouldReload = True

        for fileName in self._getCommandFiles():
            if fileName not in self._fileDependencies:
                self._fileDependencies.append(fileName)
                self._lastMods[fileName] = os.stat( fileName ).st_mtime
                shouldReload = True

        if shouldReload:
            self._reloadPyScripts()


def getScriptsFolderName():
    if hasattr(enso.config, "SCRIPTS_FOLDER_NAME"):
        if os.path.isdir(enso.config.SCRIPTS_FOLDER_NAME):#IGNORE:E1101
            return enso.config.SCRIPTS_FOLDER_NAME#IGNORE:E1101
        else:
            raise Exception("enso.config.SCRIPTS_FOLDER_NAME is not valid folder: \"%s\""
                            % enso.config.SCRIPTS_FOLDER_NAME)#IGNORE:E1101
    else:
        if not os.path.isdir(_SCRIPTS_FOLDER_NAME):
            os.makedirs(_SCRIPTS_FOLDER_NAME)
        return _SCRIPTS_FOLDER_NAME
