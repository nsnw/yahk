import uuid
import logging

logger = logging.getLogger(__name__)

class Bridge(object):

    def __init__(self, bot, name=None):
        self.members = []
        self.bot = bot
        if not name:
            self.name = str(uuid.uuid4())
        else:
            self.name = name

        logger.debug("New bridge {0} created.".format(self.name))

    def __del__(self):
        logger.debug("Deleting bridge {0}...".format(self.name))

    def add(self, member):
        logger.debug("Adding {0} to bridge {1}".format(member.name, self.name))
        self.members.append(member)

    def remove(self, member):
        self.members.remove(member)

    async def send(self, message, exclude=None):
        for member in self.members:
            if exclude and member in exclude:
                logger.debug("Excluding {0}...".format(member.name))
            else:
                logger.debug("Sending text to {0}...".format(member.name))
                await member.send(message)

    async def receive(self, text, chat, source):
        logger.debug("Bridge {0} received text from {1}@{2}: {3}".format(
            self.name,
            source,
            chat.id,
            text
        ))

        if self.bot.source_format == 'short':
            source_id = source
        else:
            source_id = "{0}@{1}".format(source, chat.id)

        await self.send("<{0}> {1}".format(
            source_id,
            text
        ), [chat])

        await self.debugtools(text, chat, source)

    async def debugtools(self, text, chat, source):
        recent_message = "{0}/{1}/{2}".format(source, chat.id, text)

        if self.bot.recent.get(recent_message):
            logger.debug("Suppressed duplicate message")
        else:
            if text[0] == self.bot.prefix:
                command = text[1:]

                if command in self.bot.commands:
                    logger.debug("Found command {0}".format(command))
                    await self.bot.commands[command](chat, source)
            # if text == ".chats":
            #     chats = [x.id for x in self.members]
            #     await self.send("[{0}] - {1}".format(self.name, chats))
            # elif text == ".bridge":
            #     await self.send("Current bridge is {0}".format(self.name))
            # elif text == ".whereami":
            #     await self.send("You are at {0}".format(chat.id))
            # elif text == ".bridges":
            #     await self.send("[{0}] - {1}".format(chat.name, chat.bridges))
            # elif text == ".break":
            #     logger.debug("Breakpoint called")
            # elif text == ".quit":
            #     await self.bot.quit()
            # elif text == ".restart":
            #     await self.bot.restart()
            # elif text == ".ping":
            #     await self.send("pong!")

            self.bot.recent[recent_message] = True