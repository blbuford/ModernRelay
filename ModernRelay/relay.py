import ipaddress
import logging
from email import message_from_bytes
from email import policy


class ModernRelay:
    def __init__(self, network_agents_map, network_destinations_map):
        self.network_agent_map = network_agents_map
        self.network_destinations_map = network_destinations_map
        self.logger = logging.getLogger("ModernRelay.log")

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        allowed_destinations = None
        addr = ipaddress.ip_address(session.peer[0])
        for key in self.network_destinations_map.keys():
            if addr in key:
                allowed_destinations = self.network_destinations_map[key]

        if type(allowed_destinations) is str:
            if allowed_destinations == "all":
                envelope.rcpt_tos.append(address)
            else:
                self.logger.error(f"{allowed_destinations} is a string, but its not 'all'.")
                return '550 Error with allowed destinations'
        elif type(allowed_destinations) is list:
            domain = address.split("@")[-1]
            if domain in allowed_destinations:
                envelope.rcpt_tos.append(address)
            else:
                self.logger.error(f"{domain} is not in {allowed_destinations}.")
                return '550 Domain is not allowed to be relayed'
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        relay = None
        addr = ipaddress.ip_address(session.peer[0])
        for key in self.network_agent_map.keys():
            if addr in key:
                relay = self.network_agent_map[key]

        if not relay:
            self.logger.error(
                f"Message from {session.peer[0]} failed to relay because it could not be matched to a delivery agent")
            return f"500 Failed to match session with delivery agent"

        em = message_from_bytes(envelope.original_content, policy=policy.default)

        attachments = [{
            'name': i.get_filename(),
            'contentType': i.get_content_type(),
            'contentBytes': i.get_payload(decode=False).replace('\r\n', '')
        } for i in em.iter_attachments()]

        resp = await relay.send_mail(
            {
                'from': envelope.mail_from,
                'to': envelope.rcpt_tos,
                'subject': em['subject'],
                'body_type': em.get_body().get_content_type(),
                'body_content': em.get_body().get_content()
            }, headers=None, attachments=attachments)

        if resp[-1] == 202:
            self.logger.info(f"Message from {addr} successfully relayed to {relay.__class__.__name__}.")
            self.logger.debug(f"Peer IP: {addr} - From:{envelope.mail_from} - To: {envelope.rcpt_tos} - "
                              f"HTTP Response: {resp[-1]}")
            return '250 Message accepted for delivery'
        else:
            self.logger.error(
                f"Message from {addr} failed to relay to {relay.__class__.__name__} with status code {resp[-1]}")
            return f'500 Delivery agent failed with status code {resp[-1]}'
