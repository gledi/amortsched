import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel

from amortsched.core.entities import Schedule


class BalanceSchema(BaseModel):
    before: Decimal
    after: Decimal


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


class TotalsSchema(BaseModel):
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total_outflow: Decimal
    months: int
    paid_off: bool


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
            installments=[
                InstallmentSchema(
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
                )
                for inst in schedule.installments
            ],
            totals=TotalsSchema(
                principal=schedule.totals.principal,
                interest=schedule.totals.interest,
                fees=schedule.totals.fees,
                total_outflow=schedule.totals.total_outflow,
                months=schedule.totals.months,
                paid_off=schedule.totals.paid_off,
            )
            if schedule.totals
            else None,
            generated_at=schedule.generated_at,
        )
