"""
    Tests for the enso.utils.strings module.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import random        
import unittest

from enso.utils.strings import smartQuote
from enso.utils.strings import stringRatio
from enso.utils.strings import stringRatioBestMatch
from enso.utils.strings import CLOSE_QUOTE
from enso.utils.strings import OPEN_QUOTE
from enso.utils.strings import CLOSE_SINGLE_QUOTE
from enso.utils.strings import OPEN_SINGLE_QUOTE


# ----------------------------------------------------------------------------
# Unit Tests
# ----------------------------------------------------------------------------

class SmartQuoteTest( unittest.TestCase ):
    NULL_CASES = [
        "I can't.",
        "You're can't.",
        "I'm sick of you're inability.",
        "She's sick of he's being sick.",
        "I've been Elmer's gran-dad.",
        "He's sick of this.",
        ]

    def testNullCases( self ):
        for testString in self.NULL_CASES:
            self.failUnlessEqual( testString,
                                  smartQuote( testString ) )

    CASES = [
        ( "\"ABC\"", OPEN_QUOTE + "ABC" + CLOSE_QUOTE ),
        ( "A\"BC\"", "A" + OPEN_QUOTE + "BC" + CLOSE_QUOTE ),
        ( "A\"B\"C", "A" + OPEN_QUOTE + "B" + CLOSE_QUOTE + "C" ),
        ( "'ABC'",
          OPEN_SINGLE_QUOTE + "ABC" + CLOSE_SINGLE_QUOTE ),
        ( "A'BC'",
          "A" + OPEN_SINGLE_QUOTE + "BC" + CLOSE_SINGLE_QUOTE ),
        ( "A'B'C",
          "A" + OPEN_SINGLE_QUOTE + "B" + CLOSE_SINGLE_QUOTE + "C" ),
        ]

    def testCases( self ):
        for source, target in self.CASES:
            self.failUnlessEqual( target,
                                  smartQuote( source ) )
            

class StringComparisonTests( unittest.TestCase ):
    def setUp( self ):
        random.seed( 0 )
    

    def testRandomIdentities( self ):
        MAX_LENGTH = 30
        CHARS = "abcdefghijklmnopqrstuvwxyz"
        CHARS += CHARS.upper()
        CHARS += "`1234567890-=~!@#$%^&*()_+[]\\{}|;':\",./<>?"
        for i in range( MAX_LENGTH ):
            for j in range( MAX_LENGTH ):
                string = random.sample( CHARS, i )
                string += random.sample( CHARS, j )
                string = "".join( string )
                self.failUnlessEqual( stringRatio( string[:], string[:] ),
                                      1 )


# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
