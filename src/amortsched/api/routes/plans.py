import csv
import io
import uuid
from decimal import Decimal

from fastapi import APIRouter, Response, status

from amortsched.api.dependencies import (
    AddExtraPayment,
    AddInterestRateChange,
    AddRecurringExtraPayment,
    CreatePlan,
    CurrentUserId,
    DeletePlan,
    DuplicatePlan,
    GetPlan,
    ListPlans,
    ReplaceAdjustments,
    SavePlan,
    UpdatePlan,
)
from amortsched.api.schemas.plans import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    AdjustmentsSchema,
    CreatePlanRequest,
    PlanResponse,
    UpdatePlanRequest,
)
from amortsched.app.commands.plans import (
    AddInterestRateChangeCommand,
    AddOneTimeExtraPaymentCommand,
    AddRecurringExtraPaymentCommand,
    CreatePlanCommand,
    DeletePlanCommand,
    DuplicatePlanCommand,
    ReplaceAdjustmentsCommand,
    SavePlanCommand,
    UpdatePlanCommand,
)
from amortsched.app.queries.plans import GetPlanQuery, ListPlansQuery
from amortsched.core.entities import Plan
from amortsched.core.utils import today
from amortsched.core.values import EarlyPaymentFees, Term

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: CreatePlanRequest,
    user_id: CurrentUserId,
    handler: CreatePlan,
) -> PlanResponse:
    command = CreatePlanCommand(
        user_id=user_id,
        name=body.name,
        amount=body.amount,
        term=Term(body.term.years, body.term.months),
        interest_rate=body.interest_rate,
        start_date=body.start_date or today(),
        loan_type=body.loan_type,
        currency=body.currency,
        lender=body.lender,
        upfront_fees=body.upfront_fees,
        early_payment_fees=EarlyPaymentFees(
            fixed=body.early_payment_fees.fixed, percent=body.early_payment_fees.percent
        ),
        housing_costs=body.housing_costs.to_value() if body.housing_costs else None,
        interest_rate_application=body.interest_rate_application,
        one_time_extra_payments=tuple(item.to_value() for item in body.one_time_extra_payments),
        recurring_extra_payments=tuple(item.to_value() for item in body.recurring_extra_payments),
        interest_rate_changes=tuple(item.to_value() for item in body.interest_rate_changes),
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    user_id: CurrentUserId,
    handler: ListPlans,
    limit: int | None = None,
) -> list[PlanResponse]:
    plans = await handler.handle(ListPlansQuery(user_id=user_id, limit=limit))
    return [PlanResponse.from_entity(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    user_id: CurrentUserId,
    handler: GetPlan,
) -> PlanResponse:
    plan = await handler.handle(GetPlanQuery(plan_id=plan_id, user_id=user_id))
    return PlanResponse.from_entity(plan)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    body: UpdatePlanRequest,
    user_id: CurrentUserId,
    handler: UpdatePlan,
) -> PlanResponse:
    command = UpdatePlanCommand(
        plan_id=plan_id,
        user_id=user_id,
        name=body.name,
        amount=body.amount,
        interest_rate=body.interest_rate,
        term=Term(body.term.years, body.term.months) if body.term else None,
        start_date=body.start_date,
        loan_type=body.loan_type,
        currency=body.currency,
        lender=body.lender,
        upfront_fees=body.upfront_fees,
        housing_costs=body.housing_costs.to_value() if body.housing_costs else None,
        early_payment_fees=EarlyPaymentFees(
            fixed=body.early_payment_fees.fixed, percent=body.early_payment_fees.percent
        )
        if body.early_payment_fees
        else None,
        interest_rate_application=body.interest_rate_application,
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: uuid.UUID,
    user_id: CurrentUserId,
    handler: DeletePlan,
) -> None:
    await handler.handle(DeletePlanCommand(plan_id=plan_id, user_id=user_id))


@router.post("/{plan_id}/save", response_model=PlanResponse)
async def save_plan(
    plan_id: uuid.UUID,
    user_id: CurrentUserId,
    handler: SavePlan,
) -> PlanResponse:
    plan = await handler.handle(SavePlanCommand(plan_id=plan_id, user_id=user_id))
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/extra-payments", response_model=PlanResponse)
async def add_extra_payment(
    plan_id: uuid.UUID,
    body: AddExtraPaymentRequest,
    user_id: CurrentUserId,
    handler: AddExtraPayment,
) -> PlanResponse:
    command = AddOneTimeExtraPaymentCommand(plan_id=plan_id, user_id=user_id, date=body.date, amount=body.amount)
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/recurring-extra-payments", response_model=PlanResponse)
async def add_recurring_extra_payment(
    plan_id: uuid.UUID,
    body: AddRecurringExtraPaymentRequest,
    user_id: CurrentUserId,
    handler: AddRecurringExtraPayment,
) -> PlanResponse:
    command = AddRecurringExtraPaymentCommand(
        plan_id=plan_id,
        user_id=user_id,
        start_date=body.start_date,
        amount=body.amount,
        count=body.count,
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/interest-rate-changes", response_model=PlanResponse)
async def add_interest_rate_change(
    plan_id: uuid.UUID,
    body: AddInterestRateChangeRequest,
    user_id: CurrentUserId,
    handler: AddInterestRateChange,
) -> PlanResponse:
    command = AddInterestRateChangeCommand(
        plan_id=plan_id,
        user_id=user_id,
        effective_date=body.effective_date,
        rate=body.rate,
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.put("/{plan_id}/adjustments", response_model=PlanResponse)
async def replace_adjustments(
    plan_id: uuid.UUID,
    body: AdjustmentsSchema,
    user_id: CurrentUserId,
    handler: ReplaceAdjustments,
) -> PlanResponse:
    command = ReplaceAdjustmentsCommand(
        plan_id=plan_id,
        user_id=user_id,
        one_time_extra_payments=tuple(item.to_value() for item in body.one_time_extra_payments),
        recurring_extra_payments=tuple(item.to_value() for item in body.recurring_extra_payments),
        interest_rate_changes=tuple(item.to_value() for item in body.interest_rate_changes),
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/duplicate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_plan(
    plan_id: uuid.UUID,
    user_id: CurrentUserId,
    handler: DuplicatePlan,
) -> PlanResponse:
    plan = await handler.handle(DuplicatePlanCommand(plan_id=plan_id, user_id=user_id))
    return PlanResponse.from_entity(plan)


CSV_COLUMNS = [
    "installment",
    "period",
    "type",
    "principal",
    "interest",
    "fees",
    "loan_payment",
    "property_tax",
    "insurance",
    "hoa",
    "pmi",
    "total_payment",
    "balance_before",
    "balance_after",
]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def schedule_csv(plan: Plan) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for inst in plan.generate().installments:
        housing = inst.housing
        zero = Decimal("0")
        writer.writerow(
            [
                "" if inst.i is None else inst.i,
                f"{inst.year:04d}-{int(inst.month):02d}",
                inst.payment.kind.value,
                _money(inst.payment.principal),
                _money(inst.payment.interest),
                _money(inst.payment.fees),
                _money(inst.payment.total),
                _money(housing.property_tax if housing else zero),
                _money(housing.insurance if housing else zero),
                _money(housing.hoa if housing else zero),
                _money(housing.pmi if housing else zero),
                _money(inst.payment.total + (housing.total if housing else zero)),
                _money(inst.balance.before),
                _money(inst.balance.after),
            ]
        )
    return buffer.getvalue()


@router.get("/{plan_id}/schedule.csv", response_class=Response)
async def export_schedule_csv(
    plan_id: uuid.UUID,
    user_id: CurrentUserId,
    handler: GetPlan,
) -> Response:
    plan = await handler.handle(GetPlanQuery(plan_id=plan_id, user_id=user_id))
    filename = f"{plan.slug or 'plan'}-schedule.csv"
    return Response(
        content=schedule_csv(plan),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
