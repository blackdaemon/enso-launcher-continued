import pytest

from enso.commands.manager import CommandManager
from enso.contrib.help import HelpCommand
from enso.contrib.scriptotron.cmdretriever import getCommandsFromObjects
from enso.contrib.scriptotron.adapters import makeCommandFromInfo
from textwrap import dedent


@pytest.yield_fixture(scope="session")
def command_manager():
    command_manager = CommandManager().get()
    
    # Register named command 'enso help'
    named_help_cmd = HelpCommand
    command_manager.registerCommand(
        named_help_cmd.NAME,
        named_help_cmd(None)
    )

    # Register arbitrary postfix command 'enso' with valid argument 'help'
    execGlobals = {}
    exec dedent("""
        def cmd_enso(ensoapi, what):
            pass
        cmd_enso.valid_args = ['about', 'help']
        """) in execGlobals
    commands = getCommandsFromObjects(execGlobals)
    assert len(commands) == 1
    script_help_cmd = makeCommandFromInfo(commands[0], None, None)
    assert script_help_cmd is not None
    command_manager.registerCommand(
        script_help_cmd.NAME,
        script_help_cmd
    )

    yield command_manager
    

def test_getCommand(command_manager):
    # Test longest match
    cmd = command_manager.getCommand("enso help")
    assert cmd
    assert cmd.getName() == "enso help"
    
    cmd = command_manager.getCommand("enso help ")
    assert cmd
    assert cmd.getName() == "enso"

    cmd = command_manager.getCommand("enso help a")
    assert cmd
    assert cmd.getName() == "enso"

    cmd = command_manager.getCommand("enso hel")
    assert cmd
    assert cmd.getName() == "enso"

    cmd = command_manager.getCommand("enso ab")
    assert cmd
    assert cmd.getName() == "enso"


def test_getCommandPrefix(command_manager):
    # Test longest match
    prefix = command_manager.getCommandPrefix("enso help")
    assert prefix
    assert prefix == "enso help "
    
    prefix = command_manager.getCommandPrefix("enso help ")
    assert prefix
    assert prefix == "enso "

    prefix = command_manager.getCommandPrefix("enso help a")
    assert prefix
    assert prefix == "enso "

    prefix = command_manager.getCommandPrefix("enso hel")
    assert prefix
    assert prefix == "enso "

    prefix = command_manager.getCommandPrefix("enso ab")
    assert prefix
    assert prefix == "enso "


if __name__ == '__main__':
    pass
