import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel

from amortsched.core.entities import Schedule
from amortsched.core.money import round_cents
from amortsched.core.values import HousingPayment, Installment, ScheduleTotals


class BalanceSchema(BaseModel):
    before: Decimal
    after: Decimal


class HousingPaymentSchema(BaseModel):
    property_tax: Decimal
    insurance: Decimal
    hoa: Decimal
    pmi: Decimal
    total: Decimal

    @classmethod
    def from_value(cls, housing: HousingPayment) -> "HousingPaymentSchema":
        return cls(
            property_tax=round_cents(housing.property_tax),
            insurance=round_cents(housing.insurance),
            hoa=round_cents(housing.hoa),
            pmi=round_cents(housing.pmi),
            total=round_cents(housing.total),
        )


class InstallmentSchema(BaseModel):
    installment_number: int | None
    year: int
    month: int
    month_name: str
    type: str
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    balance: BalanceSchema
    housing: HousingPaymentSchema | None = None
    total_with_housing: Decimal

    @classmethod
    def from_value(cls, inst: Installment) -> "InstallmentSchema":
        housing_total = inst.housing.total if inst.housing is not None else Decimal("0")
        return cls(
            installment_number=inst.i,
            year=inst.year,
            month=int(inst.month),
            month_name=inst.month.name,
            type=inst.payment.kind.value,
            principal=inst.payment.principal,
            interest=inst.payment.interest,
            fees=inst.payment.fees,
            total=inst.payment.total,
            balance=BalanceSchema(before=inst.balance.before, after=inst.balance.after),
            housing=None if inst.housing is None else HousingPaymentSchema.from_value(inst.housing),
            total_with_housing=round_cents(inst.payment.total + housing_total),
        )


class TotalsSchema(BaseModel):
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total_outflow: Decimal
    months: int
    paid_off: bool
    pmi: Decimal
    escrow: Decimal

    @classmethod
    def from_value(cls, totals: ScheduleTotals) -> "TotalsSchema":
        return cls(
            principal=totals.principal,
            interest=totals.interest,
            fees=totals.fees,
            total_outflow=totals.total_outflow,
            months=totals.months,
            paid_off=totals.paid_off,
            pmi=round_cents(totals.pmi),
            escrow=round_cents(totals.escrow),
        )


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    installments: list[InstallmentSchema]
    totals: TotalsSchema | None
    generated_at: datetime.datetime

    @classmethod
    def from_entity(cls, schedule: Schedule) -> "ScheduleResponse":
        return cls(
            id=schedule.id,
            plan_id=schedule.plan_id,
            installments=[InstallmentSchema.from_value(inst) for inst in schedule.installments],
            totals=TotalsSchema.from_value(schedule.totals) if schedule.totals else None,
            generated_at=schedule.generated_at,
        )
