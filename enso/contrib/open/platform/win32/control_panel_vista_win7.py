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

import os
import logging
import glob
import unicodedata
import ctypes
import win32api
import win32con
import _winreg as winreg
from ctypes import wintypes
from win32com.shell import shell, shellcon
import xml.etree.cElementTree as ElementTree

try:
    import regex as re
except Exception, e:
    import re

# TODO: This import should be changed as soon as registry support gets merged
# into the working branch
from enso.contrib.open.platform.win32 import registry

from enso.contrib.open.platform.win32.control_panel import ControlPanelInfo
from enso.contrib.open.platform.win32 import utils
from enso.contrib.open import shortcuts


def read_task_links_xml(xml_file = None, xml = None):
    shortcuts_list = []

    APPS_NS = "http://schemas.microsoft.com/windows/cpltasks/v1"
    TASKS_NS = "http://schemas.microsoft.com/windows/tasks/v1"
    TASKS_NS2 = "http://schemas.microsoft.com/windows/tasks/v2"

    if xml_file:
        tree = ElementTree.ElementTree().parse(xml_file)
    elif xml:
        tree = ElementTree.fromstring(xml)
    else:
        raise AssertionError("Provide xml_file or xml parameter.")

    for app in tree.findall("{%s}application" % APPS_NS):
        for item in app.findall('{%s}task' % TASKS_NS):
            name = item.findtext("{%s}name" % TASKS_NS)
            cmd = item.findtext("{%s}command" % TASKS_NS)
            cp = item.find("{%s}controlpanel" % TASKS_NS2)
            if cmd is not None or cp is not None:
                name = read_mui_string_from_dll(name)
                name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').lower()
                if cp is not None:
                    cname = cp.get('name')
                    cpage = cp.get('page')
                    if cpage:
                        cmd = "control.exe /name %s /page %s" % (cname, cpage)
                    else:
                        cmd = "control.exe /name %s" % cname
                else:
                    pass
                    #print cmd
                sh = shortcuts.Shortcut(
                    u"%s (control panel)" % name,
                    shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
                    cmd
                )
                shortcuts_list.append(sh)
    return shortcuts_list


def read_default_windows7_tasklist_xml():
    handle = win32api.LoadLibraryEx(
        "shell32.dll",
        None,
        win32con.LOAD_LIBRARY_AS_DATAFILE | win32con.DONT_RESOLVE_DLL_REFERENCES)
    #TODO: Is the resource-id (#21) same for all builds of Windows 7?
    xml = win32api.LoadResource(handle, "XML", 21)
    return xml


def get_control_panel_applets(use_categories=True):
    """
    http://msdn.microsoft.com/en-us/library/cc144195(v=VS.85).aspx
    """

    control_panel_applets = []
    cpi = ControlPanelInfo()

    for clsid in registry.walk_keys(win32con.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ControlPanel\\NameSpace",
        key_filter_regex=r"\{[A-F0-9-]+\}"):

        try:
            canonical_name = registry.get_value(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s" % clsid, "System.ApplicationName")
        except Exception, e:
            logging.error("Error opening registry entry %s: %s", "CLSID\\%s" % clsid, e)
            continue
        if canonical_name:
            canonical_name = canonical_name[1]
        else:
            continue

        try:
            display_name = registry.get_value(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s" % clsid, "")
        except Exception, e:
            logging.error("Error opening registry entry %s: %s", "CLSID\\%s" % clsid, e)
            continue
        if display_name and display_name[1].startswith("@"):
            display_name = read_mui_string_from_reg(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s" % clsid,
                "")
        elif display_name:
            display_name = unicode(display_name[1])

        try:
            localized_name = registry.get_value(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s" % clsid, "LocalizedString")
            if localized_name[0] == win32con.REG_EXPAND_SZ:
                localized_name = localized_name[2]
            else:
                localized_name = localized_name[1]
            if localized_name.startswith("@"):
                localized_name = read_mui_string_from_reg(
                    win32con.HKEY_CLASSES_ROOT,
                    "CLSID\\%s" % clsid,
                    "LocalizedString")
        except:
            localized_name = None

        try:
            command = registry.get_value(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s\\Shell\\Open\\Command" % clsid, "")
            if command[0] == win32con.REG_EXPAND_SZ:
                command = command[2]
            else:
                command = command[1]
        except:
            command = None

        if localized_name:
            logging.debug(
                u"%s: %s",
                canonical_name,
                unicodedata.normalize('NFKD', localized_name).encode('ascii', 'ignore'))
            #logging.error(u"name: %s", localized_name)
        else:
            logging.error(u"%s: %s", canonical_name, display_name)
        #print clsid, canonical_name, display_name, localized_name, command

        if not (localized_name or display_name):
            continue

        name = localized_name if localized_name else display_name
        name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').lower()
        control_panel_applets.append(
            shortcuts.Shortcut(
                (u"%s (control panel)" % name) if use_categories else name,
                shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
                command if command else "control.exe /name %s" % canonical_name
            ))

        try:
            tasks_file = registry.get_value(
                win32con.HKEY_CLASSES_ROOT,
                "CLSID\\%s" % clsid, "System.Software.TasksFileUrl")
            if tasks_file:
                if tasks_file[0] == win32con.REG_EXPAND_SZ:
                    tasks_file = tasks_file[2]
                else:
                    tasks_file = tasks_file[1]
                if os.path.isfile(tasks_file) and os.path.splitext(tasks_file)[1].lower() == ".xml":
                    control_panel_applets.extend(read_task_links_xml(tasks_file))
        except:
            tasks_file = None

    # In Windows7 all *.cpl files in windows/system32 directory are disabled
    # by default due to different means of accessing their functionality
    # (see above code). However, we are going to process them anyway
    cpl_disabled_panels = []
    for cplfile, _, _ in registry.walk_values(win32con.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\don't load",
        valuetypes = (win32con.REG_SZ,)):
        cpl_disabled_panels.append(cplfile.lower())

    # List control-panel applets from system directory
    cpl_files = [cpl for cpl
        in glob.iglob(os.path.join(os.path.expandvars("${WINDIR}"), "system32", "*.cpl"))
        if os.path.basename(cpl).lower() not in cpl_disabled_panels]

    # Add control-panel applets from custom locations, read from registry
    for _, cplfile, _ in registry.walk_values(
        win32con.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Control Panel\\Cpls",
        valuetypes = (win32con.REG_EXPAND_SZ, win32con.REG_SZ),
        autoexpand = True):
        if not os.path.isfile(cplfile):
            continue
        if os.path.basename(cplfile).lower() in cpl_disabled_panels:
            continue
        cpl_files.append(cplfile)

    # Read descriptions of control-panel applets from the .cpl files directly
    for cplfile in cpl_files:
        for file, name, desc, index in cpi.get_cplinfo(cplfile):
            title = "%s - %s" % (name, desc.rstrip(". "))
            title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').lower()
            #name = xml_escape(name)

            control_panel_applets.append(
                shortcuts.Shortcut(
                    (u"%s (control panel)" % title) if use_categories else title,
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
            u"windows network diagnostics",
            shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
            "C:\\Windows\\System32\\msdt.exe -skip TRUE "
            "-path C:\\Windows\\diagnostics\\system\\networking "
            "-ep NetworkDiagnosticsNetworkMiniMap")
    ])

    # Add printers properties
    try:
        from win32com.client import GetObject
        wmiservice = GetObject(
            r"winmgmts:{impersonationLevel=impersonate}!\\localhost\root\cimv2")
        if wmiservice:
            for printer in wmiservice.ExecQuery("Select * from Win32_Printer"):
                control_panel_applets.append(
                    shortcuts.Shortcut(
                        u"printer properties: %s %s" % (
                            printer.Name,
                            u" (control panel)" if use_categories else ""),
                        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
                        u"rundll32.exe PRINTUI.DLL,PrintUIEntry /p /n \"%s\""
                            % printer.Name
                    )
                )
    except Exception, e:
        print e


    """
    #Another set of special items
    shortcuts.Shortcut(
        u"unplug or eject hardware",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "rundll32.exe shell32.dll,Control_RunDLL HotPlug.dll"),
    shortcuts.Shortcut(
        u"device manager (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        #"rundll32.exe shell32.dll,Control_RunDLL sysdm.cpl,,1"
        "rundll32.exe devmgr.dll DeviceManager_Execute"),
    shortcuts.Shortcut(
        u"disk management (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "diskmgmt.msc"),
    shortcuts.Shortcut(
        u"scheduled tasks (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "control.exe schedtasks"),
    shortcuts.Shortcut(
        u"scanners and cameras (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "control.exe sticpl.cpl"),
    shortcuts.Shortcut(
        u"removable storage (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "ntmsmgr.msc"),
    shortcuts.Shortcut(
        u"performance monitor (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "perfmon.msc"),
    shortcuts.Shortcut(
        u"private character editor (control panel)",
        shortcuts.SHORTCUT_TYPE_CONTROL_PANEL,
        "eudcedit.msc"),
    """

    control_panel_applets.extend(
        read_task_links_xml(xml=read_default_windows7_tasklist_xml()))

    return control_panel_applets


def read_mui_string_from_dll(id):
    assert id.startswith("@") and ",-" in id, \
           "id has invalid format. Expected format is '@dllfilename,-id'"

    m = re.match("@([^,]+),-([0-9]+)(;.*)?", id)
    if m:
        dll_filename = utils.expand_win_path_variables(m.group(1))
        string_id = long(m.group(2))
    else:
        raise Exception("Error parsing dll-filename and string-resource-id from '%s'" % id)

    h = win32api.LoadLibraryEx(
        dll_filename,
        None,
        win32con.LOAD_LIBRARY_AS_DATAFILE | win32con.DONT_RESOLVE_DLL_REFERENCES)
    if h:
        s = win32api.LoadString(h, string_id)
        return s
    return None


def read_mui_string_from_reg(hkey, key, value):
    _dll_handle = ctypes.windll.LoadLibrary("advapi32")

    load_mui_string = _dll_handle.RegLoadMUIStringW
    load_mui_string.argtypes = [
        wintypes.HKEY, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.LPCWSTR]
    #HKEY, LPCWSTR pwszValue, LPWSTR pwszBuffer, DWORD cbBuffer, LPDWORD pcbData, DWORD dwFlags, LPCWSTR pwszBaseDir )

    kh = winreg.OpenKey(hkey, key, 0, winreg.KEY_QUERY_VALUE)
    #print kh
    outbuf = ctypes.create_unicode_buffer(1024)
    #print ctypes.byref(outbuf)
    #print ctypes.sizeof(outbuf)
    #return_size = ctypes.c_int32(0)
    REG_MUI_STRING_TRUNCATE = 1
    try:
        result = load_mui_string(
            kh.handle,
            value,
            ctypes.byref(outbuf),
            ctypes.sizeof(outbuf),
            None, #ctypes.byref(return_size),
            REG_MUI_STRING_TRUNCATE,
            None
        )
        if result != 0:
            return None
    except Exception, e:
        logging.error(e)
        return None

    return outbuf.value


def extract_strings_from_dll(dll_filename, output_filename):
    if os.path.isfile(output_filename):
        logging.error("File %s already exists.", output_filename)
        return 0

    h = win32api.LoadLibraryEx(
        dll_filename,
        None,
        win32con.LOAD_LIBRARY_AS_DATAFILE | win32con.DONT_RESOLVE_DLL_REFERENCES)
    if not h:
        return 0

    dll_filename = os.path.basename(dll_filename)

    extracted = 0
    #strings = []

    with open(output_filename, "w+") as output_file:
        #for id in win32api.EnumResourceNames(h, win32con.RT_STRING):
        for id in xrange(0, 9999999):
            try:
                s = win32api.LoadString(h, id)
                if s == "%s":
                    continue
            except Exception, e:
                continue

            s = unicodedata.normalize(
                'NFKD',
                s
                ).encode('ascii', 'ignore').lower()

            if "&" in s:
                s = s.replace("&", "")
            #print id, s
            #strings.append((id, s))
            output_file.write("%d: %s\n" % (id, s))

            extracted += 1

    #with open(output_filename, "w+") as output_file:
    #    output_file.write("\n".join(("%d: %s" % (id, s) for (id, s) in strings)))

    #return len(strings)
    return extracted


if __name__ == "__main__":
    #    print read_mui_string(
    #    winreg.HKEY_CLASSES_ROOT,
    #    "CLSID\\{BA78511A-5B9E-4736-95A4-0497E4BA1D10}",
    #    "InfoTip")

    #get_control_panel_applets()

    #h = win32api.LoadLibraryEx("shell32.dll", None, win32con.LOAD_LIBRARY_AS_DATAFILE | win32con.DONT_RESOLVE_DLL_REFERENCES)
    #s = win32api.LoadString(h, 24399)
    #r = win32api.LoadResource(h, "XML", 20)

    import glob
    import Queue
    import threading
    import psyco
    import sys
    import subprocess
    import win32process

    psyco.full()

    def process_dll(queue, affinity):
        while 1:
            dllfile, outputfile = queue.get()
            p = subprocess.Popen("c:\\python26\\python.exe -OO enso\\contrib\\open\\platform\\win32\\control_panel_win7.py %s %s"
                % (dllfile, outputfile),
                shell=False, bufsize=1024, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            #proc = win32api.OpenProcess(win32con.PROCESS_SET_INFORMATION | win32con.PROCESS_QUERY_INFORMATION, 0, p.pid)
            #paf = win32process.GetProcessAffinityMask(proc)
            #win32process.SetProcessAffinityMask(proc, affinity)
            p.wait()
            out = p.stdout.read().strip()
            if len(out) > 0:
                print out
            err = p.stderr.read().strip()
            if len(err) > 0:
                print err
            #extracted = extract_strings_from_dll(dllfile, outputfile)
            #print "%s: %d" % (dllfile, extracted)
            queue.task_done()


    if len(sys.argv) > 2:
        #print sys.argv
        dllfile = sys.argv[1]
        outputfile = sys.argv[2]
        extracted = extract_strings_from_dll(dllfile, outputfile)
        print "%s: %d" % (dllfile, extracted)
        sys.exit(extracted)

    q = Queue.Queue()

    for dllfile in glob.iglob("c:\\windows\\system32\\*.dll"):
        outputfile = "c:\\tmp\\resourcestrings_%s.txt" % os.path.basename(dllfile).lower()
        q.put((dllfile, outputfile))
    for exefile in glob.iglob("c:\\windows\\system32\\*.exe"):
        outputfile = "c:\\tmp\\resourcestrings_%s.txt" % os.path.basename(exefile).lower()
        q.put((exefile, outputfile))
    for cplfile in glob.iglob("c:\\windows\\system32\\*.cpl"):
        outputfile = "c:\\tmp\\resourcestrings_%s.txt" % os.path.basename(cplfile).lower()
        q.put((cplfile, outputfile))

    for i in xrange(10):
        t = threading.Thread(target=process_dll,args=(q, (i % 2) + 1))
        t.setDaemon(True)
        t.start()

    q.join()

    pass
    #read_task_links_xml(r"C:\develope\python\enso\enso-open-source\enso\contrib\open\platform\win32\shell32_21_XML.xml")

# vim:set tabstop=4 shiftwidth=4 expandtab:
