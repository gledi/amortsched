from mashumaro.exceptions import InvalidFieldValue
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from amortsched.amortization import AmortizationSchedule, EarlyPaymentFees
from amortsched.validators import (
    AmortizationRequest,
    AmortizationResponse,
    BalanceResponse,
    InstallmentResponse,
    TotalsResponse,
)


async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def create_schedule(request: Request) -> Response:
    try:
        body = await request.body()
        req = AmortizationRequest.from_json(body)
    except (InvalidFieldValue, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    schedule = AmortizationSchedule(
        amount=req.amount,
        term=(req.term.years, req.term.months),
        interest_rate=req.interest_rate,
        early_payment_fees=EarlyPaymentFees(fixed=req.early_payment_fees.fixed, percent=req.early_payment_fees.percent),
    )

    for ep in req.extra_payments:
        schedule.add_one_time_extra_payment(ep.date, ep.amount)
    for rep in req.recurring_extra_payments:
        schedule.add_recurring_extra_payment(start_date=rep.start_date, amount=rep.amount, count=rep.count)

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
        for item in schedule.generate(start_date=req.start_date)
    ]

    totals_payload = None
    if t := schedule.last_totals:
        totals_payload = TotalsResponse(
            principal=t.principal,
            interest=t.interest,
            fees=t.fees,
            total=t.total_outflow,
            months=t.months,
            paid_off=t.paid_off,
        )

    resp_data = AmortizationResponse(installments=installments, totals=totals_payload)
    return Response(content=resp_data.to_json(), media_type="application/json")


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/amortization", create_schedule, methods=["POST"]),
]

app = Starlette(debug=False, routes=routes)
