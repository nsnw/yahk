import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from yahk.db.classes import *

logger = logging.getLogger(__name__)
logger.debug("Loading DB module...")

#Base = declarative_base()

class DB(object):

    def __init__(self):
        self.engine = create_engine(
            'sqlite:///yahk.db',
            connect_args={'check_same_thread': False},
            echo=False
        )
        self.sessionmaker = sessionmaker(bind=self.engine)
        self._destroy()
        Base.metadata.create_all(self.engine)

    def _destroy(self):
        Base.metadata.drop_all(self.engine)

    @property
    def session(self) -> Session:
        return self.sessionmaker()

    def get_bridge(self, db_id):
        s = self.session

        logger.debug("Querying for bridge id: {0}".format(
            db_id
        ))

        try:
            bridge = s.query(DBBridge).filter(DBBridge.id==db_id).one()
            logger.debug("Found service {0}".format(bridge))
            s.close()
            return bridge
        except MultipleResultsFound:
            logger.error("Found multiple bridges with id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No bridge with id {0} found".format(db_id))
            return None

    def get_bridge_by_name(self, name):
        s = self.session

        logger.debug("Querying for bridge name: {0}".format(
            name
        ))

        try:
            bridge = s.query(DBBridge).filter(DBBridge.name==name).one()
            logger.debug("Found bridge {0}".format(bridge))
            s.close()
            return bridge
        except MultipleResultsFound:
            logger.error("Found multiple bridgess with name {0}".format(name))
            raise
        except NoResultFound:
            logger.info("No bridge with name {0} found".format(name))
            return None

    def get_service(self, service_type: DBService, db_id):
        s = self.session

        logger.debug("Querying for service of type: {0}, id: {1}".format(
            service_type, db_id
        ))

        try:
            service = s.query(service_type).filter(service_type.id==db_id).one()
            logger.debug("Found service {0}".format(service))
            s.close()
            return service
        except MultipleResultsFound:
            logger.error("Found multiple services with id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No service with id {0} found".format(db_id))
            return None

    def get_service_by_identifier(self, service_type: DBService, identifier):
        s = self.session

        logger.debug("Querying for service of type: {0}, name: {1}".format(
            service_type, identifier
        ))

        try:
            service = s.query(service_type).filter(service_type.identifier==identifier).one()
            logger.debug("Found service {0}".format(service))
            s.close()
            return service
        except MultipleResultsFound:
            logger.error("Found multiple services with name {0}".format(identifier))
            raise
        except NoResultFound:
            logger.info("No service with {0} found".format(identifier))
            return None

    def get_chat(self, chat_type: DBChat, db_id):
        s = self.session

        logger.debug("Querying for chat of type: {0}, db_id: {1}".format(
            chat_type, db_id
        ))

        try:
            chat = s.query(chat_type).filter(
                chat_type.id == db_id
            ).one()
            logger.debug("Found chat {0}".format(chat))
            s.close()
            return chat
        except MultipleResultsFound:
            logger.error("Found multiple chats with identifier {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No chat with {0} found".format(db_id))
            return None

    def get_chat_by_identifier(self, service, identifier):
        s = self.session
        chat_type = service.db_chat_type
        service_db_id = service.db_id

        logger.debug("Querying for chat of type: {0}, service_db_id: {1}, identifier: {2}".format(
            chat_type, service_db_id, identifier
        ))

        try:
            chat = s.query(chat_type).filter(
                chat_type.service_id==service_db_id
            ).filter(
                chat_type.identifier == identifier
            ).one()
            logger.debug("Found chat {0}".format(chat))
            s.close()
            return chat
        except MultipleResultsFound:
            logger.error("Found multiple chats with identifier {0}".format(identifier))
            raise
        except NoResultFound:
            logger.info("No chat with {0} found".format(identifier))
            return None

    def get_bot_user(self, db_id):
        s = self.session

        logger.debug("Querying for bot user db_id: {0}".format(
            db_id
        ))

        try:
            bot_user = s.query(DBBotUser).filter(
                DBBotUser.id == db_id
            ).one()
            logger.debug("Found user {0}".format(bot_user))
            s.close()
            return bot_user
        except MultipleResultsFound:
            logger.error("Found multiple bot users with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No bot user with db_id {0} found".format(db_id))
            return None

    def get_bot_user_by_name(self, name):
        s = self.session

        logger.debug("Querying for bot user name: {0}".format(
            name
        ))

        try:
            bot_user = s.query(DBBotUser).filter(
                DBBotUser.name == name
            ).one()
            logger.debug("Found bot user {0}".format(bot_user))
            s.close()
            return bot_user
        except MultipleResultsFound:
            logger.error("Found multiple bot users with name {0}".format(
                name
            ))
            raise
        except NoResultFound:
            logger.info("No bot user with identifier {0} found".format(name))
            return None

    def get_user(self, user_type: DBUser, db_id):
        s = self.session

        logger.debug("Querying for user of type: {0}, db_id: {1}".format(
            user_type, db_id
        ))

        try:
            user = s.query(user_type).filter(
                user_type.id == db_id
            ).one()
            logger.debug("Found user {0}".format(user))
            s.close()
            return user
        except MultipleResultsFound:
            logger.error("Found multiple users with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No user with db_id {0} found".format(db_id))
            return None

    def get_user_by_identifier(self, service, identifier):
        s = self.session
        user_type = service.db_user_type
        service_db_id = service.db_id

        logger.debug("Querying for user of type: {0}, service_db_id: {1}, name: {2}".format(
            user_type, service_db_id, identifier
        ))

        try:
            user = s.query(user_type).filter(
                user_type.service_id == service_db_id
            ).filter(
                user_type.identifier == identifier
            ).one()
            logger.debug("Found user {0}".format(user))
            s.close()
            return user
        except MultipleResultsFound:
            logger.error("Found multiple users with identifier {0}".format(
                identifier
            ))
            raise
        except NoResultFound:
            logger.info("No user with identifier {0} found".format(identifier))
            return None

    def get_chat_user(self, chat_user_type: DBChatUser, db_id):
        s = self.session

        logger.debug("Querying for chat_user of type: {0}, db_id: {1}".format(
            chat_user_type, db_id
        ))

        try:
            chat_user = s.query(chat_user_type).filter(
                chat_user_type.id == db_id
            ).one()
            logger.debug("Found chat_user {0}".format(chat_user))
            s.close()
            return chat_user
        except MultipleResultsFound:
            logger.error("Found multiple chat_users with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No chat_user with db_id {0} found".format(db_id))
            return None

    def get_bridge_chat(self, bridge_chat_type: DBBridgeChat, db_id):
        s = self.session

        logger.debug("Querying for bridge_chat of type: {0}, db_id: {1}".format(
            bridge_chat_type, db_id
        ))

        try:
            bridge_chat = s.query(bridge_chat_type).filter(
                bridge_chat_type.id == db_id
            ).one()
            logger.debug("Found bridge_chat {0}".format(bridge_chat))
            s.close()
            return bridge_chat
        except MultipleResultsFound:
            logger.error("Found multiple bridge_chats with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No bridge_chat with db_id {0} found".format(db_id))
            return None

    def get_bridge_chat_by_bridge_chat(self, bridge, chat):
        s = self.session
        bridge_chat_type = DBBridgeChat

        logger.debug("Querying for bridge_chat {0}/{1}".format(
            bridge.name, chat.name
        ))

        try:
            bridge_chat = s.query(bridge_chat_type).filter(
                bridge_chat_type.bridge_id == bridge.db_id
            ).filter(
                bridge_chat_type.chat_id == chat.db_id
            ).one()
            logger.debug("Found user {0}".format(bridge_chat))
            s.close()
            return bridge_chat
        except MultipleResultsFound:
            logger.error("Found multiple bridge_chats with identifier {0} and {1}".format(
                bridge, chat
            ))
            raise
        except NoResultFound:
            logger.info("No bridge_chat with identifier {0} and {1} found".format(bridge, chat))
            return None

    def get_chat_user_by_chat_user(self, service, chat, user):
        s = self.session
        chat_user_type = service.db_chat_user_type
        service_db_id = service.db_id

        logger.debug("Querying for chatuser {0}/{1}".format(
            chat.name, user.name
        ))

        try:
            chat_user = s.query(chat_user_type).filter(
                chat_user_type.chat_id == chat.db_id
            ).filter(
                chat_user_type.user_id == user.db_id
            ).one()
            logger.debug("Found user {0}".format(chat_user))
            s.close()
            return chat_user
        except MultipleResultsFound:
            logger.error("Found multiple chatusers with identifier {0} and {1}".format(
                chat, user
            ))
            raise
        except NoResultFound:
            logger.info("No chatuser with identifier {0} and {1} found".format(chat, user))
            return None

    def get_message(self, message_type: DBMessage, db_id):
        s = self.session

        logger.debug("Querying for message of type: {0}, db_id: {1}".format(
            message_type, db_id
        ))

        try:
            message = s.query(message_type).filter(
                message_type.id == db_id
            ).one()
            logger.debug("Found user {0}".format(message))
            s.close()
            return message
        except MultipleResultsFound:
            logger.error("Found multiple messages with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No message with db_id {0} found".format(db_id))
            return None

    def get_event(self, event_type: DBEvent, db_id):
        s = self.session

        logger.debug("Querying for event of type: {0}, db_id: {1}".format(
            event_type, db_id
        ))

        try:
            event = s.query(event_type).filter(
                event_type.id == db_id
            ).one()
            logger.debug("Found event {0}".format(event))
            s.close()
            return event
        except MultipleResultsFound:
            logger.error("Found multiple events with db_id {0}".format(db_id))
            raise
        except NoResultFound:
            logger.info("No event with db_id {0} found".format(db_id))
            return None