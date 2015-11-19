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

import os
import sys
import logging
import glob
import unicodedata
import ctypes
import win32api
import win32con
from ctypes import wintypes
import pythoncom
from win32com.shell import shell, shellcon

from enso.contrib.open.platform.win32 import utils
from enso.contrib.open.platform.win32.control_panel import ControlPanelInfo
from enso.contrib.open import shortcuts
# TODO: This import should be changed as soon as registry support gets merged
# into working branch
from enso.contrib.open.platform.win32 import registry


def get_control_panel_applets(use_categories=True):
    if utils.platform_windows_vista() or utils.platform_windows_7():
        from enso.contrib.open.platform.win32 import control_panel_win7
        return control_panel_win7.get_control_panel_applets()

    control_panel_applets = []
    cpi = ControlPanelInfo()

    # Cache disabled ("don't load") control-panels from registry for lookup
    # Note: Control-panel applets can be disabled using TweakUI
    cpl_disabled_panels = set(
        cplfile.lower() for cplfile,_,_ in registry.walk_values(win32con.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\don't load",
        valuetypes = (win32con.REG_SZ,))
    )

    # List control-panel applets from system directory, exclude disabled applets
    cpl_files = [cpl for cpl
        in glob.iglob(os.path.join(os.path.expandvars("${WINDIR}"), "system32", "*.cpl"))
        if os.path.basename(cpl).lower() not in cpl_disabled_panels]

    # Add control-panel applets from custom locations, read from registry
    search_paths = os.getenv('PATH').split(";")
    search_paths.insert(0, os.path.join(os.getenv('WINDIR'), "System32"))
    for _, cplfile, _ in registry.walk_values(
        win32con.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\Cpls",
        valuetypes = (win32con.REG_EXPAND_SZ, win32con.REG_SZ),
        autoexpand = True):
        if not os.path.isfile(cplfile):
            if os.path.isabs(cplfile):
                continue
            for dirname in search_paths:
                possible = os.path.join(os.path.normpath(dirname), cplfile)
                if os.path.isfile(possible):
                    cplfile = possible
                    break
            else:
                continue
        # Exclude disabled applets
        if os.path.basename(cplfile).lower() in cpl_disabled_panels:
            continue
        cpl_files.append(cplfile)

    # Read descriptions of control-panel applets from the .cpl files directly
    for cplfile in cpl_files:
        for file, name, desc, index in cpi.get_cplinfo(cplfile):
            name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
            name = name.lower()
            #name = xml_escape(name)
            control_panel_applets.append(
                shortcuts.Shortcut(
                    (u"%s (control panel)" % name) if use_categories else name,
                    shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
                    "rundll32.exe shell32.dll,Control_RunDLL \"%s\",@%d"
                        % (cplfile, index)
                ))
    del cpi

    # Extend control-panel applets list with few useful shortcuts that can't be
    # reached from the control-panel directly
    control_panel_applets.extend([
        shortcuts.Shortcut(
            u"control panel",
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "rundll32.exe shell32.dll,Control_RunDLL"),
        shortcuts.Shortcut(
            u"about microsoft windows%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "rundll32.exe shell32.dll,ShellAboutW "),
        shortcuts.Shortcut(
            u"safely remove hardware",
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "rundll32.exe shell32.dll,Control_RunDLL HotPlug.dll"),
        shortcuts.Shortcut(
            u"unplug or eject hardware",
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "rundll32.exe shell32.dll,Control_RunDLL HotPlug.dll"),
        shortcuts.Shortcut(
            u"device manager%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            #"rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,1"
            "rundll32.exe devmgr.dll DeviceManager_Execute"),
        shortcuts.Shortcut(
            u"disk management%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "diskmgmt.msc"),
        shortcuts.Shortcut(
            u"scheduled tasks%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "control.exe schedtasks"),
        shortcuts.Shortcut(
            u"scanners and cameras%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "control.exe sticpl.cpl"),
        shortcuts.Shortcut(
            u"removable storage%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "ntmsmgr.msc"),
        shortcuts.Shortcut(
            u"performance monitor%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "perfmon.msc"),
        shortcuts.Shortcut(
            u"private character editor%s" % (
                " (control panel)" if use_categories else ""),
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "eudcedit.msc"),
    ])

    return control_panel_applets


"""
def cpl_file_exists(cpl_name):
    return (
        os.path.isfile(
            os.path.expandvars("${WINDIR}\\%s.cpl") % cpl_name)
        or os.path.isfile(
            os.path.expandvars("${WINDIR}\\system32\\%s.cpl") % cpl_name)
        )

control_panel_applets = [i[:3] for i in (
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"control panel",
        "rundll32.exe shell32.dll,Control_RunDLL"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"accessibility options (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL access.cpl"),
    #accessibility options (Keyboard):
    #    rundll32.exe shell32.dll,Control_RunDLL access.cpl,,1
    #accessibility options (Sound):
    #    rundll32.exe shell32.dll,Control_RunDLL access.cpl,,2
    #accessibility options (Display):
    #    rundll32.exe shell32.dll,Control_RunDLL access.cpl,,3
    #accessibility options (Mouse):
    #    rundll32.exe shell32.dll,Control_RunDLL access.cpl,,4
    #accessibility options (General):
    #    rundll32.exe shell32.dll,Control_RunDLL access.cpl,,5
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"add or remove programs (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL appwiz.cpl"),
    #add or remove programs (Install/Uninstall):
    #    rundll32.exe shell32.dll,Control_RunDLL appwiz.cpl,,1
    #add or remove programs (Windows Setup):
    #    rundll32.exe shell32.dll,Control_RunDLL appwiz.cpl,,2
    #add or rove programs (Startup Disk):
    #    rundll32.exe shell32.dll,Control_RunDLL appwiz.cpl,,3
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"display properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL desk.cpl"),
    #Display Properties (Background):
    #    rundll32.exe shell32.dll,Control_RunDLL desk.cpl,,0
    #Display Properties (Screen Saver):
    #    rundll32.exe shell32.dll,Control_RunDLL desk.cpl,,1
    #Display Properties (Appearance):
    #    rundll32.exe shell32.dll,Control_RunDLL desk.cpl,,2
    #Display Properties (Settings):
    #    rundll32.exe shell32.dll,Control_RunDLL desk.cpl,,3

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"regional and language options (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL intl.cpl"),
    #Regional Settings Properties (Regional Settings):
    #    rundll32.exe shell32.dll,Control_RunDLL intl.cpl,,0
    #Regional Settings Properties (Number):
    #    rundll32.exe shell32.dll,Control_RunDLL intl.cpl,,1
    #Regional Settings Properties (Currency):
    #    rundll32.exe shell32.dll,Control_RunDLL intl.cpl,,2
    #Regional Settings Properties (Time):
    #    rundll32.exe shell32.dll,Control_RunDLL intl.cpl,,3
    #Regional Settings Properties (Date):
    #    rundll32.exe shell32.dll,Control_RunDLL intl.cpl,,4

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"game controllers (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL joy.cpl"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"mouse properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL main.cpl @0"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"keyboard properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL main.cpl @1"),
    # DOES NOT WORK
    #Printers:
    #   rundll32.exe shell32.dll,Control_RunDLL main.cpl @2

    # DOES NOT WORK
    #Fonts:
    #    rundll32.exe shell32.dll,Control_RunDLL main.cpl @3

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"microsoft exchange profiles (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL mlcfg32.cpl",
        _cpl_exists("mlcfg32")),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"sounds and audio devices (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl"),
    #Multimedia Properties (Audio):
    #    rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl,,0
    #Multimedia Properties (Video):
    #    rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl,,1
    #Multimedia Properties (MIDI):
    #    rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl,,2
    #Multimedia Properties (CD Music):
    #    rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl,,3
    #Multimedia Properties (Advanced):
    #    rundll32.exe shell32.dll,Control_RunDLL mmsys.cpl,,4

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"modem properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL modem.cpl",
        _cpl_exists("modem")),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"network connections (control panel)",
        "RUNDLL32.exe SHELL32.DLL,Control_RunDLL NCPA.CPL"),

    #Password Properties (Change Passwords):
    #    rundll32.exe shell32.dll,Control_RunDLL password.cpl
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"system properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,0"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"device manager (control panel)",
        #"rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,1"
        "devmgmt.msc"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"disk management (control panel)",
        "diskmgmt.msc"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"scanners and cameras (control panel)",
        "control.exe sticpl.cpl"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"removable storage (control panel)",
        "ntmsmgr.msc"),

    #dfrg.msc Disk defrag
    #eventvwr.msc Event viewer
    #eventvwr.exe \\computername View the Event Log at a remote computer
    #fsmgmt.msc Shared folders
    #gpedit.msc Group policies
    #lusrmgr.msc Local users and groups
    #perfmon.msc Performance monitor
    #rsop.msc Resultant set of policies
    #secpol.msc Local security settings
    #services.msc Various Services

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"hardware profiles (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,2"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"advanced system properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,3"),

    #Add New Hardware Wizard:
    #    rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl @1

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"date and time (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL timedate.cpl"),

    #Microsoft Workgroup Postoffice Admin:
    #    rundll32.exe shell32.dll,Control_RunDLL wgpocpl.cpl

    #Open With (File Associations):
    #    rundll32.exe shell32.dll,OpenAs_RunDLL d:\path\filename.ext

    #Run Diskcopy Dialog:
    #    rundll32 diskcopy.dll,DiskCopyRunDll

    #Create New Shortcut Wizard:
    #    'puts the new shortcut in the location specified by %1
    #    rundll32.exe AppWiz.Cpl,NewLinkHere %1

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"add new hardware wizard (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL hdwwiz.cpl @1"),

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"add printer wizard (control panel)",
        "rundll32.exe shell32.dll,SHHelpShortcuts_RunDLL AddPrinter"),
    #(SHORTCUT_TYPE_CONTROL_PANEL,
    #    u"dialup networking wizard (cp)",
    #    "rundll32.exe rnaui.dll,RnaWizard"),

    #Open a Scrap Document:
    #    rundll32.exe shscrap.dll,OpenScrap_RunDLL /r /x %1

    #Create a Briefcase:
    #    rundll32.exe syncui.dll,Briefcase_Create

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"printers and faxes (control panel)",
        "rundll32.exe shell32.dll,SHHelpShortcuts_RunDLL PrintersFolder"),

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"fonts (control panel)",
        "rundll32.exe shell32.dll,SHHelpShortcuts_RunDLL FontsFolder"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"windows firewall (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL firewall.cpl"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"speech properties (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL \"${COMMONPROGRAMFILES}\\Microsoft Shared\\Speech\\sapi.cpl\"",
        os.path.isfile(os.path.expandvars("${COMMONPROGRAMFILES}\\Microsoft Shared\\Speech\\sapi.cpl"))),

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"internet options (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL inetcpl.cpl"),

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"odbc data source administrator (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL odbccp32.cpl"),
    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"power options (control panel)",
        "rundll32.exe shell32.dll,Control_RunDLL powercfg.cpl"),

    (SHORTCUT_TYPE_CONTROL_PANEL,
        u"bluetooth properties (control panel)",
        "control.exe bhtprops.cpl",
        _cpl_exists("bhtprops")),

    #Pick a Time Zone Dialog:
    #    rundll32.exe shell32.dll,Control_RunDLL timedate.cpl,,/f
) if len(i) < 4 or i[3]]
#print control_panel_applets
"""

"""
def get_control_panel_applets():
    import _winreg as reg

    reghandle = None
    cpl_applets = []
    try:
        regkey = None
        try:
            reghandle = reg.ConnectRegistry(None, reg.HKEY_LOCAL_MACHINE)
            key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\Cpls"
            regkey = reg.OpenKey(reghandle, key)
            index = 0
            try:
                while True:
                    regval = reg.EnumValue(regkey, index)
                    cpl_applets.append((
                        SHORTCUT_TYPE_CONTROL_PANEL,
                        regval[0].lower().replace("/"," ") + " (control panel)",
                        regval[1]))
                    index += 1
            except Exception, e:
                pass
        except Exception, e:
            print e
        finally:
            if regkey:
                reg.CloseKey(regkey)

        regkey = None
        try:
            key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ControlPanel\\Namespace"
            regkey = reg.OpenKey(reghandle, key)
            index = 0
            try:
                while True:
                    cplkey = reg.EnumKey(regkey, index)
                    regkey1 = None
                    try:
                        regkey1 = reg.OpenKey(reghandle, key + "\\" + cplkey)
                        cpl_applets.append((
                            SHORTCUT_TYPE_CONTROL_PANEL,
                            reg.QueryValueEx(regkey1, "Name")[0].lower().replace("/"," ") + " (control panel)",
                            reg.QueryValueEx(regkey1, "Module")[0]))
                    except:
                        pass
                    finally:
                        if regkey1:
                            reg.CloseKey(regkey1)
                    index += 1
            except Exception, e:
                pass
        except Exception, e:
            print e
        finally:
            if regkey:
                reg.CloseKey(regkey)
    finally:
        if reghandle:
            reg.CloseKey(reghandle)
    return cpl_applets


print get_control_panel_applets()
"""


# vim:set tabstop=4 shiftwidth=4 expandtab: