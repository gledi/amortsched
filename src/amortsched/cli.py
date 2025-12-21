import argparse
import datetime
import sys

from rich.console import Console
from rich.table import Table

from amortsched.amortization import AmortizationSchedule


class Namespace(argparse.Namespace):
    rate: float
    years: int
    months: int
    amount: float


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

    return parser


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv, namespace=Namespace())
    schedule = AmortizationSchedule(amount=args.amount, term=(args.years, args.months), interest_rate=args.rate)
    console = Console()
    table = Table(title="Amortization Schedule")
    table.add_column("Installment #", justify="right", style="cyan", no_wrap=True)
    table.add_column("Year/Month", style="magenta")
    table.add_column("Principal", justify="right", style="green")
    table.add_column("Interest", justify="right", style="red")
    table.add_column("Total Payment", justify="right", style="yellow")
    table.add_column("Balance Before", justify="right", style="blue")
    table.add_column("Balance After", justify="right", style="blue")
    for installment in schedule.generate(start_date=datetime.date.today()):
        table.add_row(*installment.to_row())
    console.print(table)

    console.print(f"[bold]Total Interest Paid:[/bold] {schedule.total_interest_paid:,.2f}")
    console.print(f"[bold]Total Amount Paid:[/bold] {schedule.total_amount_paid:,.2f}")


if __name__ == "__main__":
    main()
