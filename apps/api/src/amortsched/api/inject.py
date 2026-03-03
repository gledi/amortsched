"""Dependency injection decorator for Starlette route handlers."""

import functools
import inspect
from typing import Any, get_type_hints

from starlette.requests import Request
from starlette.websockets import WebSocket

_SKIP_TYPES: set[type] = {Request, WebSocket}


def _get_injectables(fn: Any) -> tuple[int, tuple[tuple[str, Any], ...]]:
    """Return (request_index, injectable_params) for a function.

    request_index is the positional index of the Request parameter.
    injectable_params is a tuple of (name, type) for params to resolve.
    """
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    request_index = -1
    injectables: list[tuple[str, type]] = []

    for i, name in enumerate(sig.parameters):
        if name == "self":
            continue
        hint = hints.get(name)
        if hint is None:
            continue
        if hint in _SKIP_TYPES or (isinstance(hint, type) and issubclass(hint, tuple(_SKIP_TYPES))):
            request_index = i
            continue
        injectables.append((name, hint))

    return request_index, tuple(injectables)


def inject(fn: Any) -> Any:
    """Decorator that resolves parameters from the rodi container.

    Inspects type annotations at decoration time. At call time, finds the
    Request in the positional args, gets the container from
    request.app.state.container, and resolves each injectable parameter.

    Skips: self, Request, WebSocket, unannotated parameters.
    """
    request_index, injectables = _get_injectables(fn)

    if not injectables:
        return fn

    if request_index < 0:
        raise TypeError(
            f"@inject on {fn.__qualname__}: found injectable parameters "
            f"but no Request/WebSocket parameter to locate the container"
        )

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request = args[request_index]
            container = request.app.state.container
            for name, hint in injectables:
                if name not in kwargs:
                    kwargs[name] = container.resolve(hint)
            return await fn(*args, **kwargs)

        return async_wrapper

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        request: Request = args[request_index]
        container = request.app.state.container
        for name, hint in injectables:
            if name not in kwargs:
                kwargs[name] = container.resolve(hint)
        return fn(*args, **kwargs)

    return sync_wrapper
