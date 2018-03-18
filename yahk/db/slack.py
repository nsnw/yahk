from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean
from yahk.db import DBUser, DBService, DBChat, DBChatUser, DBMessage, DBEvent

class DBSlackUser(DBUser):

    __tablename__ = 'slack_user'
    id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    ident = Column(String)
    host = Column(String)
    real_name = Column(String)
    server = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_user'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBSlackService(DBService):
    #chat_type = SlackChat
    #user_type = SlackUser

    __tablename__ = 'slack_service'
    id = Column(Integer, ForeignKey('service.id'), primary_key=True)
    token = Column(String)
    url = Column(String)
    team = Column(String)
    team_id = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_service'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBSlackChat(DBChat):
    #service_type = SlackService
    #user_type = SlackUser

    __tablename__ = 'slack_chat'
    id = Column(Integer, ForeignKey('chat.id'), primary_key=True)
    topic = Column(String)
    purpose = Column(String)
    deleted = Column(Boolean)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_chat'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBSlackChatUser(DBChatUser):
    #service_type = SlackService
    #user_type = SlackUser

    __tablename__ = 'slack_chat_user'
    id = Column(Integer, ForeignKey('chat_user.id'), primary_key=True)
    operator = Column(Boolean, default=False)
    voiced = Column(Boolean, default=False)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_chat_user'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBSlackMessage(DBMessage):

    __tablename__ = 'slack_message'
    id = Column(Integer, ForeignKey('message.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_message'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

class DBSlackEvent(DBEvent):

    __tablename__ = 'slack_event'
    id = Column(Integer, ForeignKey('event.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'slack_event'
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)