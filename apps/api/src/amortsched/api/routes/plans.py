"""Plan routes."""

import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from amortsched.api.inject import inject
from amortsched.api.middleware import get_current_user_id
from amortsched.api.validators import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    CreatePlanRequest,
    EarlyPaymentFeesSchema,
    ExtraPaymentSchema,
    InterestRateChangeSchema,
    PlanResponse,
    RecurringExtraPaymentSchema,
    TermSchema,
    UpdatePlanRequest,
)
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
from amortsched.core.values import EarlyPaymentFees, InterestRateApplication


def _plan_to_response(plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        name=plan.name,
        slug=plan.slug,
        amount=plan.amount,
        term=TermSchema(years=plan.term.years, months=plan.term.months),
        interest_rate=plan.interest_rate,
        start_date=plan.start_date,
        early_payment_fees=EarlyPaymentFeesSchema(
            fixed=plan.early_payment_fees.fixed, percent=plan.early_payment_fees.percent
        ),
        interest_rate_application=plan.interest_rate_application.value,
        status=plan.status.value,
        one_time_extra_payments=[
            ExtraPaymentSchema(date=ep.date, amount=ep.amount) for ep in plan.one_time_extra_payments
        ],
        recurring_extra_payments=[
            RecurringExtraPaymentSchema(start_date=rp.start_date, amount=rp.amount, count=rp.count)
            for rp in plan.recurring_extra_payments
        ],
        interest_rate_changes=[
            InterestRateChangeSchema(effective_date=rc.effective_date, yearly_interest_rate=rc.yearly_interest_rate)
            for rc in plan.interest_rate_changes
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@inject
async def create_plan(request: Request, handler: CreatePlanHandler) -> Response:
    user_id = get_current_user_id(request)
    body = await request.body()
    req = CreatePlanRequest.from_json(body)
    early_fees = EarlyPaymentFees(fixed=req.early_payment_fees.fixed, percent=req.early_payment_fees.percent)
    plan = handler.handle(
        CreatePlanCommand(
            user_id=user_id,
            name=req.name,
            amount=req.amount,
            term=(req.term.years, req.term.months),
            interest_rate=req.interest_rate,
            start_date=req.start_date,
            early_payment_fees=early_fees,
            interest_rate_application=InterestRateApplication(req.interest_rate_application),
        )
    )
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json", status_code=201)


@inject
async def list_plans(request: Request, handler: ListPlansHandler) -> Response:
    user_id = get_current_user_id(request)
    plans = handler.handle(ListPlansQuery(user_id=user_id))
    payload = [_plan_to_response(p).to_dict() for p in plans]
    return JSONResponse(payload)


@inject
async def get_plan(request: Request, handler: GetPlanHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    plan = handler.handle(GetPlanQuery(plan_id=plan_id, user_id=user_id))
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def update_plan(request: Request, handler: UpdatePlanHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    body = await request.body()
    req = UpdatePlanRequest.from_json(body)
    early_fees = None
    if req.early_payment_fees is not None:
        early_fees = EarlyPaymentFees(fixed=req.early_payment_fees.fixed, percent=req.early_payment_fees.percent)
    ira = InterestRateApplication(req.interest_rate_application) if req.interest_rate_application else None
    term = (req.term.years, req.term.months) if req.term else None
    plan = handler.handle(
        UpdatePlanCommand(
            plan_id=plan_id,
            user_id=user_id,
            name=req.name,
            amount=req.amount,
            term=term,
            interest_rate=req.interest_rate,
            start_date=req.start_date,
            early_payment_fees=early_fees,
            interest_rate_application=ira,
        )
    )
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def delete_plan(request: Request, handler: DeletePlanHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    handler.handle(DeletePlanCommand(plan_id=plan_id, user_id=user_id))
    return Response(status_code=204)


@inject
async def save_plan(request: Request, handler: SavePlanHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    plan = handler.handle(SavePlanCommand(plan_id=plan_id, user_id=user_id))
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def add_extra_payment(request: Request, handler: AddOneTimeExtraPaymentHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    body = await request.body()
    req = AddExtraPaymentRequest.from_json(body)
    plan = handler.handle(
        AddOneTimeExtraPaymentCommand(plan_id=plan_id, user_id=user_id, date=req.date, amount=req.amount)
    )
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def add_recurring_extra_payment(request: Request, handler: AddRecurringExtraPaymentHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    body = await request.body()
    req = AddRecurringExtraPaymentRequest.from_json(body)
    plan = handler.handle(
        AddRecurringExtraPaymentCommand(
            plan_id=plan_id, user_id=user_id, start_date=req.start_date, amount=req.amount, count=req.count
        )
    )
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def add_interest_rate_change(request: Request, handler: AddInterestRateChangeHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    body = await request.body()
    req = AddInterestRateChangeRequest.from_json(body)
    plan = handler.handle(
        AddInterestRateChangeCommand(plan_id=plan_id, user_id=user_id, effective_date=req.effective_date, rate=req.rate)
    )
    resp = _plan_to_response(plan)
    return Response(content=resp.to_json(), media_type="application/json")


routes = [
    Route("/api/plans", create_plan, methods=["POST"]),
    Route("/api/plans", list_plans, methods=["GET"]),
    Route("/api/plans/{plan_id}", get_plan, methods=["GET"]),
    Route("/api/plans/{plan_id}", update_plan, methods=["PUT"]),
    Route("/api/plans/{plan_id}", delete_plan, methods=["DELETE"]),
    Route("/api/plans/{plan_id}/save", save_plan, methods=["POST"]),
    Route("/api/plans/{plan_id}/extra-payments", add_extra_payment, methods=["POST"]),
    Route("/api/plans/{plan_id}/recurring-extra-payments", add_recurring_extra_payment, methods=["POST"]),
    Route("/api/plans/{plan_id}/interest-rate-changes", add_interest_rate_change, methods=["POST"]),
]
