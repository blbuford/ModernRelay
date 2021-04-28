import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Union, List, Tuple

import aiofiles
from aiosmtpd.smtp import Envelope


class FileManager:
    def __init__(self, encrypt):
        self.encrypt = encrypt
        self.folder = Path(__file__).parent.parent / "spool"
        self.logger = logging.getLogger('ModernRelay.log')

        self.folder.mkdir(parents=True, exist_ok=True)

    def get_files(self) -> List[Path]:
        return [x for x in self.folder.iterdir() if x.is_file()]

    async def save_file(self, envelope: Envelope, peer: str) -> Union[None, Path]:
        file_name = uuid.uuid4()
        file_path = self.folder / str(file_name)

        try:
            j = {}
            j.update(envelope.__dict__)
            j['original_content'] = base64.b64encode(envelope.original_content).decode('ascii')
            j['content'] = base64.b64encode(envelope.content).decode('ascii')
            j['peer'] = peer
            encoded = base64.b64encode(json.dumps(j).encode('ascii'))
        except TypeError:
            self.logger.exception('Error in FileManager.save_file() while encoding the envelope and peer')
            return None

        if self.encrypt:
            pass

        try:
            async with aiofiles.open(file_path, mode='wb') as file:
                await file.write(encoded)
        except OSError:
            self.logger.exception(f'Error in FileManager.save_file() while opening/writing at {file_path}')
            return None

        return file_path

    async def open_file(self, file_path) -> Union[None, Tuple[Envelope, str]]:
        try:
            async with aiofiles.open(file_path, mode='rb') as file:
                content = await file.read()
        except OSError:
            self.logger.exception(f'Error in FileManager.open_file() while opening/reading at {file_path}')
            return None

        if self.encrypt:
            pass

        try:
            encoded = json.loads(base64.b64decode(content).decode('ascii'))
            encoded['original_content'] = base64.b64decode(encoded['original_content'])
            encoded['content'] = base64.b64decode(encoded['content'])
            envelope = Envelope()
            envelope.__dict__.update(encoded)
            peer = envelope.__dict__.pop('peer')
        except KeyError:
            self.logger.exception('Error in FileManager.open_file() while accessing JSON keys')
            return None
        except ValueError:
            self.logger.exception('Error in FileManager.open_file() while decoding the envelope and peer')
            return None

        return envelope, peer
