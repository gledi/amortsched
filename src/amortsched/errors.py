import datetime
from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    pass


class UserNotFoundError(DomainError):
    def __init__(self, user_id: UUID | str) -> None:
        super().__init__(f"User not found: {user_id}")
        self.user_id = user_id


class DuplicateEmailError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")
        self.email = email


class AuthenticationError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class PlanNotFoundError(DomainError):
    def __init__(self, plan_id: UUID) -> None:
        super().__init__(f"Plan not found: {plan_id}")
        self.plan_id = plan_id


class PlanOwnershipError(DomainError):
    def __init__(self, plan_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} does not own plan {plan_id}")
        self.plan_id = plan_id
        self.user_id = user_id


class UnboundPlanError(DomainError):
    def __init__(self, plan_id: UUID) -> None:
        super().__init__(f"Plan {plan_id} is not bound to a user")
        self.plan_id = plan_id


class AmortizationError(DomainError):
    pass


class InvalidTermError(AmortizationError):
    def __init__(self, message: str, term: object) -> None:
        super().__init__(message)
        self.term = term


class InvalidExtraPaymentError(AmortizationError):
    def __init__(self, message: str, date: datetime.date, amount: int | float | Decimal) -> None:
        super().__init__(message)
        self.date = date
        self.amount = amount


class InvalidRecurringPaymentError(AmortizationError):
    def __init__(self, message: str, start_date: datetime.date, amount: int | float | Decimal, count: int) -> None:
        super().__init__(message)
        self.start_date = start_date
        self.amount = amount
        self.count = count
