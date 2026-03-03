"""Add a recurring extra payment to a plan."""

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.values import Amount, RecurringExtraPayment

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class AddRecurringExtraPaymentCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    start_date: datetime.date
    amount: Amount
    count: int


class AddRecurringExtraPaymentHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: AddRecurringExtraPaymentCommand) -> Plan:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.recurring_extra_payments.append(
            RecurringExtraPayment(start_date=command.start_date, amount=amount, count=command.count)
        )
        plan.touch()
        self._plan_repo.update(plan)
        return plan
