from directories import *

import subprocess
from enso.platform.linux.utils import get_cmd_output


def startfile(file_name):
    program = "gnome-open"
    params = file_name
    status, output = get_cmd_output([program, params])  # subprocess.call([program, params])
    if status != 0:
        program = "/usr/bin/open"
        status, output = get_cmd_output([program, params])  # command_run = subprocess.call([program, params])
    return status, output
