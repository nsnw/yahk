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
                        self.service.logger.debug("Making API call to {0}...".format(method))
                        if response.status != 200:
                            self.service.logger.error("{0}: Failed to make API call to {1}".format(self.service.id, method))
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
                            self.service.logger.debug("{0}".format(msg.data))
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

        def __init__(self, service, channel_id, name=None, topic=None, purpose=None, deleted=False):
            self.db_type = service.db_chat_type
            self._topic = topic
            self._purpose = purpose
            self._deleted = deleted
            self.child_attrs = ['topic', 'purpose', 'deleted']

            if not name:
                name = channel_id

            self._name = name

            super().__init__(service, channel_id, name)

            self.service.bot.loop.create_task(self._conversations_info())
            #self._conversations_info()

        @property
        def topic(self):
            return self._topic

        @topic.setter
        def topic(self, value):
            self._topic = value
            self.save()

        @property
        def purpose(self):
            return self._purpose

        @purpose.setter
        def purpose(self, value):
            self._purpose = value
            self.save()

        @property
        def deleted(self):
            return self._deleted

        @deleted.setter
        def deleted(self, value):
            self._deleted = value
            self.save()

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

        async def _conversations_info(self):
            response = await self.service.conn.api_call(
                'conversations.info',
                {'channel': self.identifier}
            )

            if 'error' in response and response['error'] == 'channel_not_found':
                self.logger.debug("Channel information not found for {0}".format(self.identifier))
                return False

            self.name = response['channel']['name']

            if 'topic' in response['channel']:
                self.topic = response['channel']['topic']['value']
                self.logger.debug("Set topic to {0}".format(self.topic))

            if 'purpose' in response['channel']:
                self.purpose = response['channel']['purpose']['value']
                self.logger.debug("Set purpose to {0}".format(self.purpose))

            self.logger.debug(response)

    class SlackUser(User):

        def __init__(self, service, user_id, name=None):
            self.db_type = service.db_user_type

            if not name:
                name = user_id

            self._name = name

            super().__init__(service, user_id, name)

            self.service.bot.loop.create_task(self._users_info())

        async def _users_info(self):
            response = await self.service.conn.api_call(
                'users.info',
                {'user': self.identifier}
            )

            self.name = response['user']['name']


    class SlackChatUser(ChatUser):

        def __init__(self, service, chat, user):
            self.db_type = service.db_chat_user_type

            super().__init__(service, chat, user)

    class SlackMessage(Message):
        def __init__(self, service, chat, user, message):
            self.db_type = service.db_message_type

            super().__init__(service, chat, user, message)

    class SlackEvent(Event):

        def __init__(self, service, event, new_value=None, old_value=None, chat=None, user=None):
            self.db_type = service.db_event_type

            super().__init__(service, event, new_value=new_value, old_value=old_value, chat=chat, user=user)

    class SlackTopicEvent(SlackEvent):

        def __init__(self, service, chat, user, topic):
            super().__init__(service, 'topic_set', new_value=topic, old_value=chat.topic, chat=chat, user=user)

    class SlackPurposeEvent(SlackEvent):

        def __init__(self, service, chat, user, purpose):
            super().__init__(service, 'purpose_set', new_value=purpose, old_value=chat.purpose, chat=chat, user=user)

    class SlackJoinEvent(SlackEvent):

        def __init__(self, service, chat, user):
            super().__init__(service, 'user_joined', chat=chat, user=user)

    class SlackLeaveEvent(SlackEvent):

        def __init__(self, service, chat, user):
            super().__init__(service, 'user_left', chat=chat, user=user)

    class SlackInviteEvent(SlackEvent):

        def __init__(self, service, chat, user, invited_user):
            super().__init__(service, 'user_invited', chat=chat, user=user, target_user=invited_user)



    def __init__(self, bot, id, name, enabled, token, channels, team=None, team_id=None, url=None):
        self.chat_class = self.SlackChat
        self.user_class = self.SlackUser
        self.chat_user_class = self.SlackChatUser
        self.message_class = self.SlackMessage

        self.child_attrs = ['token', 'team', 'team_id', 'url']

        super().__init__(bot, id, name, enabled)
        self._token = token
        self._team = team
        self._team_id = team_id
        self._url = url
        self.channels = channels

        self.logger.info("Initialising Slack bot {0}".format(id))

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self.save()

    @property
    def team(self):
        return self._team

    @team.setter
    def team(self, value):
        self._team = value
        self.save()

    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, value):
        self._team_id = value
        self.save()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.save()

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

    async def _auth_test(self):
        response = await self.conn.api_call('auth.test')

        if not response or not response['ok']:
            return False

        return response

    async def chat_from_message(self, message):
        if not 'channel' in message:
            self.logger.error("No channel key in message")
            return False

        channel_id = message['channel']
        c = self.chat_by_identifier(channel_id)
        return c

    async def user_from_message(self, message):
        if not 'user' in message:
            self.logger.error("No user key in message")
            return False

        user_id = message['user']
        u = self.user_by_identifier(user_id)
        return u

    async def receive(self, data):
        self.logger.debug(data)

        if data['type'] == 'hello':
            self.logger.debug("Got hello from Slack RTM API")

            # Request info about ourselves
            response = await self._auth_test()

            if not response:
                self.logger.error("Could not retrieve information about ourselves from the Slack API!")
            else:
                url = response['url']
                team = response['team']
                team_id = response['team_id']
                user_name = response['user']
                user_id = response['user_id']

                user = self.user_by_identifier(user_id)
                user.name = user_name

                self.team = team
                self.team_id = team_id
                self.url = url

                self.me = user

                self.logger.debug("Team is {0} ({1})".format(team, team_id))
                self.logger.debug("URL is {0}".format(url))
                self.logger.debug("We are {0} ({1})".format(user_name, user_id))

        if data['type'] == 'message':
            if 'subtype' in data:
                if data['subtype'] == 'channel_topic':
                    await self.on_topic(data)
                elif data['subtype'] == 'channel_purpose':
                    await self.on_purpose(data)

            else:
                await self.on_message(data)

        if data['type'] == 'user_typing':
            await self.on_user_typing(data)

        if data['type'] == 'member_left_channel':
            await self.on_user_join(data)

        if data['type'] == 'member_joined_channel':
            await self.on_user_left(data)

        if data['type'] == 'channel_created':
            await self.on_channel_created(data)

        if data['type'] == 'channel_deleted':
            await self.on_channel_deleted(data)

    async def get_chat_and_user_from_message(self, message):
        chat = await self.chat_from_message(message)
        user = await self.user_from_message(message)
        chat_user = chat.get_chat_user(user)

        return chat, user, chat_user

    async def on_message(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)

    async def on_user_typing(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)

    async def on_topic(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)
        topic = message['topic']

        self.logger.debug("{0} changed topic in {1} to {2}".format(
            user.name, chat.name, topic
        ))

        chat.topic = topic
        event = self.SlackTopicEvent(self, chat, user, topic)

    async def on_purpose(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)
        purpose = message['purpose']

        self.logger.debug("{0} changed purpose of {1} to {2}".format(
            user.name, chat.name, purpose
        ))

        chat.purpose = purpose
        event = self.SlackPurposeEvent(self, chat, user, purpose)

    async def on_user_join(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)
        chat_user.active = True

        event = self.SlackJoinEvent(self, chat, user)

    async def on_user_left(self, message):
        chat, user, chat_user = await self.get_chat_and_user_from_message(message)
        chat_user.active = False

        event = self.SlackLeaveEvent(self, chat, user)

    async def on_channel_created(self, message):
        # Get the channel ID from the message
        channel_id = message['channel']['id']
        chat = self.chat_by_identifier(channel_id)

        # Get the user ID from the message
        creator_id = message['channel']['creator']
        user = self.user_by_identifier(creator_id)

        self.logger.debug("New channel {0} created by {1}".format(chat.name, user.name))

    async def on_channel_deleted(self, message):
        chat = await self.chat_from_message(message)

        self.logger.debug("Channel {0} deleted".format(chat.name))

    async def on_invite(self, message):
        chat = await self.chat_from_message(message)
        user = await self.user_from_message(message)
        inviter_id = message['inviter']
        inviter = self.user_by_identifier(inviter_id)

        self.logger.debug("User {0} invited to channel {1} by {2}".format(
            user.name, chat.name, inviter.name
        ))
