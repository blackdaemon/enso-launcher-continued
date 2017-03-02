__updated__ = "2017-03-01"

import sys
from enso.providers import ProviderUnavailableError


PLATFORM_NAME_WINDOWS = "win"
PLATFORM_NAME_LINUX = "linux"
PLATFORM_NAME_OSX = "osx"

CURRENT_PLATFORM = ""
if sys.platform.startswith("win"):
    CURRENT_PLATFORM = PLATFORM_NAME_WINDOWS
elif sys.platform == "darwin":
    CURRENT_PLATFORM = PLATFORM_NAME_OSX
elif any(
    sys.platform.startswith(p) for p in [
        "linux", "openbsd", "freebsd", "netbsd", ]
):
    CURRENT_PLATFORM = PLATFORM_NAME_LINUX
    

class PlatformUnsupportedError(ProviderUnavailableError):
    """
    Exception that should be raised by a submodule of this package if
    it can't be used because the host is running an unsupported
    platform.
    """
    pass


def ensure_supported_platform(platforms):
    if any(1 for p in platforms if p == CURRENT_PLATFORM):
        return
    raise PlatformUnsupportedError()
