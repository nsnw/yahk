import logging

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('yahk.log')
ch = logging.StreamHandler()

fh.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)

long_formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)-12s/%(funcName)-16s\n-> %(message)s')
short_formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')

fh.setFormatter(long_formatter)
ch.setFormatter(short_formatter)

logger.addHandler(fh)
logger.addHandler(ch)

from yahk.bot import Bot
b = Bot()