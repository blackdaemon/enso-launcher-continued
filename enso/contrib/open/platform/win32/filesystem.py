# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:

#
# "jaraco.windows" is written by Jason R. Coombs.  It is licensed under an
# MIT-style permissive license:
# <http://www.opensource.org/licenses/mit-license.php>
#

from __future__ import division
import ctypes
import os
from ctypes import (
    POINTER,
    Structure,
    byref,
    c_int,
    c_short,
    c_size_t,
    c_uint,
    c_uint64,
    c_ushort,
    cast,
    create_string_buffer,
    create_unicode_buffer,
    windll,
    wintypes,
)
from ctypes.wintypes import (
    BOOL,
    BOOLEAN,
    DWORD,
    FILETIME,
    HANDLE,
    HWND,
    LPVOID,
    LPWSTR,
    UINT,
    WCHAR,
    WORD,
)
from itertools import ifilter, imap, izip

from enso.contrib.open.platform.win32.error import WindowsError


MAX_PATH = 260


class WIN32_FIND_DATA(Structure):
    _fields_ = [
        ('file_attributes', DWORD),
        ('creation_time', FILETIME),
        ('last_access_time', FILETIME),
        ('last_write_time', FILETIME),
        ('file_size_words', DWORD * 2),
        ('reserved', DWORD * 2),
        ('filename', WCHAR * MAX_PATH),
        ('alternate_filename', WCHAR * 14),
    ]
LPWIN32_FIND_DATA = POINTER(WIN32_FIND_DATA)


class SECURITY_ATTRIBUTES(Structure):
    _fields_ = (
        ('length', DWORD),
        ('p_security_descriptor', LPVOID),
        ('inherit_handle', BOOLEAN),
    )
LPSECURITY_ATTRIBUTES = POINTER(SECURITY_ATTRIBUTES)

FindFirstFile = windll.kernel32.FindFirstFileW
FindFirstFile.argtypes = (LPWSTR, LPWIN32_FIND_DATA)
FindFirstFile.restype = HANDLE

FindNextFile = windll.kernel32.FindNextFileW
FindNextFile.argtypes = (HANDLE, LPWIN32_FIND_DATA)
FindNextFile.restype = BOOLEAN

GetFileAttributes = windll.kernel32.GetFileAttributesW
GetFileAttributes.argtypes = LPWSTR,
GetFileAttributes.restype = DWORD

GetFinalPathNameByHandle = windll.kernel32.GetFinalPathNameByHandleW
GetFinalPathNameByHandle.argtypes = (
    HANDLE, LPWSTR, DWORD, DWORD,
)
GetFinalPathNameByHandle.restype = DWORD

CreateFile = windll.kernel32.CreateFileW
CreateFile.argtypes = (
    LPWSTR,
    DWORD,
    DWORD,
    LPSECURITY_ATTRIBUTES,
    DWORD,
    DWORD,
    HANDLE,
)
CreateFile.restype = HANDLE

CloseHandle = windll.kernel32.CloseHandle
CloseHandle.argtypes = (HANDLE,)
CloseHandle.restype = BOOLEAN

ERROR_NO_MORE_FILES = 0x12
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_FLAG_BACKUP_SEMANTICS = 0x2000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_SHARE_DELETE = 4
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FSCTL_GET_REPARSE_POINT = 0x900a8
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
INVALID_HANDLE_VALUE = HANDLE(-1).value
IO_REPARSE_TAG_SYMLINK = 0xA000000C
NULL = 0
OPEN_EXISTING = 3
VOLUME_NAME_DOS = 0

LPDWORD = ctypes.POINTER(wintypes.DWORD)
LPOVERLAPPED = wintypes.LPVOID

_DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
_DeviceIoControl.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    LPDWORD,
    LPOVERLAPPED,
]

_DeviceIoControl.restype = wintypes.BOOL

wchar_size = ctypes.sizeof(wintypes.WCHAR)


class REPARSE_DATA_BUFFER(ctypes.Structure):
    _fields_ = [
        ('tag', ctypes.c_ulong),
        ('data_length', ctypes.c_ushort),
        ('reserved', ctypes.c_ushort),
        ('substitute_name_offset', ctypes.c_ushort),
        ('substitute_name_length', ctypes.c_ushort),
        ('print_name_offset', ctypes.c_ushort),
        ('print_name_length', ctypes.c_ushort),
        ('flags', ctypes.c_ulong),
        ('path_buffer', ctypes.c_byte * 1),
    ]

    def get_print_name(self):
        arr_typ = wintypes.WCHAR * (self.print_name_length // wchar_size)
        data = ctypes.byref(self.path_buffer, self.print_name_offset)
        return ctypes.cast(data, ctypes.POINTER(arr_typ)).contents.value

    def get_substitute_name(self):
        arr_typ = wintypes.WCHAR * (self.substitute_name_length // wchar_size)
        data = ctypes.byref(self.path_buffer, self.substitute_name_offset)
        return ctypes.cast(data, ctypes.POINTER(arr_typ)).contents.value


def handle_nonzero_success(result):
    if result == 0:
        raise WindowsError()


def DeviceIoControl(device, io_control_code, in_buffer, out_buffer, overlapped=None):
    if overlapped is not None:
        raise NotImplementedError("overlapped handles not yet supported")

    if isinstance(out_buffer, int):
        out_buffer = ctypes.create_string_buffer(out_buffer)

    in_buffer_size = len(in_buffer) if in_buffer is not None else 0
    out_buffer_size = len(out_buffer)
    assert isinstance(out_buffer, ctypes.Array)

    returned_bytes = wintypes.DWORD()

    res = _DeviceIoControl(
        device,
        io_control_code,
        in_buffer, in_buffer_size,
        out_buffer, out_buffer_size,
        returned_bytes,
        overlapped,
    )

    handle_nonzero_success(res)
    handle_nonzero_success(returned_bytes)

    return out_buffer[:returned_bytes.value]


def _patch_path(path):
    """
    Paths have a max length of api.MAX_PATH characters (260). If a target path
    is longer than that, it needs to be made absolute and prepended with
    \\?\ in order to work with API calls.
    See http://msdn.microsoft.com/en-us/library/aa365247%28v=vs.85%29.aspx for
    details.
    """
    if path.startswith('\\\\?\\'):
        return path
    abs_path = os.path.abspath(path)
    if not abs_path[1] == ':':
        # python doesn't include the drive letter, but \\?\ requires it
        abs_path = os.getcwd()[:2] + abs_path
    return '\\\\?\\' + abs_path


def join(*paths):
    r"""
    Wrapper around os.path.join that works with Windows drive letters.

    >>> join('d:\\foo', '\\bar')
    'd:\\bar'
    """
    paths_with_drives = imap(os.path.splitdrive, paths)
    drives, paths = zip(*paths_with_drives)
    # the drive we care about is the last one in the list
    drive = next(ifilter(None, reversed(drives)), '')
    return os.path.join(drive, os.path.join(*paths))


def resolve_path(target, start=os.path.curdir):
    r"""
    Find a path from start to target where target is relative to start.

    >>> orig_wd = os.getcwd()
    >>> os.chdir('c:\\windows') # so we know what the working directory is

    >>> findpath('d:\\')
    'd:\\'

    >>> findpath('d:\\', 'c:\\windows')
    'd:\\'

    >>> findpath('\\bar', 'd:\\')
    'd:\\bar'

    >>> findpath('\\bar', 'd:\\foo') # fails with '\\bar'
    'd:\\bar'

    >>> findpath('bar', 'd:\\foo')
    'd:\\foo\\bar'

    >>> findpath('\\baz', 'd:\\foo\\bar') # fails with '\\baz'
    'd:\\baz'

    >>> os.path.abspath(findpath('\\bar'))
    'c:\\bar'

    >>> os.path.abspath(findpath('bar'))
    'c:\\windows\\bar'

    >>> findpath('..', 'd:\\foo\\bar')
    'd:\\foo'

    The parent of the root directory is the root directory.
    >>> findpath('..', 'd:\\')
    'd:\\'
    """
    return os.path.normpath(join(start, target))

findpath = resolve_path


def readlink(link):
    """
    readlink(link) -> target
    Return a string representing the path to which the symbolic link points.
    """
    handle = CreateFile(
        link,
        0,
        0,
        None,
        OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )

    if handle == INVALID_HANDLE_VALUE:
        raise WindowsError()

    res = DeviceIoControl(handle, FSCTL_GET_REPARSE_POINT, None, 10240)

    bytes = create_string_buffer(res)
    p_rdb = cast(bytes, POINTER(REPARSE_DATA_BUFFER))
    rdb = p_rdb.contents
    if not rdb.tag == IO_REPARSE_TAG_SYMLINK:
        raise RuntimeError("Expected IO_REPARSE_TAG_SYMLINK, but got %d" % rdb.tag)
    path = rdb.get_substitute_name()
    if not os.path.exists(path):
        path = rdb.get_print_name()
    return rdb.get_print_name()  # path


def find_files(filepath):
    """
    A pythonic wrapper around the FindFirstFile/FindNextFile win32 api.

    >>> root_files = tuple(find_files(r'c:\*'))
    >>> len(root_files) > 1
    True
    >>> root_files[0].filename == root_files[1].filename
    False

    This test might fail on a non-standard installation
    >>> 'Windows' in (fd.filename for fd in root_files)
    True
    """
    handle = None
    try:
        fd = WIN32_FIND_DATA()
        handle = FindFirstFile(filepath, byref(fd))
        while True:
            if handle == INVALID_HANDLE_VALUE:
                raise WindowsError()
            yield fd
            fd = WIN32_FIND_DATA()
            res = FindNextFile(handle, byref(fd))
            if res == 0:  # error
                error = WindowsError()
                if error.code == ERROR_NO_MORE_FILES:
                    break
                else:
                    raise error
    finally:
        # todo: how to close handle when generator is destroyed?
        # hint: catch GeneratorExit
        if handle:
            windll.kernel32.FindClose(handle)


def is_reparse_point(path):
    """
    Determine if the given path is a reparse point.
    """
    res = GetFileAttributes(path)
    if res == INVALID_FILE_ATTRIBUTES:
        raise WindowsError()
    return bool(res & FILE_ATTRIBUTE_REPARSE_POINT)


def is_link(path):
    "Determine if the given path is a symlink"
    return is_reparse_point(path) and is_symlink(path)


def is_symlink(path):
    """
    Assuming path is a reparse point, determine if it's a symlink.

    >>> symlink('foobaz', 'foobar')
    >>> is_symlink('foobar')
    True
    >>> os.remove('foobar')
    """
    path = _patch_path(path)
    try:
        fd = next(find_files(path))
        return fd.reserved[0] == IO_REPARSE_TAG_SYMLINK
    except WindowsError:
        raise


def get_final_path(path):
    """
    For a given path, determine the ultimate location of that path.
    Useful for resolving symlink targets.
    This functions wraps the GetFinalPathNameByHandle from the Windows
    SDK.

    Note, this function fails if a handle cannot be obtained (such as
    for C:\Pagefile.sys on a stock windows system). Consider using
    trace_symlink_target instead.
    """
    hFile = CreateFile(
        path,
        NULL,  # desired access
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,  # share mode
        LPSECURITY_ATTRIBUTES(),  # NULL pointer
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        NULL,
    )

    if hFile == INVALID_HANDLE_VALUE:
        raise WindowsError()

    buf_size = GetFinalPathNameByHandle(hFile, LPWSTR(), 0, VOLUME_NAME_DOS)
    handle_nonzero_success(buf_size)
    buf = create_unicode_buffer(buf_size)
    result_length = GetFinalPathNameByHandle(hFile, buf, len(buf), VOLUME_NAME_DOS)

    assert result_length < len(buf)
    handle_nonzero_success(result_length)
    handle_nonzero_success(CloseHandle(hFile))

    return buf[:result_length]


def trace_symlink_target(link):
    """
    Given a file that is known to be a symlink, trace it to its ultimate
    target.

    Raises TargetNotPresent when the target cannot be determined.
    Raises ValueError when the specified link is not a symlink.
    """

    if not is_symlink(link):
        raise ValueError("Link must point to a symlink on the system")
    while is_symlink(link):
        orig = os.path.dirname(link)
        link = readlink(link)
        link = resolve_path(link, orig)
    return link
