"""
    Tests for the Command Manager.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import unittest
import os

from enso.commands.manager import CommandObjectRegistry
from enso.commands.manager import CommandAlreadyRegisteredError
from enso.commands.interfaces import CommandExpression


# ----------------------------------------------------------------------------
# Object Registry Unit Tests
# ----------------------------------------------------------------------------

class FakeCommand:
    def __init__( self, name ):
        self.name = name

class RegistryTester( unittest.TestCase ):
    def setUp( self ):
        self.TESTS = range( ord("a"), ord("z") )
        self.TESTS = [ chr(i) for i in self.TESTS ]

        self.registry = CommandObjectRegistry()
        for name in self.TESTS:
            expr = CommandExpression( name )
            self.registry.addCommandObj(  FakeCommand(name), expr )


    def tearDown( self ):
        self.registry = None

    def testAlreadyRegistered( self ):
        for name in self.TESTS:
            expr = CommandExpression( name )
            self.failUnlessRaises( CommandAlreadyRegisteredError,
                                   self.registry.addCommandObj,
                                   FakeCommand(name), expr )

    def testRegistered( self ):
        for name in self.TESTS:
            cmd = self.registry.getCommandObj( name )
            self.failUnlessEqual( name, cmd.name )

        self.failUnlessEqual( set( self.registry.getCommandList() ),
                              set( self.TESTS ) )

    # TODO: Match testing.
    # TODO: Suggestion testing.

        
# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
