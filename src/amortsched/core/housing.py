from collections.abc import Iterable
from decimal import Decimal

from amortsched.core.values import HousingCosts, Installment


def apply_housing_costs(
    installments: Iterable[Installment],
    costs: HousingCosts,
    loan_amount: Decimal,
) -> tuple[Decimal, Decimal]:
    """Attach monthly housing costs to each scheduled installment.

    PMI is charged on the original loan amount while the loan-to-value ratio of the balance
    before the payment exceeds the cancellation threshold, and stops for good once it does not.

    Returns:
        The escrow total (tax, insurance, HOA) and the PMI total over the schedule.
    """
    escrow_total = Decimal("0.00")
    pmi_total = Decimal("0.00")
    pmi_active = costs.has_pmi
    for installment in installments:
        if installment.i is None:
            continue
        if pmi_active and not costs.pmi_applies(installment.balance.before):
            pmi_active = False
        housing = costs.monthly_payment(loan_amount=loan_amount, pmi_active=pmi_active)
        installment.housing = housing
        escrow_total += housing.escrow
        pmi_total += housing.pmi
    return escrow_total, pmi_total
