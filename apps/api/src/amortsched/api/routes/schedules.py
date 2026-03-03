"""Schedule routes."""

import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from amortsched.api.inject import inject
from amortsched.api.middleware import get_current_user_id
from amortsched.api.validators import (
    BalanceResponse,
    InstallmentResponse,
    ScheduleResponse,
    TotalsResponse,
)
from amortsched.app.plans import (
    DeleteScheduleCommand,
    DeleteScheduleHandler,
    GenerateScheduleHandler,
    GenerateScheduleQuery,
    GetScheduleHandler,
    GetScheduleQuery,
    ListSchedulesHandler,
    ListSchedulesQuery,
    SaveScheduleCommand,
    SaveScheduleHandler,
)


def _schedule_to_response(schedule) -> ScheduleResponse:
    installments = [
        InstallmentResponse(
            installment=item.i,
            year=item.year,
            month=item.month.value,
            month_name=item.month_name,
            type=item.payment.kind,
            principal=item.payment.principal,
            interest=item.payment.interest,
            fees=item.payment.fees,
            total=item.payment.total,
            balance=BalanceResponse(before=item.balance.before, after=item.balance.after),
        )
        for item in schedule.installments
    ]
    totals = None
    if schedule.totals is not None:
        totals = TotalsResponse(
            principal=schedule.totals.principal,
            interest=schedule.totals.interest,
            fees=schedule.totals.fees,
            total=schedule.totals.total_outflow,
            months=schedule.totals.months,
            paid_off=schedule.totals.paid_off,
        )
    return ScheduleResponse(
        id=schedule.id,
        plan_id=schedule.plan_id,
        generated_at=schedule.generated_at,
        installments=installments,
        totals=totals,
    )


@inject
async def preview_schedule(request: Request, handler: GenerateScheduleHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    schedule = handler.handle(GenerateScheduleQuery(plan_id=plan_id, user_id=user_id))
    resp = _schedule_to_response(schedule)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def save_schedule(request: Request, handler: SaveScheduleHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    schedule = handler.handle(SaveScheduleCommand(plan_id=plan_id, user_id=user_id))
    resp = _schedule_to_response(schedule)
    return Response(content=resp.to_json(), media_type="application/json", status_code=201)


@inject
async def list_schedules(request: Request, handler: ListSchedulesHandler) -> Response:
    user_id = get_current_user_id(request)
    plan_id = uuid.UUID(request.path_params["plan_id"])
    schedules = handler.handle(ListSchedulesQuery(plan_id=plan_id, user_id=user_id))
    payload = [_schedule_to_response(s).to_dict() for s in schedules]
    return JSONResponse(payload)


@inject
async def get_schedule(request: Request, handler: GetScheduleHandler) -> Response:
    user_id = get_current_user_id(request)
    schedule_id = uuid.UUID(request.path_params["schedule_id"])
    schedule = handler.handle(GetScheduleQuery(schedule_id=schedule_id, user_id=user_id))
    resp = _schedule_to_response(schedule)
    return Response(content=resp.to_json(), media_type="application/json")


@inject
async def delete_schedule(request: Request, handler: DeleteScheduleHandler) -> Response:
    user_id = get_current_user_id(request)
    schedule_id = uuid.UUID(request.path_params["schedule_id"])
    handler.handle(DeleteScheduleCommand(schedule_id=schedule_id, user_id=user_id))
    return Response(status_code=204)


routes = [
    Route("/api/plans/{plan_id}/schedules/preview", preview_schedule, methods=["POST"]),
    Route("/api/plans/{plan_id}/schedules", save_schedule, methods=["POST"]),
    Route("/api/plans/{plan_id}/schedules", list_schedules, methods=["GET"]),
    Route("/api/plans/{plan_id}/schedules/{schedule_id}", get_schedule, methods=["GET"]),
    Route("/api/plans/{plan_id}/schedules/{schedule_id}", delete_schedule, methods=["DELETE"]),
]
