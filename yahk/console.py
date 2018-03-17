import logging
import asyncio
import argparse
from aioconsole import AsynchronousConsole, AsynchronousCli

logger = logging.getLogger(__name__)

class Console(object):

    def __init__(self, bot):
        self.bot = bot
        self.sessions = []

        logger.debug("Console initialised")

    def broadcast(self, message, skip_source=None):
        for session in self.sessions:
            if skip_source and session is skip_source:
                logger.debug("Skipping session since it is our source")
                continue
            session.write('{0}\n'.format(message))

    def create_server(self):
        s = self.Server(self)
        return s

    class Server(asyncio.Protocol):
        def __init__(self, console):
            self.transport = None
            self.bridges = []
            self.console = console
            logger.debug("New Server instance created")

        def _fmt(self, message):
            return bytes(message, encoding='UTF-8')

        def _decode(self, data):
            return data.decode()

        def _prompt(self):
            self.write('yahk> ')

        def _banner(self):
            self.write('Welcome to the Yahk debug console!\n\n')

        def write(self, message):
            self.transport.write(self._fmt(message))

        def write_line(self, message):
            self.write('{0}\n'.format(message))

        def disconnect(self):
            logger.debug("Client disconnected")

        def connection_made(self, transport):
            self.transport = transport
            self.remote_ip, self.remote_port = transport.get_extra_info('peername')
            self.id = 'Console/{0}-{1}'.format(self.remote_ip, self.remote_port)
            self.name = self.id
            logger.debug("Client connected - {0}:{1}".format(self.remote_ip, self.remote_port))
            self.console.sessions.append(self)
            #self.transport.write(bytes(str(self.console.sessions), encoding='UTF-8'))
            self._banner()
            self._prompt()
            self.console.broadcast("New client connected", skip_source=self)

        def show_services(self):
            self.write_line('Current services:')

            for service_id in self.console.bot.services:
                service = self.console.bot.services[service_id]
                self.write_line(' - {0} ({1})'.format(
                    service_id,
                    'enabled' if service.enabled else 'disabled'
                ))

        def show_bridges(self):
            self.write_line('Current bridges:')

            for bridge_name in self.console.bot.bridges:
                bridge = self.console.bot.bridges[bridge_name]
                self.write_line(' - {0}'.format(bridge_name))
                for chat in bridge.members:
                    self.write_line('   - {0} ({1})'.format(chat.name, chat.id))

        def show_connected_bridges(self):
            self.write_line('Current connected bridges:')

            for bridge in self.bridges:
                self.write_line(' - {0}'.format(bridge.name))
                for chat in bridge.members:
                    self.write_line('   - {0} ({1})'.format(chat.name, chat.id))

        def join_bridge(self, bridge_name):
            if bridge_name not in self.console.bot.bridges:
                self.write_line('Bridge name {0} not found.'.format(bridge_name))
            else:
                bridge = self.console.bot.bridges[bridge_name]
                bridge.add(self)
                self.bridges.append(bridge)

        def leave_bridge(self, bridge_name):
            if bridge_name not in self.console.bot.bridges:
                self.write_line('Bridge name {0} not found.'.format(bridge_name))
            else:
                bridge = self.console.bot.bridges[bridge_name]
                bridge.remove(self)

        def data_received(self, data):
            logger.debug('Data received: {0}'.format(data))

            decoded_data = data.decode().rstrip('\r\n')
            cmd = decoded_data.split(' ')
            logger.debug('Command: {0}'.format(cmd))

            if cmd[0] == "services":
                self.show_services()
            elif cmd[0] == "bridges":
                self.show_bridges()
            elif cmd[0] == "shutdown":
                asyncio.ensure_future(self.console.bot.quit())
            elif cmd[0] == "join_bridge":
                if len(cmd) < 2:
                    self.write_line('Missing argument to join_bridge')
                else:
                    self.join_bridge(cmd[1])
            elif cmd[0] == "leave_bridge":
                if len(cmd) < 2:
                    self.write_line('Missing argument to leave_bridge')
                else:
                    self.leave_bridge(cmd[1])
            elif cmd[0] == "connected_bridges":
                self.show_connected_bridges()
            elif cmd[0] == "send":
                _, message = decoded_data.split(' ', 1)
                self.send_to_bridges(message)

            self._prompt()

        def connection_lost(self, exc):
            logger.debug("Connection lost")
            self.console.sessions.remove(self)

        async def send(self, message):
            self.write_line(message)

        def send_to_bridges(self, message):
            for bridge in self.bridges:
                asyncio.ensure_future(
                    bridge.receive(message, self, 'Console')
                )
