from amortsched.adapters.persistence.helpers import normalize_paginated_limit
from amortsched.core.pagination import Paginated, PaginatedMeta


def test_paginated_meta_handles_zero_limit():
    meta = PaginatedMeta(total=0, limit=0, offset=0)
    assert meta.page == 1
    assert meta.size == 0
    assert meta.has_next is False
    assert meta.has_previous is False


def test_normalize_paginated_limit():
    assert normalize_paginated_limit(None, 0) == 1
    assert normalize_paginated_limit(None, 50) == 50
    assert normalize_paginated_limit(20, 100) == 20
    assert normalize_paginated_limit(0, 10) == 1


def test_paginated_from_page_size():
    items = ["a", "b", "c"]
    p = Paginated.from_page_size(items, total=10, page=1, size=3)
    assert p.items == items
    assert p.meta.page == 1
    assert p.meta.size == 3
    assert p.meta.has_next is True
    assert p.meta.has_previous is False
    assert p.meta.next == 2


def test_paginated_from_limit_offset():
    items = ["x", "y"]
    p = Paginated.from_limit_offset(items, total=5, limit=2, offset=2)
    assert p.meta.page == 2
    assert p.meta.has_next is True
    assert p.meta.has_previous is True
