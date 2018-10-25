__updated__ = "2018-06-20"

import os
import sys
import subprocess

VERSION_PY = """# This file is originally generated from Git information by running version.py.
# Distribution package contains a pre-generated copy of this file.
VERSION = '%s'
"""


def _get_enso_directory():
    """Get Enso root directory absolute path"""
    global __ENSO_DIR
    try:
        # Get cached value
        return __ENSO_DIR
    except NameError:
        # Compute if cached value not exist
        dir_name = os.path.dirname(os.path.realpath(sys.argv[0]))
        if dir_name.endswith("%sscripts" % os.path.sep):
            dir_name = os.path.realpath(os.path.join(dir_name, ".."))
        __ENSO_DIR = dir_name
        return dir_name


def _get_cmd_output(cmd, cwd="."):
    """Return (status, output) of executing cmd in a shell."""
    if sys.platform.startswith("win"):
        p = subprocess.Popen(cmd,
                             cwd=_get_enso_directory(),
                             stdout=subprocess.PIPE)
        stdout = p.communicate()
        return p.returncode, stdout[0].strip() if stdout else ""
    else:
        # On Linux this is much faster approach than using subprocess module
        pipe = os.popen('{ cd "%s"; %s; } 2>&1' % (cwd, cmd), 'r')
        text = pipe.read()
        sts = pipe.close()
        if sts is None:
            sts = 0
        return sts, text.strip() if text else ""


def is_git_repository():
    """Determine if Enso root directory is a Git repository
    Checks for .git directory presence
    """
    return os.path.isdir(os.path.join(_get_enso_directory(), ".git"))


def get_git_dirty_version():
    """Get current version (dirty) of Enso git repository
    Raises:
        Exception
    """
    try:
        rc, stdout = _get_cmd_output(
            "git describe --tags --always --dirty",
            cwd=_get_enso_directory()
        )
        if rc == 0:
            return stdout.strip()
        else:
            raise Exception("Error running command: (%d) %s" % (rc, stdout))
    except Exception as e:
        # It can fail if git command does not exist
        print "Error determining git repo dirty version; %s" % e
        return ""


def get_git_remote_version():
    """Get current remote version (origin/master) of Enso git repository
    """
    try:
        if sys.platform.startswith("win"):
            rc, version = _get_cmd_output(
                'git describe --tags --always origin/master', # | sed -rn "s/-[0-9a-z]+$//p") [$(git show -s --format=%ci origin/master)]"',
                cwd=_get_enso_directory())
            if rc != 0:
                raise Exception("Error running command: (%d) %s" % (rc, version))
            rc, build_time = _get_cmd_output(
                'git show -s --format=%ci origin/master',
                cwd=_get_enso_directory())
            if rc != 0:
                raise Exception("Error running command: (%d) %s" % (rc, build_time))
            return "%s [%s]" % (version, build_time)
        else:
            rc, stdout = _get_cmd_output(
                'echo -n "origin/master $(git describe --tags --always origin/master | sed -rn "s/-[0-9a-z]+$//p") [$(git show -s --format=%ci origin/master)]"',
                cwd=_get_enso_directory())
            if rc == 0:
                return stdout.strip()
            else:
                raise Exception("Error running command: (%d) %s" % (rc, stdout))
    except Exception as e:
        # It can fail if git command does not exist
        print "Error determining git repo remote version; %s" % e
        return ""


def write_version_file(version, file_name):
    #print "Set %s to '%s'" % (file_name, version)
    with open(os.path.join(_get_enso_directory(), "enso", file_name), "w") as fd:
        fd.write(VERSION_PY % version)


def is_git_installed():
    try:
        rc, stdout = _get_cmd_output(
            'git --version',
            cwd=_get_enso_directory())
        return rc == 0 and "git version" in stdout
    except Exception as e:
        return False


def update_version_py():
    if not is_git_repository():
        return
    if not is_git_installed():
        return
    dirty_ver = get_git_dirty_version()
    if dirty_ver:
        write_version_file(dirty_ver, "_version_local.py")
    remote_ver = get_git_remote_version()
    if remote_ver:
        write_version_file(remote_ver, "_version_remote.py")


update_version_py()
