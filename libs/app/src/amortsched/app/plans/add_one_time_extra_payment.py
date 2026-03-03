"""Add a one-time extra payment to a plan."""

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.values import Amount, OneTimeExtraPayment

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class AddOneTimeExtraPaymentCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    date: datetime.date
    amount: Amount


class AddOneTimeExtraPaymentHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: AddOneTimeExtraPaymentCommand) -> Plan:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.one_time_extra_payments.append(OneTimeExtraPayment(date=command.date, amount=amount))
        plan.touch()
        self._plan_repo.update(plan)
        return plan
