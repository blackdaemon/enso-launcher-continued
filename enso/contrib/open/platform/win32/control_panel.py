import ctypes
import logging
import os
import sys
from contextlib import contextmanager
from ctypes import wintypes

import win32api


class ControlPanelInfo(object):
    CPL_INIT = 1
    CPL_GETCOUNT = 2
    CPL_INQUIRE = 3
    CPL_EXIT = 7
    CPL_NEWINQUIRE = 8

    class NEWCPLINFO(ctypes.Structure):
        class _NEWCPLINFO_UNION(ctypes.Union):
            class _NEWCPLINFO_A(ctypes.Structure):
                # ANSI version
                _fields_ = [
                    ('szName', ctypes.c_char * 32), # array [0..31] of CHAR short name
                    ('szInfo', ctypes.c_char * 64), # array [0..63] of CHAR long name (status line)
                    ('szHelpFile', ctypes.c_char * 128) # array [0..127] of CHAR path to help file to use
                    ]

            class _NEWCPLINFO_W(ctypes.Structure):
                # Unicode version
                _fields_ = [
                    ('szName', ctypes.c_wchar * 32), # array [0..31] of CHAR short name
                    ('szInfo', ctypes.c_wchar * 64), # array [0..63] of CHAR long name (status line)
                    ('szHelpFile', ctypes.c_wchar * 128) # array [0..127] of CHAR path to help file to use
                ]

            # Union of ANSI and Unicode version
            _fields_ = [
                ('szStringsW', _NEWCPLINFO_W),
                ('szStringsA', _NEWCPLINFO_A)
            ]

        _fields_ = [
            ('dwSize', wintypes.DWORD),
            ('dwFlags', wintypes.DWORD),
            ('dwHelpContext', wintypes.DWORD), # help context to use
            ('lData', ctypes.c_void_p), # LONG_PTR user defined data
            ('hIcon', wintypes.HANDLE), # icon to use, this is owned by CONTROL.EXE (may be deleted)
            ('u', _NEWCPLINFO_UNION)
        ]

    class CPLINFO(ctypes.Structure):
        _fields_ = [
            ('idIcon', wintypes.DWORD), # icon resource id, provided by CPlApplet()
            ('idName', wintypes.DWORD), # name string res. id, provided by CPlApplet()
            ('idInfo', wintypes.DWORD), # info string res. id, provided by CPlApplet()
            ('lData', ctypes.c_void_p) # user defined data
        ]

    @contextmanager
    def GetLibrary(self, dll_filename):
        try:
            dll_handle = ctypes.windll.kernel32.LoadLibraryA(dll_filename)
            dll = ctypes.WinDLL(None, handle=dll_handle)
            yield dll_handle, dll
        except Exception, e:
            logging.error("Error loading DLL %s: %s", dll_filename, e)
            raise
        else:
            try:
                ctypes.windll.kernel32.FreeLibrary(dll_handle)
            except Exception, e:
                logging.error("Error freeing DLL %s: %s", dll_filename, e)
            finally:
                del dll
                dll = None
                dll_handle = None


    def get_cplinfo(self, filename):
        with self.GetLibrary(filename) as (cpl_dll_handle, cpl_dll):
            try:
                cpl_applet = cpl_dll.CPlApplet
            except Exception, e:
                logging.error("%s : %s", filename, e)
                return

            try:
                cpl_applet.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.LPARAM, ctypes.c_void_p]
                try:
                    if cpl_applet(0, self.CPL_INIT, 0, 0) == 0:
                        pass
                except Exception, e:
                    logging.error("1: %s %s", filename, e)

                try:
                    dialog_cnt = cpl_applet(0, self.CPL_GETCOUNT, 0, 0)
                except Exception, e:
                    logging.error("2: %s %s", filename, e)
                if dialog_cnt == 0:
                    return
                if not 0 < dialog_cnt <= 20:
                    logging.warning("Suspicious dialog count for %s: %d" % (filename, dialog_cnt))
                    return

                for dialog_i in range(0, dialog_cnt):
                    newcplinfo = self.NEWCPLINFO()
                    newcplinfo.dwSize = 0
                    try:
                        cpl_applet(0, self.CPL_NEWINQUIRE, dialog_i, ctypes.byref(newcplinfo))
                    except Exception, e:
                        logging.error("3: %s %s", filename, e)

                    name = None
                    info = None
                    if newcplinfo.dwSize > 0:
                        if newcplinfo.dwSize == 244:
                            # Descriptions are in ANSI
                            name = newcplinfo.u.szStringsA.szName.decode(sys.getfilesystemencoding())
                            info = newcplinfo.u.szStringsA.szInfo.decode(sys.getfilesystemencoding())
                        else:
                            # Descriptions are in Unicode
                            name = unicode(newcplinfo.u.szStringsW.szName) #.decode("utf-8")
                            info = unicode(newcplinfo.u.szStringsW.szInfo) #.decode("utf-8")

                    if not name and not info:
                        cplinfo = self.CPLINFO()
                        try:
                            cpl_applet(0, self.CPL_INQUIRE, dialog_i, ctypes.byref(cplinfo))
                        except Exception, e:
                            logging.error("4: %s %s", filename, e)

                        handle = None
                        result = None
                        try:
                            name = win32api.LoadString(cpl_dll_handle, cplinfo.idName).strip(" \n\0")
                            info = win32api.LoadString(cpl_dll_handle, cplinfo.idInfo).strip(" \n\0")
                        finally:
                            pass

                    result = (
                        os.path.basename(filename),
                        name,
                        info,
                        dialog_i)
                    yield result
            finally:
                try:
                    cpl_applet(0, self.CPL_EXIT, 0, 0)
                except Exception, e:
                    logging.error("5: %s %s", filename, e)


# vim:set tabstop=4 shiftwidth=4 expandtab:
