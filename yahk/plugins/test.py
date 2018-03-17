from yahk.plugin import Plugin, commands, matches

class ExamplePlugin(Plugin):

    @commands('test', 'test2')
    async def test_command(self, chat, message):
        await chat.send("Test received!")

    @commands('echo')
    async def echo(self, chat, message):
        await chat.send("You said: {0}".format(message[6:]))

    @commands('services')
    async def services(self, chat, message):
        await chat.send("Current services: {0}".format(
            ', '.join(self.bot.services)
        ))

    @commands('bridges')
    async def services(self, chat, message):
        await chat.send("Current bridges: {0}".format(
            ', '.join(self.bot.bridges)
        ))
