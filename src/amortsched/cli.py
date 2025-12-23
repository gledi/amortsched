import argparse
import datetime
import sys
from decimal import Decimal

from rich.console import Console
from rich.table import Table

from amortsched.amortization import AmortizationSchedule, EarlyPaymentFees


class Namespace(argparse.Namespace):
    rate: float
    years: int
    months: int
    amount: float


def parse_extra_arg(arg: str) -> tuple[datetime.date, Decimal]:
    parts = arg.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("Expected format YYYY-MM-DD:amount")
    date = datetime.date.fromisoformat(parts[0])
    amount = Decimal(parts[1])
    return date, amount


def parse_recurring_arg(
    arg: str,
) -> tuple[datetime.date, Decimal, int]:
    parts = arg.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("Expected format YYYY-MM-DD:amount:count")
    start = datetime.date.fromisoformat(parts[0])
    amount = Decimal(parts[1])
    count = int(parts[2]) if len(parts) >= 3 else 0
    if count <= 0:
        raise argparse.ArgumentTypeError("count must be a positive integer")
    return start, amount, count


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Amortization Schedule Generator")

    parser.add_argument(
        "-r",
        "--rate",
        type=float,
        required=True,
        help="Annual interest rate (as a percentage, e.g., 5.5 for 5.5%% not 0.055)",
    )

    parser.add_argument(
        "-y",
        "--years",
        type=int,
        required=True,
        help="Term in years",
    )

    parser.add_argument(
        "-m",
        "--months",
        type=int,
        default=0,
        help="Additional term in months",
    )

    parser.add_argument("amount", type=float, help="Loan amount")

    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="One-time extra payment as YYYY-MM-DD:amount",
    )

    parser.add_argument(
        "--recurring-extra",
        action="append",
        default=[],
        help="Recurring extra payment as YYYY-MM-DD:amount:count",
    )

    parser.add_argument("--early-fee-fixed", type=Decimal, default=Decimal("0.00"), help="Fixed fee for extra payments")
    parser.add_argument(
        "--early-fee-percent",
        type=Decimal,
        default=Decimal("0.00"),
        help="Percent fee (of remaining principal) for extra payments",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv, namespace=Namespace())
    early_payment_fees = EarlyPaymentFees(
        fixed=args.early_fee_fixed,
        percent=args.early_fee_percent,
    )
    schedule = AmortizationSchedule(
        amount=args.amount,
        term=(args.years, args.months),
        interest_rate=args.rate,
        early_payment_fees=early_payment_fees,
    )
    for extra_arg in args.extra:
        dt, amount = parse_extra_arg(extra_arg)
        schedule.add_one_time_extra_payment(dt, amount)
    for recurring_arg in args.recurring_extra:
        start, amount, count = parse_recurring_arg(recurring_arg)
        schedule.add_recurring_extra_payment(start_date=start, amount=amount, count=count)
    console = Console()
    table = Table(title="Amortization Schedule")
    table.add_column("Installment #", justify="right", style="cyan", no_wrap=True)
    table.add_column("Year/Month", style="magenta")
    table.add_column("Type", style="magenta")
    table.add_column("Principal", justify="right", style="green")
    table.add_column("Interest", justify="right", style="red")
    table.add_column("Fees", justify="right", style="red")
    table.add_column("Total", justify="right", style="yellow")
    table.add_column("Balance Before", justify="right", style="blue")
    table.add_column("Balance After", justify="right", style="blue")
    for installment in schedule.generate(start_date=datetime.date.today()):
        table.add_row(*installment.to_row())
    console.print(table)
    totals = schedule.last_totals
    if totals:
        console.print(f"[bold]Total Principal Paid:[/bold] {totals.principal:,.2f}")
        console.print(f"[bold]Total Interest Paid:[/bold] {totals.interest:,.2f}")
        console.print(f"[bold]Total Fees Paid:[/bold] {totals.fees:,.2f}")
        console.print(f"[bold]Total Amount Paid:[/bold] {totals.total_outflow:,.2f}")


if __name__ == "__main__":
    main()
