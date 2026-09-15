from fastapi import APIRouter

from amortsched.api.dependencies import ComparePlans, CurrentUserId
from amortsched.api.schemas.comparisons import PlanComparisonRequest, PlanComparisonResponse
from amortsched.app.queries.comparisons import ComparePlansQuery

router = APIRouter(prefix="/api/plan-comparisons", tags=["plan-comparisons"])


@router.post("/preview", response_model=PlanComparisonResponse)
async def preview_comparison(
    body: PlanComparisonRequest,
    user_id: CurrentUserId,
    handler: ComparePlans,
) -> PlanComparisonResponse:
    result = await handler.handle(ComparePlansQuery(plan_ids=tuple(body.plan_ids), user_id=user_id))
    return PlanComparisonResponse.from_result(result)
