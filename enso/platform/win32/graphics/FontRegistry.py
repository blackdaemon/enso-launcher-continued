import win32gui
import os
import re
import atexit
import operator
import _winreg as reg
from struct import *
import Queue
import threading
import logging

from enso.utils.memoize import memoized
import enso.system

FONT_DIR = enso.system.get_system_folder(enso.system.SYSTEMFOLDER_FONTS)
FONT_LIST_REG_KEY = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"
RE_BARE_FONT_NAME = re.compile("^(.*) \\(.*\\)$", re.I)


def not_implemented_yet(f):
    """ Not-Implemented-Yet function decorator """
    def wrap(*args, **kw):
        logging.error("The function '%s' is not implemented yet" % f.__name__)
        raise NotImplementedError, "The function '%s' is not implemented yet" % f.__name__
    return wrap


def synchronized(lock):
    """ Synchronization function decorator """
    def wrap(f):
        def newFunction(*args, **kw):
            while not lock.acquire(False):
                logging.warn("font cache lock acquire() has been blocked")
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return newFunction
    return wrap

_font_detail_cache_lock = threading.Lock()

class FontRegistry:

    __instance = None
    __font_detail_cache = {}

    @classmethod
    def get( cls ):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance


    def __init__(self):
        self.__requests = Queue.Queue()
        self.request_queue = Queue.Queue()
        self._cache_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._name_to_file_cache = {}
        self._active_requests = {}


    def _get_font_file_from_name(self, font_id):
        """
        Return filename of the font identified by font_id
        (font name as seen in Fonts control panel
        """
        assert font_id is not None
        assert len(font_id) > 0

        font_id = font_id.strip().lower()

        font_name, ext = os.path.splitext(font_id)
        if lower(ext) == ".ttf":
            return os.path.normpath(os.path.join(FONT_DIR, font_name, ext))

        # Get the list of all TrueType font files
        font_files = [font_file for font_file
                in os.listdir(FONT_DIR)
                if operator.itemgetter(1)(
                    os.path.splitext(font_file)
                ).lower() == ".ttf"
            ]

        # Narrow font list to probable matches by seeking every font_id
        # word inside the filename
        regexp = re.compile("(" + "|".join(font_id.split(" ")) + ")")
        probable_matches = [
            font for font
            in font_files
            if regexp.search(operator.itemgetter(0)(os.path.splitext(font)).lower())]

        logging.debug("Probable font file matches: " + repr(probable_matches))

        # Search through probable matches first
        for font in probable_matches:
            del font_files[font_files.index(font)]
            font_file = os.path.join(FONT_DIR, font)
            font_name = self._get_font_name_from_file(font_file)
            if font_name and font_name.lower() == font_id:
                return font_file

        # Search the rest of font files (can take a while)
        for font in font_files:
            font_file = os.path.join(FONT_DIR, font)
            font_name = self._get_font_name_from_file(font_file)
            if font_name and font_name.lower() == font_id:
                return font_file

        return None


    def _get_font_name_from_file(self, font_file):
        """
        Open font file and parse it to get the font name
        """
        assert os.path.isfile(font_file)

        font_full_name = None
        f = None
        try:
            # Open in binary mode
            f = open(font_file, 'rb')

            # Get header
            shead = Struct( '>IHHHH' )
            fhead = f.read( shead.size )
            dhead = shead.unpack_from( fhead, 0 )

            # Get font directory
            stable = Struct( '>4sIII' )
            ftable = f.read( stable.size * dhead[ 1 ] )
            for i in range( dhead[1] ): #directory records
                dtable = stable.unpack_from(
                    ftable, i * stable.size)
                if dtable[0]== 'name':
                    break
            assert dtable[0]== 'name'

            # Get name table
            f.seek( dtable[2] ) #at offset
            fnametable= f.read( dtable[3] ) #length
            snamehead= Struct( '>HHH' ) #name table head
            dnamehead= snamehead.unpack_from( fnametable, 0 )

            sname= Struct( '>HHHHHH' )
            for i in range( dnamehead[1] ): #name table records
                dname= sname.unpack_from(
                    fnametable, snamehead.size+ i* sname.size )
                if dname[3]== 4: #key == 4: "full name of font"
                    s= unpack_from(
                        '%is'% dname[4], fnametable,
                        dnamehead[2]+ dname[5] )[0]
                    # Return the font name, test names for different encodings in preferred order
                    if dname[0] == 1 and dname[1] == 0: # Macintosh, Default, English
                        # This one is usually looking best
                        font_full_name = s
                        break
                    elif dname[0] == 0 and dname[1] == 3: # Unicode, Unicode 2.0, English
                        font_full_name = s
                        break
                    elif dname[0] == 3 and dname[1] == 1: # Windows, Version 1.1
                        font_full_name = unicode(s, "UTF-16BE")
                        break
        except Exception, e:
            logging.error(e)
        finally:
            if f:
                f.close()

        return font_full_name


    @synchronized(_font_detail_cache_lock)
    def get_font_detail(self, font_id):
        assert font_id is not None and len(font_id.strip()) > 0

        #while not self.__font_detail_cache_lock(False):
        #    logging.warn("font cache lock acquire() has been blocked"

        font_id = font_id.strip().lower()

        if self.__font_detail_cache.get(font_id):
            #logging.debug("Font cache hit for \"%s\"" % font_id)
            return self.__font_detail_cache[font_id]

        font_info = {}
        reghandle = None
        try:
            reghandle = reg.ConnectRegistry(None, reg.HKEY_LOCAL_MACHINE)
            regkey = reg.OpenKey(reghandle, FONT_LIST_REG_KEY)
            fonts = []
            i = 0
            try:
                while True:
                    font_name, font_file, _ = reg.EnumValue(regkey, i)
                    i += 1

                    _, ext = os.path.splitext(font_file)
                    if ext.lower() != ".ttf":
                        continue

                    font_path = os.path.join(FONT_DIR, font_file)
                    if RE_BARE_FONT_NAME.match(font_name):
                        font_name = RE_BARE_FONT_NAME.match(font_name).group(1)

                    if font_name.lower() == font_id or font_file.lower() == font_id:
                        font_info['names'] = [font_name]
                        font_info['filename'] = font_file
                        font_info['filepath'] = font_path
                        self.__font_detail_cache[font_id] = font_info
                        break
            except Exception, e:
                pass
            """
                    font_name2 = self._get_font_name_from_file(font_path)
                        if font_name2 and font_name != font_name2:
                            font_info['names'].append(font_name2)
            """
        except Exception, e:
            logging.error(e)

        if reghandle is not None:
            try:
                reg.CloseKey(reghandle)
            except:
                pass
            reghandle = None

        return font_info


    @not_implemented_yet
    def get_font_registry(self):
        font_registry = {}
        reghandle = None
        try:
            reghandle = reg.ConnectRegistry(None, reg.HKEY_LOCAL_MACHINE)
            regkey = reg.OpenKey(reghandle, FONT_LIST_REG_KEY)
            i = 0
            try:
                while True:
                    font_name, font_file, _ = reg.EnumValue(regkey, i)
                    font_path = FONT_DIR + "\\" + font_file
                    if os.path.isfile(font_path):
                        #print font_def[0], font_path
                        font_registry[font_name] = (font_name, font_path)
                        font_registry[font_file] = (font_name, font_path)
                    i += 1
            except:
                pass
        except:
            pass

        if reghandle is not None:
            try:
                reg.CloseKey(reghandle)
            except:
                pass
            reghandle = None

        return font_registry
