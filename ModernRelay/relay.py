import ipaddress
import logging
from email import message_from_bytes
from email import policy


class ModernRelay:
    def __init__(self, peer_map):
        self.peer_map = peer_map
        self.logger = logging.getLogger("ModernRelay.log")

    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        session.host_name = hostname
        self.logger.info(f"EHLO from {hostname} ({session.peer[0]})")
        return responses

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        addr = ipaddress.ip_address(session.peer[0])
        for peer in self.peer_map:
            if addr in peer:
                if (self.peer_map[peer]['authentication'] == "anonymous" and not session.authenticated) or (
                        self.peer_map[peer]['authentication'] in ('LOGIN', 'PLAIN') and session.authenticated):
                    session.mr_agent = self.peer_map[peer]['agent']
                    session.mr_destinations = self.peer_map[peer]['destinations']
                    break
                else:
                    self.logger.warning(f"MAIL FROM {address} ({session.peer[0]}) denied! Authentication Required")
                    return "530 5.7.0 Authentication required"

        if not session.mr_agent:
            self.logger.warning(
                f"MAIL FROM {address} ({session.peer[0]}) denied! IP address not found in allowed peers")
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
            else:
                self.logger.error(f"{session.mr_destinations} is a string, but its not 'all'.")
                return '550 Error with allowed destinations'
        elif type(session.mr_destinations) is list:
            domain = address.split("@")[-1]
            if domain in session.mr_destinations:
                envelope.rcpt_tos.append(address)
            else:
                self.logger.error(f"{domain} is not in {session.mr_destinations}.")
                return '550 Domain is not allowed to be relayed'
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        if not session.mr_agent:
            self.logger.error(
                f"Message from {session.peer[0]} failed to relay because it could not be matched to a delivery agent")
            return f"500 Failed to match session with delivery agent"

        em = message_from_bytes(envelope.original_content, policy=policy.default)

        attachments = [{
            'name': i.get_filename(),
            'contentType': i.get_content_type(),
            'contentBytes': i.get_payload(decode=False).replace('\r\n', '')
        } for i in em.iter_attachments()]

        resp = await session.mr_agent.send_mail(
            {
                'from': envelope.mail_from,
                'to': envelope.rcpt_tos,
                'subject': em['subject'],
                'body_type': em.get_body().get_content_type(),
                'body_content': em.get_body().get_content()
            }, headers=None, attachments=attachments)

        addr = session.peer[0]
        if resp[-1] == 202:
            self.logger.info(f"Message from {addr} successfully relayed to {session.mr_agent.__class__.__name__}.")
            self.logger.debug(f"Peer IP: {addr} - From:{envelope.mail_from} - To: {envelope.rcpt_tos} - "
                              f"HTTP Response: {resp[-1]}")
            return '250 Message accepted for delivery'
        else:
            self.logger.error(
                f"Message from {addr} failed to relay to {session.mr_agent.__class__.__name__} with status code {resp[-1]}")
            return f'500 Delivery agent failed with status code {resp[-1]}'
