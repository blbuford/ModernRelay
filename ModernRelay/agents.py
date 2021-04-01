from abc import ABC, abstractmethod
import os

from msgraph_async import GraphAdminClient
import exceptions


class DeliveryAgentABC(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        pass


class GraphDeliveryAgent(DeliveryAgentABC):
    def __init__(self):
        self.graph = GraphAdminClient()
        if not os.getenv('MR_MS365_APP_ID'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_APP_ID is not set!")

        if not os.getenv('MR_MS365_APP_SECRET'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_APP_SECRET is not set!")

        if not os.getenv('MR_MS365_TENANT_ID'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_TENANT_ID is not set!")

        super().__init__()

    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        if not self.graph.is_managed:
            await self.graph.manage_token(os.getenv('MR_MS365_APP_ID'),
                                          os.getenv('MR_MS365_APP_SECRET'),
                                          os.getenv('MR_MS365_TENANT_ID'))

        message['body_type'] = "HTML" if message['body_type'] == "text/html" else "Text"
        resp = await self.graph.send_mail(
            message,
            headers=headers,
            attachments=attachments)

        return resp
