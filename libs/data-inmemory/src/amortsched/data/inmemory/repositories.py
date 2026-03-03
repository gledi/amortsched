import itertools
import uuid
from collections.abc import Iterator, Sequence
from typing import Any, ClassVar

from amortsched.core.entities import Plan, Profile, Schedule, User
from amortsched.core.errors import (
    DuplicateEmailError,
    PlanNotFoundError,
    ProfileNotFoundError,
    ScheduleNotFoundError,
    UserNotFoundError,
)
from amortsched.core.pagination import LimitOffset, PageSize, Paginated, Pagination
from amortsched.core.specifications import Rel, Specification

from .filters import extract_rels, to_filter
from .store import InMemoryStore, Relationship


class InMemoryUserRepository:
    _relationships: ClassVar[dict[str, Relationship]] = {
        "plans": Relationship(key="plans", entity=Plan, link_field="user_id", many=True),
        "profile": Relationship(key="profiles", entity=Profile, link_field="user_id", reverse=True),
    }

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _load_relations(self, entity: Any, rels: list[Rel]) -> None:
        for rel in rels:
            if rel.relation not in self._relationships:
                raise ValueError(f"Unknown relationship '{rel.relation}' for {type(entity).__name__}")
            config = self._relationships[rel.relation]
            collection: dict[uuid.UUID, object] = getattr(self._store, config.key)
            if config.many:
                related = [item for item in collection.values() if getattr(item, config.link_field) == entity.id]
                if rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    related = [item for item in related if predicate(item)]
                setattr(entity, rel.relation, related)
            else:
                if config.reverse:
                    related_item = None
                    for item in collection.values():
                        if getattr(item, config.link_field) == entity.id:
                            related_item = item
                            break
                else:
                    related_id = getattr(entity, config.link_field)
                    related_item = collection.get(related_id)
                if related_item is not None and rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    if not predicate(related_item):
                        related_item = None
                setattr(entity, rel.relation, related_item)

    def get_by_id(self, id: uuid.UUID, specification: Specification[User] | None = None) -> User | None:
        filter_spec, rels = extract_rels(specification)
        user = self._store.users.get(id)
        if user is None:
            return None
        if filter_spec is not None:
            predicate = to_filter(filter_spec)
            if not predicate(user):
                return None
        self._load_relations(user, rels)
        return user

    def get_one(self, specification: Specification[User]) -> User:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for user in self._store.users.values():
            if predicate(user):
                self._load_relations(user, rels)
                return user
        raise UserNotFoundError("matching specification")

    def get_one_or_none(self, specification: Specification[User]) -> User | None:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for user in self._store.users.values():
            if predicate(user):
                self._load_relations(user, rels)
                return user
        return None

    def get_items(
        self,
        specification: Specification[User] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> Iterator[User]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        items = (u for u in self._store.users.values() if predicate(u))
        if limit is not None:
            items = itertools.islice(items, limit)
        for user in items:
            self._load_relations(user, rels)
            yield user

    def get_paginated(
        self,
        specification: Specification[User] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[User]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        all_items = [u for u in self._store.users.values() if predicate(u)]
        total = len(all_items)

        match pagination:
            case PageSize(page=page, size=size):
                limit = size
                offset = (page - 1) * size
            case LimitOffset(limit=limit, offset=offset):
                pass
            case None:
                limit = total
                offset = 0

        page_items = all_items[offset : offset + limit]
        for user in page_items:
            self._load_relations(user, rels)
        return Paginated.from_limit_offset(page_items, total=total, limit=limit, offset=offset)

    def count(self, specification: Specification[User] | None = None) -> int:
        filter_spec, _rels = extract_rels(specification)
        if filter_spec is None:
            return len(self._store.users)
        predicate = to_filter(filter_spec)
        return sum(1 for u in self._store.users.values() if predicate(u))

    def exists(self, specification: Specification[User]) -> bool:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        return any(predicate(u) for u in self._store.users.values())

    def add(self, item: User) -> User:
        if item.email in self._store.email_index:
            raise DuplicateEmailError(item.email)
        self._store.users[item.id] = item
        self._store.email_index[item.email] = item.id
        return item

    def update(self, item: User) -> User:
        if item.id not in self._store.users:
            raise UserNotFoundError(item.id)
        existing_id = self._store.email_index.get(item.email)
        if existing_id is not None and existing_id != item.id:
            raise DuplicateEmailError(item.email)
        # Remove stale email index entry (handles both same-object and different-object cases)
        stale_emails = [
            email for email, uid in self._store.email_index.items() if uid == item.id and email != item.email
        ]
        for email in stale_emails:
            del self._store.email_index[email]
        self._store.email_index[item.email] = item.id
        self._store.users[item.id] = item
        return item

    def save(self, item: User) -> User:
        if item.id in self._store.users:
            return self.update(item)
        return self.add(item)

    def delete(self, specification: Specification[User]) -> int:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        to_remove = [uid for uid, user in self._store.users.items() if predicate(user)]
        for uid in to_remove:
            user = self._store.users.pop(uid)
            self._store.email_index.pop(user.email, None)
        return len(to_remove)

    def purge(self, specification: Specification[User]) -> int:
        return self.delete(specification)


class InMemoryPlanRepository:
    _relationships: ClassVar[dict[str, Relationship]] = {
        "user": Relationship(key="users", entity=User, link_field="user_id"),
        "schedules": Relationship(key="schedules", entity=Schedule, link_field="plan_id", many=True),
    }

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _load_relations(self, entity: Any, rels: list[Rel]) -> None:
        for rel in rels:
            if rel.relation not in self._relationships:
                raise ValueError(f"Unknown relationship '{rel.relation}' for {type(entity).__name__}")
            config = self._relationships[rel.relation]
            collection: dict[uuid.UUID, object] = getattr(self._store, config.key)
            if config.many:
                related = [item for item in collection.values() if getattr(item, config.link_field) == entity.id]
                if rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    related = [item for item in related if predicate(item)]
                setattr(entity, rel.relation, related)
            else:
                if config.reverse:
                    related_item = None
                    for item in collection.values():
                        if getattr(item, config.link_field) == entity.id:
                            related_item = item
                            break
                else:
                    related_id = getattr(entity, config.link_field)
                    related_item = collection.get(related_id)
                if related_item is not None and rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    if not predicate(related_item):
                        related_item = None
                setattr(entity, rel.relation, related_item)

    def get_by_id(self, id: uuid.UUID, specification: Specification[Plan] | None = None) -> Plan | None:
        filter_spec, rels = extract_rels(specification)
        plan = self._store.plans.get(id)
        if plan is None:
            return None
        if filter_spec is not None:
            predicate = to_filter(filter_spec)
            if not predicate(plan):
                return None
        self._load_relations(plan, rels)
        return plan

    def get_one(self, specification: Specification[Plan]) -> Plan:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for plan in self._store.plans.values():
            if predicate(plan):
                self._load_relations(plan, rels)
                return plan
        raise PlanNotFoundError("matching specification")

    def get_one_or_none(self, specification: Specification[Plan]) -> Plan | None:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for plan in self._store.plans.values():
            if predicate(plan):
                self._load_relations(plan, rels)
                return plan
        return None

    def get_items(
        self,
        specification: Specification[Plan] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> Iterator[Plan]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        items = (p for p in self._store.plans.values() if predicate(p))
        if limit is not None:
            items = itertools.islice(items, limit)
        for plan in items:
            self._load_relations(plan, rels)
            yield plan

    def get_paginated(
        self,
        specification: Specification[Plan] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[Plan]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        all_items = [p for p in self._store.plans.values() if predicate(p)]
        total = len(all_items)

        match pagination:
            case PageSize(page=page, size=size):
                limit = size
                offset = (page - 1) * size
            case LimitOffset(limit=limit, offset=offset):
                pass
            case None:
                limit = total
                offset = 0

        page_items = all_items[offset : offset + limit]
        for plan in page_items:
            self._load_relations(plan, rels)
        return Paginated.from_limit_offset(page_items, total=total, limit=limit, offset=offset)

    def count(self, specification: Specification[Plan] | None = None) -> int:
        filter_spec, _rels = extract_rels(specification)
        if filter_spec is None:
            return len(self._store.plans)
        predicate = to_filter(filter_spec)
        return sum(1 for p in self._store.plans.values() if predicate(p))

    def exists(self, specification: Specification[Plan]) -> bool:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        return any(predicate(p) for p in self._store.plans.values())

    def add(self, item: Plan) -> Plan:
        self._store.plans[item.id] = item
        return item

    def update(self, item: Plan) -> Plan:
        if item.id not in self._store.plans:
            raise PlanNotFoundError(item.id)
        self._store.plans[item.id] = item
        return item

    def save(self, item: Plan) -> Plan:
        if item.id in self._store.plans:
            return self.update(item)
        return self.add(item)

    def delete(self, specification: Specification[Plan]) -> int:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        to_remove = [pid for pid, plan in self._store.plans.items() if predicate(plan)]
        for pid in to_remove:
            del self._store.plans[pid]
        return len(to_remove)

    def purge(self, specification: Specification[Plan]) -> int:
        return self.delete(specification)


class InMemoryScheduleRepository:
    _relationships: ClassVar[dict[str, Relationship]] = {
        "plan": Relationship(key="plans", entity=Plan, link_field="plan_id"),
    }

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _load_relations(self, entity: Any, rels: list[Rel]) -> None:
        for rel in rels:
            if rel.relation not in self._relationships:
                raise ValueError(f"Unknown relationship '{rel.relation}' for {type(entity).__name__}")
            config = self._relationships[rel.relation]
            collection: dict[uuid.UUID, object] = getattr(self._store, config.key)
            if config.many:
                related = [item for item in collection.values() if getattr(item, config.link_field) == entity.id]
                if rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    related = [item for item in related if predicate(item)]
                setattr(entity, rel.relation, related)
            else:
                if config.reverse:
                    related_item = None
                    for item in collection.values():
                        if getattr(item, config.link_field) == entity.id:
                            related_item = item
                            break
                else:
                    related_id = getattr(entity, config.link_field)
                    related_item = collection.get(related_id)
                if related_item is not None and rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    if not predicate(related_item):
                        related_item = None
                setattr(entity, rel.relation, related_item)

    def get_by_id(self, id: uuid.UUID, specification: Specification[Schedule] | None = None) -> Schedule | None:
        filter_spec, rels = extract_rels(specification)
        schedule = self._store.schedules.get(id)
        if schedule is None:
            return None
        if filter_spec is not None:
            predicate = to_filter(filter_spec)
            if not predicate(schedule):
                return None
        self._load_relations(schedule, rels)
        return schedule

    def get_one(self, specification: Specification[Schedule]) -> Schedule:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for schedule in self._store.schedules.values():
            if predicate(schedule):
                self._load_relations(schedule, rels)
                return schedule
        raise ScheduleNotFoundError("matching specification")

    def get_one_or_none(self, specification: Specification[Schedule]) -> Schedule | None:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for schedule in self._store.schedules.values():
            if predicate(schedule):
                self._load_relations(schedule, rels)
                return schedule
        return None

    def get_items(
        self,
        specification: Specification[Schedule] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> Iterator[Schedule]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        items = (s for s in self._store.schedules.values() if predicate(s))
        if limit is not None:
            items = itertools.islice(items, limit)
        for schedule in items:
            self._load_relations(schedule, rels)
            yield schedule

    def get_paginated(
        self,
        specification: Specification[Schedule] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[Schedule]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        all_items = [s for s in self._store.schedules.values() if predicate(s)]
        total = len(all_items)

        match pagination:
            case PageSize(page=page, size=size):
                limit = size
                offset = (page - 1) * size
            case LimitOffset(limit=limit, offset=offset):
                pass
            case None:
                limit = total
                offset = 0

        page_items = all_items[offset : offset + limit]
        for schedule in page_items:
            self._load_relations(schedule, rels)
        return Paginated.from_limit_offset(page_items, total=total, limit=limit, offset=offset)

    def count(self, specification: Specification[Schedule] | None = None) -> int:
        filter_spec, _rels = extract_rels(specification)
        if filter_spec is None:
            return len(self._store.schedules)
        predicate = to_filter(filter_spec)
        return sum(1 for s in self._store.schedules.values() if predicate(s))

    def exists(self, specification: Specification[Schedule]) -> bool:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        return any(predicate(s) for s in self._store.schedules.values())

    def add(self, item: Schedule) -> Schedule:
        self._store.schedules[item.id] = item
        return item

    def update(self, item: Schedule) -> Schedule:
        if item.id not in self._store.schedules:
            raise ScheduleNotFoundError(item.id)
        self._store.schedules[item.id] = item
        return item

    def save(self, item: Schedule) -> Schedule:
        if item.id in self._store.schedules:
            return self.update(item)
        return self.add(item)

    def delete(self, specification: Specification[Schedule]) -> int:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        to_remove = [sid for sid, schedule in self._store.schedules.items() if predicate(schedule)]
        for sid in to_remove:
            del self._store.schedules[sid]
        return len(to_remove)

    def purge(self, specification: Specification[Schedule]) -> int:
        return self.delete(specification)


class InMemoryUserProfileRepository:
    _relationships: ClassVar[dict[str, Relationship]] = {
        "user": Relationship(key="users", entity=User, link_field="user_id"),
    }

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _load_relations(self, entity: Any, rels: list[Rel]) -> None:
        for rel in rels:
            if rel.relation not in self._relationships:
                raise ValueError(f"Unknown relationship '{rel.relation}' for {type(entity).__name__}")
            config = self._relationships[rel.relation]
            collection: dict[uuid.UUID, object] = getattr(self._store, config.key)
            if config.many:
                related = [item for item in collection.values() if getattr(item, config.link_field) == entity.id]
                if rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    related = [item for item in related if predicate(item)]
                setattr(entity, rel.relation, related)
            else:
                if config.reverse:
                    related_item = None
                    for item in collection.values():
                        if getattr(item, config.link_field) == entity.id:
                            related_item = item
                            break
                else:
                    related_id = getattr(entity, config.link_field)
                    related_item = collection.get(related_id)
                if related_item is not None and rel.spec is not None:
                    predicate = to_filter(rel.spec)
                    if not predicate(related_item):
                        related_item = None
                setattr(entity, rel.relation, related_item)

    def get_by_id(self, id: uuid.UUID, specification: Specification[Profile] | None = None) -> Profile | None:
        filter_spec, rels = extract_rels(specification)
        profile = self._store.profiles.get(id)
        if profile is None:
            return None
        if filter_spec is not None:
            predicate = to_filter(filter_spec)
            if not predicate(profile):
                return None
        self._load_relations(profile, rels)
        return profile

    def get_one(self, specification: Specification[Profile]) -> Profile:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for profile in self._store.profiles.values():
            if predicate(profile):
                self._load_relations(profile, rels)
                return profile
        raise ProfileNotFoundError("matching specification")

    def get_one_or_none(self, specification: Specification[Profile]) -> Profile | None:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        for profile in self._store.profiles.values():
            if predicate(profile):
                self._load_relations(profile, rels)
                return profile
        return None

    def get_items(
        self,
        specification: Specification[Profile] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> Iterator[Profile]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        items = (p for p in self._store.profiles.values() if predicate(p))
        if limit is not None:
            items = itertools.islice(items, limit)
        for profile in items:
            self._load_relations(profile, rels)
            yield profile

    def get_paginated(
        self,
        specification: Specification[Profile] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[Profile]:
        filter_spec, rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        all_items = [p for p in self._store.profiles.values() if predicate(p)]
        total = len(all_items)

        match pagination:
            case PageSize(page=page, size=size):
                limit = size
                offset = (page - 1) * size
            case LimitOffset(limit=limit, offset=offset):
                pass
            case None:
                limit = total
                offset = 0

        page_items = all_items[offset : offset + limit]
        for profile in page_items:
            self._load_relations(profile, rels)
        return Paginated.from_limit_offset(page_items, total=total, limit=limit, offset=offset)

    def count(self, specification: Specification[Profile] | None = None) -> int:
        filter_spec, _rels = extract_rels(specification)
        if filter_spec is None:
            return len(self._store.profiles)
        predicate = to_filter(filter_spec)
        return sum(1 for p in self._store.profiles.values() if predicate(p))

    def exists(self, specification: Specification[Profile]) -> bool:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        return any(predicate(p) for p in self._store.profiles.values())

    def add(self, item: Profile) -> Profile:
        self._store.profiles[item.id] = item
        self._store.user_profile_index[item.user_id] = item.id
        return item

    def update(self, item: Profile) -> Profile:
        if item.id not in self._store.profiles:
            raise ProfileNotFoundError(item.user_id)
        self._store.profiles[item.id] = item
        self._store.user_profile_index[item.user_id] = item.id
        return item

    def save(self, item: Profile) -> Profile:
        if item.id in self._store.profiles:
            return self.update(item)
        return self.add(item)

    def delete(self, specification: Specification[Profile]) -> int:
        filter_spec, _rels = extract_rels(specification)
        predicate = to_filter(filter_spec)
        to_remove = [pid for pid, profile in self._store.profiles.items() if predicate(profile)]
        for pid in to_remove:
            profile = self._store.profiles.pop(pid)
            self._store.user_profile_index.pop(profile.user_id, None)
        return len(to_remove)

    def purge(self, specification: Specification[Profile]) -> int:
        return self.delete(specification)
