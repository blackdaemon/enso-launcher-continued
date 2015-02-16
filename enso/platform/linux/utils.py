"""
Author : Guillaume "iXce" Seguin
Email  : guillaume@segu.in

Copyright (C) 2008, Guillaume Seguin <guillaume@segu.in>.
All rights reserved.

Author : Pavel Vitis "blackdaemon"
Email  : pavelvitis@gmail.com


Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  3. Neither the name of Enso nor the names of its contributors may
     be used to endorse or promote products derived from this
     software without specific prior written permission.

THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from Xlib.display import Display
import gtk
import os

from enso.utils.memoize import memoized


DE_GNOME = "GNOME"
DE_KDE = "KDE"
DE_UNITY = "Unity"
DE_XFCE = "XFCE"
DE_CINNAMON = "Cinnamon"
DE_MATE = "MATE"
DE_LXDE = "LXDE"
DE_UNKNOWN = None


def get_display ():
    return Display(os.environ["DISPLAY"])

def get_keycode (key, display = None):
    '''Helper function to get a keycode from raw key name'''
    if not display:
        display = get_display ()
    keysym = gtk.gdk.keyval_from_name (key)
    keycode = display.keysym_to_keycode (keysym)
    return keycode

def sanitize_char (keyval):
    '''Sanitize a single character keyval by attempting to convert it'''
    char = unichr (int (keyval))
    if len (char) > 0 and ord (char) > 0 and ord (char) < 65000:
        #print keyval, char
        return char
    return None

@memoized
def detect_desktop_environment():
    """ 
    Detect desktop environment
    Logic taken from https://github.com/alexeevdv/dename
    """
    # Detect GNOME
    rc = os.system("ps -e | grep -E '^.* gnome-session$' > /dev/null")
    if rc == 0:
        return DE_GNOME
    rc = os.system("ps -e | grep -E '^.* kded4$' > /dev/null")
    if rc == 0:
        return DE_KDE
    rc = os.system("ps -e | grep -E '^.* unity-panel$' > /dev/null")
    if rc == 0:
        return DE_UNITY
    rc = os.system("ps -e | grep -E '^.* xfce4-session$' > /dev/null")
    if rc == 0:
        return DE_XFCE
    rc = os.system("ps -e | grep -E '^.* cinnamon$' > /dev/null")
    if rc == 0:
        return DE_CINNAMON
    rc = os.system("ps -e | grep -E '^.* mate-panel$' > /dev/null")
    if rc == 0:
        return DE_MATE
    rc = os.system("ps -e | grep -E '^.* lxsession$' > /dev/null")
    if rc == 0:
        return DE_LXDE
    
    return DE_UNKNOWN


  