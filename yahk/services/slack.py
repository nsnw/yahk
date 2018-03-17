from yahk.services import Service, Chat, User, ChatUser, Message, Event
from yahk.db.slack import DBSlackService, DBSlackChat, DBSlackUser, DBSlackChatUser, DBSlackMessage, DBSlackEvent
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

    db_type = DBSlackService
    db_chat_type = DBSlackChat
    db_user_type = DBSlackUser
    db_chat_user_type = DBSlackChatUser
    db_message_type = DBSlackMessage
    db_event_type = DBSlackEvent

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
                            await self.service.receive(j)
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

    class SlackChat(Chat):

        def __init__(self, service, channel_id, name=None):
            if not name:
                name = channel_id

            super().__init__(service, channel_id, name)

        @property
        def id(self):
            return "{0}/{1}".format(
                self.service.id, self.name
            )

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

    class SlackUser(User):

        pass

    class SlackChatUser(ChatUser):

        pass

    class SlackMessage(Message):

        pass



    def __init__(self, bot, id, name, enabled, token, channels):
        self.chat_class = self.SlackChat
        self.user_class = self.SlackUser
        self.chat_user_class = self.SlackChatUser
        self.message_class = self.SlackMessage

        super().__init__(bot, id, name, enabled)
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

    async def chat_from_message(self, message):
        if not 'channel' in message:
            self.logger.error("No channel key in message")
            return False

        channel_id = message['channel']
        if channel_id in self.chats:
            chat = self.chats[channel_id]
            self.logger.debug("Found existing chat {0} in service".format(chat))
            return chat

        self.logger.debug("Didn't find chat in service already, creating new object...")
        c = self.SlackChat(self, channel_id)

    async def receive(self, data):
        self.logger.debug(data)

        if data['type'] == 'message':
            pass

    async def on_msg(self, message):
        chat = self.chat_from_message(message)
        pass