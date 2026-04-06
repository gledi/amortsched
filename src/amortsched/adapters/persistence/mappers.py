import datetime
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, cast

from amortsched.core.entities import Plan, Profile, Schedule, User
from amortsched.core.values import (
    Balance,
    EarlyPaymentFees,
    Installment,
    InterestRateApplication,
    InterestRateChange,
    Month,
    OneTimeExtraPayment,
    Payment,
    PaymentKind,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
)

type RowLike = Mapping[str, Any] | Any


def user_to_values(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def user_from_row(row: RowLike) -> User:
    return User(
        id=_row_value(row, "id"),
        email=_row_value(row, "email"),
        name=_row_value(row, "name"),
        is_active=_row_value(row, "is_active"),
        password_hash=_row_value(row, "password_hash"),
        created_at=_row_value(row, "created_at"),
        updated_at=_row_value(row, "updated_at"),
    )


def profile_to_values(profile: Profile) -> dict[str, object]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": profile.display_name,
        "phone": profile.phone,
        "locale": profile.locale,
        "timezone": profile.timezone,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def profile_from_row(row: RowLike) -> Profile:
    return Profile(
        id=_row_value(row, "id"),
        user_id=_row_value(row, "user_id"),
        display_name=_row_value(row, "display_name"),
        phone=_row_value(row, "phone"),
        locale=_row_value(row, "locale"),
        timezone=_row_value(row, "timezone"),
        created_at=_row_value(row, "created_at"),
        updated_at=_row_value(row, "updated_at"),
    )


def plan_to_values(plan: Plan) -> dict[str, object]:
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "name": plan.name,
        "slug": plan.slug,
        "amount": plan.amount,
        "term_years": plan.term.years,
        "term_months": plan.term.months,
        "interest_rate": plan.interest_rate,
        "start_date": plan.start_date,
        "early_payment_fees": _early_payment_fees_to_payload(plan.early_payment_fees),
        "interest_rate_application": plan.interest_rate_application.value,
        "status": plan.status.value,
        "one_time_extra_payments": [_one_time_extra_payment_to_payload(item) for item in plan.one_time_extra_payments],
        "recurring_extra_payments": [
            _recurring_extra_payment_to_payload(item) for item in plan.recurring_extra_payments
        ],
        "interest_rate_changes": [_interest_rate_change_to_payload(item) for item in plan.interest_rate_changes],
        "is_deleted": plan.is_deleted,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def plan_from_row(row: RowLike) -> Plan:
    return Plan(
        id=_row_value(row, "id"),
        user_id=_row_value(row, "user_id"),
        name=_row_value(row, "name"),
        slug=_row_value(row, "slug"),
        amount=Decimal(str(_row_value(row, "amount"))),
        term=Term(_row_value(row, "term_years"), _row_value(row, "term_months")),
        interest_rate=Decimal(str(_row_value(row, "interest_rate"))),
        start_date=_row_value(row, "start_date"),
        early_payment_fees=_early_payment_fees_from_payload(_row_value(row, "early_payment_fees")),
        interest_rate_application=InterestRateApplication(_row_value(row, "interest_rate_application")),
        status=Plan.Status(_row_value(row, "status")),
        one_time_extra_payments=[
            _one_time_extra_payment_from_payload(item)
            for item in cast(list[dict[str, Any]], _row_value(row, "one_time_extra_payments"))
        ],
        recurring_extra_payments=[
            _recurring_extra_payment_from_payload(item)
            for item in cast(list[dict[str, Any]], _row_value(row, "recurring_extra_payments"))
        ],
        interest_rate_changes=[
            _interest_rate_change_from_payload(item)
            for item in cast(list[dict[str, Any]], _row_value(row, "interest_rate_changes"))
        ],
        is_deleted=_row_value(row, "is_deleted"),
        created_at=_row_value(row, "created_at"),
        updated_at=_row_value(row, "updated_at"),
    )


def schedule_to_values(schedule: Schedule) -> dict[str, object]:
    return {
        "id": schedule.id,
        "plan_id": schedule.plan_id,
        "installments": [_installment_to_payload(item) for item in schedule.installments],
        "totals": None if schedule.totals is None else _totals_to_payload(schedule.totals),
        "generated_at": schedule.generated_at,
        "is_deleted": schedule.is_deleted,
    }


def schedule_from_row(row: RowLike) -> Schedule:
    installments_payload = cast(list[dict[str, Any]], _row_value(row, "installments"))
    totals_payload = cast(dict[str, Any] | None, _row_value(row, "totals"))
    return Schedule(
        id=_row_value(row, "id"),
        plan_id=_row_value(row, "plan_id"),
        installments=[_installment_from_payload(item) for item in installments_payload],
        totals=None if totals_payload is None else _totals_from_payload(totals_payload),
        generated_at=_row_value(row, "generated_at"),
        is_deleted=_row_value(row, "is_deleted"),
    )


def _row_value(row: RowLike, key: str) -> Any:
    if isinstance(row, Mapping):
        return row[key]
    return getattr(row, key)


def _decimal_to_string(value: Decimal) -> str:
    return str(value)


def _date_to_string(value: datetime.date) -> str:
    return value.isoformat()


def _date_from_string(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


def _early_payment_fees_to_payload(fees: EarlyPaymentFees) -> dict[str, str]:
    return {
        "fixed": _decimal_to_string(Decimal(fees.fixed)),
        "percent": _decimal_to_string(Decimal(fees.percent)),
    }


def _early_payment_fees_from_payload(payload: Mapping[str, Any]) -> EarlyPaymentFees:
    return EarlyPaymentFees(
        fixed=Decimal(str(payload["fixed"])),
        percent=Decimal(str(payload["percent"])),
    )


def _one_time_extra_payment_to_payload(payment: OneTimeExtraPayment) -> dict[str, str]:
    return {
        "date": _date_to_string(payment.date),
        "amount": _decimal_to_string(payment.amount),
    }


def _one_time_extra_payment_from_payload(payload: Mapping[str, Any]) -> OneTimeExtraPayment:
    return OneTimeExtraPayment(
        date=_date_from_string(str(payload["date"])),
        amount=Decimal(str(payload["amount"])),
    )


def _recurring_extra_payment_to_payload(payment: RecurringExtraPayment) -> dict[str, Any]:
    return {
        "start_date": _date_to_string(payment.start_date),
        "amount": _decimal_to_string(payment.amount),
        "count": payment.count,
    }


def _recurring_extra_payment_from_payload(payload: Mapping[str, Any]) -> RecurringExtraPayment:
    return RecurringExtraPayment(
        start_date=_date_from_string(str(payload["start_date"])),
        amount=Decimal(str(payload["amount"])),
        count=int(payload["count"]),
    )


def _interest_rate_change_to_payload(change: InterestRateChange) -> dict[str, str]:
    return {
        "effective_date": _date_to_string(change.effective_date),
        "yearly_interest_rate": _decimal_to_string(change.yearly_interest_rate),
    }


def _interest_rate_change_from_payload(payload: Mapping[str, Any]) -> InterestRateChange:
    return InterestRateChange(
        effective_date=_date_from_string(str(payload["effective_date"])),
        yearly_interest_rate=Decimal(str(payload["yearly_interest_rate"])),
    )


def _installment_to_payload(installment: Installment) -> dict[str, Any]:
    return {
        "i": installment.i,
        "year": installment.year,
        "month": int(installment.month),
        "payment": {
            "kind": installment.payment.kind.value,
            "principal": _decimal_to_string(installment.payment.principal),
            "interest": _decimal_to_string(installment.payment.interest),
            "fees": _decimal_to_string(installment.payment.fees),
        },
        "balance": {
            "before": _decimal_to_string(installment.balance.before),
            "after": _decimal_to_string(installment.balance.after),
        },
    }


def _installment_from_payload(payload: Mapping[str, Any]) -> Installment:
    payment_payload = cast(Mapping[str, Any], payload["payment"])
    balance_payload = cast(Mapping[str, Any], payload["balance"])
    return Installment(
        i=cast(int | None, payload["i"]),
        year=int(payload["year"]),
        month=Month(int(payload["month"])),
        payment=Payment(
            kind=PaymentKind(str(payment_payload["kind"])),
            principal=Decimal(str(payment_payload["principal"])),
            interest=Decimal(str(payment_payload["interest"])),
            fees=Decimal(str(payment_payload["fees"])),
        ),
        balance=Balance(
            before=Decimal(str(balance_payload["before"])),
            after=Decimal(str(balance_payload["after"])),
        ),
    )


def _totals_to_payload(totals: ScheduleTotals) -> dict[str, Any]:
    return {
        "principal": _decimal_to_string(totals.principal),
        "interest": _decimal_to_string(totals.interest),
        "fees": _decimal_to_string(totals.fees),
        "months": totals.months,
        "paid_off": totals.paid_off,
    }


def _totals_from_payload(payload: Mapping[str, Any]) -> ScheduleTotals:
    return ScheduleTotals(
        principal=Decimal(str(payload["principal"])),
        interest=Decimal(str(payload["interest"])),
        fees=Decimal(str(payload["fees"])),
        months=int(payload["months"]),
        paid_off=bool(payload["paid_off"]),
    )


__all__ = [
    "plan_from_row",
    "plan_to_values",
    "profile_from_row",
    "profile_to_values",
    "schedule_from_row",
    "schedule_to_values",
    "user_from_row",
    "user_to_values",
]
