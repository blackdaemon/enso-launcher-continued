command_valid_args = ['a', 'b', 'c', 'long']

def cmd_command(ensoapi, param ):
	if param not in command_valid_args:
		ensoapi.display_message("invalid arg for 'command' => '%s'" % param)
	else:
		ensoapi.display_message("command '%s'" % param)

cmd_command.valid_args = command_valid_args

def cmd_command_long(ensoapi, param):
	ensoapi.display_message(u"command_long '%s'" % param)

cmd_command_long.valid_args = ['a', 'b', 'c']

