import logging
import agents
from email import message_from_bytes
from email import policy


class ModernRelay:
    def __init__(self, delivery_agent: agents.DeliveryAgentABC):
        self.agent = delivery_agent
        self.logger = logging.getLogger("ModernRelay.log")

    async def handle_DATA(self, server, session, envelope):
        em = message_from_bytes(envelope.original_content, policy=policy.default)

        attachments = [{
            'name': i.get_filename(),
            'contentType': i.get_content_type(),
            'contentBytes': i.get_payload(decode=False).replace('\r\n', '')
        } for i in em.iter_attachments()]

        resp = await self.agent.send_mail(
            {
                'from': envelope.mail_from,
                'to': envelope.rcpt_tos,
                'subject': em['subject'],
                'body_type': em.get_body().get_content_type(),
                'body_content': em.get_body().get_content()
            }, headers=None, attachments=attachments)

        if resp[-1] == 202:
            self.logger.info(f"Message from {session.peer[0]} successfully relayed to {self.agent.__class__.__name__}.")
            self.logger.debug(f"Peer IP: {session.peer[0]} - From:{envelope.mail_from} - To: {envelope.rcpt_tos}")
            return '250 Message accepted for delivery'
        else:
            self.logger.error(
                f"Message from {session.peer[0]} failed to relay to {self.agent.__class__.__name__} with status code {resp[-1]}")
            return f'500 Delivery agent failed with status code {resp[-1]}'
