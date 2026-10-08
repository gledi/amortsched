from fastapi import APIRouter

from amortsched.api.dependencies import CurrentUserId, PrepayVsInvestPlan, RefinancePlan
from amortsched.api.schemas.tools import (
    AffordabilityRequest,
    AffordabilityResponse,
    CurrentLoanResponse,
    LoanTermsResponse,
    PrepayVsInvestRequest,
    PrepayVsInvestResponse,
    RefinanceRequest,
    RefinanceResponse,
)
from amortsched.app.queries.tools import (
    PrepayVsInvestPlanQuery,
    RefinancePlanQuery,
    compare_refinance,
    entered_terms_schedule,
)
from amortsched.core.calculators import PrepayVsInvestInput, affordability, prepay_vs_invest
from amortsched.core.money import round_cents
from amortsched.core.utils import today

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/affordability", response_model=AffordabilityResponse)
async def run_affordability(body: AffordabilityRequest, _user_id: CurrentUserId) -> AffordabilityResponse:
    return AffordabilityResponse.from_result(affordability(body.to_input()))


@router.post("/refinance", response_model=RefinanceResponse)
async def run_refinance(body: RefinanceRequest, user_id: CurrentUserId, handler: RefinancePlan) -> RefinanceResponse:
    if body.plan_id is not None:
        query = RefinancePlanQuery(
            plan_id=body.plan_id,
            user_id=user_id,
            as_of=body.as_of or today(),
            new_rate=body.new_rate,
            new_term_months=body.new_term_months,
            closing_costs=body.closing_costs,
            roll_costs_into_loan=body.roll_costs_into_loan,
        )
        outcome = await handler.handle(query)
        snapshot = outcome.snapshot
        current = CurrentLoanResponse(
            balance=round_cents(snapshot.balance),
            rate=snapshot.rate,
            remaining_months=snapshot.remaining_months,
            currency=snapshot.currency,
        )
        return RefinanceResponse.from_result(current, outcome.result)

    assert body.current_balance is not None and body.current_rate is not None and body.remaining_months is not None
    as_of = body.as_of or today()
    current_schedule = entered_terms_schedule(body.current_balance, body.current_rate, body.remaining_months)
    result = compare_refinance(
        current=current_schedule.generate(as_of),
        current_balance=body.current_balance,
        new_loan=lambda principal: entered_terms_schedule(principal, body.new_rate, body.new_term_months),
        new_start=as_of,
        closing_costs=body.closing_costs,
        roll_costs_into_loan=body.roll_costs_into_loan,
    )
    current = CurrentLoanResponse(
        balance=body.current_balance,
        rate=body.current_rate,
        remaining_months=body.remaining_months,
        currency=None,
    )
    return RefinanceResponse.from_result(current, result)


@router.post("/prepay-vs-invest", response_model=PrepayVsInvestResponse)
async def run_prepay_vs_invest(
    body: PrepayVsInvestRequest,
    user_id: CurrentUserId,
    handler: PrepayVsInvestPlan,
) -> PrepayVsInvestResponse:
    if body.plan_id is not None:
        query = PrepayVsInvestPlanQuery(
            plan_id=body.plan_id,
            user_id=user_id,
            extra_monthly=body.extra_monthly,
            annual_return=body.annual_return,
        )
        outcome = await handler.handle(query)
        loan = LoanTermsResponse(
            principal=outcome.principal,
            interest_rate=outcome.interest_rate,
            term_months=outcome.term_months,
            currency=outcome.currency,
        )
        return PrepayVsInvestResponse.from_result(loan, outcome.result)

    assert body.principal is not None and body.interest_rate is not None and body.term_months is not None
    data = PrepayVsInvestInput(
        principal=body.principal,
        interest_rate=body.interest_rate,
        term_months=body.term_months,
        extra_monthly=body.extra_monthly,
        annual_return=body.annual_return,
    )
    loan = LoanTermsResponse(
        principal=data.principal,
        interest_rate=data.interest_rate,
        term_months=data.term_months,
        currency=None,
    )
    return PrepayVsInvestResponse.from_result(loan, prepay_vs_invest(data))
