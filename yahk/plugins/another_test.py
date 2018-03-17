from yahk.plugin import Plugin, commands, matches

class Example2Plugin(Plugin):

    @commands('test3', 'test4')
    async def another_test_command(self, source, message):
        await source.send("Another test received!")
