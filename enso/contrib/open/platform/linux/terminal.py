def is_known_terminal_executable(exearg):
    if "gnome-terminal" == exearg:
        return True
    return False


def get_configured_terminal():
    """
    Return the configured Terminal object
    """
    return "gnome-terminal"
