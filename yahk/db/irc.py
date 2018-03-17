from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean
from yahk.db import DBUser, DBService, DBChat, DBChatUser, DBMessage, DBEvent

class DBIRCUser(DBUser):
    #service_type = IRCService
    #chat_type = IRCChat

    __tablename__ = 'irc_user'
    id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    ident = Column(String)
    host = Column(String)
    real_name = Column(String)
    server = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_user'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBIRCService(DBService):
    #chat_type = IRCChat
    #user_type = IRCUser

    __tablename__ = 'irc_service'
    id = Column(Integer, ForeignKey('service.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_service'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBIRCChat(DBChat):
    #service_type = IRCService
    #user_type = IRCUser

    __tablename__ = 'irc_chat'
    id = Column(Integer, ForeignKey('chat.id'), primary_key=True)
    topic = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_chat'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBIRCChatUser(DBChatUser):
    #service_type = IRCService
    #user_type = IRCUser

    __tablename__ = 'irc_chat_user'
    id = Column(Integer, ForeignKey('chat_user.id'), primary_key=True)
    operator = Column(Boolean, default=False)
    voiced = Column(Boolean, default=False)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_chat_user'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBIRCMessage(DBMessage):

    __tablename__ = 'irc_message'
    id = Column(Integer, ForeignKey('message.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_message'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

class DBIRCEvent(DBEvent):

    __tablename__ = 'irc_event'
    id = Column(Integer, ForeignKey('event.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'irc_event'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)