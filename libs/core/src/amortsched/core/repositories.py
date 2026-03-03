import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Protocol

from .pagination import Paginated, Pagination
from .specifications import Specification


class ReadItemRepository[T](Protocol):
    def get_by_id(self, id: uuid.UUID, specification: Specification[T] | None = None) -> T | None: ...

    def get_one(self, specification: Specification[T]) -> T: ...

    def get_one_or_none(self, specification: Specification[T]) -> T | None: ...


class ReadCollectionRepository[T](Protocol):
    def get_items(
        self,
        specification: Specification[T] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> Iterator[T]: ...

    def get_paginated(
        self,
        specification: Specification[T] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[T]: ...

    def count(self, specification: Specification[T] | None = None) -> int: ...

    def exists(self, specification: Specification[T]) -> bool: ...


class ReadRepository[T](ReadItemRepository[T], ReadCollectionRepository[T], Protocol):
    pass


class AddRepository[T](Protocol):
    def add(self, item: T) -> T: ...


class UpdateRepository[T](Protocol):
    def update(self, item: T) -> T: ...

    def save(self, item: T) -> T: ...


class DeleteRepository[T](Protocol):
    def delete(self, specification: Specification[T]) -> int: ...

    def purge(self, specification: Specification[T]) -> int: ...


class WriteRepository[T](AddRepository[T], UpdateRepository[T], DeleteRepository[T], Protocol):
    pass


class Repository[T](ReadRepository[T], WriteRepository[T], Protocol):
    pass


class BulkAddRepository[T](Protocol):
    def bulk_add(self, items: Sequence[T]) -> Sequence[T]: ...


class BulkUpdateRepository[T](Protocol):
    def bulk_update(self, items: Sequence[T]) -> Sequence[T]: ...

    def bulk_save(self, items: Sequence[T]) -> Sequence[T]: ...


class BulkRepository[T](BulkAddRepository[T], BulkUpdateRepository[T], Protocol):
    pass


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

    async def save(self, item: T) -> T: ...


class DeleteAsyncRepository[T](Protocol):
    async def delete(self, specification: Specification[T]) -> int: ...

    async def purge(self, specification: Specification[T]) -> int: ...


class WriteAsyncRepository[T](AddAsyncRepository[T], UpdateAsyncRepository[T], DeleteAsyncRepository[T], Protocol):
    pass


class AsyncRepository[T](ReadAsyncRepository[T], WriteAsyncRepository[T], Protocol):
    pass


class BulkAddAsyncRepository[T](Protocol):
    async def bulk_add(self, items: Sequence[T]) -> Sequence[T]: ...


class BulkUpdateAsyncRepository[T](Protocol):
    async def bulk_update(self, items: Sequence[T]) -> Sequence[T]: ...

    async def bulk_save(self, items: Sequence[T]) -> Sequence[T]: ...


class BulkAsyncRepository[T](BulkAddAsyncRepository[T], BulkUpdateAsyncRepository[T], Protocol):
    pass
