import datetime
import enum
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, runtime_checkable

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.errors import (
    DuplicatePlanError,
    DuplicateProfileError,
    PlanAssociationError,
    ProfileAssociationError,
    ScheduleAssociationError,
    UnboundPlanError,
    UnboundProfileError,
    UnboundScheduleError,
    UserAssociationError,
)
from amortsched.core.utils import now
from amortsched.core.values import (
    EarlyPaymentFees,
    Installment,
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
)


@runtime_checkable
class Entity(Protocol):
    id: uuid.UUID


@dataclass(kw_only=True, slots=True)
class Schedule:
    id: uuid.UUID = field(default_factory=uuid.uuid7)
    plan_id: uuid.UUID
    installments: list[Installment]
    totals: ScheduleTotals | None = None
    generated_at: datetime.datetime = field(default_factory=now)
    is_deleted: bool = False

    _revision: int = field(default=0, init=False, repr=False)
    _plan: Plan | None = field(default=None, init=False, repr=False)

    @property
    def plan(self) -> Plan:
        if self._plan is None:
            raise UnboundScheduleError(schedule_id=self.id)
        return self._plan

    @plan.setter
    def plan(self, plan: Plan | None) -> None:
        self._plan = plan


@dataclass(kw_only=True, slots=True)
class RefreshToken:
    id: uuid.UUID = field(default_factory=uuid.uuid7)
    user_id: uuid.UUID
    token_hash: str
    family_id: uuid.UUID
    expires_at: datetime.datetime
    used_at: datetime.datetime | None = None
    revoked_at: datetime.datetime | None = None
    created_at: datetime.datetime = field(default_factory=now)


@dataclass(kw_only=True, slots=True)
class Plan:
    class Status(enum.StrEnum):
        Draft = "draft"
        Saved = "saved"

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

    is_deleted: bool = False

    created_at: datetime.datetime = field(default_factory=now)
    updated_at: datetime.datetime = field(default_factory=now)

    _revision: int = field(default=0, init=False, repr=False)
    _user: User | None = field(default=None, init=False, repr=False)
    _schedules: list[Schedule] = field(default_factory=list, init=False, repr=False)

    @property
    def user(self) -> User:
        if self._user is None:
            raise UnboundPlanError(plan_id=self.id)
        return self._user

    @user.setter
    def user(self, user: User | None) -> None:
        self._user = user

    def add_user(self, user: User) -> None:
        if user.id != self.user_id:
            raise UserAssociationError(plan_id=self.id, plan_user_id=self.user_id, user_id=user.id)
        self._user = user

    @property
    def schedules(self) -> list[Schedule]:
        return self._schedules

    @schedules.setter
    def schedules(self, schedules: list[Schedule]) -> None:
        self._schedules = schedules

    def add_schedule(self, schedule: Schedule) -> None:
        if schedule.plan_id != self.id:
            raise ScheduleAssociationError(
                schedule_id=schedule.id, expected_plan_id=schedule.plan_id, actual_plan_id=self.id
            )
        schedule._plan = self
        self._schedules.append(schedule)

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

    def generate(self) -> Schedule:
        schedule_engine = self.to_schedule()
        installments = list(schedule_engine.generate(self.start_date))
        totals = schedule_engine.last_totals
        schedule = Schedule(plan_id=self.id, installments=installments, totals=totals)
        schedule.plan = self
        return schedule

    def touch(self) -> None:
        self.updated_at = now()


@dataclass(kw_only=True, slots=True)
class Profile:
    id: uuid.UUID = field(default_factory=uuid.uuid7)
    user_id: uuid.UUID
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None

    created_at: datetime.datetime = field(default_factory=now)
    updated_at: datetime.datetime = field(default_factory=now)

    _revision: int = field(default=0, init=False, repr=False)
    _user: User | None = field(default=None, init=False, repr=False)

    @property
    def user(self) -> User:
        if self._user is None:
            raise UnboundProfileError(profile_id=self.id)
        return self._user

    @user.setter
    def user(self, user: User | None) -> None:
        self._user = user

    def touch(self) -> None:
        self.updated_at = now()


@dataclass(kw_only=True, slots=True)
class User:
    id: uuid.UUID = field(default_factory=uuid.uuid7)

    email: str
    name: str

    is_active: bool = True

    password_hash: str = field(default="", repr=False)

    created_at: datetime.datetime = field(default_factory=now)
    updated_at: datetime.datetime = field(default_factory=now)

    _revision: int = field(default=0, init=False, repr=False)
    _plans: list[Plan] = field(default_factory=list, init=False, repr=False)
    _profile: Profile | None = field(default=None, init=False, repr=False)

    @property
    def plans(self) -> list[Plan]:
        return self._plans

    @plans.setter
    def plans(self, plans: list[Plan]) -> None:
        self._plans = plans

    @property
    def profile(self) -> Profile | None:
        return self._profile

    @profile.setter
    def profile(self, profile: Profile | None) -> None:
        self._profile = profile

    def add_profile(self, profile: Profile) -> None:
        if profile.user_id != self.id:
            raise ProfileAssociationError(
                profile_id=profile.id, expected_user_id=profile.user_id, actual_user_id=self.id
            )
        if self._profile is not None:
            raise DuplicateProfileError(user_id=self.id)
        profile._user = self
        self._profile = profile

    def add_plan(self, plan: Plan) -> None:
        if plan.user_id != self.id:
            raise PlanAssociationError(plan_id=plan.id, expected_user_id=plan.user_id, actual_user_id=self.id)
        if any(p.id == plan.id for p in self._plans):
            raise DuplicatePlanError(plan_id=plan.id, user_id=self.id)
        plan._user = self
        self._plans.append(plan)

    def add_plans(self, plans: Sequence[Plan]) -> None:
        for plan in plans:
            self.add_plan(plan)

    def touch(self) -> None:
        self.updated_at = now()
