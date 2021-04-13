import asyncio
import ipaddress
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

import confuse
from aiosmtpd.controller import Controller
from dotenv import load_dotenv

import agents
import exceptions
from auth import Authenticator
from relay import ModernRelay

FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_FILE = "ModernRelay.log"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name, level=logging.DEBUG):
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    logger.propagate = False
    return logger


def parse_peers(config):
    peers = []
    for (peer_name, peer_details) in config['peers'].get().items():
        detail = {}
        if 'cidr_address' in peer_details:
            if '/' in peer_details['cidr_address']:
                detail['cidr_address'] = ipaddress.ip_network(peer_details['cidr_address'])
            else:
                detail['cidr_address'] = ipaddress.ip_network(peer_details['cidr_address'] + "/32")
        else:
            raise Exception("Error parsing configuration! cidr_address is a required field in the config")

        if 'agent' in peer_details:
            detail['agent'] = peer_details['agent']
        else:
            raise Exception("Error parsing configuration! agent is a required field in the config")

        if 'authentication' in peer_details:
            if peer_details['authentication'] == "anonymous":
                detail['authentication'] = peer_details['authentication']
            else:
                raise NotImplementedError("Authentication not implemented yet, please remove it from the config to "
                                          "default to anonymous")
        else:
            detail['authentication'] = "anonymous"

        if 'destination' in peer_details:
            raise NotImplementedError("Destination limits not implemented yet, please remove it from the config to "
                                      "default to all")
        else:
            detail['destination'] = "all"

        peers.append(detail)
    return peers


async def main(config):
    logger = logging.getLogger("ModernRelay.log")
    try:
        peer_map = {}
        for peer in config['peers']:
            peer_map[peer['cidr_address']] = {
                'agent': agents.DeliveryAgentBase.create(peer['agent']),
                'destinations': peer['destination'],
                'authentication': peer['authentication']
            }

        handler = ModernRelay(peer_map)
        controller = Controller(
            handler,
            authenticator=Authenticator('modernrelay.db'),
            port=8025,
            hostname='172.16.128.109')
        controller.start()
        logger.info(f"SMTP Controller live on {controller.hostname}:{controller.port}!")
    except exceptions.DeliveryAgentException:
        logger.exception("Failed to create delivery agent!")


if __name__ == "__main__":
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(BASEDIR, 'dev.env'))
    conf = confuse.Configuration("ModernRelay", __name__)
    logLevel = conf['logLevel'].get()
    get_logger("ModernRelay.log", getattr(logging, logLevel))
    parsed = parse_peers(conf)

    loop = asyncio.get_event_loop()
    loop.create_task(main({"peers": parsed}))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
