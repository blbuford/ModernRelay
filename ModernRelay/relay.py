import asyncio
import ipaddress
import logging
from datetime import timedelta, datetime
from email import message_from_bytes, policy
from pathlib import Path

from aiosmtpd.smtp import Envelope, Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler

from ModernRelay.exceptions import AuthenticationRequiredException, RelayRefusedException
from ModernRelay.file_manager import FileManager


class ModernRelay:
    def __init__(self, peer_map, file_manager=None):
        self.peer_map = peer_map
        self.logger = logging.getLogger("ModernRelay.log")
        self.scheduler = AsyncIOScheduler()
        self.file_manager = file_manager
        if self.file_manager:
            self.scheduler.add_job(func=load_old_jobs,
                                   args=[self.file_manager, self.peer_map, self.scheduler],
                                   misfire_grace_time=None,
                                   coalesce=True)

        self.scheduler.start()

    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        session.host_name = hostname
        self.logger.info(f"250 EHLO from {hostname} ({session.peer[0]})")
        return responses

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        try:
            parse_peer(session, self.peer_map)
        except RelayRefusedException:
            self.logger.warning(
                f"530 MAIL FROM {address} ({session.peer[0]}) denied! IP address not found in allowed peers")
            return "550 Mail from this IP address is refused"
        except AuthenticationRequiredException:
            self.logger.warning(f"530 MAIL FROM {address} ({session.peer[0]}) denied! Authentication Required")
            return "530 5.7.0 Authentication required"

        self.logger.info(
            f"MAIL FROM {address} ({session.peer[0]}) with options: {mail_options} allowed")
        envelope.mail_from = address
        envelope.mail_options.extend(mail_options)
        return "250 OK"

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):

        if type(session.mr_destinations) is str:
            if session.mr_destinations == "all":
                envelope.rcpt_tos.append(address)
                envelope.rcpt_options.extend(rcpt_options)
            else:
                self.logger.error(f"550 {session.mr_destinations} is a string, but its not 'all'. Typo?")
                return '550 Error with allowed destinations'
        elif type(session.mr_destinations) is list:
            domain = address.split("@")[-1].lower()
            if domain in session.mr_destinations:
                envelope.rcpt_tos.append(address)
                envelope.rcpt_options.extend(rcpt_options)
            else:
                self.logger.error(f"550 {domain} is not in {session.mr_destinations}.")
                return '550 Domain is not allowed to be relayed'
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        if not hasattr(session, 'mr_agent'):
            self.logger.error(
                f"500 Message from {session.peer[0]} failed to relay because it could not be matched to a delivery "
                f"agent")
            return "500 Failed to match session with delivery agent"

        message, attachments = get_message_and_attachments(envelope)

        result = await session.mr_agent.send_mail(message, headers=None, attachments=attachments)

        addr = session.peer[0]
        if result:
            self.logger.info(f"250 Message from {addr} successfully relayed to {session.mr_agent.__class__.__name__}.")
            self.logger.debug(f"Peer IP: {addr} - From:{envelope.mail_from} - To: {envelope.rcpt_tos}")
            return '250 Message accepted for delivery'
        else:
            self.logger.error(
                f"500 Message from {addr} failed to relay to {session.mr_agent.__class__.__name__}")
            if self.file_manager:
                file_path = await self.file_manager.save_file(envelope, addr)
                if file_path:
                    self.scheduler.add_job(func=send_mail_from_disk,
                                           trigger='interval',
                                           seconds=30,
                                           args=[file_path, self.file_manager, self.scheduler, session],
                                           misfire_grace_time=None,
                                           coalesce=True,
                                           next_run_time=datetime.now() + timedelta(seconds=30),
                                           id=file_path.name)
                    self.logger.debug(f"Message from {addr} saved to {file_path}. "
                                      f"Job is scheduled to try again in 5 minutes")
                else:
                    self.logger.critical("Unable to save email to disk!")

            return '500 Delivery agent failed'


def parse_peer(session, peer_map):
    addr = ipaddress.ip_address(session.peer[0])

    denied_once = False
    for peer in peer_map:
        if addr in peer:
            if not peer_map[peer]['authenticated'] or (
                    peer_map[peer]['authenticated'] and session.authenticated):
                session.mr_agent = peer_map[peer]['agent']
                session.mr_destinations = peer_map[peer]['destinations']
                return True
            else:
                denied_once = True

    if denied_once:
        raise AuthenticationRequiredException()
    raise RelayRefusedException()


def get_message_and_attachments(envelope: Envelope):
    em = message_from_bytes(envelope.original_content, policy=policy.default)

    message = {
        'from': envelope.mail_from,
        'to': envelope.rcpt_tos,
        'subject': em['subject'],
        'body_type': em.get_body().get_content_type(),
        'body_content': em.get_body().get_content()
    }
    attachments = [{
        'name': i.get_filename(),
        'contentType': i.get_content_type(),
        'contentBytes': i.get_payload(decode=False).replace('\r\n', '')
    } for i in em.iter_attachments()]

    return message, attachments


async def send_mail_from_disk(file_path: Path, file_manager: FileManager, scheduler: BaseScheduler,
                              session: Session) -> bool:
    logger = logging.getLogger("ModernRelay.log")
    envelope, _ = await file_manager.open_file(file_path)
    message, attachments = get_message_and_attachments(envelope)

    result = await session.mr_agent.send_mail(message, headers=None, attachments=attachments)

    if result:
        logger.info(
            f"Success! {file_path} sent with agent {session.mr_agent.__class__.__name__} to {envelope.rcpt_tos}")
        scheduler.remove_job(file_path.name)
        file_path.unlink()
        return True
    else:
        logger.warning(f"{file_path} failed to send with agent {session.mr_agent.__class__.__name__}")
    return False


async def load_old_jobs(file_manager, peer_map, scheduler):
    logger = logging.getLogger("ModernRelay.log")
    for job_file in file_manager.get_files():
        envelope, peer = await file_manager.open_file(job_file)
        session = Session(loop=asyncio.get_event_loop())
        session.authenticated = True
        session.peer = (peer,)
        try:
            parse_peer(session, peer_map)
        except RelayRefusedException:
            logger.warning(
                f"Unable to match file({job_file}), IP({session.peer[0]}) to an allowed peer!")
            continue

        scheduler.add_job(func=send_mail_from_disk,
                          trigger='interval',
                          seconds=30,
                          args=[job_file, file_manager, scheduler, session],
                          misfire_grace_time=None,
                          coalesce=True,
                          next_run_time=datetime.now() + timedelta(seconds=30),
                          id=job_file.name)
