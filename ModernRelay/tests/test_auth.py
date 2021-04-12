from base64 import b64encode
from smtplib import (
    SMTP as SMTPClient,
)
from typing import Callable, Tuple

import pytest
from aiosmtpd.testing.statuscodes import SMTP_STATUS_CODES as S


class _CommonMethods:
    """Contain snippets that keep being performed again and again and again..."""

    def _helo(self, client: SMTPClient, domain: str = "example.org") -> bytes:
        code, mesg = client.helo(domain)
        assert code == 250
        return mesg

    def _ehlo(self, client: SMTPClient, domain: str = "example.com") -> bytes:
        code, mesg = client.ehlo(domain)
        assert code == 250
        return mesg


@pytest.mark.usefixtures('modern_relay_controller')
class TestAuthenticator(_CommonMethods):

    @pytest.fixture
    def do_auth_plain(
            self, client
    ) -> Callable[[str], Tuple[int, bytes]]:
        self._ehlo(client)

        def do(param: str) -> Tuple[int, bytes]:
            return client.docmd("AUTH PLAIN " + param)

        do.client = client
        return do

    @pytest.fixture
    def do_auth_login(
            self, client
    ) -> Callable[[str], Tuple[int, bytes]]:
        self._ehlo(client)
        resp = client.docmd("AUTH LOGIN")
        assert resp == S.S334_AUTH_USERNAME

        def do(param: str) -> Tuple[int, bytes]:
            return client.docmd(param)

        do.client = client
        return do

    def test_plain_auth_success(self, do_auth_plain):
        password = "test"
        resp = do_auth_plain(b64encode(b"\0test\0" + password.encode("ascii")).decode())

        assert resp == S.S235_AUTH_SUCCESS

    def test_plain_auth_bad_password(self, do_auth_plain):
        password = "totally-wrong"
        resp = do_auth_plain(b64encode(b"\0test\0" + password.encode("ascii")).decode())

        assert resp == S.S535_AUTH_INVALID

    def test_plain_auth_bad_user(self, do_auth_plain):
        password = "totally-wrong"
        resp = do_auth_plain(b64encode(b"\0baduser\0" + password.encode("ascii")).decode())

        assert resp == S.S535_AUTH_INVALID

    def test_login_auth_success(self, do_auth_login):
        resp = do_auth_login(b64encode(b"test").decode())
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login(b64encode(b"test").decode())
        assert resp == S.S235_AUTH_SUCCESS

    def test_login_auth_bad_password(self, do_auth_login):
        resp = do_auth_login(b64encode(b"test").decode())
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login(b64encode(b"total-wrong").decode())
        assert resp == S.S535_AUTH_INVALID
