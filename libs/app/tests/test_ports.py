"""Tests for application layer port protocols."""

from dataclasses import dataclass
from typing import Any

from amortsched.app.ports import Validator


@dataclass(frozen=True, slots=True)
class _FakeSchema:
    name: str


class _FakeValidator:
    def validate(self, data: dict[str, Any]) -> _FakeSchema:
        return _FakeSchema(name=data["name"])

    def serialize(self, obj: _FakeSchema) -> dict[str, Any]:
        return {"name": obj.name}


def test_validator_protocol_is_satisfied_by_structural_subtype():
    v: Validator[_FakeSchema] = _FakeValidator()
    result = v.validate({"name": "test"})
    assert result == _FakeSchema(name="test")


def test_validator_serialize_returns_dict():
    v: Validator[_FakeSchema] = _FakeValidator()
    result = v.serialize(_FakeSchema(name="hello"))
    assert result == {"name": "hello"}
