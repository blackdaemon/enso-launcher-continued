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

import os
import logging
import pythoncom

from win32com.shell import shell, shellcon

from enso.contrib.open.interfaces import abstractmethod


class _PyShortcut():
    def __init__(self, base, filename=None):
        self._base = base
        self._base_loaded = False
        self._shortcut_type = None

        self.__filename = None
        if filename:
            self.load(filename)

    def load(self, filename = None):
        if filename:
            assert self.__filename is None, "_PyShortcut.load(): Filename can't be changed once it is set."
            self.__filename = filename
        else:
            assert self.__filename, "_PyShortcut.load(): Filename has to be provided at least once."
        try:
            self._base.QueryInterface( pythoncom.IID_IPersistFile ).Load( self.__filename ) #, win32com.storagecon.STGM_READ )
            self._base_loaded = True
        except Exception, e: #IGNORE:W0703
            self._base_loaded = False
            logging.error("Error loading shell-link for file %s", self.__filename)
            logging.error(e)

    def save(self, filename = None):
        if filename:
            assert self.__filename is None, "_PyShortcut.save(): Filename can't be changed once it is set."
            self.__filename = filename
        else:
            assert self.__filename, "_PyShortcut.save(): Filename has to be provided at least once."
        try:
            self._base.QueryInterface( pythoncom.IID_IPersistFile ).Save( self.__filename, 0 )
            self._base_loaded = True
        except Exception, e: #IGNORE:W0703
            self._base_loaded = False
            logging.error("Error saving shell-link for file %s", self.__filename)
            logging.error(e)

    def get_filename(self):
        return self.__filename

    @abstractmethod
    def get_target(self):
        pass

    """
    def get_type(self):
        if not self._base_loaded:
            raise Exception(
                "Shortcut data has not been yet initialized. "
                "Use load(filename) or save(filename) before using get_type()")

        name, ext = os.path.splitext(self._filename)
        if ext.lower() == '.lnk':
            file_path = self._base.GetPath(0)
            if file_path and file_path[0]:
                if os.path.isdir(file_path[0]):
                    self._shortcut_type = SHORTCUT_TYPE_FOLDER
                elif (os.path.splitext(file_path[0])[1].lower()
                    in ('.exe', '.com', '.cmd', '.bat', '.py', '.pyw')):
                    self._shortcut_type = SHORTCUT_TYPE_EXECUTABLE
                else:
                    self._shortcut_type = SHORTCUT_TYPE_DOCUMENT
            else:
                self._shortcut_type = SHORTCUT_TYPE_DOCUMENT
        elif ext.lower() == '.url':
            self._shortcut_type = SHORTCUT_TYPE_URL
        else:
            self._shortcut_type = SHORTCUT_TYPE_DOCUMENT
        return self._shortcut_type

    def __getattr__( self, name ):
        if name != "_base":
            return getattr( self._base, name )

    """


class PyShellLink(_PyShortcut):
    def __init__(self, filename=None):
        base = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink
        )
        _PyShortcut.__init__(self, base, filename)

    """
    def read_custom_properties(self):
        from win32com import storagecon
        FMTID_UserDefinedProperties = "{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"
        FMTID_CustomDefinedProperties = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

        if not pythoncom.StgIsStorageFile(self.get_filename()):
            print "the file is not a storage file!"
            return
        flags = storagecon.STGM_READWRITE  | storagecon.STGM_SHARE_EXCLUSIVE

        stg = pythoncom.StgOpenStorage(self.get_filename(), None, flags)

        try:
            property_set_storage = stg.QueryInterface(pythoncom.IID_IPropertySetStorage)
        except pythoncom.com_error:
            print "No summary information os available"
            return

        user_defined_property_set = property_set_storage.Open(FMTID_UserDefinedProperties, flags)
        custom_defined_property_set = property_set_storage.Open(FMTID_CustomDefinedProperties, flags)

        udps_enum = user_defined_property_set.Enum()
        cdps_enum = custom_defined_property_set.Enum()
        udp = udps_enum.Next(1)
        while udp:
            print 'udp=',udp
            property_name = udp[0]
            property_value = user_defined_property_set.ReadMultiple((property_name[1],))
            if property_name[0] == None:
                print "(property id)%s = %s" % (property_name[1], property_value[0])
            else:
                print "(property_name)%s = %s" % (property_name[0],	property_value[0])
            udp = udps_enum.Next(1)

        cdp = cdps_enum.Next(1)

        while cdp:
            property_name = cdp[0]
            property_value = custom_defined_property_set.ReadMultiple((property_name[1],))
            print 'cdp = ', cdp, 'property_value = ',property_value

        if property_name[0] == None:
            print "(property id)%s = %s" % (property_name[1], property_value[0])
        else:
            print "(property_name)%s = %s" % (property_name[0],	property_value[0])

        cdp = cdps_enum.Next(1)
    """

    def get_target(self):
        # TODO: http://blogs.msdn.com/b/oldnewthing/archive/2010/07/02/10033646.aspx
        target = None
        path = self._base.GetPath(shell.SLGP_UNCPRIORITY)
        if path and path[0]:
            target = path[0]
            #shortcut_type = get_file_type(target)
        else:
            #FIXME: This is hack for .lnk files containing IE web link
            # Why it doesn't use normal .url files?
            # The format is somewhat cryptic, no documentation found anywhere
            #self.read_custom_properties()

            """
            base = pythoncom.CoCreateInstance(
                shell.CLSID_InternetShortcut,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IUniformResourceLocator
            )
            base.QueryInterface( pythoncom.IID_IPersistFile ).Load(self.get_filename())
            try:
                pss = base.QueryInterface(pythoncom.IID_IPropertySetStorage)
            except Exception, e: #IGNORE:W0703
                logging.error(e)
            else:
                try:
                    ps=pss.Open(shell.FMTID_InternetSite)
                except Exception, e: #IGNORE:W0703
                    logging.error(e)
                else:
                    property_ids = [(k,v) for k,v in shellcon.__dict__.items() if k.startswith('PID_INTSITE_')]
                    for pname, pval in property_ids:
                        print pname, ps.ReadMultiple((pval,))[0]

                try:
                    ps=pss.Open(shell.FMTID_Intshcut)
                except Exception, e: #IGNORE:W0703
                    logging.error(e)
                else:
                    for k, v in shellcon.__dict__.items():
                        if k.startswith('PID_IS_'):
                            print k, ps.ReadMultiple((v,))
            """
            idlist = self._base.GetIDList()
            # URL is on 2nd position
            if idlist and len(idlist) > 1:
                # Always in UTF-16 encoding (widechar)
                try:
                    iditem = idlist[1].decode("UTF-16LE")
                except UnicodeDecodeError, e:
                    logging.error(e)
                    try:
                        iditem = idlist[1].decode("UTF-16")
                    except UnicodeDecodeError, e:
                        logging.error(e)
                        try:
                            iditem = idlist[1].decode("UTF-8")
                        except UnicodeDecodeError, e:
                            logging.error(e)
                else:
                    #FIXME: Is this format always same? u"\u8061\x00\x00{URL}\x00\x00"
                    if len(iditem) > 5 and iditem.startswith(u"\u8061"):
                        iditem = iditem[1:].strip(u"\x00")
                        if iditem.startswith(("http://", "https://", "hcp://")):
                            target = iditem
                            #shortcut_type = SHORTCUT_TYPE_URL
        return target

    def get_working_dir(self):
        return self._base.GetWorkingDirectory()

    def set_path(self, path):
        self._base.SetPath(path)

    def set_working_dir(self, workdir):
        self._base.SetWorkingDirectory(workdir)

    def set_icon_location(self, iconloc, idx):
        self._base.SetIconLocation(iconloc, idx)


class PyInternetShortcut(_PyShortcut):
    def __init__(self, filename=None):
        base = pythoncom.CoCreateInstance(
            shell.CLSID_InternetShortcut,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IUniformResourceLocator
        )
        _PyShortcut.__init__(self, base, filename)

    def get_target(self):
        return self._base.GetURL()

    def set_url(self, url):
        self._base.SetURL(url)


class PyShortcutFactory( object ):
    def get_shortcut(self, filename):
        assert os.path.isfile(filename), "Shortcut file doesn't exist: %s" % filename

        _, ext = os.path.splitext(filename)
        if ext == ".lnk":
            return PyShellLink(filename)
        elif ext == ".url":
            return PyInternetShortcut(filename)
        else:
            assert False, "Shortcut file must have .lnk or .url extension: %s" % filename

# vim:set tabstop=4 shiftwidth=4 expandtab: