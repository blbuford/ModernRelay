import sqlite3
from pathlib import Path

from aiosmtpd.smtp import AuthResult, LoginPassword
from argon2 import PasswordHasher


class Authenticator:
    def __init__(self, auth_database):
        self.auth_db = Path(auth_database)
        self.ph = PasswordHasher()

    def __call__(self, server, session, envelope, mechanism, auth_data):
        fail_nothandled = AuthResult(success=False, handled=False)
        if mechanism not in ("LOGIN", "PLAIN"):
            return fail_nothandled
        if not isinstance(auth_data, LoginPassword):
            return fail_nothandled
        username = auth_data.login
        password = auth_data.password
        hashpass = self.ph.hash(password)
        conn = sqlite3.connect(self.auth_db)
        curs = conn.execute(
            "SELECT hashpass FROM userauth WHERE username=?", (username,)
        )
        hash_db = curs.fetchone()
        conn.close()
        if not hash_db:
            return fail_nothandled
        if hashpass != hash_db[0]:
            return fail_nothandled
        return AuthResult(success=True)
