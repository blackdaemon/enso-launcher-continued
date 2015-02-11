"""
    Unit tests for enso.utils.memoize.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import unittest

from enso.utils.memoize import memoized


# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

class TestMemoize( unittest.TestCase ):
    def setUp( self ):
        self.calledCount = 0

    def tearDown( self ):
        pass

    @memoized
    def add( self, a, b ):
        self.calledCount += 1
        return a + b

    def _testPair( self, a, b ):
        for i in range( 100 ):
            self.failUnlessEqual( self.add( a, b ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )
        for i in range( 100 ):
            self.failUnlessEqual( self.add( *[a,b] ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )
        for i in range( 100 ):
            self.failUnlessEqual( self.add( a=a, b=b ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )
        for i in range( 100 ):
            self.failUnlessEqual( self.add( **{"a":a,"b":b} ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )
        for i in range( 100 ):
            self.failUnlessEqual( self.add( a, b=b ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )
        for i in range( 100 ):
            self.failUnlessEqual( self.add( a, **{ "b":b } ), a + b )
            self.failUnlessEqual( self.calledCount, 1 )

    def testNumbers( self ):
        self._testPair( 1, 1 )

    def testTuples( self ):
        self._testPair( (1,) , (2,) )

    @memoized
    def something( self, a ):
        self.calledCount += 1
        return [ a, 1 ]

    def testKwargs( self ):
        def foo(**kwargs):
            pass
        self.assertRaises(
            AssertionError,
            memoized,
            foo
            )

    def testTypes( self ):
        types = [
            "a",
            1,
            1.2,
            ]

        called = 0
        for t in types:
            called += 1
            for i in range( 100 ):
                self.failUnlessEqual( self.something( t ), [t,1] )
                self.failUnlessEqual( self.calledCount, called )


# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
