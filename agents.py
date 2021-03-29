from abc import ABC, abstractmethod
from http import HTTPStatus

from msgraph_async import GraphAdminClient


class DeliveryAgentABC(ABC):
    def __init__(self, config):
        self.config = config
        super().__init__()

    @abstractmethod
    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        pass


class GraphDeliveryAgent(DeliveryAgentABC):
    def __init__(self, config):
        self.graph = GraphAdminClient()
        super().__init__(config)

    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        if not self.graph.is_managed:
            await self.graph.manage_token(self.config['MR_MS365_APP_ID'],
                                          self.config['MR_MS365_APP_SECRET'],
                                          self.config['MR_MS365_TENANT_ID'])

        message['body_type'] = "HTML" if message['body_type'] == "text/html" else "Text"
        resp = await self.graph.send_mail(
            message,
            headers=headers,
            attachments=attachments,
            expected_statuses=(HTTPStatus.ACCEPTED,))

        return resp
