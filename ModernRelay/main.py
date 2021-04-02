import asyncio
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from aiosmtpd.controller import Controller
from dotenv import load_dotenv
import confuse

import agents
from relay import ModernRelay
import exceptions

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


async def main(config):
    logger = logging.getLogger("ModernRelay.log")
    try:
        delivery_agent = agents.GraphDeliveryAgent()
        handler = ModernRelay(delivery_agent)
        controller = Controller(handler, port=8025)
        controller.start()
        logger.info(f"SMTP Controller live on {controller.hostname}:{controller.port}!")
    except exceptions.DeliveryAgentException as e:
        logger.exception(f"Failed to create delivery agent!")


if __name__ == "__main__":
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(BASEDIR, 'dev.env'))
    config = confuse.Configuration("ModernRelay", __name__)
    logLevel = config['logLevel'].get()
    get_logger("ModernRelay.log", getattr(logging, logLevel))

    loop = asyncio.get_event_loop()
    loop.create_task(main({}))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
