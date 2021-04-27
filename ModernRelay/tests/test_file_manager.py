from pathlib import Path

import aiofiles
import pytest
from aiosmtpd.smtp import Envelope

from ModernRelay.file_manager import FileManager


@pytest.mark.asyncio
async def test_create_file(envelope_peer_spooled, file_manager, cleanup_files):
    fm = file_manager(encrypted=False)
    envelope, peer = envelope_peer_spooled

    result = await fm.save_file(envelope, peer)

    assert result
    assert result.parent.name == "spool"


@pytest.mark.asyncio
async def test_open_file(envelope_peer_spooled):
    envelope, peer = envelope_peer_spooled
    assert isinstance(peer, str)
    assert len(peer) > 0
    assert envelope.mail_from
    assert envelope.rcpt_tos
    assert isinstance(envelope.original_content, bytes)
    assert isinstance(envelope.content, bytes)
    assert len(envelope.original_content) > 0


@pytest.mark.asyncio
async def test_get_spooled_files(envelope_peer_spooled, file_manager, cleanup_files):
    envelope, peer = envelope_peer_spooled
    fm = file_manager(encrypted=False)

    saved_file = await fm.save_file(envelope, peer)
    spooled_files = fm.get_files()

    assert len(spooled_files) == 1
    assert spooled_files[0].name == saved_file.name
