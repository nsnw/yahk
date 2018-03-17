from yahk.services import Service, Chat
from aiotg import Bot, Chat
import json
import logging
from itertools import count


# Set up logging
logger = logging.getLogger(__name__)
logger.debug("Loading Slack services...")

class Telegram(Service):

    chats = {}

    class TelegramChat(Chat):

        def __init__(self, service, name, channel):
            super().__init__(service, name)

            self.id = "{0}/{1}/{2}".format(
                service.id, channel.server.name, channel.name
            )
            self.channel = channel

        # async def join(self):
        #     self.service.conn.send("JOIN {}".format(self.name))
        #
        async def send(self, message):
            #self.service.conn.send("PRIVMSG {0} :{1}".format(self.name, message))
            await self.service.conn.send_message(self.channel, message)


        async def receive(self, message):
            # Build context
            text = message.content
            author = message.author
            name = author.name

            if author.id == self.service.conn.user.id:
                logger.debug("{0}: Message is from us - ignoring.".format(self.service.id))
            else:
                for bridge in self.bridges:
                    await bridge.receive(text, self, name)

    def __init__(self, bot, id, name, enabled, token):
        super().__init__()

        self.bot = bot
        self.id = id
        self.name = name
        self.enabled = enabled
        self.token = token

        self.logger.info("Initialising Slack bot {0}".format(id))

    def create(self):
        # Create Slack connection
        self.conn = Bot(api_token=self.token)


        # Event registration
        #self.conn.event(self.on_ready)
        #self.conn.event(self.on_message)
        self.conn.add_command(r'.*', self.on_message)

    def start(self):
        if self.enabled:
            self.create()
            return self.conn.loop()

        else:
            logger.info("{0} is currently disabled".format(self.id))
            return

    async def create_chat(self, channel, discord_channel):
        logger.debug("{0} creating chat for {1}".format(self.id, channel['name']))
        chat = self.DiscordChat(self, channel['name'], discord_channel)

        if 'bridges' not in channel:
            bridges = [None]
        else:
            bridges = channel['bridges']

        # Get/create bridges
        for bridge_name in bridges:
            bridge = self.bot.get_bridge(bridge_name)
            bridge.add(chat)
            chat.bridges.append(bridge)

        self.chats[chat.channel.id] = chat
        #await chat.join()
        #await chat.send("Hello {}!".format(chat.name))

    # async def on_join(self, conn, message):
    #     nick = message.prefix.nick
    #     channel = message.parameters[0]
    #     logger.debug("{0}: {1} joined {2}".format(self.id, nick, channel))
    #
    #     if nick == self.nick:
    #         # This is us
    #         logger.debug("{0}: We've joined {1}".format(self.id, channel))
    #         self.chats[channel].joined = True
    #
    # async def log(self, conn, message):
    #     logger.debug("{0}: {1}".format(self.id, message))
    #
    async def on_message(self, chat, match):
        user = chat.sender
        message = chat.message
        chat_details = message['chat']

        logger.debug("{0}: message received: [{1} ({2}, {3})] {4} (@{5}) {6}".format(
            self.id,
            chat_details['title'],
            chat.id,
            chat.type,
            user['first_name'],
            user['username'],
            message['text']
        ))
        #channel = message.channel.id

        #if channel in self.chats:
        #    await self.chats[channel].receive(message)
        #else:
        #    logger.debug("{0}: Ignoring message in unconfigured channel.".format(self.id))

    async def quit(self):
        logger.debug("{0}: Quitting...".format(self.id))
        self.conn.stop()
        logger.debug("{0}: Disconnected!".format(self.id))