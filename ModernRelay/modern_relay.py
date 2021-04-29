import asyncio
import logging
import os
import ssl

import confuse
from aiosmtpd.controller import Controller
from dotenv import load_dotenv

import agents
import exceptions
from ModernRelay.common import get_logger, parse_config
from ModernRelay.file_manager import FileManager
from auth import Authenticator
from relay import ModernRelay


async def main(config, peers):
    logger = logging.getLogger("ModernRelay.log")
    try:
        for addr in peers:
            peers[addr]['agent'] = agents.DeliveryAgentBase.create(peers[addr]['agent'])

        tls_context = None
        tls_required = False

        if 'public_key' in config['tls'] and 'private_key' in config['tls']:
            tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            tls_context.load_cert_chain(config['tls']['public_key'], config['tls']['private_key'])

        if 'required' in config['tls']:
            tls_required = config['tls']['required']

        handler = ModernRelay(peers, FileManager(False))
        controller = Controller(
            handler,
            authenticator=Authenticator('modernrelay.db'),
            port=8025,
            hostname='172.16.128.109',
            require_starttls=tls_required,
            tls_context=tls_context)
        controller.start()
        logger.info(f"SMTP Controller live on {controller.hostname}:{controller.port}! "
                    f"Require_STARTTLS: {tls_required}")
    except exceptions.DeliveryAgentException:
        logger.exception("Failed to create delivery agent!")


if __name__ == "__main__":
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(BASEDIR, 'dev.env'))
    conf = confuse.Configuration("ModernRelay", __name__)

    log_level = conf['logging']['log_level'].get()
    log_file_name = conf['logging']['log_file_name'].get()
    get_logger("ModernRelay.log", getattr(logging, log_level), log_file_name)

    server_conf, peers = parse_config(conf)

    loop = asyncio.get_event_loop()
    loop.create_task(main(server_conf, peers))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass