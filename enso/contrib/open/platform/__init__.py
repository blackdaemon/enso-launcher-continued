# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:

import sys


if sys.platform.startswith("win"):
    from enso.contrib.open.platform import win32
    OpenCommandImpl = win32.OpenCommandImpl
elif any(map(sys.platform.startswith, ("linux", "openbsd", "freebsd", "netbsd"))):
    from enso.contrib.open.platform import linux
    OpenCommandImpl = linux.OpenCommandImpl
elif sys.platform == "darwin":
    from enso.contrib.open.platform import osx
    OpenCommandImpl = osx.OpenCommandImpl
else:
    import enso.platform
    raise enso.platform.PlatformUnsupportedError()
