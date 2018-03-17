from yahk.services import Service, Chat, User, ChatUser, Message, Event
from yahk.db import DBIRCService, DBIRCChat, DBIRCUser, DBIRCChatUser, DBIRCMessage, DBIRCEvent
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.debug("Loading IRC services...")

class IRC(Service):

    db_type = DBIRCService
    db_chat_type = DBIRCChat
    db_user_type = DBIRCUser
    db_chat_user_type = DBIRCChatUser
    db_message_type = DBIRCMessage
    db_event_type = DBIRCEvent

    class IRCChat(Chat):

        def __init__(self, service, name, topic=None):
            self.db_type = service.db_chat_type
            self._topic = topic
            self.child_attrs = ['topic']
            super().__init__(service, name)


        @property
        def topic(self):
            return self._topic

        @topic.setter
        def topic(self, value):
            self._topic = value
            self.save()


        async def join(self):
            self.service.conn.send("JOIN {}".format(self.name))

        async def send(self, message):
            self.service.conn.send("PRIVMSG {0} :{1}".format(self.name, message))

        async def receive(self, message):
            # Build context
            text = message.parameters[1][1:]
            nick = message.prefix.nick
            for bridge in self.bridges:
                await bridge.receive(text, self, nick)

        async def query_users(self):
            self.service.conn.send("WHO {0}".format(self.name))

    class IRCUser(User):

        def __init__(self, service, name, ident=None, host=None, real_name=None, server=None):
            self.db_type = service.db_user_type
            self._ident = ident
            self._host = host
            self._real_name = real_name
            self._server = server
            self.child_attrs = ['ident', 'host', 'real_name', 'server']

            super().__init__(service, name)

        @property
        def ident(self):
            return self._ident

        @ident.setter
        def ident(self, value):
            self._ident = value
            self.save()

        @property
        def host(self):
            return self._host

        @host.setter
        def host(self, value):
            self._host = value
            self.save()

        @property
        def real_name(self):
            return self._real_name

        @real_name.setter
        def real_name(self, value):
            self._real_name = value
            self.save()

        @property
        def server(self):
            return self._server

        @server.setter
        def server(self, value):
            self._server = value
            self.save()

    class IRCChatUser(ChatUser):

        def __init__(self, service, chat, user):
            self.db_type = service.db_chat_user_type
            self._operator = False
            self._voiced = False
            self._child_attrs = ['operator', 'voiced']

            super().__init__(service, chat, user)

        @property
        def operator(self):
            return self._operator

        @operator.setter
        def operator(self, value: bool):
            self._operator = value
            self.logger.debug("Set operator status for {0} to {1}".format(self, value))
            self.save()

        @property
        def voiced(self):
            return self._voiced

        @voiced.setter
        def voiced(self, value: bool):
            self._voiced = value
            self.save()

    class IRCMessage(Message):

        def __init__(self, service, chat, user, message):
            self.db_type = service.db_message_type

            super().__init__(service, chat, user, message)

    class IRCEvent(Event):

        def __init__(self, service, event, new_value=None, old_value=None, chat=None, user=None):
            self.db_type = service.db_event_type

            super().__init__(service, event, new_value=new_value, old_value=old_value, chat=chat, user=user)

    class IRCTopicEvent(IRCEvent):

        def __init__(self, service, chat, user, topic):
            super().__init__(service, 'topic_set', new_value=topic, old_value=chat.topic, chat=chat, user=user)

    class IRCJoinEvent(IRCEvent):

        def __init__(self, service, chat, user):
            super().__init__(service, 'user_joined', chat=chat, user=user)

    class IRCLeaveEvent(IRCEvent):

        def __init__(self, service, chat, user):
            super().__init__(service, 'user_left', chat=chat, user=user)


    def __init__(self, bot, id, name, enabled, hosts, nick, real_name, channels):
        self.chat_class = self.IRCChat
        self.user_class = self.IRCUser
        self.chat_user_class = self.IRCChatUser
        self.message_class = self.IRCMessage

        super().__init__(bot, id, name, enabled)

        # Initialise ourselves
        self.id = id
        self.hosts = hosts
        self.nick = nick
        self.real_name = real_name
        self.channels = channels

        self.logger.info("Initialising IRC server {0}".format(id))
        self.logger.debug("{0}: hosts: {1}, nick: {2}, realname: {3}".format(
            self.name, self.hosts, self.nick, self.real_name
        ))


    async def create(self):
        # Create IRC server connection
        servers = []
        for host in self.hosts:
            servers.append(
                Server(host['host'], host['port'], host['ssl'])
            )
        self.conn = IrcProtocol(
            servers=servers,
            nick=self.nick,
            realname=self.real_name,
            logger=self.logger
        )
        self.conn.register_cap('account-notify')
        self.conn.register('*', self.log)
        self.conn.register('001', self.connected)
        self.conn.register('JOIN', self.on_join)
        self.conn.register('PRIVMSG', self.on_privmsg)
        self.conn.register('TOPIC', self.on_topic)
        self.conn.register('NICK', self.on_nick)
        self.conn.register('PART', self.on_part)
        self.conn.register('KICK', self.on_kick)
        self.conn.register('352', self.on_whoreply)
        self.conn.register('INVITE', self.on_invite)
        self.conn.register('MODE', self.on_mode)
        self.conn.register('332', self.on_topicreply)

    async def start(self):
        if self.enabled:
            await self.create()
            await self.conn.connect()
        else:
            self.logger.info("{0} is currently disabled".format(self.id))
            return

    def connection_lost(self):
        self.logger.debug("Connection lost.")

    async def connected(self, conn, message):
        self.logger.info("Connected!")

        # Join configured channels, and create/register with bridges
        for channel in self.channels:
            self.logger.debug("Joining channel {0}...".format(channel['name']))
            await self.create_chat(channel)

    async def create_chat(self, channel):
        chat = self.IRCChat(self, channel['name'])

        if 'bridges' not in channel:
            bridges = [None]
        else:
            bridges = channel['bridges']

        # Get/create bridges
        for bridge_name in bridges:
            bridge = self.bot.get_bridge(bridge_name)
            bridge.add(chat)
            chat.bridges.append(bridge)

        self.chats[chat.name] = chat
        await chat.join()
        #await chat.send("Hello {}!".format(chat.name))

    async def log(self, conn, message):
        self.logger.debug(message)

    def user_from_message(self, message):
        nick, ident, host = message.prefix
        return self.user_from_tuple(nick, ident, host)

    def user_from_tuple(self, nick, ident, host):
        # Check to see if the service has this user already
        for user in self.users:
            self.logger.debug(user)
            self.logger.debug("Matching {0} = {1}, {2} = {3}, {4} = {5}".format(
                nick, user.name, ident, user.ident, host, user.host
            ))
            if user.name == nick and user.ident == ident and user.host == host:
                self.logger.debug("Found existing user {0} in service".format(user))
                return user

        self.logger.debug("Didn't find user in service already, creating new object...")
        u = self.IRCUser(self, nick, ident, host)
        self.add_user(u)
        return u

    def chat_from_message(self, message):
        name = message.parameters[0]
        return self.chat_from_name(name)

    def chat_from_name(self, name):

        # Check to see if the service has this chat already
        if name in self.chats:
            chat = self.chats[name]
            self.logger.debug("Found existing chat {0} in service".format(chat))
            return chat

        self.logger.debug("Didn't find chat in service already, creating new object...")
        c = self.IRCChat(self, name)
        self.add_chat(c)
        return c

    async def on_join(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)
        chat_user = chat.get_chat_user(user)
        self.logger.debug("{0} joined {1}".format(user.name, chat.name))

        if user.name == self.nick:
            # This is us
            self.logger.debug("We've joined {0}".format(chat.name))
            await chat.query_users()

            # TODO - fix
            self.chats[chat.name].joined = True
        else:
            chat_user.active = True

    async def on_part(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)
        chat_user = chat.get_chat_user(user)
        self.logger.debug("{0} left {1}".format(user.name, chat.name))

        if user.name == self.nick:
            # This is us
            self.logger.debug("We've left {0}".format(chat.name))

            # TODO - fix
            self.chats[chat.name].joined = False
        else:
            chat_user.active = False

    async def on_quit(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)
        chat_user = chat.get_chat_user(user)
        self.logger.debug("{0} left {1}".format(user.name, chat.name))

        if user.name == self.nick:
            # This is us
            self.logger.debug("We've left {0}".format(chat.name))

            # TODO - fix
            self.chats[chat.name].joined = False
        else:
            chat_user.active = False

    async def on_topic(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)
        chat_user = chat.get_chat_user(user)
        topic = message.parameters[1][1:]

        self.logger.debug("{0} changed topic on {1} to {2}".format(
            user.name, chat.name, topic
        ))

        event = self.IRCTopicEvent(self, chat, user, topic)

        chat.topic = topic

    async def on_topicreply(self, conn, message):
        pass

    async def on_nick(self, conn, message):
        user = self.user_from_message(message)
        new_nick = message.parameters[0][1:]

        self.logger.debug("{0} changed nick to {1}".format(
            user.name, new_nick
        ))

        user.name = new_nick


    async def on_privmsg(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)
        msg = self.IRCMessage(self, chat, user, message.parameters[1][1:])

        self.logger.debug("PRIVMSG received")

        await self.chats[chat.name].receive(message)

    async def on_kick(self, conn, message):
        user = self.user_from_message(message)
        chat = self.chat_from_message(message)

        kicked_user = self.user_by_identifier(message.parameters[1])
        kick_message = message.parameters[2][1:]

        self.logger.debug("{0} kicked {1} from {2}".format(
            user.name, kicked_user, chat.name
        ))

        # TODO - fix
        #chat.remove_user(kicked_user)

    async def on_whoreply(self, conn, message):
        chat = self.chat_from_name(message.parameters[1])
        user = self.user_from_tuple(
            message.parameters[5],
            message.parameters[2],
            message.parameters[3]
        )
        user.real_name = message.parameters[7][3:]
        user.server = message.parameters[4]

        chat_user = chat.get_chat_user(user)
        chat_user.active = True
        chat_user.operator = True

    async def on_invite(self, conn, message):
        self.logger.debug(message)

    async def on_mode(self, conn, message):
        self.logger.debug(message)

    async def quit(self):
        self.logger.debug("Quitting...")
        self.conn.quit()
        self.logger.debug("Disconnected!")