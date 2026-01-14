import datetime
from decimal import Decimal
from uuid import UUID

from amortsched.amortization import (
    Amount,
    EarlyPaymentFees,
    Installment,
    InterestRate,
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
    TermType,
)
from amortsched.entities import Plan, User
from amortsched.errors import AuthenticationError, PlanOwnershipError, UserNotFoundError
from amortsched.repositories import PlanRepository, UserRepository
from amortsched.security import PasswordHasher


class UserService:
    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    def register(self, *, email: str, name: str, password: str) -> User:
        password_hash = self._password_hasher.hash(password)
        user = User(email=email, name=name, password_hash=password_hash)
        self._user_repo.add(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        try:
            user = self._user_repo.get_by_email(email)
        except UserNotFoundError:
            raise AuthenticationError() from None
        if not self._password_hasher.verify(password, user.password_hash):
            raise AuthenticationError()
        return user

    def get_user(self, user_id: UUID) -> User:
        return self._user_repo.get_by_id(user_id)


class PlanService:
    def __init__(self, plan_repo: PlanRepository) -> None:
        self._plan_repo = plan_repo

    def create_plan(
        self,
        *,
        user_id: UUID,
        name: str,
        amount: Amount,
        term: TermType,
        interest_rate: InterestRate,
        start_date: datetime.date,
        early_payment_fees: EarlyPaymentFees | None = None,
        interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth,
    ) -> Plan:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        interest_rate = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if isinstance(term, int):
            term = Term(term, 0)
        elif isinstance(term, tuple):
            term = Term(*term)
        plan = Plan(
            user_id=user_id,
            name=name,
            slug=name.lower().replace(" ", "-"),
            amount=amount,
            term=term,
            interest_rate=interest_rate,
            start_date=start_date,
            early_payment_fees=early_payment_fees if early_payment_fees is not None else EarlyPaymentFees(),
            interest_rate_application=interest_rate_application,
        )
        self._plan_repo.add(plan)
        return plan

    def _get_owned_plan(self, plan_id: UUID, user_id: UUID) -> Plan:
        plan = self._plan_repo.get_by_id(plan_id)
        if plan.user_id != user_id:
            raise PlanOwnershipError(plan_id, user_id)
        return plan

    def get_plan(self, plan_id: UUID, user_id: UUID) -> Plan:
        return self._get_owned_plan(plan_id, user_id)

    def list_plans(self, user_id: UUID) -> list[Plan]:
        return self._plan_repo.list_by_user(user_id)

    def update_plan(
        self,
        plan_id: UUID,
        user_id: UUID,
        *,
        name: str | None = None,
        amount: Amount | None = None,
        term: TermType | None = None,
        interest_rate: InterestRate | None = None,
        start_date: datetime.date | None = None,
        early_payment_fees: EarlyPaymentFees | None = None,
        interest_rate_application: InterestRateApplication | None = None,
    ) -> Plan:
        plan = self._get_owned_plan(plan_id, user_id)
        if name is not None:
            plan.name = name
        if amount is not None:
            plan.amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        if term is not None:
            if isinstance(term, int):
                plan.term = Term(term, 0)
            elif isinstance(term, tuple):
                plan.term = Term(*term)
            else:
                plan.term = term
        if interest_rate is not None:
            plan.interest_rate = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if start_date is not None:
            plan.start_date = start_date
        if early_payment_fees is not None:
            plan.early_payment_fees = early_payment_fees
        if interest_rate_application is not None:
            plan.interest_rate_application = interest_rate_application
        plan.touch()
        self._plan_repo.update(plan)
        return plan

    def add_one_time_extra_payment(self, plan_id: UUID, user_id: UUID, date: datetime.date, amount: Amount) -> Plan:
        plan = self._get_owned_plan(plan_id, user_id)
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        plan.one_time_extra_payments.append(OneTimeExtraPayment(date=date, amount=amount))
        plan.touch()
        self._plan_repo.update(plan)
        return plan

    def add_recurring_extra_payment(
        self, plan_id: UUID, user_id: UUID, start_date: datetime.date, amount: Amount, count: int
    ) -> Plan:
        plan = self._get_owned_plan(plan_id, user_id)
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        plan.recurring_extra_payments.append(RecurringExtraPayment(start_date=start_date, amount=amount, count=count))
        plan.touch()
        self._plan_repo.update(plan)
        return plan

    def add_interest_rate_change(
        self, plan_id: UUID, user_id: UUID, effective_date: datetime.date, rate: InterestRate
    ) -> Plan:
        plan = self._get_owned_plan(plan_id, user_id)
        rate = rate if isinstance(rate, Decimal) else Decimal(rate)
        plan.interest_rate_changes.append(InterestRateChange(effective_date=effective_date, yearly_interest_rate=rate))
        plan.interest_rate_changes.sort(key=lambda c: c.effective_date)
        plan.touch()
        self._plan_repo.update(plan)
        return plan

    def save_plan(self, plan_id: UUID, user_id: UUID) -> Plan:
        plan = self._get_owned_plan(plan_id, user_id)
        plan.status = Plan.Status.Saved
        plan.touch()
        self._plan_repo.update(plan)
        return plan

    def delete_plan(self, plan_id: UUID, user_id: UUID) -> None:
        self._get_owned_plan(plan_id, user_id)
        self._plan_repo.remove(plan_id)

    def generate_schedule(self, plan_id: UUID, user_id: UUID) -> tuple[list[Installment], ScheduleTotals | None]:
        plan = self._get_owned_plan(plan_id, user_id)
        schedule = plan.to_schedule()
        installments = list(schedule.generate(plan.start_date))
        return installments, schedule.last_totals
