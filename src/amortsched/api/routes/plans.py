import uuid

from fastapi import APIRouter, Depends, status

from amortsched.api.dependencies import (
    get_add_extra_payment_handler,
    get_add_interest_rate_change_handler,
    get_add_recurring_extra_payment_handler,
    get_create_plan_handler,
    get_current_user_id,
    get_delete_plan_handler,
    get_get_plan_handler,
    get_list_plans_handler,
    get_save_plan_handler,
    get_update_plan_handler,
)
from amortsched.api.schemas.plans import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    CreatePlanRequest,
    PlanResponse,
    UpdatePlanRequest,
)
from amortsched.app.commands.plans import (
    AddInterestRateChangeCommand,
    AddInterestRateChangeHandler,
    AddOneTimeExtraPaymentCommand,
    AddOneTimeExtraPaymentHandler,
    AddRecurringExtraPaymentCommand,
    AddRecurringExtraPaymentHandler,
    CreatePlanCommand,
    CreatePlanHandler,
    DeletePlanCommand,
    DeletePlanHandler,
    SavePlanCommand,
    SavePlanHandler,
    UpdatePlanCommand,
    UpdatePlanHandler,
)
from amortsched.app.queries.plans import GetPlanHandler, GetPlanQuery, ListPlansHandler, ListPlansQuery
from amortsched.core.utils import today
from amortsched.core.values import EarlyPaymentFees, Term

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: CreatePlanRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: CreatePlanHandler = Depends(get_create_plan_handler),
) -> PlanResponse:
    command = CreatePlanCommand(
        user_id=user_id,
        name=body.name,
        amount=body.amount,
        term=Term(body.term.years, body.term.months),
        interest_rate=body.interest_rate,
        start_date=body.start_date or today(),
        early_payment_fees=EarlyPaymentFees(
            fixed=body.early_payment_fees.fixed, percent=body.early_payment_fees.percent
        ),
        interest_rate_application=body.interest_rate_application,
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: ListPlansHandler = Depends(get_list_plans_handler),
) -> list[PlanResponse]:
    plans = await handler.handle(ListPlansQuery(user_id=user_id))
    return [PlanResponse.from_entity(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: GetPlanHandler = Depends(get_get_plan_handler),
) -> PlanResponse:
    plan = await handler.handle(GetPlanQuery(plan_id=plan_id, user_id=user_id))
    return PlanResponse.from_entity(plan)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    body: UpdatePlanRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: UpdatePlanHandler = Depends(get_update_plan_handler),
) -> PlanResponse:
    command = UpdatePlanCommand(
        plan_id=plan_id,
        user_id=user_id,
        name=body.name,
        amount=body.amount,
        interest_rate=body.interest_rate,
        term=Term(body.term.years, body.term.months) if body.term else None,
        start_date=body.start_date,
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
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: DeletePlanHandler = Depends(get_delete_plan_handler),
) -> None:
    await handler.handle(DeletePlanCommand(plan_id=plan_id, user_id=user_id))


@router.post("/{plan_id}/save", response_model=PlanResponse)
async def save_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: SavePlanHandler = Depends(get_save_plan_handler),
) -> PlanResponse:
    plan = await handler.handle(SavePlanCommand(plan_id=plan_id, user_id=user_id))
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/extra-payments", response_model=PlanResponse)
async def add_extra_payment(
    plan_id: uuid.UUID,
    body: AddExtraPaymentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: AddOneTimeExtraPaymentHandler = Depends(get_add_extra_payment_handler),
) -> PlanResponse:
    command = AddOneTimeExtraPaymentCommand(plan_id=plan_id, user_id=user_id, date=body.date, amount=body.amount)
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)


@router.post("/{plan_id}/recurring-extra-payments", response_model=PlanResponse)
async def add_recurring_extra_payment(
    plan_id: uuid.UUID,
    body: AddRecurringExtraPaymentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: AddRecurringExtraPaymentHandler = Depends(get_add_recurring_extra_payment_handler),
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
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: AddInterestRateChangeHandler = Depends(get_add_interest_rate_change_handler),
) -> PlanResponse:
    command = AddInterestRateChangeCommand(
        plan_id=plan_id,
        user_id=user_id,
        effective_date=body.effective_date,
        rate=body.rate,
    )
    plan = await handler.handle(command)
    return PlanResponse.from_entity(plan)
