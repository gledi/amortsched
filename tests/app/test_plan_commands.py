import datetime
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from amortsched.app.commands.plans import CreatePlanCommand, CreatePlanHandler
from amortsched.core.errors import ValidationError
from amortsched.core.values import Term


@pytest.mark.anyio
async def test_create_plan_rejects_negative_upfront_fees_before_persisting():
    repo = SimpleNamespace(add=AsyncMock())
    handler = CreatePlanHandler(repo)
    command = CreatePlanCommand(
        user_id=uuid.uuid4(),
        name="Offer",
        amount=Decimal("100000"),
        term=Term(15),
        interest_rate=Decimal("4.5"),
        start_date=datetime.date(2026, 1, 1),
        upfront_fees=Decimal("-0.01"),
    )

    with pytest.raises(ValidationError):
        await handler.handle(command)

    repo.add.assert_not_awaited()


@pytest.mark.anyio
async def test_create_plan_normalizes_lender_and_preserves_upfront_fees():
    captured_plans = []

    def capture(plan):
        captured_plans.append(plan)
        return plan

    repo = SimpleNamespace(add=AsyncMock(side_effect=capture))
    handler = CreatePlanHandler(repo)
    command = CreatePlanCommand(
        user_id=uuid.uuid4(),
        name="Offer",
        amount=Decimal("100000"),
        term=Term(15),
        interest_rate=Decimal("4.5"),
        start_date=datetime.date(2026, 1, 1),
        lender="  Bank Alpha  ",
        upfront_fees=Decimal("25.00"),
    )

    plan = await handler.handle(command)

    assert captured_plans == [plan]
    assert plan.lender == "Bank Alpha"
    assert plan.upfront_fees == Decimal("25.00")
