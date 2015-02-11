import os
import sys

from enso.config import DEFAULT_PLATFORMS
from enso.platform import PlatformUnsupportedError

def get_platforms_to_build():
    platforms = []
    for module_name in DEFAULT_PLATFORMS:
        try:
            __import__( module_name )
            platforms.append( module_name.split(".")[-1] )
        except PlatformUnsupportedError:
            pass
    return platforms

for platform in get_platforms_to_build():
    filename = ".".join( ["SConstruct", platform] )
    if os.path.exists( filename ):
        SConscript( filename )
