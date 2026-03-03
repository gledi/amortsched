import datetime
from decimal import Decimal

import click
import msgspec
from rodi import Container

from amortsched.app.services import PlanService, UserService
from amortsched.core.security import PBKDF2PasswordHasher
from amortsched.core.values import EarlyPaymentFees
from amortsched.data.inmemory.repositories import InMemoryPlanRepository, InMemoryUserRepository


class ExtraPayment(msgspec.Struct):
    date: datetime.date
    amount: Decimal


class RecurringExtraPayment(msgspec.Struct):
    start_date: datetime.date
    amount: Decimal
    count: int


def _parse_extra(value: str) -> ExtraPayment:
    try:
        date_str, amount_str = value.split(":", 1)
        return ExtraPayment(date=datetime.date.fromisoformat(date_str), amount=Decimal(amount_str))
    except (ValueError, msgspec.ValidationError) as exc:
        raise click.BadParameter("Expected format YYYY-MM-DD:amount") from exc


def _parse_recurring_extra(value: str) -> RecurringExtraPayment:
    try:
        date_str, amount_str, count_str = value.split(":", 2)
        return RecurringExtraPayment(
            start_date=datetime.date.fromisoformat(date_str),
            amount=Decimal(amount_str),
            count=int(count_str),
        )
    except (ValueError, msgspec.ValidationError) as exc:
        raise click.BadParameter("Expected format YYYY-MM-DD:amount:count") from exc


def _build_container() -> Container:
    container = Container()
    container.register(InMemoryUserRepository, life_style="singleton")
    container.register(InMemoryPlanRepository, life_style="singleton")
    container.register(PBKDF2PasswordHasher)
    container.register(UserService)
    container.register(PlanService)
    return container


@click.group()
def cli() -> None:
    """Amortization CLI."""


@cli.command()
@click.option("--rate", type=float, required=True, help="Annual interest rate (e.g. 5.5)")
@click.option("--years", type=int, required=True, help="Term in years")
@click.option("--months", type=int, default=0, help="Additional term in months")
@click.option("--extra", multiple=True, callback=lambda _c, _p, v: [_parse_extra(x) for x in v])
@click.option("--recurring-extra", multiple=True, callback=lambda _c, _p, v: [_parse_recurring_extra(x) for x in v])
@click.option("--early-fee-fixed", type=str, default="0.00")
@click.option("--early-fee-percent", type=str, default="0.00")
@click.argument("amount", type=float)
def schedule(
    *,
    rate: float,
    years: int,
    months: int,
    extra: list[ExtraPayment],
    recurring_extra: list[RecurringExtraPayment],
    early_fee_fixed: str,
    early_fee_percent: str,
    amount: float,
) -> None:
    container = _build_container()
    plan_service = container.resolve(PlanService)
    user_service = container.resolve(UserService)

    user = user_service.register(email="cli@example.com", name="CLI User", password="cli")
    early_payment_fees = EarlyPaymentFees(fixed=Decimal(early_fee_fixed), percent=Decimal(early_fee_percent))
    plan = plan_service.create_plan(
        user_id=user.id,
        name="CLI Plan",
        amount=amount,
        term=(years, months),
        interest_rate=rate,
        start_date=datetime.date.today(),
        early_payment_fees=early_payment_fees,
    )

    for item in extra:
        plan_service.add_one_time_extra_payment(plan.id, user.id, item.date, item.amount)
    for item in recurring_extra:
        plan_service.add_recurring_extra_payment(plan.id, user.id, item.start_date, item.amount, item.count)

    result = plan_service.generate_schedule(plan.id, user.id)
    click.echo(f"Installments: {len(result.installments)}")
    if result.totals:
        click.echo(f"Total principal: {result.totals.principal:,.2f}")
        click.echo(f"Total interest: {result.totals.interest:,.2f}")
        click.echo(f"Total fees: {result.totals.fees:,.2f}")
        click.echo(f"Total paid: {result.totals.total_outflow:,.2f}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
