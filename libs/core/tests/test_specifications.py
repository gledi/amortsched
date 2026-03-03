from amortsched.core.specifications import And, Eq, Id, IsActive, Not, Or, Rel


def test_spec_eq_creates_with_field_and_value():
    spec = Eq("email", "a@b.com")
    assert spec.field == "email"
    assert spec.value == "a@b.com"


def test_spec_id_creates_with_id():
    spec = Id(42)
    assert spec.id == 42


def test_spec_and_via_operator():
    left = Eq("a", 1)
    right = Eq("b", 2)
    combined = left & right
    assert isinstance(combined, And)
    assert combined.left is left
    assert combined.right is right


def test_spec_or_via_operator():
    left = Eq("a", 1)
    right = Eq("b", 2)
    combined = left | right
    assert isinstance(combined, Or)
    assert combined.left is left
    assert combined.right is right


def test_spec_not_via_invert():
    spec = Eq("a", 1)
    negated = ~spec
    assert isinstance(negated, Not)
    assert negated.spec is spec


def test_spec_rel_with_spec():
    inner = IsActive()
    rel = Rel("payments", inner)
    assert rel.relation == "payments"
    assert rel.spec is inner


def test_spec_rel_without_spec():
    rel = Rel("payments")
    assert rel.relation == "payments"
    assert rel.spec is None
