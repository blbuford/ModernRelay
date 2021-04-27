import base64
import json
import uuid
from pathlib import Path
from typing import Union, List, Tuple

import aiofiles
from aiosmtpd.smtp import Envelope


class FileManager:
    def __init__(self, encrypt):
        self.encrypt = encrypt
        self.folder = Path(__file__).parent.parent / "spool"

        self.folder.mkdir(parents=True, exist_ok=True)

    def get_files(self) -> List[Path]:
        return [x for x in self.folder.iterdir() if x.is_file()]

    async def save_file(self, envelope: Envelope, peer: str) -> Union[None, Path]:
        file_name = uuid.uuid4()
        file_path = self.folder / str(file_name)

        j = {}
        j.update(envelope.__dict__)
        j['original_content'] = base64.b64encode(envelope.original_content).decode('ascii')
        j['content'] = base64.b64encode(envelope.content).decode('ascii')
        j['peer'] = peer
        encoded = base64.b64encode(json.dumps(j).encode('ascii'))

        if self.encrypt:
            pass

        async with aiofiles.open(file_path, mode='wb') as file:
            await file.write(encoded)
        return file_path

    async def open_file(self, file_path) -> Tuple[Envelope, str]:
        async with aiofiles.open(file_path, mode='rb') as file:
            content = await file.read()

        if self.encrypt:
            pass

        encoded = json.loads(base64.b64decode(content).decode('ascii'))
        encoded['original_content'] = base64.b64decode(encoded['original_content'])
        encoded['content'] = base64.b64decode(encoded['content'])
        envelope = Envelope()
        envelope.__dict__.update(encoded)
        peer = envelope.pop('peer')
        return envelope, peer
