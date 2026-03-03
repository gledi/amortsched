"""Plan routes."""

import uuid

from fastapi import APIRouter, Depends, Response

from amortsched.app.plans import (
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
    GetPlanHandler,
    GetPlanQuery,
    ListPlansHandler,
    ListPlansQuery,
    SavePlanCommand,
    SavePlanHandler,
    UpdatePlanCommand,
    UpdatePlanHandler,
)
from amortsched.core.values import EarlyPaymentFees as DomainEarlyPaymentFees
from amortsched.core.values import InterestRateApplication
from amortsched.web.deps import (
    get_add_interest_rate_change_handler,
    get_add_one_time_extra_payment_handler,
    get_add_recurring_extra_payment_handler,
    get_create_plan_handler,
    get_delete_plan_handler,
    get_list_plans_handler,
    get_plan_handler,
    get_save_plan_handler,
    get_update_plan_handler,
)
from amortsched.web.middleware import get_current_user_id
from amortsched.web.models import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    CreatePlanRequest,
    EarlyPaymentFees,
    ExtraPayment,
    InterestRateChange,
    PlanResponse,
    RecurringExtraPayment,
    Term,
    UpdatePlanRequest,
)

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _plan_to_response(plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        userId=plan.user_id,
        name=plan.name,
        slug=plan.slug,
        amount=plan.amount,
        term=Term(years=plan.term.years, months=plan.term.months),
        interestRate=plan.interest_rate,
        startDate=plan.start_date,
        earlyPaymentFees=EarlyPaymentFees(fixed=plan.early_payment_fees.fixed, percent=plan.early_payment_fees.percent),
        interestRateApplication=plan.interest_rate_application.value,
        status=plan.status.value,
        oneTimeExtraPayments=[ExtraPayment(date=ep.date, amount=ep.amount) for ep in plan.one_time_extra_payments],
        recurringExtraPayments=[
            RecurringExtraPayment(startDate=rp.start_date, amount=rp.amount, count=rp.count)
            for rp in plan.recurring_extra_payments
        ],
        interestRateChanges=[
            InterestRateChange(effectiveDate=rc.effective_date, yearlyInterestRate=rc.yearly_interest_rate)
            for rc in plan.interest_rate_changes
        ],
        createdAt=plan.created_at,
        updatedAt=plan.updated_at,
    )


@router.post("", response_model=PlanResponse, status_code=201)
def create_plan(
    payload: CreatePlanRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: CreatePlanHandler = Depends(get_create_plan_handler),  # noqa: B008
) -> PlanResponse:
    early_fees = DomainEarlyPaymentFees(
        fixed=payload.early_payment_fees.fixed, percent=payload.early_payment_fees.percent
    )
    plan = handler.handle(
        CreatePlanCommand(
            user_id=user_id,
            name=payload.name,
            amount=payload.amount,
            term=(payload.term.years, payload.term.months),
            interest_rate=payload.interest_rate,
            start_date=payload.start_date,
            early_payment_fees=early_fees,
            interest_rate_application=InterestRateApplication(payload.interest_rate_application),
        )
    )
    return _plan_to_response(plan)


@router.get("", response_model=list[PlanResponse])
def list_plans(
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: ListPlansHandler = Depends(get_list_plans_handler),  # noqa: B008
) -> list[PlanResponse]:
    plans = handler.handle(ListPlansQuery(user_id=user_id))
    return [_plan_to_response(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: GetPlanHandler = Depends(get_plan_handler),  # noqa: B008
) -> PlanResponse:
    plan = handler.handle(GetPlanQuery(plan_id=plan_id, user_id=user_id))
    return _plan_to_response(plan)


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: uuid.UUID,
    payload: UpdatePlanRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: UpdatePlanHandler = Depends(get_update_plan_handler),  # noqa: B008
) -> PlanResponse:
    early_fees = None
    if payload.early_payment_fees is not None:
        early_fees = DomainEarlyPaymentFees(
            fixed=payload.early_payment_fees.fixed, percent=payload.early_payment_fees.percent
        )
    ira = InterestRateApplication(payload.interest_rate_application) if payload.interest_rate_application else None
    term = (payload.term.years, payload.term.months) if payload.term else None
    plan = handler.handle(
        UpdatePlanCommand(
            plan_id=plan_id,
            user_id=user_id,
            name=payload.name,
            amount=payload.amount,
            term=term,
            interest_rate=payload.interest_rate,
            start_date=payload.start_date,
            early_payment_fees=early_fees,
            interest_rate_application=ira,
        )
    )
    return _plan_to_response(plan)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: DeletePlanHandler = Depends(get_delete_plan_handler),  # noqa: B008
) -> Response:
    handler.handle(DeletePlanCommand(plan_id=plan_id, user_id=user_id))
    return Response(status_code=204)


@router.post("/{plan_id}/save", response_model=PlanResponse)
def save_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: SavePlanHandler = Depends(get_save_plan_handler),  # noqa: B008
) -> PlanResponse:
    plan = handler.handle(SavePlanCommand(plan_id=plan_id, user_id=user_id))
    return _plan_to_response(plan)


@router.post("/{plan_id}/extra-payments", response_model=PlanResponse)
def add_extra_payment(
    plan_id: uuid.UUID,
    payload: AddExtraPaymentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: AddOneTimeExtraPaymentHandler = Depends(get_add_one_time_extra_payment_handler),  # noqa: B008
) -> PlanResponse:
    plan = handler.handle(
        AddOneTimeExtraPaymentCommand(plan_id=plan_id, user_id=user_id, date=payload.date, amount=payload.amount)
    )
    return _plan_to_response(plan)


@router.post("/{plan_id}/recurring-extra-payments", response_model=PlanResponse)
def add_recurring_extra_payment(
    plan_id: uuid.UUID,
    payload: AddRecurringExtraPaymentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: AddRecurringExtraPaymentHandler = Depends(get_add_recurring_extra_payment_handler),  # noqa: B008
) -> PlanResponse:
    plan = handler.handle(
        AddRecurringExtraPaymentCommand(
            plan_id=plan_id, user_id=user_id, start_date=payload.start_date, amount=payload.amount, count=payload.count
        )
    )
    return _plan_to_response(plan)


@router.post("/{plan_id}/interest-rate-changes", response_model=PlanResponse)
def add_interest_rate_change(
    plan_id: uuid.UUID,
    payload: AddInterestRateChangeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: AddInterestRateChangeHandler = Depends(get_add_interest_rate_change_handler),  # noqa: B008
) -> PlanResponse:
    plan = handler.handle(
        AddInterestRateChangeCommand(
            plan_id=plan_id, user_id=user_id, effective_date=payload.effective_date, rate=payload.rate
        )
    )
    return _plan_to_response(plan)
