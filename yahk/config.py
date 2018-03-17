import yaml
import sys
import logging

logger = logging.getLogger(__name__)

class Config(object):

    def __init__(self):
        pass

    def load(self):
        try:
            with open('config.yml', 'r') as f:
                c = f.read()
                self.config = yaml.load(c)
                logger.debug("Config loaded")
        except FileNotFoundError as e:
            logger.critical("Could not find configuration file!")
            sys.exit(1)

    def save(self):
        try:
            with open('config.yml', 'w') as f:
                config_file = yaml.dump(self.config)
                f.write(config_file)
                logger.debug("Config saved")
        except FileNotFoundError as e:
            logger.critical("Could not find configuration file!")
            sys.exit(1)

    @property
    def services(self):
        return list(self.config.keys())