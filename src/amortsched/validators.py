import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin


def _decimal_serializer(value: Decimal) -> str:
    return f"{value:.2f}"


class SchemaConfig(BaseConfig):
    serialization_strategy = {Decimal: {"serialize": _decimal_serializer, "deserialize": Decimal}}


@dataclass
class TermSchema(DataClassORJSONMixin):
    years: int = 0
    months: int = 0


@dataclass
class EarlyPaymentFeesSchema(DataClassORJSONMixin):
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")


@dataclass
class ExtraPaymentSchema(DataClassORJSONMixin):
    date: datetime.date
    amount: Decimal


@dataclass
class RecurringExtraPaymentSchema(DataClassORJSONMixin):
    start_date: datetime.date
    amount: Decimal
    count: int

    class Config(SchemaConfig):
        aliases = {"start_date": "startDate"}
        allow_deserialization_not_by_alias = True


@dataclass
class AmortizationRequest(DataClassORJSONMixin):
    amount: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date = field(default_factory=datetime.date.today)
    early_payment_fees: EarlyPaymentFeesSchema = field(default_factory=EarlyPaymentFeesSchema)
    extra_payments: list[ExtraPaymentSchema] = field(default_factory=list)
    recurring_extra_payments: list[RecurringExtraPaymentSchema] = field(default_factory=list)

    def __post_init__(self):
        if self.term.years <= 0 and self.term.months <= 0:
            raise ValueError("Term must include a positive number of months or years")

    class Config(SchemaConfig):
        aliases = {
            "start_date": "startDate",
            "early_payment_fees": "earlyPaymentFees",
            "extra_payments": "extraPayments",
            "recurring_extra_payments": "recurringExtraPayments",
        }
        allow_deserialization_not_by_alias = True


@dataclass
class BalanceResponse(DataClassORJSONMixin):
    before: Decimal
    after: Decimal

    class Config(SchemaConfig):
        serialize_by_alias = True


@dataclass
class InstallmentResponse(DataClassORJSONMixin):
    installment: int | None
    year: int
    month: int
    month_name: str
    type: str
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    balance: BalanceResponse

    class Config(SchemaConfig):
        aliases = {"month_name": "monthName"}
        serialize_by_alias = True


@dataclass
class TotalsResponse(DataClassORJSONMixin):
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    months: int
    paid_off: bool

    class Config(SchemaConfig):
        aliases = {"paid_off": "paidOff"}
        serialize_by_alias = True


@dataclass
class AmortizationResponse(DataClassORJSONMixin):
    installments: list[InstallmentResponse]
    totals: Optional[TotalsResponse] = None

    class Config(SchemaConfig):
        serialize_by_alias = True
