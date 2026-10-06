import datetime
from collections.abc import Mapping
from decimal import Decimal
from typing import cast
from uuid import UUID

from amortsched.core.entities import AccountToken, Plan, Profile, RefreshToken, Schedule, User
from amortsched.core.values import (
    Balance,
    EarlyPaymentFees,
    HousingCosts,
    HousingPayment,
    Installment,
    InterestRateApplication,
    InterestRateChange,
    LoanType,
    Month,
    OneTimeExtraPayment,
    Payment,
    PaymentKind,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
)


def _decimal_to_string(value: Decimal) -> str:
    return str(value)


def _date_to_string(value: datetime.date) -> str:
    return value.isoformat()


def _date_from_string(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


def user_to_values(user: User) -> Mapping[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at,
        "password_hash": user.password_hash,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def user_from_row(row: Mapping[str, object]) -> User:
    return User(
        id=cast(UUID, row["id"]),
        email=cast(str, row["email"]),
        name=cast(str, row["name"]),
        is_active=cast(bool, row["is_active"]),
        email_verified_at=cast(datetime.datetime | None, row["email_verified_at"]),
        password_hash=cast(str, row["password_hash"]),
        created_at=cast(datetime.datetime, row["created_at"]),
        updated_at=cast(datetime.datetime, row["updated_at"]),
    )


def profile_to_values(profile: Profile) -> Mapping[str, object]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": profile.display_name,
        "phone": profile.phone,
        "locale": profile.locale,
        "timezone": profile.timezone,
        "currency": profile.currency,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def profile_from_row(row: Mapping[str, object]) -> Profile:
    return Profile(
        id=cast(UUID, row["id"]),
        user_id=cast(UUID, row["user_id"]),
        display_name=cast(str | None, row["display_name"]),
        phone=cast(str | None, row["phone"]),
        locale=cast(str | None, row["locale"]),
        timezone=cast(str | None, row["timezone"]),
        currency=cast(str | None, row["currency"]),
        created_at=cast(datetime.datetime, row["created_at"]),
        updated_at=cast(datetime.datetime, row["updated_at"]),
    )


def plan_to_values(plan: Plan) -> Mapping[str, object]:
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
        "loan_type": plan.loan_type.value,
        "currency": plan.currency,
        "lender": plan.lender,
        "upfront_fees": plan.upfront_fees,
        "early_payment_fees": _early_payment_fees_to_payload(plan.early_payment_fees),
        "housing_costs": _housing_costs_to_payload(plan.housing_costs),
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


def plan_from_row(row: Mapping[str, object]) -> Plan:
    return Plan(
        id=cast(UUID, row["id"]),
        user_id=cast(UUID, row["user_id"]),
        name=cast(str, row["name"]),
        slug=cast(str, row["slug"]),
        amount=Decimal(str(row["amount"])),
        term=Term(cast(int, row["term_years"]), cast(int, row["term_months"])),
        interest_rate=Decimal(str(row["interest_rate"])),
        start_date=cast(datetime.date, row["start_date"]),
        loan_type=LoanType(cast(str, row["loan_type"])),
        currency=cast(str, row["currency"]),
        lender=cast(str | None, row["lender"]),
        upfront_fees=Decimal(str(row["upfront_fees"])),
        early_payment_fees=_early_payment_fees_from_payload(cast(Mapping[str, object], row["early_payment_fees"])),
        housing_costs=_housing_costs_from_payload(cast(Mapping[str, object], row["housing_costs"])),
        interest_rate_application=InterestRateApplication(cast(str, row["interest_rate_application"])),
        status=Plan.Status(cast(str, row["status"])),
        one_time_extra_payments=[
            _one_time_extra_payment_from_payload(item)
            for item in cast(list[Mapping[str, object]], row["one_time_extra_payments"])
        ],
        recurring_extra_payments=[
            _recurring_extra_payment_from_payload(item)
            for item in cast(list[Mapping[str, object]], row["recurring_extra_payments"])
        ],
        interest_rate_changes=[
            _interest_rate_change_from_payload(item)
            for item in cast(list[Mapping[str, object]], row["interest_rate_changes"])
        ],
        is_deleted=cast(bool, row["is_deleted"]),
        created_at=cast(datetime.datetime, row["created_at"]),
        updated_at=cast(datetime.datetime, row["updated_at"]),
    )


def schedule_to_values(schedule: Schedule) -> Mapping[str, object]:
    return {
        "id": schedule.id,
        "plan_id": schedule.plan_id,
        "installments": [_installment_to_payload(item) for item in schedule.installments],
        "totals": None if schedule.totals is None else _totals_to_payload(schedule.totals),
        "generated_at": schedule.generated_at,
        "is_deleted": schedule.is_deleted,
    }


def schedule_from_row(row: Mapping[str, object]) -> Schedule:
    installments_payload = cast(list[Mapping[str, object]], row["installments"])
    totals_payload = cast(Mapping[str, object] | None, row["totals"])
    return Schedule(
        id=cast(UUID, row["id"]),
        plan_id=cast(UUID, row["plan_id"]),
        installments=[_installment_from_payload(item) for item in installments_payload],
        totals=None if totals_payload is None else _totals_from_payload(totals_payload),
        generated_at=cast(datetime.datetime, row["generated_at"]),
        is_deleted=cast(bool, row["is_deleted"]),
    )


def refresh_token_to_values(token: RefreshToken) -> Mapping[str, object]:
    return {
        "id": token.id,
        "user_id": token.user_id,
        "token_hash": token.token_hash,
        "family_id": token.family_id,
        "expires_at": token.expires_at,
        "used_at": token.used_at,
        "revoked_at": token.revoked_at,
        "created_at": token.created_at,
    }


def refresh_token_from_row(row: Mapping[str, object]) -> RefreshToken:
    return RefreshToken(
        id=cast(UUID, row["id"]),
        user_id=cast(UUID, row["user_id"]),
        token_hash=cast(str, row["token_hash"]),
        family_id=cast(UUID, row["family_id"]),
        expires_at=cast(datetime.datetime, row["expires_at"]),
        used_at=cast(datetime.datetime | None, row["used_at"]),
        revoked_at=cast(datetime.datetime | None, row["revoked_at"]),
        created_at=cast(datetime.datetime, row["created_at"]),
    )


def account_token_to_values(token: AccountToken) -> Mapping[str, object]:
    return {
        "id": token.id,
        "user_id": token.user_id,
        "purpose": token.purpose.value,
        "token_hash": token.token_hash,
        "expires_at": token.expires_at,
        "used_at": token.used_at,
        "created_at": token.created_at,
    }


def account_token_from_row(row: Mapping[str, object]) -> AccountToken:
    return AccountToken(
        id=cast(UUID, row["id"]),
        user_id=cast(UUID, row["user_id"]),
        purpose=AccountToken.Purpose(cast(str, row["purpose"])),
        token_hash=cast(str, row["token_hash"]),
        expires_at=cast(datetime.datetime, row["expires_at"]),
        used_at=cast(datetime.datetime | None, row["used_at"]),
        created_at=cast(datetime.datetime, row["created_at"]),
    )


def _early_payment_fees_to_payload(fees: EarlyPaymentFees) -> Mapping[str, object]:
    return {
        "fixed": _decimal_to_string(Decimal(fees.fixed)),
        "percent": _decimal_to_string(Decimal(fees.percent)),
    }


def _early_payment_fees_from_payload(payload: Mapping[str, object]) -> EarlyPaymentFees:
    return EarlyPaymentFees(
        fixed=Decimal(str(payload["fixed"])),
        percent=Decimal(str(payload["percent"])),
    )


def _housing_costs_to_payload(costs: HousingCosts) -> Mapping[str, object]:
    if costs.is_empty:
        return {}
    return {
        "property_value": None if costs.property_value is None else _decimal_to_string(costs.property_value),
        "property_tax_annual": _decimal_to_string(costs.property_tax_annual),
        "insurance_annual": _decimal_to_string(costs.insurance_annual),
        "hoa_monthly": _decimal_to_string(costs.hoa_monthly),
        "pmi_annual_rate": _decimal_to_string(costs.pmi_annual_rate),
        "pmi_cancel_ltv": _decimal_to_string(costs.pmi_cancel_ltv),
    }


def _housing_costs_from_payload(payload: Mapping[str, object]) -> HousingCosts:
    if not payload:
        return HousingCosts()
    property_value = payload.get("property_value")
    return HousingCosts(
        property_value=None if property_value is None else Decimal(str(property_value)),
        property_tax_annual=Decimal(str(payload.get("property_tax_annual", "0"))),
        insurance_annual=Decimal(str(payload.get("insurance_annual", "0"))),
        hoa_monthly=Decimal(str(payload.get("hoa_monthly", "0"))),
        pmi_annual_rate=Decimal(str(payload.get("pmi_annual_rate", "0"))),
        pmi_cancel_ltv=Decimal(str(payload.get("pmi_cancel_ltv", "78"))),
    )


def _one_time_extra_payment_to_payload(payment: OneTimeExtraPayment) -> Mapping[str, object]:
    return {
        "date": _date_to_string(payment.date),
        "amount": _decimal_to_string(payment.amount),
    }


def _one_time_extra_payment_from_payload(payload: Mapping[str, object]) -> OneTimeExtraPayment:
    return OneTimeExtraPayment(
        date=_date_from_string(str(payload["date"])),
        amount=Decimal(str(payload["amount"])),
    )


def _recurring_extra_payment_to_payload(payment: RecurringExtraPayment) -> Mapping[str, object]:
    return {
        "start_date": _date_to_string(payment.start_date),
        "amount": _decimal_to_string(payment.amount),
        "count": payment.count,
    }


def _recurring_extra_payment_from_payload(payload: Mapping[str, object]) -> RecurringExtraPayment:
    return RecurringExtraPayment(
        start_date=_date_from_string(str(payload["start_date"])),
        amount=Decimal(str(payload["amount"])),
        count=cast(int, payload["count"]),
    )


def _interest_rate_change_to_payload(change: InterestRateChange) -> Mapping[str, object]:
    return {
        "effective_date": _date_to_string(change.effective_date),
        "yearly_interest_rate": _decimal_to_string(change.yearly_interest_rate),
    }


def _interest_rate_change_from_payload(payload: Mapping[str, object]) -> InterestRateChange:
    return InterestRateChange(
        effective_date=_date_from_string(str(payload["effective_date"])),
        yearly_interest_rate=Decimal(str(payload["yearly_interest_rate"])),
    )


def _housing_payment_to_payload(housing: HousingPayment) -> Mapping[str, object]:
    return {
        "property_tax": _decimal_to_string(housing.property_tax),
        "insurance": _decimal_to_string(housing.insurance),
        "hoa": _decimal_to_string(housing.hoa),
        "pmi": _decimal_to_string(housing.pmi),
    }


def _housing_payment_from_payload(payload: Mapping[str, object]) -> HousingPayment:
    return HousingPayment(
        property_tax=Decimal(str(payload["property_tax"])),
        insurance=Decimal(str(payload["insurance"])),
        hoa=Decimal(str(payload["hoa"])),
        pmi=Decimal(str(payload["pmi"])),
    )


def _installment_to_payload(installment: Installment) -> Mapping[str, object]:
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
        "housing": None if installment.housing is None else _housing_payment_to_payload(installment.housing),
    }


def _installment_from_payload(payload: Mapping[str, object]) -> Installment:
    payment_payload = cast(Mapping[str, object], payload["payment"])
    balance_payload = cast(Mapping[str, object], payload["balance"])
    housing_payload = cast(Mapping[str, object] | None, payload.get("housing"))
    return Installment(
        i=cast(int | None, payload["i"]),
        year=cast(int, payload["year"]),
        month=Month(cast(int, payload["month"])),
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
        housing=None if housing_payload is None else _housing_payment_from_payload(housing_payload),
    )


def _totals_to_payload(totals: ScheduleTotals) -> Mapping[str, object]:
    return {
        "principal": _decimal_to_string(totals.principal),
        "interest": _decimal_to_string(totals.interest),
        "fees": _decimal_to_string(totals.fees),
        "months": totals.months,
        "paid_off": totals.paid_off,
        "pmi": _decimal_to_string(totals.pmi),
        "escrow": _decimal_to_string(totals.escrow),
    }


def _totals_from_payload(payload: Mapping[str, object]) -> ScheduleTotals:
    return ScheduleTotals(
        principal=Decimal(str(payload["principal"])),
        interest=Decimal(str(payload["interest"])),
        fees=Decimal(str(payload["fees"])),
        months=cast(int, payload["months"]),
        paid_off=bool(payload["paid_off"]),
        pmi=Decimal(str(payload.get("pmi", "0"))),
        escrow=Decimal(str(payload.get("escrow", "0"))),
    )
