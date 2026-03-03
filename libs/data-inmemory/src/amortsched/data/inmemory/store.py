"""Shared in-memory storage and relationship configuration."""

import uuid
from dataclasses import dataclass, field

from amortsched.core.entities import Plan, Profile, Schedule, User


@dataclass(frozen=True, slots=True)
class Relationship:
    """Declarative relationship config for in-memory repositories.

    Attributes:
        key: Attribute name on InMemoryStore (e.g. "plans", "users").
        entity: Related entity class.
        link_field: Foreign key field name. For many=True, the field is on
            the related entity. For many=False, the field is on this entity.
        many: True for to-many, False for to-one.
        reverse: True for reverse to-one lookups (FK is on related side).
    """

    key: str
    entity: type
    link_field: str
    many: bool = False
    reverse: bool = False


@dataclass
class InMemoryStore:
    """Single backing storage for all in-memory repositories.

    Emulates a database: one storage engine, multiple "tables".
    """

    users: dict[uuid.UUID, User] = field(default_factory=dict)
    plans: dict[uuid.UUID, Plan] = field(default_factory=dict)
    email_index: dict[str, uuid.UUID] = field(default_factory=dict)
    schedules: dict[uuid.UUID, Schedule] = field(default_factory=dict)
    profiles: dict[uuid.UUID, Profile] = field(default_factory=dict)
    user_profile_index: dict[uuid.UUID, uuid.UUID] = field(default_factory=dict)  # user_id -> profile_id
