"""Schedule routes."""

import uuid

from fastapi import APIRouter, Depends, Response

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
from amortsched.web.deps import (
    get_delete_schedule_handler,
    get_generate_schedule_handler,
    get_list_schedules_handler,
    get_save_schedule_handler,
    get_schedule_handler,
)
from amortsched.web.middleware import get_current_user_id
from amortsched.web.models import Balance, InstallmentResponse, ScheduleResponse, TotalsResponse

router = APIRouter(prefix="/api/plans/{plan_id}/schedules", tags=["schedules"])


def _schedule_to_response(schedule) -> ScheduleResponse:
    installments = [
        InstallmentResponse(
            installment=item.i,
            year=item.year,
            month=item.month.value,
            monthName=item.month_name,
            type=item.payment.kind,
            principal=item.payment.principal,
            interest=item.payment.interest,
            fees=item.payment.fees,
            total=item.payment.total,
            balance=Balance(before=item.balance.before, after=item.balance.after),
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
            paidOff=schedule.totals.paid_off,
        )
    return ScheduleResponse(
        id=schedule.id,
        planId=schedule.plan_id,
        generatedAt=schedule.generated_at,
        installments=installments,
        totals=totals,
    )


@router.post("/preview", response_model=ScheduleResponse)
def preview_schedule(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: GenerateScheduleHandler = Depends(get_generate_schedule_handler),  # noqa: B008
) -> ScheduleResponse:
    schedule = handler.handle(GenerateScheduleQuery(plan_id=plan_id, user_id=user_id))
    return _schedule_to_response(schedule)


@router.post("", response_model=ScheduleResponse, status_code=201)
def save_schedule(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: SaveScheduleHandler = Depends(get_save_schedule_handler),  # noqa: B008
) -> ScheduleResponse:
    schedule = handler.handle(SaveScheduleCommand(plan_id=plan_id, user_id=user_id))
    return _schedule_to_response(schedule)


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: ListSchedulesHandler = Depends(get_list_schedules_handler),  # noqa: B008
) -> list[ScheduleResponse]:
    schedules = handler.handle(ListSchedulesQuery(plan_id=plan_id, user_id=user_id))
    return [_schedule_to_response(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: GetScheduleHandler = Depends(get_schedule_handler),  # noqa: B008
) -> ScheduleResponse:
    schedule = handler.handle(GetScheduleQuery(schedule_id=schedule_id, user_id=user_id))
    return _schedule_to_response(schedule)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: DeleteScheduleHandler = Depends(get_delete_schedule_handler),  # noqa: B008
) -> Response:
    handler.handle(DeleteScheduleCommand(schedule_id=schedule_id, user_id=user_id))
    return Response(status_code=204)
