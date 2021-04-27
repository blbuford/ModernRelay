import pytest
from aiosmtpd.smtp import Envelope

from ModernRelay.file_manager import FileManager


@pytest.fixture
def file_manager():
    def inner(encrypted):
        return FileManager(encrypted)

    return inner


@pytest.mark.asyncio
async def test_create_file(file_manager, cleanup_files):
    fm = file_manager(encrypted=False)
    envelope = Envelope()
    envelope.original_content = b"lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis tellus velit, " \
                                b"tempor quis convallis ut, euismod nec arcu. "
    envelope.content = envelope.original_content
    result = await fm.save_file(envelope, '172.16.100.2/24')
    assert result
