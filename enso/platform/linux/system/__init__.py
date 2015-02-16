from Folders import *

import subprocess

def startfile(file):
    program = "gnome-open"
    params = file
    command_run = subprocess.call([program, params])
    if command_run != 0:
        program = "/usr/bin/open"
        command_run = subprocess.call([program, params])
