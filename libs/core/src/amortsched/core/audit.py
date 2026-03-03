import datetime
import enum
import uuid
from dataclasses import dataclass, field

from amortsched.core.utils import now


class AuditAction(enum.StrEnum):
    Created = "created"
    Updated = "updated"
    Deleted = "deleted"
    Purged = "purged"


@dataclass(kw_only=True, slots=True)
class AuditEntry:
    id: uuid.UUID = field(default_factory=uuid.uuid7)
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    description: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    occurred_at: datetime.datetime = field(default_factory=now)
