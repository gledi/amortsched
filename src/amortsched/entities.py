import datetime
import enum
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import NamedTuple, Self, TypedDict, cast

from amortsched.amortization import (
    AmortizationSchedule,
    EarlyPaymentFees,
    Installment,
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    RecurringExtraPayment,
    Term,
)
from amortsched.utils import now


@dataclass(kw_only=True, slots=True)
class User:
    class Item(NamedTuple):
        id: uuid.UUID
        email: str
        name: str
        is_active: bool
        password_hash: str
        created_at: datetime.datetime
        updated_at: datetime.datetime

    class Record(TypedDict):
        id: uuid.UUID
        email: str
        name: str
        is_active: bool
        password_hash: str
        created_at: datetime.datetime
        updated_at: datetime.datetime

    id: uuid.UUID = field(default_factory=uuid.uuid7)

    email: str
    name: str

    is_active: bool = True

    password_hash: str = field(default="", repr=False)

    created_at: datetime.datetime = field(default_factory=now)
    updated_at: datetime.datetime = field(default_factory=now)

    _plans: list[Plan] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def from_item(cls, item: Item) -> Self:
        return cls(
            id=item.id,
            email=item.email,
            name=item.name,
            is_active=item.is_active,
            password_hash=item.password_hash,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    def from_record(cls, record: Record) -> Self:
        return cls(**record)

    def to_item(self) -> Item:
        return cast(User.Item, asdict(self))

    def to_record(self) -> Record:
        return cast(User.Record, asdict(self))

    @property
    def plans(self) -> list[Plan]:
        return self._plans

    def add_plan(self, plan: Plan) -> None:
        if plan.user_id != self.id:
            raise ValueError("The plan does not belong to the user")
        self._plans.append(plan)

    def load_plans(self, plans: list[Plan]) -> None:
        if any(plan.user_id != self.id for plan in plans):
            raise ValueError("Some plans do not belong to the user")

        for plan in plans:
            self.add_plan(plan)


@dataclass(kw_only=True, slots=True)
class Plan:
    class Status(enum.StrEnum):
        Draft = "draft"
        Saved = "saved"

    class Item(NamedTuple):
        id: uuid.UUID
        user_id: uuid.UUID
        name: str
        slug: str
        amount: Decimal
        term: Term
        interest_rate: Decimal
        start_date: datetime.date
        early_payment_fees: EarlyPaymentFees
        interest_rate_application: InterestRateApplication
        status: Plan.Status
        one_time_extra_payments: list[OneTimeExtraPayment]
        recurring_extra_payments: list[RecurringExtraPayment]
        interest_rate_changes: list[InterestRateChange]
        created_at: datetime.datetime
        updated_at: datetime.datetime

    class Record(TypedDict):
        id: uuid.UUID
        user_id: uuid.UUID
        name: str
        slug: str
        amount: Decimal
        term: Term
        interest_rate: Decimal
        start_date: datetime.date
        early_payment_fees: EarlyPaymentFees
        interest_rate_application: InterestRateApplication
        status: Plan.Status
        one_time_extra_payments: list[OneTimeExtraPayment]
        recurring_extra_payments: list[RecurringExtraPayment]
        interest_rate_changes: list[InterestRateChange]
        created_at: datetime.datetime
        updated_at: datetime.datetime

    id: uuid.UUID = field(default_factory=uuid.uuid7)

    user_id: uuid.UUID

    name: str
    slug: str

    amount: Decimal
    term: Term
    interest_rate: Decimal
    start_date: datetime.date
    early_payment_fees: EarlyPaymentFees = field(default_factory=EarlyPaymentFees)
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth
    status: Status = Status.Draft
    one_time_extra_payments: list[OneTimeExtraPayment] = field(default_factory=list)
    recurring_extra_payments: list[RecurringExtraPayment] = field(default_factory=list)
    interest_rate_changes: list[InterestRateChange] = field(default_factory=list)

    created_at: datetime.datetime = field(default_factory=now)
    updated_at: datetime.datetime = field(default_factory=now)

    _user: User | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_item(cls, item: Item) -> Self:
        return cls(
            id=item.id,
            user_id=item.user_id,
            name=item.name,
            slug=item.slug,
            amount=item.amount,
            term=item.term,
            interest_rate=item.interest_rate,
            start_date=item.start_date,
            early_payment_fees=item.early_payment_fees,
            interest_rate_application=item.interest_rate_application,
            status=item.status,
            one_time_extra_payments=item.one_time_extra_payments,
            recurring_extra_payments=item.recurring_extra_payments,
            interest_rate_changes=item.interest_rate_changes,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    def from_record(cls, record: Record) -> Self:
        return cls(**record)

    @property
    def user(self) -> User:
        if self._user is None:
            raise ValueError("User not loaded")
        return self._user

    def to_item(self) -> Item:
        return cast(Plan.Item, asdict(self))

    def to_record(self) -> Record:
        return cast(Plan.Record, asdict(self))

    def bind_user(self, user: User) -> None:
        if user.id != self.user_id:
            raise ValueError("The user does not match the plan's user_id")
        self._user = user

    def to_schedule(self) -> AmortizationSchedule:
        schedule = AmortizationSchedule(
            amount=self.amount,
            term=self.term,
            interest_rate=self.interest_rate,
            early_payment_fees=self.early_payment_fees,
            interest_rate_application=self.interest_rate_application,
        )
        for otp in self.one_time_extra_payments:
            schedule.add_one_time_extra_payment(otp.date, otp.amount)
        for rp in self.recurring_extra_payments:
            schedule.add_recurring_extra_payment(rp.start_date, rp.amount, count=rp.count)
        for rc in self.interest_rate_changes:
            schedule.add_interest_rate_change(rc.effective_date, rc.yearly_interest_rate)
        return schedule

    def generate(self) -> list[Installment]:
        schedule = self.to_schedule()
        return list(schedule.generate(self.start_date))

    def touch(self) -> None:
        self.updated_at = datetime.datetime.now(datetime.UTC)
