"""
    Tester file for Suggestion objects (including auto-completions).
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import unittest

from enso.commands import suggestions


# ----------------------------------------------------------------------------
# Unit Tests
# ----------------------------------------------------------------------------

class SuggestionBasicTests( unittest.TestCase ):
    SOURCE = "abcd"
    SUGGESTIONS = [
        ( "zabcd", "<ins>z</ins>abcd" ),
        ( "azbcd", "a<ins>z</ins>bcd" ),
        ( "abzcd", "ab<ins>z</ins>cd" ),
        ( "abczd", "abc<ins>z</ins>d" ),
        ( "abcdz", "abcd<ins>z</ins>" ),
        ( "zbcd", "<alt>z</alt>bcd" ),
        ( "azcd", "a<alt>z</alt>cd" ),
        ( "abzd", "ab<alt>z</alt>d" ),
        ( "abcz", "abc<alt>z</alt>" ),
        ]

    SUGGESTIONS_SHORT = [
        ( "abc", "abc" ),
        ( "azd", "a<alt>z</alt>d" ),
        ]

    SUGGESTIONS_SORT = [
        ( "abcdz", "abcd<ins>z</ins>" ),
        ( "abcdzz", "abcd<ins>zz</ins>" ),
        ( "abcdzzz", "abcd<ins>zzz</ins>" ),
        ( "abcdzzzz", "abcd<ins>zzzz</ins>" ),
        ( "abcdzzzzz", "abcd<ins>zzzzz</ins>" ),
        ( "abcdzzzzzz", "abcd<ins>zzzzzz</ins>" ),
        ( "abcdzzzzzzz", "abcd<ins>zzzzzzz</ins>" ),
        ( "abcdzzzzzzzz", "abcd<ins>zzzzzzzz</ins>" ),
        ]

    def testSuggestions( self ):
        for text, xmlText in self.SUGGESTIONS:
            sugg = suggestions.Suggestion( self.SOURCE, text )
            self.failUnlessEqual( sugg.toText(), text )
            self.failUnlessEqual( sugg.toXml(), xmlText )
            self.failUnlessEqual( sugg.getSource(), self.SOURCE )

    def testComparison( self ):
        aSugg = suggestions.Suggestion( self.SOURCE,
                                        self.SUGGESTIONS_SORT[0][0] )
        bSugg = suggestions.Suggestion( self.SOURCE,
                                        self.SUGGESTIONS_SORT[1][0] )
        cSugg = suggestions.Suggestion( self.SOURCE,
                                        self.SUGGESTIONS_SORT[1][0] )

        self.failUnless( aSugg != bSugg )
        self.failUnless( bSugg != aSugg )
        self.failUnless( bSugg == cSugg )
        self.failUnless( cSugg == bSugg )
        self.failUnless( aSugg != cSugg )
        self.failUnless( cSugg != aSugg )
        
        self.failUnless( cmp( aSugg, bSugg ) != 0 )
        self.failUnless( cmp( bSugg, cSugg ) == 0 )
        self.failUnless( cmp( aSugg, cSugg ) != 0 )

        NOT_SUGGESTIONS = [ None, aSugg.toText(), 0, 1, False ]

        for obj in NOT_SUGGESTIONS:
            self.failIf( aSugg == obj )
            self.failIf( bSugg == obj )
            self.failIf( cSugg == obj )
            
            self.failUnless( aSugg != obj )
            self.failUnless( bSugg != obj )
            self.failUnless( cSugg != obj )

    def testAutoCompletion( self ):
        for sugg in self.SUGGESTIONS_SHORT:
            self.failUnlessRaises( AssertionError,
                                   suggestions.AutoCompletion,
                                   self.SOURCE,
                                   sugg )

        # Make sure we can create empty AutoCompletions
        # We're checking to see whether errors get raised.
        suggestions.AutoCompletion( self.SOURCE, "" )
    

# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
