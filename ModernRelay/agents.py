import os
from abc import abstractmethod

from msgraph_async import GraphAdminClient

import exceptions


class DeliveryAgentBase:
    subclasses = {}

    def __init__(self):
        super().__init__()

    @classmethod
    def register_subclass(cls, agent):
        def decorator(subclass):
            cls.subclasses[agent] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, agent):
        if agent not in cls.subclasses:
            raise exceptions.DeliveryAgentException(f"Agent type {agent} not registered in "
                                                    f"DeliveryAgentBase.subclasses! Did you decorate your class with "
                                                    f"@DeliveryAgentBase.register_subclass()?")
        return cls.subclasses[agent]()

    @abstractmethod
    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        pass


@DeliveryAgentBase.register_subclass('GraphDeliveryAgent')
class GraphDeliveryAgent(DeliveryAgentBase):
    def __init__(self):
        self.graph = None
        if not os.getenv('MR_MS365_APP_ID'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_APP_ID is not set!")

        if not os.getenv('MR_MS365_APP_SECRET'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_APP_SECRET is not set!")

        if not os.getenv('MR_MS365_TENANT_ID'):
            raise exceptions.DeliveryAgentException("Environment variable MR_MS365_TENANT_ID is not set!")

        super().__init__()

    async def send_mail(self, message: dict, headers: dict = None, attachments: dict = None):
        if not self.graph:
            self.graph = GraphAdminClient()
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
