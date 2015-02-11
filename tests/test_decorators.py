"""
    Unit tests for enso.utils.decorators.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import unittest

from enso.utils.decorators import finalizeWrapper


# ----------------------------------------------------------------------------
# Example Functions
# ----------------------------------------------------------------------------

def myDec( oldFunc ):
    """
    A decorator.
    """
    def newFunc( *args, **kwargs ):
        return "newFunc", oldFunc( *args, **kwargs )
    return finalizeWrapper( oldFunc, newFunc, "myDec" )

def a():
    "a doc"
    return "a"
def b():
    "b doc"
    return "b"
def c():
    "c doc"
    return "c"
def d():
    "d doc"
    return "d"

class SomeClass:
    def classFunc( self ):
        "classFunc doc"
        return "classFunc"


FUNCS = {
    "a":a,
    "b":b,
    "c":c,
    "d":d,
    "classFunc":SomeClass().classFunc,
    }


# ----------------------------------------------------------------------------
# Unit Tests
# ----------------------------------------------------------------------------

class FinaleWrapperTests( unittest.TestCase ):

    def testAll( self ):
        for funcName in FUNCS:
            func = FUNCS[funcName]
            self.failUnlessEqual( funcName, func() )
            self.failUnlessEqual( funcName, func.__name__ )

            newFunc = myDec( func )
            # The new function has a different return value, though
            # the old value should be contained in the new value.
            self.failIfEqual( funcName, newFunc() )
            self.failUnless( func() in newFunc() )
            # The new function should have the same name.
            self.failUnlessEqual( funcName, newFunc.__name__ )
            # The docstring of the old function should be
            # contained in the docstring of the new function
            self.failUnless( func.__doc__ in newFunc.__doc__ )


# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
