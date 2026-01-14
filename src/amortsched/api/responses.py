from decimal import Decimal

import orjson
from starlette.responses import Response


def _default(obj: object) -> object:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class ORJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: object) -> bytes:
        return orjson.dumps(content, default=_default)
