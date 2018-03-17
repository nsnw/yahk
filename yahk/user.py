import logging

logger = logging.getLogger(__name__)
logger.debug("Loading user module...")

class User(object):

    def __init__(self, name):
        self.name = name

    