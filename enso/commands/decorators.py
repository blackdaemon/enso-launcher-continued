# Copyright (c) 2008, Humanized, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso.commands.factories
#
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#
#   Imports
#
# ----------------------------------------------------------------------------
import inspect
import warnings

# ----------------------------------------------------------------------------
#
#   Functions
#
# ----------------------------------------------------------------------------


def getpublicnames(obj):
    "Return the public names in obj.__dict__"
    return set(n for n in vars(obj) if not n.startswith('_'))


def find_common_names(classes):
    "Perform n*(n-1)/2 namespace overlapping checks on a set of n classes"
    n = len(classes)
    names = map(getpublicnames, classes)
    for i in range(0, n):
        for j in range(i + 1, n):
            ci, cj = classes[i], classes[j]
            common = names[i] & names[j]
            if common:
                yield common, ci, cj


class OverridingWarning(Warning):
    pass

                        
# ----------------------------------------------------------------------------
#
#   Decorators
#
# ----------------------------------------------------------------------------

def warn_overriding(cls):
    """
    Print a warning for each public name which is overridden in the class
    hierarchy, unless if is listed in the "override" class attribute.
    """
    override = set(vars(cls).get("override", []))
    ancestors = inspect.getmro(cls)
    if ancestors[-1] is object:  # remove the trivial ancestor <object>
        ancestors = ancestors[:-1]
    for common, c1, c2 in find_common_names(ancestors):
        override = set(vars(c2).get("override", []))
        overridden = ', '.join(common - override - set(["override"]))
        if ',' in overridden:  # for better display of the names
            overridden = '{%s}' % overridden
        if overridden:
            msg = '%s.%s overriding %s.%s' % (
                c1.__name__, overridden, c2.__name__, overridden)
            warnings.warn(msg, OverridingWarning, stacklevel=2)
    return cls
