import ipaddress
import logging
import os
import sys
import platform
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from ModernRelay.exceptions import ConfigParsingException

FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def resolve_env_vars(unresolved):
    plat = platform.system().lower()

    if plat == "windows":
        env_vars_regex = re.compile(r"%(.+)%")
        matches = env_vars_regex.findall(unresolved)
        for match in matches:
            unresolved = unresolved.replace("%" + match + "%", os.getenv(match))
    else:
        env_vars_regex = re.compile(r"\$(.+)/?}")
        matches = env_vars_regex.findall(unresolved)
        for match in matches:
            unresolved = unresolved.replace("$" + match, os.getenv(match))

    return unresolved


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler(filename):
    filename = resolve_env_vars(filename)
    file_handler = TimedRotatingFileHandler(filename, when='midnight', backupCount=5)
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name, level=logging.DEBUG, filename="ModernRelay.log"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    if level < logging.INFO:
        logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler(filename))
    logger.propagate = False
    return logger


def parse_config(config):
    peers = {}
    server_conf = {}
    for (peer_name, peer_details) in config['peers'].get().items():

        if '/' in peer_name:
            peer_name = ipaddress.ip_network(peer_name)
        else:
            peer_name = ipaddress.ip_network(peer_name + "/32")

        peers[peer_name] = {}

        if 'agent' in peer_details:
            peers[peer_name]['agent'] = peer_details['agent']
        else:
            raise ConfigParsingException("Error! 'agent' is a required field for each peer in the configuration")

        if 'authenticated' in peer_details:
            peers[peer_name]['authenticated'] = peer_details['authenticated']
        else:
            peers[peer_name]['authenticated'] = False

        if 'destinations' in peer_details:
            dests = peer_details['destinations']
            if isinstance(dests, str):
                if dests == "all":
                    peers[peer_name]['destinations'] = "all"
                else:
                    raise ConfigParsingException("Error! 'destinations' is read as string, but its not 'all'.")
            elif isinstance(dests, list):
                peers[peer_name]['destinations'] = dests
            else:
                raise ConfigParsingException("Error! 'destinations' is set to something that can't be parsed "
                                             "(not string or list).")
        else:
            peers[peer_name]['destinations'] = "all"

    server_conf['tls'] = {}
    server_conf['networking'] = {}
    server_conf['files'] = {}
    if 'tls' in config:
        server_conf['tls']['required'] = config['tls']['required'].get(bool)
        server_conf['tls']['public_key'] = Path(config['tls']['public_key'].get(str)).absolute()
        server_conf['tls']['private_key'] = Path(config['tls']['private_key'].get(str)).absolute()

    if 'networking' in config:
        server_conf['networking']['port'] = config['networking']['port'].get(int)
        server_conf['networking']['host_name'] = config['networking']['host_name'].get(str)

    if 'files' in config:
        server_conf['files']['spool_dir'] = config['files']['spool_dir'].get(str)

    return server_conf, peers
