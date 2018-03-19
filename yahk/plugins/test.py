from yahk.plugin import Plugin, commands, matches

class TestPlugin(Plugin):

    @commands('test')
    async def test_command(self, args, chat, user, message):
        await chat.send("Test received!")

    @matches('^[A-Z\s\d\W]+$')
    async def all_caps(self, args, chat, user, message):
        await chat.send("STOP SHOUTING")
