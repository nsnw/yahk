from yahk.plugin import Plugin, commands, matches

class AdminPlugin(Plugin):

    @commands('ping')
    async def test_command(self, args, chat, user, message):
        await chat.send("Test received!")

    @commands('echo')
    async def echo(self, args, chat, user, message):
        await chat.send("You said: {0}".format(' '.join(args)))

    @commands('services')
    async def services(self, args, chat, user, message):
        await chat.send("Current services: {0}".format(
            ', '.join(self.bot.services)
        ))

    @commands('bridges')
    async def services(self, args, chat, user, message):
        await chat.send("Current bridges: {0}".format(
            ', '.join(map(lambda x: self.bot.bridges[x].name, self.bot.bridges))
        ))

    @commands('bridge-name')
    async def bridge_name(self, args, chat, user, message):
        if args:
            bridge_name = args[0]
            chat.bridge.name = bridge_name
            await chat.send("Bridge name changed to {0}".format(bridge_name))
        else:
            await chat.send("No name given!")

    @commands('whoami')
    async def whoami(self, args, bridge_chat, chat_user, message):
        await bridge_chat.send("You are {0} ({1}), in {2} ({3}) on {4}".format(
            chat_user.user.name,
            chat_user.user.identifier,
            bridge_chat.chat.name,
            bridge_chat.chat.identifier,
            bridge_chat.chat.service.name
        ))

    @commands('whereami')
    async def whereami(self, args, bridge_chat, chat_user, message):
        await bridge_chat.send("You are in {0} ({1}), on {2}, part of bridge {3}".format(
            bridge_chat.chat.name,
            bridge_chat.chat.identifier,
            bridge_chat.chat.service.name,
            bridge_chat.bridge.name
        ))

