import uuid
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .entities import RefreshToken

from .pagination import Paginated, Pagination
from .specifications import Specification


class ReadItemAsyncRepository[T](Protocol):
    async def get_by_id(self, id: uuid.UUID, specification: Specification[T] | None = None) -> T | None: ...

    async def get_one(self, specification: Specification[T]) -> T: ...

    async def get_one_or_none(self, specification: Specification[T]) -> T | None: ...


class ReadCollectionAsyncRepository[T](Protocol):
    def get_items(
        self,
        specification: Specification[T] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[T]: ...

    async def get_paginated(
        self,
        specification: Specification[T] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[T]: ...

    async def count(self, specification: Specification[T] | None = None) -> int: ...

    async def exists(self, specification: Specification[T]) -> bool: ...


class ReadAsyncRepository[T](ReadItemAsyncRepository[T], ReadCollectionAsyncRepository[T], Protocol):
    pass


class AddAsyncRepository[T](Protocol):
    async def add(self, item: T) -> T: ...


class UpdateAsyncRepository[T](Protocol):
    async def update(self, item: T) -> T: ...

    async def save(self, item: T, conflict_on: Sequence[str] = ("id",)) -> T: ...


class DeleteAsyncRepository[T](Protocol):
    async def delete(self, specification: Specification[T]) -> int: ...

    async def purge(self, specification: Specification[T]) -> int: ...


class WriteAsyncRepository[T](AddAsyncRepository[T], UpdateAsyncRepository[T], DeleteAsyncRepository[T], Protocol):
    pass


class AsyncRepository[T](ReadAsyncRepository[T], WriteAsyncRepository[T], Protocol):
    pass


class RefreshTokenRepository(AsyncRepository["RefreshToken"], Protocol):
    async def get_by_token_hash(self, token_hash: str) -> "RefreshToken | None": ...
    async def revoke_family(self, family_id: uuid.UUID) -> int: ...
    async def mark_used(self, token_id: uuid.UUID) -> None: ...


class BulkAddAsyncRepository[T](Protocol):
    async def bulk_add(self, items: Sequence[T]) -> Sequence[T]: ...


class BulkUpdateAsyncRepository[T](Protocol):
    async def bulk_update(self, items: Sequence[T]) -> Sequence[T]: ...

    async def bulk_save(self, items: Sequence[T], conflict_on: Sequence[str] = ("id",)) -> Sequence[T]: ...


class BulkAsyncRepository[T](BulkAddAsyncRepository[T], BulkUpdateAsyncRepository[T], Protocol):
    pass
