import argparse
import sqlite3
from pathlib import Path
from typing import Dict

from argon2 import PasswordHasher

DB_FILE = "modernrelay.db"
USER_AND_PASSWORD: Dict[str, str] = {
    "test": "test",
    "test2": "test2"
}


class ParseKwargs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            key, value = value.split('=')
            getattr(namespace, self.dest)[key[1:-1]] = value[1:-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creates users and stores them in a sqlite database.')
    parser.add_argument('-dbname', help='The name of the database file')
    parser.add_argument('-users', nargs='*', action=ParseKwargs, help='users in \'user\'=\'password\' format')

    args = parser.parse_args()
    if args.dbname:
        dbfp = Path(args.dbname).absolute()
    else:
        dbfp = Path(DB_FILE).absolute()
    if dbfp.exists():
        dbfp.unlink()
    if args.dbname:
        conn = sqlite3.connect(args.dbname)
    else:
        conn = sqlite3.connect(DB_FILE)
    curs = conn.cursor()
    curs.execute("CREATE TABLE userauth (username text, hashpass text)")
    ph = PasswordHasher()
    insert_up = "INSERT INTO userauth VALUES (?, ?)"
    if args.users:
        USER_AND_PASSWORD = args.users
    for u, p in USER_AND_PASSWORD.items():
        print(f"[-] Inserting {u} into the database")
        h = ph.hash(p)
        curs.execute(insert_up, (u, h))
    conn.commit()
    conn.close()
    assert dbfp.exists()
    print(f"[+] Database created at {dbfp}")
