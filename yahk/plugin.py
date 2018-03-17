
# This borrows heavily from how Sopel uses decorators for plugins, with some minor changes
# See https://github.com/sopel-irc/sopel/blob/master/sopel/module.py

def commands(*commands):

    def add_commands(function):
        if not hasattr(function, "commands"):
            function.commands = []
        function.commands.extend(commands)
        return function

    return add_commands

def matches(value):

    def add_matches(function):
        if not hasattr(function, "matches"):
            function.matches = []
        function.matches.append(value)
        return function

    return add_matches

class Plugin(object):

    def __init__(self, bot):
        self.bot = bot

