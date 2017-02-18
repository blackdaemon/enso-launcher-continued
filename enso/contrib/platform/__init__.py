# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:
    
import logging
import sys


__impl_class_cache = {}


def get_command_platform_impl(command_name, impl_class_name=None):
    """
    Returns platform specific implementation class for a given command by doing
    import from its correct platform directory.

    Import for the implementation class is equivalent to:

      from enso.contrib.<command_name>.platform.<platform> import <command_name>CommandImpl
      return <command_name>CommandImpl

    so for 'open' command on MacOS platform it would be:

      from enso.contrib.open.platform.osx import OpenCommandImpl
      return OpenCommandImpl

    Supported platform names are 'win32', 'osx' and 'linux'.

    The class name scheme <command_name>CommandImpl can be overriden by
    impl_class_name parameter.

    Importing of the module is done just once, the result is cached for all
    subsequent calls for given command_name and impl_class_name combination.

    Throws:
        enso.platform.PlatformUnsupportedError
        ImportError

    """

    if sys.platform.startswith("win"):
        platform_name = "win32"
    elif any(map(sys.platform.startswith, ("linux", "openbsd", "freebsd", "netbsd"))):
        platform_name = "linux"
    elif sys.platform == "darwin":
        platform_name = "osx"
    else:
        import enso.platform
        raise enso.platform.PlatformUnsupportedError()

    module_package = "enso.contrib.%s.platform.%s" % (command_name, platform_name)
    if not impl_class_name:
        impl_class_name = "%sCommandImpl" % command_name.title()

    __cache_id = "%s.%s" % (module_package, impl_class_name)
    CommandImpl = __impl_class_cache.get(__cache_id, None)
    if CommandImpl:
        return CommandImpl

    logging.info(
        "Importing command platform-specific implementation "
        "\"from %s import %s\""
        % (module_package, impl_class_name)
    )

    try:
        mod = __import__(module_package, globals(), locals(), [], 0)
        components = module_package.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        CommandImpl = getattr(mod, impl_class_name)
    except ImportError, e:
        logging.error(e)
        raise e

    # Cache it for further import
    __impl_class_cache[__cache_id] = CommandImpl
    return CommandImpl
