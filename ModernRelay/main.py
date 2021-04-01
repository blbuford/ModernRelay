import asyncio
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from aiosmtpd.controller import Controller
from dotenv import dotenv_values

import agents
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


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    logger.propagate = False
    return logger


async def main(config):
    delivery_agent = agents.GraphDeliveryAgent(config)
    handler = ModernRelay(delivery_agent)
    controller = Controller(handler, port=8025)
    controller.start()
    logger = logging.getLogger("ModernRelay.log")
    logger.info(f"SMTP Controller live on {controller.hostname}:{controller.port}!")


if __name__ == "__main__":
    config = dotenv_values("dev.env")
    logger = get_logger("ModernRelay.log")
    loop = asyncio.get_event_loop()
    loop.create_task(main(config))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
