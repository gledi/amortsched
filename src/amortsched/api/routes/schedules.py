import uuid

from fastapi import APIRouter, Depends, status

from amortsched.api.dependencies import (
    get_current_user_id,
    get_delete_schedule_handler,
    get_generate_schedule_handler,
    get_get_schedule_handler,
    get_list_schedules_handler,
    get_save_schedule_handler,
)
from amortsched.api.schemas.schedules import ScheduleResponse
from amortsched.app.commands.plans import (
    DeleteScheduleCommand,
    DeleteScheduleHandler,
    SaveScheduleCommand,
    SaveScheduleHandler,
)
from amortsched.app.queries.schedules import (
    GenerateScheduleHandler,
    GenerateScheduleQuery,
    GetScheduleHandler,
    GetScheduleQuery,
    ListSchedulesHandler,
    ListSchedulesQuery,
)

router = APIRouter(prefix="/api/plans/{plan_id}/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def generate_schedule(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: GenerateScheduleHandler = Depends(get_generate_schedule_handler),
) -> ScheduleResponse:
    schedule = await handler.handle(GenerateScheduleQuery(plan_id=plan_id, user_id=user_id))
    return ScheduleResponse.from_entity(schedule)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: ListSchedulesHandler = Depends(get_list_schedules_handler),
) -> list[ScheduleResponse]:
    schedules = await handler.handle(ListSchedulesQuery(plan_id=plan_id, user_id=user_id))
    return [ScheduleResponse.from_entity(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    plan_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: GetScheduleHandler = Depends(get_get_schedule_handler),
) -> ScheduleResponse:
    schedule = await handler.handle(GetScheduleQuery(schedule_id=schedule_id, user_id=user_id))
    return ScheduleResponse.from_entity(schedule)


@router.post("/{schedule_id}/save", response_model=ScheduleResponse)
async def save_schedule(
    plan_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: SaveScheduleHandler = Depends(get_save_schedule_handler),
) -> ScheduleResponse:
    schedule = await handler.handle(SaveScheduleCommand(plan_id=plan_id, user_id=user_id))
    return ScheduleResponse.from_entity(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    plan_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    handler: DeleteScheduleHandler = Depends(get_delete_schedule_handler),
) -> None:
    await handler.handle(DeleteScheduleCommand(schedule_id=schedule_id, user_id=user_id))
