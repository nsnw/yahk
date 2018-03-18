from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, inspect, Table, Column, Integer, String, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
import logging

Base = declarative_base()

#chat_user_table = Table('chat_user', Base.metadata,
#                        Column('chat_id', Integer, ForeignKey('chat.id')),
#                        Column('user_id', Integer, ForeignKey('user.id'))
#                        )

class EqMixin(object):
    def compare_value(self):
        """Return a value or tuple of values to use for comparisons.
        Return instance's primary key by default, which requires that it is persistent in the database.
        Override this in subclasses to get other behavior.
        """
        return inspect(self).identity

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.compare_value() == other.compare_value()

    def __ne__(self, other):
        eq = self.__eq__(other)

        if eq is NotImplemented:
            return eq

        return not eq

    def __hash__(self):
        return hash(self.__class__) ^ hash(self.compare_value())

class DBUser(Base, EqMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    user_type = Column(String)
    service_id = Column(Integer, ForeignKey('service.id'))
    service = relationship("DBService", back_populates="users")
    #chats = relationship("DBChat", secondary=chat_user_table, back_populates="users")
    user_chats = relationship("DBChatUser", back_populates="user")
    name = Column(String)
    identifier = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': user_type
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBChat(Base):
    __tablename__ = 'chat'

    id = Column(Integer, primary_key=True)
    chat_type = Column(String)
    service_id = Column(Integer, ForeignKey('service.id'))
    service = relationship("DBService", back_populates="chats")
    #users = relationship("DBUser", secondary=chat_user_table, back_populates="chats", lazy='joined')
    chat_users = relationship("DBChatUser", back_populates="chat", lazy='joined')
    name = Column(String)
    identifier = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'chat',
        'polymorphic_on': chat_type
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBChatUser(Base):
    __tablename__ = 'chat_user'

    id = Column(Integer, primary_key=True)
    chat_user_type = Column(String)
    chat_id = Column(Integer, ForeignKey('chat.id'))
    chat = relationship("DBChat", back_populates="chat_users", lazy='joined')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("DBUser", back_populates="user_chats", lazy='joined')
    active = Column(Boolean, default=False)

    @property
    def name(self):
        return self.id

    __mapper_args__ = {
        'polymorphic_identity': 'chat_user',
        'polymorphic_on': chat_user_type
    }

class DBService(Base):
    __tablename__ = 'service'

    id = Column(Integer, primary_key=True)
    service_type = Column(String)
    name = Column(String)
    identifier = Column(String)
    users = relationship("DBUser", back_populates="service")
    chats = relationship("DBChat", back_populates="service")

    #me_id = Column(Integer, ForeignKey('user.id'))
    me = relationship("DBUser")

    __mapper_args__ = {
        'polymorphic_identity': 'service',
        'polymorphic_on': service_type
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

class DBMessage(Base):
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True)
    ts = Column(Numeric)
    message_type = Column(String)
    service_id = Column(Integer, ForeignKey('service.id'))
    service = relationship("DBService")
    chat_id = Column(Integer, ForeignKey('chat.id'))
    chat = relationship("DBChat")
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("DBUser")
    message = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'message',
        'polymorphic_on': message_type
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)

class DBEvent(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    ts = Column(Numeric)
    event_type = Column(String)
    service_id = Column(Integer, ForeignKey('service.id'))
    service = relationship("DBService")
    chat_id = Column(Integer, ForeignKey('chat.id'))
    chat = relationship("DBChat")
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("DBUser", foreign_keys=[user_id])
    event = Column(String)
    new_value = Column(String)
    old_value = Column(String)
    target_user_id = Column(Integer, ForeignKey('user.id'))
    target_user = relationship("DBUser", foreign_keys=[target_user_id])

    __mapper_args__ = {
        'polymorphic_identity': 'event',
        'polymorphic_on': event_type
    }

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)


class DBBotUser(Base):
    __tablename__ = 'bot_user'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.name)

