import asyncio
from dataclasses import dataclass

import asynctest
import pytest
from asynctest import Mock, MagicMock
from msgraph_async import GraphAdminClient

from ModernRelay.agents import DeliveryAgentBase
from ModernRelay.exceptions import DeliveryAgentException


class TestDeliveryAgentBase:
    @pytest.fixture
    def register_fake_class(self):
        @DeliveryAgentBase.register_subclass('test')
        class FakeCls:
            pass

        return FakeCls

    def test_register_subclass(self, register_fake_class):
        assert 'test' in DeliveryAgentBase.subclasses

    def test_create_subclass_success(self, register_fake_class):
        cls = DeliveryAgentBase.create('test')
        assert isinstance(cls, register_fake_class)

    def test_create_subclass_fail(self):
        with pytest.raises(DeliveryAgentException, match=".*not registered.*"):
            cls = DeliveryAgentBase.create('doesnt-exist')

    @pytest.mark.asyncio
    async def test_abstract_send_mail(self):
        DeliveryAgentBase.__abstractmethods__ = set()

        @dataclass
        class Dummy(DeliveryAgentBase):
            pass

        dummy = Dummy()
        result = await dummy.send_mail({})

        assert result is None


def set_env_vars(monkeypatch):
    monkeypatch.setenv('MR_MS365_APP_ID', 'testing')
    monkeypatch.setenv('MR_MS365_APP_SECRET', 'testing')
    monkeypatch.setenv('MR_MS365_TENANT_ID', 'testing')


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class TestGraphDeliveryAgent:
    """For testing the GraphDeliveryAgent (gda)"""

    def test_gda_fail_app_id(self):
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_APP_ID.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    def test_gda_fail_app_secret(self, monkeypatch):
        monkeypatch.setenv('MR_MS365_APP_ID', 'testing')
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_APP_SECRET.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    def test_gda_fail_tenant_id(self, monkeypatch):
        monkeypatch.setenv('MR_MS365_APP_ID', 'testing')
        monkeypatch.setenv('MR_MS365_APP_SECRET', 'testing')
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_TENANT_ID.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    @pytest.mark.asyncio
    async def test_send_mail_success(self, monkeypatch):
        set_env_vars(monkeypatch)
        mock_result = ("ACCEPTED", 202)
        async def async_magic():
            return mock_result

        MagicMock.__await__ = lambda x: async_magic().__await__()
        gda = DeliveryAgentBase.create('GraphDeliveryAgent')
        gda.graph = GraphAdminClient()
        gda.graph._refresh_token = MagicMock(return_value=asyncio.Future())
        gda.graph._refresh_token.return_value.set_result([])
        gda.graph._token = "jashdlashda"
        gda.graph._request = MagicMock(return_value=asyncio.Future())
        gda.graph._request.return_value.set_result(mock_result)
        response = await gda.send_mail({
            'from': 'test@example.com',
            'to': ['test2@example.com'],
            'body_type': 'text/html',
            'body_content': 'test'
        })
        assert response[-1] == 202
