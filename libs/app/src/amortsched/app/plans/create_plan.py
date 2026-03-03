"""Create a new amortization plan."""

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


@dataclass(frozen=True, slots=True)
class CreatePlanCommand:
    user_id: uuid.UUID
    name: str
    amount: Amount
    term: TermType
    interest_rate: InterestRate
    start_date: datetime.date
    early_payment_fees: EarlyPaymentFees | None = None
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth


class CreatePlanHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: CreatePlanCommand) -> Plan:
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        interest_rate = (
            command.interest_rate if isinstance(command.interest_rate, Decimal) else Decimal(command.interest_rate)
        )
        if isinstance(command.term, int):
            term = Term(command.term, 0)
        elif isinstance(command.term, tuple):
            term = Term(*command.term)
        else:
            term = command.term
        plan = Plan(
            user_id=command.user_id,
            name=command.name,
            slug=command.name.lower().replace(" ", "-"),
            amount=amount,
            term=term,
            interest_rate=interest_rate,
            start_date=command.start_date,
            early_payment_fees=command.early_payment_fees
            if command.early_payment_fees is not None
            else EarlyPaymentFees(),
            interest_rate_application=command.interest_rate_application,
        )
        self._plan_repo.add(plan)
        return plan
