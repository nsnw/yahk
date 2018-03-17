from yahk.services import Service, Chat
import asyncio
import aiohttp
import websockets
import json
import logging
from itertools import count


# Set up logging
logger = logging.getLogger(__name__)
logger.debug("Loading Slack services...")

class Slack(Service):

    chats = {}

    class SlackChat(Chat):

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

    class SlackAPI(object):

        def __init__(self, service, token):
            self.service = service
            self.token = token
            self._msg_id = count(1)

        async def api_call(self, method, data=None):
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData(data or {})
                form.add_field('token', self.token)

                async with session.post('https://slack.com/api/{0}'.format(method),
                    data=form) as response:
                        if response.status != 200:
                            logger.error("{0}: Failed to make API call to {1}".format(self.service.id, method))
                            return False
                        else:
                            return await response.json()

        async def rtm_start(self):
            self.service.logger.debug("Connecting to Slack RTM websocket...")
            rtm = await self.api_call('rtm.start')

            if not rtm or 'url' not in rtm:
                self.service.enabled = False
                logger.error("{0}: Could not start Slack RTM session".format(self.service.id))
                return False

            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(rtm['url']) as ws:
                    self.socket = ws
                    async for msg in ws:
                        try:
                            self.service.logger.debug("{0}".format(json.loads(msg.data)))
                            j = json.loads(msg.data)
                            if j['type'] == 'message' and j['text'] == 'break':
                                self.service.logger.debug("Break caught.")
                                raise aiohttp.EofStream()
                        except aiohttp.EofStream:
                            self.service.logger.info("Disconnected from Slack RTM stream.")
                            return

        def rtm_send(self, data):
            self.socket.send_str(data)

        def send_message(self, channel, text):
            payload = {
                'type': 'message',
                'id': next(self._msg_id),
                'channel': channel,
                'text': text
            }

            self.rtm_send(payload)


    def __init__(self, bot, id, name, enabled, token, channels):
        super().__init__()

        self.bot = bot
        self.id = id
        self.name = name
        self.enabled = enabled
        self.token = token
        self.channels = channels

        self.logger.info("Initialising Slack bot {0}".format(id))

    async def create(self):
        # Create Slack connection
        self.conn = self.SlackAPI(self, self.token)


        # Event registration
        #self.conn.event(self.on_ready)
        #self.conn.event(self.on_message)

    async def start(self):
        if self.enabled:
            await self.create()
            while self.enabled:
                await self.conn.rtm_start()
                self.logger.warn("Connection to Slack RTM websocket closed.")
        else:
            logger.info("{0} is currently disabled".format(self.id))
            return

    async def on_ready(self):
        await self.connected()

    async def connected(self):
        self.logger.info("Connected!")

        #for channel in self.conn.get_all_channels():
        #    logger.debug("{0}: -> {1}".format(self.id, channel))
        for discord_server in self.conn.servers:
            self.logger.debug("Server: {0} ({1})".format(discord_server.name, discord_server.id))

            # Match returned servers with configured servers
            for server in self.servers:
                logger.debug("{0}: Looking for server with ID {1}...".format(self.id, server['id']))
                if server['id'] == int(discord_server.id):
                    logger.debug("{0}: Found server ID {1} for {2} in configuration (as {3})".format(
                        self.id, discord_server.id, discord_server.name, server['name']
                    ))

                    # Match returned channels with configured channels
                    channels = server['channels']
                    for discord_channel in discord_server.channels:
                        if discord_channel.type != discord.ChannelType.text:
                            # Not a text channel, skipping
                            logger.debug("{0}: {1} is not a text channel (type: {2})".format(
                                self.id, discord_channel.name, discord_channel.type
                            ))
                            continue

                        logger.debug("{0}: Looking for channel with name {1}...".format(
                            self.id, discord_channel.name
                        ))
                        for channel in channels:
                            if discord_channel.name == channel['name']:
                                # Found matching channel
                                logger.debug("{0}: Found channel name {1} in configuration".format(
                                    self.id, discord_channel.name
                                ))
                                await self.create_chat(channel, discord_channel)
                                break

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
    async def on_message(self, message):
        logger.debug("{0}: message received: {1}".format(self.id, message))
        channel = message.channel.id

        if channel in self.chats:
            await self.chats[channel].receive(message)
        else:
            logger.debug("{0}: Ignoring message in unconfigured channel.".format(self.id))

    async def quit(self):
        logger.debug("{0}: Quitting...".format(self.id))
        self.conn.close()
        logger.debug("{0}: Disconnected!".format(self.id))