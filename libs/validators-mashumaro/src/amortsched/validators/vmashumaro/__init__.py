"""Mashumaro-based Validator[T] implementation."""

import re
from typing import Any, Generic, TypeVar

from mashumaro.codecs import BasicDecoder, BasicEncoder

from amortsched.core.errors import ValidationError

T = TypeVar("T")

_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")


def _to_snake(name: str) -> str:
    return _CAMEL_RE.sub(r"\1_\2", name).lower()


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _remap_keys(data: Any, key_fn: Any) -> Any:
    if isinstance(data, dict):
        return {key_fn(k): _remap_keys(v, key_fn) for k, v in data.items()}
    if isinstance(data, list):
        return [_remap_keys(item, key_fn) for item in data]
    return data


class MashumaroValidator(Generic[T]):
    """Validator[T] implementation backed by mashumaro."""

    def __init__(self, schema_type: type[T]) -> None:
        self._schema_type = schema_type
        self._decoder = BasicDecoder(schema_type)
        self._encoder = BasicEncoder(schema_type)

    def validate(self, data: dict[str, Any]) -> T:
        """Parse and validate data into a shared schema instance."""
        try:
            return self._decoder.decode(_remap_keys(data, _to_snake))
        except Exception as exc:
            raise ValidationError(
                errors=[{"message": str(exc)}],
                message="Validation failed",
            ) from exc

    def serialize(self, obj: T) -> dict[str, Any]:
        """Serialize a shared schema instance to a camelCase dict."""
        return _remap_keys(self._encoder.encode(obj), _to_camel)
