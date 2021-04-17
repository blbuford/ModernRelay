import base64
import uuid
from pathlib import Path
from typing import Union
import aiofiles

from aiosmtpd.smtp import Envelope


class FileManager:
    def __init__(self, encrypt):
        self.encrypt = encrypt
        self.folder = Path(__file__).parent.parent / "spool"

        self.folder.mkdir(parents=True, exist_ok=True)

    async def save_file(self, envelope: Envelope) -> Union[None, Path]:
        file_name = uuid.uuid4()
        file_path = self.folder / str(file_name)
        file_content = base64.b64encode(envelope.original_content)

        if self.encrypt:
            pass

        async with aiofiles.open(file_path, mode='wb') as file:
            await file.write(file_content)
        return file_path

    async def open_file(self, file_path) -> Envelope:
        async with aiofiles.open(file_path, mode='rb') as file:
            content = await file.read()

        if self.encrypt:
            pass

        envelope = Envelope()
        envelope.original_content = base64.b64decode(content)

        return envelope
