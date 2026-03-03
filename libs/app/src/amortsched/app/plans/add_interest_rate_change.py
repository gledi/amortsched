"""Add an interest rate change to a plan."""

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.values import InterestRate, InterestRateChange

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class AddInterestRateChangeCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    effective_date: datetime.date
    rate: InterestRate


class AddInterestRateChangeHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: AddInterestRateChangeCommand) -> Plan:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        rate = command.rate if isinstance(command.rate, Decimal) else Decimal(command.rate)
        plan.interest_rate_changes.append(
            InterestRateChange(effective_date=command.effective_date, yearly_interest_rate=rate)
        )
        plan.interest_rate_changes.sort(key=lambda c: c.effective_date)
        plan.touch()
        self._plan_repo.update(plan)
        return plan
