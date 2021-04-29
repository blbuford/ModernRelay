import builtins
import inspect
import io
import os
import socket
from contextlib import suppress
from smtplib import (
    SMTP as SMTPClient,
)
from typing import Callable, Generator, Any, NamedTuple, Optional, Type

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from pathlib import Path

from aiosmtpd.smtp import Envelope
from apscheduler.schedulers.base import BaseScheduler
from asynctest import mock, MagicMock, CoroutineMock

from ModernRelay.auth import Authenticator
import aiofiles

__all__ = [
    "controller_data",
    "handler_data",
    "Global"
]

from ModernRelay.file_manager import FileManager

controller_data = pytest.mark.controller_data
handler_data = pytest.mark.handler_data


class HostPort(NamedTuple):
    host: str = "localhost"
    port: int = 8025


class Global:
    SrvAddr: HostPort = HostPort()
    FQDN: str = socket.getfqdn()

    @classmethod
    def set_addr_from(cls, contr: Controller):
        cls.SrvAddr = HostPort(contr.hostname, contr.port)


@pytest.fixture
def client(request: pytest.FixtureRequest) -> Generator[SMTPClient, None, None]:
    """
    Generic SMTP Client,
    will connect to the ``host:port`` defined in ``Global.SrvAddr``
    unless overriden using :func:`client_data` marker.
    """
    marker = request.node.get_closest_marker("client_data")
    if marker:
        markerdata = marker.kwargs or {}
    else:
        markerdata = {}
    addrport = markerdata.get("connect_to", Global.SrvAddr)
    with SMTPClient(*addrport) as client:
        yield client


@pytest.fixture
def get_controller(request: pytest.FixtureRequest) -> Callable[..., Controller]:
    """
    Provides a function that will return an instance of a controller.
    Default class of the controller is Controller,
    but can be changed via the ``class_`` parameter to the function,
    or via the ``class_`` parameter of :func:`controller_data`
    Example usage::
        def test_case(get_controller):
            handler = SomeHandler()
            controller = get_controller(handler, class_=SomeController)
            ...
    """
    default_class = Controller
    marker = request.node.get_closest_marker("controller_data")
    if marker and marker.kwargs:
        # Must copy so marker data do not change between test cases if marker is
        # applied to test class
        markerdata = marker.kwargs.copy()
    else:
        markerdata = {}

    def getter(
            handler: Any,
            class_: Optional[Type[Controller]] = None,
            **server_kwargs,
    ) -> Controller:
        """
        :param handler: The handler object
        :param class_: If set to None, check controller_data(class_).
            If both are none, defaults to Controller.
        """
        assert not inspect.isclass(handler)
        marker_class: Optional[Type[Controller]]
        marker_class = markerdata.pop("class_", default_class)
        class_ = class_ or marker_class
        if class_ is None:
            raise RuntimeError(
                f"Fixture '{request.fixturename}' needs controller_data to specify "
                f"what class to use"
            )
        ip_port: HostPort = markerdata.pop("host_port", HostPort())
        # server_kwargs takes precedence, so it's rightmost (PEP448)
        server_kwargs = {**markerdata, **server_kwargs}
        server_kwargs.setdefault("hostname", ip_port.host)
        server_kwargs.setdefault("port", ip_port.port)
        return class_(
            handler,
            **server_kwargs,
        )

    return getter


@pytest.fixture
def get_handler(request: pytest.FixtureRequest) -> Callable:
    """
    Provides a function that will return an instance of
    a :ref:`handler class <handlers>`.
    Default class of the handler is Sink,
    but can be changed via the ``class_`` parameter to the function,
    or via the ``class_`` parameter of :func:`handler_data`
    Example usage::
        def test_case(get_handler):
            handler = get_handler(class_=SomeHandler)
            controller = Controller(handler)
            ...
    """
    default_class = Sink
    marker = request.node.get_closest_marker("handler_data")
    if marker and marker.kwargs:
        # Must copy so marker data do not change between test cases if marker is
        # applied to test class
        markerdata = marker.kwargs.copy()
    else:
        markerdata = {}

    def getter(*args, **kwargs) -> Any:
        if marker:
            class_ = markerdata.pop("class_", default_class)
            # *args overrides args_ in handler_data()
            args_ = markerdata.pop("args_", tuple())
            # Do NOT inline the above into the line below! We *need* to pop "args_"!
            args = args or args_
            # **kwargs override markerdata, so it's rightmost (PEP448)
            kwargs = {**markerdata, **kwargs}
        else:
            class_ = default_class
        # noinspection PyArgumentList
        return class_(*args, **kwargs)

    return getter


@pytest.fixture
def modern_relay_controller(
        get_handler: Callable,
        get_controller: Callable[..., Controller]
) -> Generator[Controller, None, None]:
    handler = get_handler()
    controller = get_controller(
        handler,
        decode_data=True,
        enable_SMTPUTF8=True,
        auth_require_tls=False,
        authenticator=Authenticator(str(Path(__file__).parent / "test.db~")),
    )
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    # Some test cases need to .stop() the controller inside themselves
    # in such cases, we must suppress Controller's raise of AssertionError
    # because Controller doesn't like .stop() to be invoked more than once
    with suppress(AssertionError):
        controller.stop()


def patch_open(open_func, files):
    def open_patched(path, mode='r', buffering=-1, encoding=None,
                     errors=None, newline=None, closefd=True,
                     opener=None):
        if 'w' in mode and not os.path.isfile(path):
            files.append(path)
        return open_func(path, mode=mode, buffering=buffering,
                         encoding=encoding, errors=errors,
                         newline=newline, closefd=closefd,
                         opener=opener)

    return open_patched


@pytest.fixture
def cleanup_files(monkeypatch):
    files = []
    monkeypatch.setattr(builtins, 'open', patch_open(builtins.open, files))
    monkeypatch.setattr(io, 'open', patch_open(io.open, files))
    monkeypatch.setattr(aiofiles, 'open', patch_open(aiofiles.open, files))
    yield
    for file in files:
        os.remove(file)


@pytest.fixture
def envelope():
    env = Envelope()
    return env


@pytest.fixture
def file_manager():
    def inner(encrypted):
        return FileManager(encrypted)

    return inner


@pytest.fixture
def spool():
    return Path(__file__).parent.parent.parent / 'spool'


@pytest.fixture
def spooled_file():
    return Path(__file__).parent / 'test_files' / "good-spooled-email-172-16-128-109"


@pytest.fixture
def spooled_file_peer_130():
    return Path(__file__).parent / 'test_files' / "good-spooled-email-172-16-130-109"


@pytest.fixture
def spooled_file_bad_peer():
    return Path(__file__).parent / 'test_files' / "bad-spooled-email-no-peer"


@pytest.fixture
def spooled_file_bad_b64():
    return Path(__file__).parent / 'test_files' / "bad-spooled-email-decode-error"


@pytest.fixture
async def envelope_peer_spooled(file_manager, spooled_file):
    fm = file_manager(encrypted=False)
    return await fm.open_file(spooled_file)


@pytest.fixture
def envelope_attachment(envelope_peer_spooled):
    envelope, _ = envelope_peer_spooled
    return envelope


@pytest.fixture
def mock_aiofiles_oserror():
    aiofiles.threadpool.wrap.register(mock.MagicMock)(
        lambda *args, **kwargs: aiofiles.threadpool.AsyncBufferedIOBase(*args, **kwargs))
    mock_file = mock.CoroutineMock()

    mock_file.__aenter__ = mock.CoroutineMock()
    mock_file.__aenter__.side_effect = OSError
    mock_file.__aexit__ = mock.CoroutineMock()

    return mock_file


@pytest.fixture
def mock_file_path():
    return MagicMock(Path)


@pytest.fixture
def mock_file_manager(envelope_peer_spooled, mock_file_path):
    file_manager = MagicMock(FileManager)
    file_manager.open_file = CoroutineMock()
    file_manager.open_file.return_value = envelope_peer_spooled
    file_manager.save_file = CoroutineMock()
    file_manager.save_file.return_value = mock_file_path
    file_manager._file_path = mock_file_path

    return file_manager


@pytest.fixture
def mock_scheduler():
    scheduler = MagicMock(BaseScheduler)
    scheduler.remove_job = MagicMock()
    scheduler.add_job = MagicMock()

    return scheduler
