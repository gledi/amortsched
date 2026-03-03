"""Update an existing plan."""

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.values import (
    Amount,
    EarlyPaymentFees,
    InterestRate,
    InterestRateApplication,
    Term,
    TermType,
)

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class UpdatePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    name: str | None = None
    amount: Amount | None = None
    term: TermType | None = None
    interest_rate: InterestRate | None = None
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFees | None = None
    interest_rate_application: InterestRateApplication | None = None


class UpdatePlanHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: UpdatePlanCommand) -> Plan:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        if command.name is not None:
            plan.name = command.name
        if command.amount is not None:
            plan.amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        if command.term is not None:
            if isinstance(command.term, int):
                plan.term = Term(command.term, 0)
            elif isinstance(command.term, tuple):
                plan.term = Term(*command.term)
            else:
                plan.term = command.term
        if command.interest_rate is not None:
            plan.interest_rate = (
                command.interest_rate if isinstance(command.interest_rate, Decimal) else Decimal(command.interest_rate)
            )
        if command.start_date is not None:
            plan.start_date = command.start_date
        if command.early_payment_fees is not None:
            plan.early_payment_fees = command.early_payment_fees
        if command.interest_rate_application is not None:
            plan.interest_rate_application = command.interest_rate_application
        plan.touch()
        self._plan_repo.update(plan)
        return plan
