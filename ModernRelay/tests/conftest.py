import inspect
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
from ModernRelay.auth import Authenticator

__all__ = [
    "controller_data",
    "handler_data",
    "Global"
]

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
