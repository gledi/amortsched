"""Tests for the @inject decorator."""

import pytest
from amortsched.api.inject import inject
from starlette.requests import Request

pytestmark = pytest.mark.anyio


class FakeService:
    """A simple service to verify container resolution."""

    def greet(self) -> str:
        return "hello"


def _make_request_with_container(**instances: object) -> Request:
    """Build a minimal Starlette Request whose app.state.container resolves the given instances."""
    from rodi import Container
    from starlette.applications import Starlette

    container = Container()
    for instance in instances.values():
        container.add_instance(instance)

    app = Starlette()
    app.state.container = container

    scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [], "app": app}
    return Request(scope)


def test_sync_function_injection():
    @inject
    def handler(request: Request, service: FakeService) -> str:
        return service.greet()

    request = _make_request_with_container(service=FakeService())
    result = handler(request)
    assert result == "hello"


async def test_async_function_injection():
    @inject
    async def handler(request: Request, service: FakeService) -> str:
        return service.greet()

    request = _make_request_with_container(service=FakeService())
    result = await handler(request)
    assert result == "hello"


async def test_method_injection_on_endpoint():
    """Simulate HttpEndpoint: self is first arg, request is second."""

    class FakeEndpoint:
        @inject
        async def get(self, request: Request, service: FakeService) -> str:
            return service.greet()

    endpoint = FakeEndpoint()
    request = _make_request_with_container(service=FakeService())
    result = await endpoint.get(request)
    assert result == "hello"


def test_request_param_is_not_resolved():
    """Request should be passed through, not resolved from container."""

    @inject
    def handler(request: Request, service: FakeService) -> tuple:
        return (request, service)

    request = _make_request_with_container(service=FakeService())
    req_out, svc_out = handler(request)
    assert req_out is request
    assert isinstance(svc_out, FakeService)


def test_unannotated_params_are_skipped():
    """Parameters without type annotations should not be resolved."""

    @inject
    def handler(request: Request, extra, service: FakeService) -> str:
        return f"{extra}-{service.greet()}"

    request = _make_request_with_container(service=FakeService())
    result = handler(request, "value")
    assert result == "value-hello"


def test_unresolvable_type_raises():
    """If the container can't resolve a type, the error propagates."""
    from rodi import CannotResolveTypeException

    class NotRegistered:
        pass

    @inject
    def handler(request: Request, dep: NotRegistered) -> str:
        return "unreachable"

    request = _make_request_with_container()
    with pytest.raises(CannotResolveTypeException):
        handler(request)


def test_websocket_param_is_skipped():
    """WebSocket-typed parameters should not be resolved from the container."""
    from starlette.websockets import WebSocket

    @inject
    def handler(ws: WebSocket, service: FakeService) -> str:
        return service.greet()

    # Build a request-like scope but for websocket — we only need the container
    from rodi import Container
    from starlette.applications import Starlette

    container = Container()
    container.add_instance(FakeService())

    app = Starlette()
    app.state.container = container
    scope = {"type": "websocket", "path": "/", "query_string": b"", "headers": [], "app": app}

    async def _noop(*args: object) -> None:
        pass

    ws = WebSocket(scope, receive=_noop, send=_noop)
    result = handler(ws)
    assert result == "hello"


def test_inject_without_request_raises_type_error():
    """@inject on a function with injectables but no Request/WebSocket should fail at decoration time."""
    with pytest.raises(TypeError, match="no Request/WebSocket parameter"):

        @inject
        def handler(service: FakeService) -> str:
            return service.greet()


def test_preserves_function_name():
    @inject
    def my_handler(request: Request) -> str:
        return "ok"

    assert my_handler.__name__ == "my_handler"


def test_generic_type_resolution():
    """Subscripted generic types like Validator[T] should be resolvable."""
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Converter(Generic[T]):
        def __init__(self, target: type[T]) -> None:
            self.target = target

    class Payload:
        pass

    converter = Converter(Payload)

    from rodi import Container
    from starlette.applications import Starlette

    container = Container()
    container.add_instance(converter, declared_class=Converter[Payload])

    app = Starlette()
    app.state.container = container
    scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [], "app": app}
    request = Request(scope)

    @inject
    def handler(request: Request, conv: Converter[Payload]) -> type:
        return conv.target

    result = handler(request)
    assert result is Payload
