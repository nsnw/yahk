import logging
import asyncio
import collections
import argparse
import importlib.util
import inspect
import os
from expiringdict import ExpiringDict
from aioconsole import AsynchronousCli, start_interactive_server
from aioconsole.server import parse_server, print_server
from yahk.console import Console
from yahk.config import Config
from yahk.bridge import Bridge
from yahk.db import DB
from yahk.services.irc import IRC
from yahk.plugin import Plugin
#from yahk.services.discord import Discord
from yahk.services.slack import Slack
#from yahk.services.telegram import Telegram

logger = logging.getLogger(__name__)

class Bot(object):

    """ Main bot object """
    def __init__(self):
        self.services = {}
        self.bridges = {}

        self.recent = ExpiringDict(max_len=100, max_age_seconds=1)

        self.prefix = '.'

        self.commands = {}

        self.load_config()

        self.db = DB()

    def load_config(self):
        # Load config
        logger.debug("Loading configuration...")
        self.config = Config()
        self.config.load()

    def setup(self):
        # Set general settings
        if 'source_format' in self.config.config['main']:
            self.source_format = self.config.config['main']['source_format']
        else:
            self.source_format = 'long'

        # Load plugins
        self.load_plugins()

        # Set up console
        logger.debug("Setting up console...")
        self.console = Console(bot=self)

        # Set up services
        logger.debug("Setting up services...")

        # Iterate over configured services
        for service in self.config.services:
            logger.debug("Configuring {0} services...".format(service))

            if service == 'irc':
                for service_name in self.config.config['irc']:
                    service_id = "IRC/{0}".format(service_name)
                    logger.debug("Configuring {0}...".format(service_id))
                    service_details = self.config.config['irc'][service_name]

                    # Configure IRC connection
                    i = IRC(
                        bot=self,
                        id=service_id,
                        name=service_name,
                        enabled=service_details['enabled'] if 'enabled' in service_details else True,
                        hosts=service_details['hosts'],
                        nick=service_details['nick'],
                        real_name=service_details['real_name'],
                        channels=service_details['channels']
                    )

                    self.services[service_id] = i

            # if service == 'discord':
            #     for service_name in self.config.config['discord']:
            #         service_id = "Discord/{0}".format(service_name)
            #         logger.debug("Configuring {0}".format(service_id))
            #         service_details = self.config.config['discord'][service_name]
            #
            #         # Configure Discord connection
            #         d = Discord(
            #             bot=self,
            #             id=service_id,
            #             name=service_name,
            #             enabled=service_details['enabled'] if 'enabled' in service_details else True,
            #             client_id=service_details['client_id'],
            #             client_secret=service_details['client_secret'],
            #             token=service_details['token'],
            #             servers=service_details['servers']
            #         )
            #
            #         self.services[service_id] = d
            #
            if service == 'slack':
                for service_name in self.config.config['slack']:
                    service_id = "Slack/{0}".format(service_name)
                    logger.debug("Configuring {0}".format(service_id))
                    service_details = self.config.config['slack'][service_name]

                    # Configure Discord connection
                    s = Slack(
                        bot=self,
                        id=service_id,
                        name=service_name,
                        enabled=service_details['enabled'] if 'enabled' in service_details else True,
                        token=service_details['token'],
                        channels=service_details['channels']
                    )

                    self.services[service_id] = s
            #
            # if service == 'telegram':
            #     for service_name in self.config.config['telegram']:
            #         service_id = "Telegram/{0}".format(service_name)
            #         logger.debug("Configuring {0}".format(service_id))
            #         service_details = self.config.config['telegram'][service_name]
            #
            #         # Configure Telegram connection
            #         t = Telegram(
            #             bot=self,
            #             id=service_id,
            #             name=service_name,
            #             enabled=service_details['enabled'] if 'enabled' in service_details else True,
            #             token=service_details['token']
            #         )
            #
            #         self.services[service_id] = t

    def start(self):
        # Init event loop
        logger.debug("Initialising event loop...")
        self.loop = asyncio.get_event_loop()

        # Create and start all tasks
        for service_id, service in self.services.items():
            logger.debug("Starting task for {0}...".format(service_id))
            self.loop.create_task(service.start())

        server = self.loop.create_server(
            self.console.create_server, '192.168.16.28', 8001
        )
        self.loop.server = self.loop.run_until_complete(server)


        self.loop.run_forever()

    async def handle_message(self, message, service, context):
        logger.debug("MSG {0}: {1}".format(service.id, message))

    def get_bridge(self, name=None):
        if name and name in self.bridges:
            logger.debug("Bridge {0} already exists.".format(name))
            return self.bridges[name]
        else:
            logger.debug("Creating bridge...")
            bridge = Bridge(self, name)
            print(bridge)
            self.bridges[bridge.name] = bridge
            return bridge

    def delete_bridge(self, bridge):
        name = bridge.name

        if name in self.bridges:
            logger.debug("Deleting bridge {0}...".format(name))
            del self.bridges[name]
            del bridge
            logger.debug("Bridge {0} deleted".format(name))
            return True
        else:
            logger.error("Bridge {0} does not exist!".format(name))
            return False

    async def quit(self):
        for service_name, service in self.services.items():
            logger.debug("Requesting quit from {0}...".format(service_name))
            await service.quit()
            del service

        self.loop.stop()

    def load_plugins(self):
        plugins = {}
        root_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_dir = os.path.join(root_dir, 'plugins')

        for path in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, path)

            if os.path.isfile(plugin_path) and plugin_path.endswith('.py'):
                name = os.path.basename(plugin_path)[:-3]

                logger.debug("Found plugin {0} ({1})".format(name, plugin_path))
                plugins[name] = plugin_path

        commands = []
        for plugin_name in plugins:
            plugin_path = plugins[plugin_name]

            try:
                module_spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)

                for obj in dict.values(vars(module)):
                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                        obj_name = obj.__name__
                        i = obj(self)

                        for o_name in dir(i):
                            o = getattr(i, o_name)
                            if callable(o):
                                if hasattr(o, 'commands'):
                                    #logger.debug("Plugin {0} has function {1} with commands {2}".format(
                                    #    plugin_name, o.__name__, o.commands
                                    #))

                                    for command in o.commands:
                                        logger.debug("Registering {0}.{1} for command {2}".format(
                                            obj_name, o_name, command
                                        ))
                                        self.commands[command] = o

            except Exception as e:
                logger.error("Could not load plugin {0}: {1}".format(plugin_name, e))

        return

    async def restart(self):
        logger.debug("Restarting...")
        self.quit()
        self.load_config()
        self.setup()
        self.start()
