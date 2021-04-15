import asyncio
from typing import Union, Tuple

import pytest
from asynctest import MagicMock
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
            DeliveryAgentBase.create('doesnt-exist')

    @pytest.mark.asyncio
    async def test_abstract_send_mail(self):
        DeliveryAgentBase.__abstractmethods__ = set()

        class Dummy(DeliveryAgentBase):
            pass

        dummy = Dummy()
        result = await dummy.send_mail({})

        assert result is None


def set_env_vars(monkeypatch):
    monkeypatch.setenv('MR_MS365_APP_ID', 'fake-app-id')
    monkeypatch.setenv('MR_MS365_APP_SECRET', 'fake-app-secret')
    monkeypatch.setenv('MR_MS365_TENANT_ID', 'fake-tenant-id')


class TestGraphDeliveryAgent:
    """For testing the GraphDeliveryAgent (gda)"""

    @pytest.fixture
    def mock_gda_token_and_request(self):
        def mockup(mock_result: Tuple[str, int], token: Union[str, None] = "fake-token") -> DeliveryAgentBase:
            async def async_magic():
                return mock_result

            MagicMock.__await__ = lambda x: async_magic().__await__()
            gda = DeliveryAgentBase.create('GraphDeliveryAgent')
            gda.graph = GraphAdminClient()
            gda.graph.acquire_token = MagicMock(return_value=asyncio.Future())
            gda.graph.acquire_token.return_value.set_result(({'access_token': token}, 200))
            if token:
                gda.graph._token = "fake-token"
            gda.graph._request = MagicMock(return_value=asyncio.Future())
            gda.graph._request.return_value.set_result(mock_result)
            return gda

        return mockup

    def test_gda_fail_app_id(self):
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_APP_ID.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    def test_gda_fail_app_secret(self, monkeypatch):
        monkeypatch.setenv('MR_MS365_APP_ID', 'fake-app-id')
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_APP_SECRET.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    def test_gda_fail_tenant_id(self, monkeypatch):
        monkeypatch.setenv('MR_MS365_APP_ID', 'fake-app-id')
        monkeypatch.setenv('MR_MS365_APP_SECRET', 'fake-app-secret')
        with pytest.raises(DeliveryAgentException, match=".*MR_MS365_TENANT_ID.*"):
            DeliveryAgentBase.create('GraphDeliveryAgent')

    @pytest.mark.asyncio
    async def test_send_mail_success(self, monkeypatch, caplog, mock_gda_token_and_request):
        set_env_vars(monkeypatch)
        mock_result = ("ACCEPTED", 202)

        gda = mock_gda_token_and_request(mock_result)
        response = await gda.send_mail({
            'from': 'test@example.com',
            'to': ['test2@example.com'],
            'body_type': 'text/html',
            'body_content': 'test'
        })
        assert response
        assert 'Error: sendmail failed.' not in caplog.text

    @pytest.mark.asyncio
    async def test_send_mail_fail_to_auth(self, monkeypatch, caplog, mock_gda_token_and_request):
        set_env_vars(monkeypatch)
        mock_result = ("NEVER RETURNED", 500)

        gda = mock_gda_token_and_request(mock_result, token=None)
        await gda.send_mail({
            'from': 'test@example.com',
            'to': ['test2@example.com'],
            'body_type': 'text/html',
            'body_content': 'test'
        })
        assert 'Error: sendmail failed at authentication' in caplog.text

    @pytest.mark.asyncio
    async def test_send_mail_fail_to_send(self, monkeypatch, caplog, mock_gda_token_and_request):
        set_env_vars(monkeypatch)
        mock_result = ("NEVER RETURNED", 500)

        gda = mock_gda_token_and_request(mock_result)
        await gda.send_mail({
            'from': 'test@example.com',
            'to': ['test2@example.com'],
            'body_type': 'text/html'
        })
        assert 'Error: sendmail failed.' in caplog.text
