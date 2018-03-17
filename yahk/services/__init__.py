import logging
import yahk.db
from yahk.db.classes import DBService, DBChat, DBUser, DBMessage
from yahk import bot

logger = logging.getLogger(__name__)
logger.debug("Loading services module...")

class Service(object):

    db_type = None
    chat_class = None
    user_class = None
    chat_user_class = None
    message_class = None
    event_class = None

    def __init__(self, bot, id, name, enabled=True):
        self.bot = bot
        self.db = bot.db
        self.id = id
        self.name = name
        self.identifier = self.name
        self.enabled = enabled

        self.db_id = None

        self.chats = {}
        self.users = []

        self.save()

    def save(self):
        # Get or create DB object
        if self.db_id:
            service = self.db.get_service(self.db_type, self.db_id)

            if not service:
                # TODO - make this nicer
                logger.critical("Database entry for service {0} ({1}) not found - potential database inconsistency".format(
                    self.name, self.db_id
                ))
                self.bot.quit()
        else:
            service = self.db.get_service_by_identifier(self.db_type, self.identifier)

        s = self.db.session

        if not service:
            service = self.db_type()

        service.name = self.name
        service.identifier = self.identifier
        s.add(service)
        s.commit()

        self.db_id = service.id

        s.close()

    def add_user(self, user):
        self.users.append(user)
        logger.debug("Added user {0} to {1}".format(user, self))

    def remove_user(self, user):
        if user in self.users:
            self.users.remove(user)
            logger.debug("Removed {0} from {1}".format(user, self))
        else:
            logger.debug("User {0} not in {1}".format(user, self))

    def add_chat(self, chat):
        self.chats[chat.identifier] = chat
        logger.debug("Added chat {0} to {1}".format(chat, self))

    def remove_chat(self, chat):
        if chat.identifier in self.chats:
            del self.chats[chat.identifier]
            logger.debug("Removed {0} from {1}".format(chat, self))
        else:
            logger.debug("Chat {0} not in {1}".format(chat, self))

    def user_by_identifier(self, identifier):
        for user in self.users:
            if identifier == user.identifier:
                logger.debug("Found {0} for {1}".format(user, self))
                return user

        logger.debug("Couldn't find {0} for {1}".format(identifier, self))
        user = self.user_class(self, identifier)
        return user

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

    class ServiceLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['service_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.ServiceLogger(logger, {'service_id': self.id})

class Chat(object):

    db_type = None

    def __init__(self, service, identifier, name=None):

        self.identifier = identifier
        if not name:
            name = identifier

        self.bridges = []
        #self.users = []
        self.chat_users = []
        self._joined = False

        logger.debug("Creating new chat {0} for {1}...".format(name, service.id))
        self.service = service
        self.db = service.db
        self.name = name
        self.id = "{0}/{1}".format(service.id, name)

        self.db_id = None

        self.save()

    def _get_db_object(self) -> DBChat:
        # Get or create DB object
        if self.db_id:
            chat = self.db.get_chat(self.db_type, self.db_id)

            if not chat:
                # TODO - make this nicer
                logger.critical("Database entry for chat {0} ({1}) not found - potential database inconsistency".format(
                    self.name, self.db_id
                ))
                self.service.bot.quit()
        else:
            chat = self.db.get_chat_by_identifier(self.service, self.identifier)

        return chat

    @property
    def dbo(self):
        return self._get_db_object()

    @dbo.setter
    def dbo(self, value):
        s = self.db.session
        logger.debug(s)
        s.add(value)
        s.commit()
        self.db_id = value.id
        s.close()

    def save(self):
        # Get or create DB object
        chat = self.dbo

        s = self.db.session

        if not chat:
            chat = self.db_type()

        chat.name = self.name
        chat.identifier = self.identifier
        chat.service_id = self.service.db_id

        # Handle attributes registered by the child class
        if hasattr(self, 'child_attrs'):
            for attr in self.child_attrs:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    logger.debug("Setting attr {0} ({1}) for {2}...".format(
                        attr, val, self
                    ))
                    setattr(chat, attr, val)

        s.add(chat)
        s.commit()

        self.db_id = chat.id

        s.close()

    def get_chat_user(self, user):
        for chat_user in self.chat_users:
            if chat_user.user == user:
                logger.debug("Found matching chat user {0} {1}".format(self, user))
                return chat_user

        logger.debug("No matching chat user found for {0} {1}, creating...".format(self, user))
        chat_user = self.service.chat_user_class(self.service, self, user)

        return chat_user

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

    @property
    def joined(self):
        return self._joined

    @joined.setter
    def joined(self, value):
        logger.debug("Setting Chat {0}/{1} joined status to {2}".format(self.id, self.name, value))
        self._joined = value

    def add_user(self, chat_user):
        self.chat_users.append(chat_user)

        logger.debug("Added chatuser {0} to {1}".format(chat_user, self))

    def remove_user(self, chat_user):
        if chat_user in self.chat_users:
            self.chat_users.remove(chat_user)

            logger.debug("Removed {0} from {1}".format(chat_user, self))
        else:
            logger.debug("User {0} not in {1}".format(chat_user, self))


    async def send(self, message):
        logger.warning("No send() method provided for service")

    async def receive(self, message):
        logger.warning("No receive() method provided for service")

    class ChatLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['chat_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.ChatLogger(logger, {'chat_id': self.id})

class User(object):

    db_type = None

    def __init__(self, service: Service, name, identifier=None):
        logger.debug("Creating new user {0} for {1}...".format(name, service.id))
        self.service = service
        self.user_chats = []
        self.db = service.bot.db
        self._name = name
        #self._id = "{0}/{1}".format(service.id, name)

        self.db_id = None

        if identifier:
            self.identifier = identifier
        else:
            self.identifier = self.name

        self.save()

    @property
    def id(self):
        return "{0}/{1}".format(self.service.id, self.name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        logger.debug("Changing name of {0} from {1} to {2}".format(
            self, self.name, value
        ))
        self._name = value
        self.save()

    def _get_db_object(self):
        # Get or create DB object
        if self.db_id:
            user = self.db.get_user(self.db_type, self.db_id)

            if not user:
                # TODO - make this nicer
                logger.critical(
                    "Database entry for user {0} ({1}) not found - potential database inconsistency".format(
                        self.name, self.db_id
                    ))
                self.service.bot.quit()
        else:
            user = self.db.get_user_by_identifier(self.service, self.identifier)

        return user

    @property
    def dbo(self):
        return self._get_db_object()

    @dbo.setter
    def dbo(self, value):
        s = self.db.session
        s.add(value)
        s.commit()
        self.db_id = value.id
        s.close()

    def save(self):
        user = self._get_db_object()

        if not user:
            user = self.db_type()

        user.name = self.name
        user.identifier = self.identifier
        user.service_id = self.service.db_id

        # Handle attributes registered by the child class
        if hasattr(self, 'child_attrs'):
            for attr in self.child_attrs:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    logger.debug("Setting attr {0} ({1}) for {2}...".format(
                        attr, val, self
                    ))
                    setattr(user, attr, val)

        self.dbo = user

    def add_chat(self, chat_user):
        self.user_chats.append(chat_user)
        logger.debug("Added chatuser {0} to {1}".format(chat_user, self))

    def remove_chat(self, chat_user):
        if chat_user in self.user_chats:
            self.user_chats.remove(chat_user)
            logger.debug("Removed {0} from {1}".format(chat_user, self))
        else:
            logger.debug("Chat {0} not in {1}".format(chat_user, self))

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

    class UserLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['user_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.UserLogger(logger, {'user_id': self.id})

class ChatUser(object):

    db_type = None

    def __init__(self, service, chat, user):
        logger.debug("Creating new chat/user association for {0} and {1}...".format(chat, user))
        self.service = service
        self.chat = chat
        self.user = user
        self._active = False
        self.db = service.bot.db
        self.db_id = None

        self.save()

    @property
    def id(self):
        return "{0}/{1}/{2}".format(self.service.name, self.chat.name, self.user.name)

    def _get_db_object(self):
        # Get or create DB object
        if self.db_id:
            chat_user = self.db.get_chat_user(self.db_type, self.db_id)

            if not chat_user:
                # TODO - make this nicer
                logger.critical(
                    "Database entry for chatuser {0} and {1} ({2})not found - potential database inconsistency".format(
                        self.chat.name, self.user.name, self.db_id
                    ))
                self.service.bot.quit()
        else:
            chat_user = self.db.get_chat_user_by_chat_user(self.service, self.chat, self.user)

        return chat_user

    @property
    def dbo(self):
        return self._get_db_object()

    @dbo.setter
    def dbo(self, value):
        s = self.db.session
        s.add(value)
        s.commit()
        self.db_id = value.id
        s.close()

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value: bool):
        logger.debug("Setting {0} to {1}".format(self, value))

        if value is True:
            self._active = True
            self.user.add_chat(self)
            self.chat.add_user(self)
        else:
            self._active = False
            self.user.remove_chat(self)
            self.chat.remove_user(self)

        o = self.dbo
        o.active = self._active
        self.dbo = o

    def save(self):
        chat_user = self._get_db_object()

        if not chat_user:
            chat_user = self.db_type()

        chat_user.chat_id = self.chat.db_id
        chat_user.user_id = self.user.db_id

        # Handle attributes registered by the child class
        if hasattr(self, 'child_attrs'):
            for attr in self.child_attrs:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    logger.debug("Setting attr {0} ({1}) for {2}...".format(
                        attr, val, self
                    ))
                    setattr(chat_user, attr, val)

        self.dbo = chat_user

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

    class ChatUserLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['chat_user_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.ChatUserLogger(logger, {'chat_user_id': self.id})

class Message(object):

    db_type = None

    def __init__(self, service, chat, user, message):
        logger.debug("Creating new message...")
        self.service = service
        self.chat = chat
        self.user = user
        self.message = message
        self.db = service.bot.db

        self.db_id = None

        self.save()

    def _get_db_object(self):
        # Get or create DB object
        if self.db_id:
            message = self.db.get_message(self.db_type, self.db_id)

            if not message:
                # TODO - make this nicer
                logger.critical(
                    "Database entry for user {0} ({1}) not found - potential database inconsistency".format(
                        self.message, self.db_id
                    ))
                self.service.bot.quit()
        else:
            message = None

        return message

    def save(self):
        message = self.dbo

        if not message:
            message = self.db_type()

        message.service_id = self.service.db_id
        message.chat_id = self.chat.db_id
        message.user_id = self.user.db_id
        message.message = self.message

        # Handle attributes registered by the child class
        if hasattr(self, 'child_attrs'):
            for attr in self.child_attrs:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    logger.debug("Setting attr {0} ({1}) for {2}...".format(
                        attr, val, self
                    ))
                    setattr(message, attr, val)

        self.dbo = message

    @property
    def dbo(self):
        return self._get_db_object()

    @dbo.setter
    def dbo(self, value):
        s = self.db.session
        s.add(value)
        s.commit()
        self.db_id = value.id
        s.close()

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.db_id)

    class MessageLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['message_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.MessageLogger(logger, {'message_id': self.db_id})

class Event(object):

    db_type = None

    def __init__(self, service, event, new_value=None, old_value=None, chat=None, user=None):
        logger.debug("Creating new event...")
        self.service = service
        self.chat = chat
        self.user = user
        self.event = event
        self.new_value = new_value
        self.old_value = old_value
        self.db = service.bot.db

        self.db_id = None

        self.save()

    def _get_db_object(self):
        # Get or create DB object
        if self.db_id:
            event = self.db.get_event(self.db_type, self.db_id)

            if not event:
                # TODO - make this nicer
                logger.critical(
                    "Database entry for event {0} ({1}) not found - potential database inconsistency".format(
                        self.event, self.db_id
                    ))
                self.service.bot.quit()
        else:
            event = None

        return event

    def save(self):
        event = self.dbo

        if not event:
            event = self.db_type()

        event.service_id = self.service.db_id
        event.chat_id = self.chat.db_id if self.chat else None
        event.user_id = self.user.db_id if self.user else None
        event.event = self.event
        event.new_value = self.new_value
        event.old_value = self.old_value

        # Handle attributes registered by the child class
        if hasattr(self, 'child_attrs'):
            for attr in self.child_attrs:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    logger.debug("Setting attr {0} ({1}) for {2}...".format(
                        attr, val, self
                    ))
                    setattr(event, attr, val)

        self.dbo = event

    @property
    def dbo(self):
        return self._get_db_object()

    @dbo.setter
    def dbo(self, value):
        s = self.db.session
        s.add(value)
        s.commit()
        self.db_id = value.id
        s.close()

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.db_id)

    class EventLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return '[{0}] {1}'.format(self.extra['event_id'], msg), kwargs

    @property
    def logger(self):
        logger = logging.getLogger(str(self.__class__.__module__))
        return self.EventLogger(logger, {'event_id': self.db_id})