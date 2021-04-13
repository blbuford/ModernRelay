import asyncio
import ipaddress

import pytest
from aiosmtpd.smtp import Session, Envelope
from asynctest import MagicMock
from pathlib import Path
import ModernRelay.relay
from ModernRelay.agents import DeliveryAgentBase


class TestRelay:

    @pytest.fixture
    def session_anon(self, event_loop):
        sess = Session(loop=event_loop)
        sess.peer = ('172.16.128.64', 64160)
        sess.extended_smtp = True
        return sess

    @pytest.fixture
    def session_auth(self, event_loop):
        sess = Session(loop=event_loop)
        sess.peer = ('172.16.129.64', 64160)
        sess.extended_smtp = True
        return sess

    @pytest.fixture
    def envelope(self):
        env = Envelope()
        return env

    @pytest.fixture
    def envelope_attachment(self, envelope):
        with open(Path(__file__).parent / 'test_email', 'rb') as email:
            envelope.original_content = email.read()
        return envelope

    @pytest.fixture
    def mocked_agent(self):
        def inner(ret=("ACCEPTED", 202)):
            DeliveryAgentBase.__abstractmethods__ = set()

            class DummyDeliveryAgent(DeliveryAgentBase):
                pass

            mocked = MagicMock(DummyDeliveryAgent())
            mocked.send_mail.return_value = asyncio.Future()
            mocked.send_mail.return_value.set_result(ret)
            return mocked

        return inner

    @pytest.fixture
    def relay(self, mocked_agent):
        peer_map = {
            ipaddress.ip_network('172.16.128.0/24'): {
                'authentication': 'anonymous',
                'agent': mocked_agent(),
                'destinations': 'all'
            },
            ipaddress.ip_network('172.16.129.0/24'): {
                'authentication': 'LOGIN',
                'agent': mocked_agent(),
                'destinations': ['example.com', 'google.com']
            }
        }
        return ModernRelay.relay.ModernRelay(peer_map)

    @pytest.mark.asyncio
    async def test_ehlo(self, relay, session_anon, envelope):
        hostname = '[172.16.128.64]'
        responses = ['250-HERMES', '250-SIZE 33554432', '250-8BITMIME', '250-SMTPUTF8', '250 HELP']
        assert await relay.handle_EHLO(None, session_anon, envelope, hostname, responses) == responses
        assert session_anon.host_name == hostname

    @pytest.mark.asyncio
    async def test_mail_anon_auth(self, relay, session_anon, envelope):
        address = 'brett@example.com'
        mail_options = ['SIZE=761132']
        result = await relay.handle_MAIL(None, session_anon, envelope, address, mail_options)

        assert result == "250 OK"
        assert hasattr(session_anon, 'mr_agent')
        assert hasattr(session_anon, 'mr_destinations')
        assert isinstance(session_anon.mr_agent, MagicMock)
        assert envelope.mail_from == address
        assert envelope.mail_options == mail_options

    @pytest.mark.asyncio
    async def test_mail_good_auth(self, relay, session_auth, envelope):
        address = 'brett@example.com'
        mail_options = ['SIZE=761132']
        session_auth.authenticated = True
        result = await relay.handle_MAIL(None, session_auth, envelope, address, mail_options)

        assert result == "250 OK"
        assert hasattr(session_auth, 'mr_agent')
        assert hasattr(session_auth, 'mr_destinations')
        assert isinstance(session_auth.mr_agent, MagicMock)
        assert envelope.mail_from == address
        assert envelope.mail_options == mail_options

    @pytest.mark.asyncio
    async def test_mail_bad_auth(self, relay, session_auth, envelope):
        address = 'brett@example.com'
        mail_options = ['SIZE=761132']
        session_auth.authenticated = False
        result = await relay.handle_MAIL(None, session_auth, envelope, address, mail_options)

        assert result == "530 5.7.0 Authentication required"

    @pytest.mark.asyncio
    async def test_mail_peer_denied_relay(self, relay, session_anon, envelope):
        address = 'brett@example.com'
        mail_options = ['SIZE=761132']
        session_anon.peer = ('192.168.1.2', 69160)
        result = await relay.handle_MAIL(None, session_anon, envelope, address, mail_options)

        assert result == "550 Mail from this IP address is refused"

    @pytest.mark.asyncio
    async def test_rcpt_allow_all(self, relay, session_anon, envelope):
        address = 'brett@example.com'
        rcpt_options = ['test-option']
        session_anon.mr_destinations = "all"
        result = await relay.handle_RCPT(None, session_anon, envelope, address, rcpt_options)

        assert result == "250 OK"
        assert address in envelope.rcpt_tos
        assert set(envelope.rcpt_options).issubset(rcpt_options)

    @pytest.mark.asyncio
    async def test_rcpt_str_destinations_not_all(self, relay, session_anon, envelope):
        address = 'brett@example.com'
        rcpt_options = []
        session_anon.mr_destinations = "oops-this-is-a-typo"
        result = await relay.handle_RCPT(None, session_anon, envelope, address, rcpt_options)

        assert result == "550 Error with allowed destinations"

    @pytest.mark.asyncio
    async def test_rcpt_list_destinations_allowed_relay(self, relay, session_anon, envelope):
        address = 'brett@example.com'
        rcpt_options = ['test-option']
        session_anon.mr_destinations = ['example.com', 'google.com']
        result = await relay.handle_RCPT(None, session_anon, envelope, address, rcpt_options)

        assert result == "250 OK"
        assert address in envelope.rcpt_tos
        assert set(envelope.rcpt_options).issubset(rcpt_options)

    @pytest.mark.asyncio
    async def test_rcpt_list_destinations_denied_relay(self, relay, session_anon, envelope):
        address = 'brett@bing.com'
        rcpt_options = []
        session_anon.mr_destinations = ['example.com', 'google.com']
        result = await relay.handle_RCPT(None, session_anon, envelope, address, rcpt_options)

        assert result == "550 Domain is not allowed to be relayed"

    @pytest.mark.asyncio
    async def test_data_no_agent(self, relay, session_anon, envelope):
        result = await relay.handle_DATA(None, session_anon, envelope)

        assert result == "500 Failed to match session with delivery agent"

    @pytest.mark.asyncio
    async def test_data_with_attachment(self, relay, session_anon, envelope_attachment, mocked_agent):
        session_anon.mr_agent = mocked_agent()

        result = await relay.handle_DATA(None, session_anon, envelope_attachment)

        assert result == "250 Message accepted for delivery"

    @pytest.mark.asyncio
    async def test_data_with_attachment_failure(self, relay, session_anon, envelope_attachment, mocked_agent):
        session_anon.mr_agent = mocked_agent(("REJECTED", 500))

        result = await relay.handle_DATA(None, session_anon, envelope_attachment)

        assert result == "500 Delivery agent failed with status code 500"
