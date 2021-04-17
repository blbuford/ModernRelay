import ipaddress
import logging
from datetime import timedelta, datetime
from email import message_from_bytes, policy
from pathlib import Path

from aiosmtpd.smtp import Envelope
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ModernRelay import common
from ModernRelay.agents import DeliveryAgentBase


class ModernRelay:
    def __init__(self, peer_map, file_manager=None):
        self.peer_map = peer_map
        self.logger = logging.getLogger("ModernRelay.log")
        self.scheduler = AsyncIOScheduler()
        self.file_manager = file_manager
        self.job_map = {}
        # TODO: Import jobs back into being

    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        session.host_name = hostname
        self.logger.info(f"250 EHLO from {hostname} ({session.peer[0]})")
        return responses

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        addr = ipaddress.ip_address(session.peer[0])
        for peer in self.peer_map:
            if addr in peer:
                if (not self.peer_map[peer]['authenticated'] and not session.authenticated) or (
                        self.peer_map[peer]['authenticated'] and session.authenticated):
                    session.mr_agent = self.peer_map[peer]['agent']
                    session.mr_destinations = self.peer_map[peer]['destinations']
                    break
                else:
                    self.logger.warning(f"530 MAIL FROM {address} ({session.peer[0]}) denied! Authentication Required")
                    return "530 5.7.0 Authentication required"

        if not hasattr(session, 'mr_agent'):
            self.logger.warning(
                f"530 MAIL FROM {address} ({session.peer[0]}) denied! IP address not found in allowed peers")
            return "550 Mail from this IP address is refused"

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
                file_path = self.file_manager.save_email(envelope)
                if file_path:
                    job = self.scheduler.add_job(func=common.send_mail_from_disk,
                                                 trigger='interval',
                                                 minutes=5,
                                                 args=[file_path, self, session.mr_agent],
                                                 misfire_grace_time=None,
                                                 coalesce=True,
                                                 next_run_time=datetime.now() + timedelta(minutes=5))
                    self.logger.debug(f"Message from {addr} saved to {file_path}. "
                                      f"Job is scheduled to try again in 5 minutes")
                    self.job_map[file_path.name] = job
                else:
                    self.logger.critical("Unable to save email to disk!")

            return '500 Delivery agent failed'


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


async def send_mail_from_disk(file_path: Path, handler: ModernRelay, delivery_agent: DeliveryAgentBase) -> bool:
    logger = logging.getLogger("ModernRelay.log")
    envelope = await handler.file_manager.open_file(file_path)
    message, attachments = get_message_and_attachments(envelope)

    result = await delivery_agent.send_mail(message, headers=None, attachments=attachments)

    if result:
        logger.info("Successful!")
        handler.scheduler.remove_job(handler.job_map[file_path.name])
        handler.job_map.pop(file_path.name)
        file_path.unlink()
    else:
        logger.warning(f"{file_path} failed to send with agent {delivery_agent.__class__.__name__}")
    return False
