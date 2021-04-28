import pytest
from asynctest import mock


class TestFileManager:

    @pytest.mark.asyncio
    async def test_save_file_success(self, envelope_peer_spooled, file_manager, cleanup_files):
        fm = file_manager(encrypted=False)
        envelope, peer = envelope_peer_spooled

        result = await fm.save_file(envelope, peer)

        assert result
        assert result.parent.name == "spool"

    @pytest.mark.asyncio
    async def test_save_file_type_error(self, envelope_peer_spooled, file_manager, cleanup_files, caplog):
        fm = file_manager(encrypted=False)
        envelope, peer = envelope_peer_spooled
        envelope.original_content = None
        result = await fm.save_file(envelope, peer)

        assert result is None
        assert "while encoding the envelope" in caplog.text

    @pytest.mark.asyncio
    async def test_save_file_open_file_failure(self, envelope_peer_spooled, file_manager,
                                               mock_aiofiles_oserror, caplog):
        fm = file_manager(encrypted=False)
        envelope, peer = envelope_peer_spooled

        with mock.patch('aiofiles.open', return_value=mock_aiofiles_oserror):
            result = await fm.save_file(envelope, peer)

        assert result is None
        assert "while opening/writing" in caplog.text

    @pytest.mark.asyncio
    async def test_open_file_success(self, file_manager, spooled_file):
        fm = file_manager(encrypted=False)
        result = await fm.open_file(spooled_file)

        assert result
        envelope, peer = result
        assert isinstance(peer, str)
        assert len(peer) > 0
        assert envelope.mail_from
        assert envelope.rcpt_tos
        assert isinstance(envelope.original_content, bytes)
        assert isinstance(envelope.content, bytes)
        assert len(envelope.original_content) > 0

    @pytest.mark.asyncio
    async def test_open_file_open_file_failure(self, spooled_file, file_manager,
                                               mock_aiofiles_oserror, caplog):
        fm = file_manager(encrypted=False)

        with mock.patch('aiofiles.open', return_value=mock_aiofiles_oserror):
            result = await fm.open_file(spooled_file)

        assert result is None
        assert "while opening/reading" in caplog.text

    @pytest.mark.asyncio
    async def test_open_key_error(self, file_manager, spooled_file_bad_peer, caplog):
        fm = file_manager(encrypted=False)
        result = await fm.open_file(spooled_file_bad_peer)
        assert result is None
        assert "while accessing JSON keys" in caplog.text

    @pytest.mark.asyncio
    async def test_open_value_error(self, file_manager, spooled_file_bad_b64, caplog):
        fm = file_manager(encrypted=False)
        result = await fm.open_file(spooled_file_bad_b64)
        assert result is None
        assert "while decoding the envelope and peer" in caplog.text

    @pytest.mark.asyncio
    async def test_get_spooled_files(self, envelope_peer_spooled, file_manager, cleanup_files):
        envelope, peer = envelope_peer_spooled
        fm = file_manager(encrypted=False)

        saved_file = await fm.save_file(envelope, peer)
        spooled_files = fm.get_files()

        assert len(spooled_files) == 1
        assert spooled_files[0].name == saved_file.name
