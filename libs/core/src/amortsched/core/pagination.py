from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(kw_only=True, frozen=True)
class PageSize:
    page: int = field(default=1)
    size: int = field(default=20)
    order_by: str | Sequence[str] | None = field(default=None)


@dataclass(kw_only=True, frozen=True)
class LimitOffset:
    limit: int = field(default=20)
    offset: int = field(default=0)
    order_by: str | Sequence[str] | None = field(default=None)


type Pagination = PageSize | LimitOffset


@dataclass(kw_only=True, frozen=True)
class PageSizeMeta:
    page: int
    size: int


@dataclass(kw_only=True, frozen=True)
class LimitOffsetMeta:
    limit: int
    offset: int


@dataclass(kw_only=True, frozen=True)
class PaginatedMeta[T]:
    total: int
    limit: int
    offset: int

    next: int | None = None
    previous: int | None = None

    @property
    def has_next(self) -> bool:
        return self.next is not None

    @property
    def has_previous(self) -> bool:
        return self.previous is not None

    @property
    def page(self) -> int:
        return self.offset // self.limit + 1

    @property
    def size(self) -> int:
        return self.limit


@dataclass(kw_only=True, frozen=True)
class Paginated[T]:
    items: Sequence[T]
    meta: PaginatedMeta[T]

    @classmethod
    def from_page_size(cls, items: Sequence[T], total: int, page: int = 1, size: int = 20) -> Paginated[T]:
        offset = (page - 1) * size
        return cls(
            items=items,
            meta=PaginatedMeta(
                total=total,
                limit=size,
                offset=offset,
                next=page + 1 if offset + size < total else None,
                previous=page - 1 if page > 1 else None,
            ),
        )

    @classmethod
    def from_limit_offset(cls, items: Sequence[T], total: int, limit: int = 20, offset: int = 0) -> Paginated[T]:
        return cls(
            items=items,
            meta=PaginatedMeta(
                total=total,
                limit=limit,
                offset=offset,
                next=offset + limit if offset + limit < total else None,
                previous=offset - limit if offset > 0 else None,
            ),
        )
