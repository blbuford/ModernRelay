import asyncio

from aiosmtpd.controller import Controller
from email import message_from_bytes
from email import policy
from dotenv import dotenv_values
import logging
import agents


class ModernRelay:
    def __init__(self, delivery_agent: agents.DeliveryAgentABC):
        self.agent = delivery_agent

    async def handle_DATA(self, server, session, envelope):
        em = message_from_bytes(envelope.original_content, policy=policy.default)

        attachments = [{
            'name': i.get_filename(),
            'contentType': i.get_content_type(),
            'contentBytes': i.get_payload(decode=False).replace('\r\n', '')
        } for i in em.iter_attachments()]

        logging.info(
            f"ModernRelay:handle_DATA:Sending mail to mail agent {self.agent.__class__.__name__}. From:{envelope.mail_from} - To: {envelope.rcpt_tos}")
        resp = await self.agent.send_mail(
            {
                'from': envelope.mail_from,
                'to': envelope.rcpt_tos,
                'subject': em['subject'],
                'body_type': em.get_body().get_content_type(),
                'body_content': em.get_body().get_content()
            }, headers=None, attachments=attachments)

        if resp[-1] == 202:
            return '250 Message accepted for delivery'
        else:
            return f'500 Delivery agent failed with status code {resp[-1]}'


async def main(config):
    delivery_agent = agents.GraphDeliveryAgent(config)
    handler = ModernRelay(delivery_agent)
    controller = Controller(handler, port=8025)
    controller.start()
    print(f"Controller live on {controller.hostname}:{controller.port}!")


if __name__ == "__main__":
    config = dotenv_values("./dev.env")
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.create_task(main(config))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
