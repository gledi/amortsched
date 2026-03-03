import datetime
from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    """Base class for not-found errors."""

    pass


class UserNotFoundError(NotFoundError):
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


class PlanNotFoundError(NotFoundError):
    def __init__(self, plan_id: UUID | str) -> None:
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


class PlanAssociationError(DomainError):
    """Raised when a plan cannot be associated with a user due to user_id mismatch."""

    def __init__(self, *, plan_id: UUID, expected_user_id: UUID, actual_user_id: UUID) -> None:
        super().__init__(
            f"Plan {plan_id} belongs to user {expected_user_id}, cannot associate with user {actual_user_id}"
        )
        self.plan_id = plan_id
        self.expected_user_id = expected_user_id
        self.actual_user_id = actual_user_id


class UserAssociationError(DomainError):
    """Raised when a user cannot be set on a plan due to user_id mismatch."""

    def __init__(self, *, plan_id: UUID, plan_user_id: UUID, user_id: UUID) -> None:
        super().__init__(f"Cannot assign user {user_id} to plan {plan_id}: plan belongs to user {plan_user_id}")
        self.plan_id = plan_id
        self.plan_user_id = plan_user_id
        self.user_id = user_id


class DuplicatePlanError(DomainError):
    """Raised when adding a plan that already exists in the user's list."""

    def __init__(self, *, plan_id: UUID, user_id: UUID) -> None:
        super().__init__(f"Plan {plan_id} already belongs to user {user_id}")
        self.plan_id = plan_id
        self.user_id = user_id


class UnboundScheduleError(DomainError):
    """Raised when accessing a schedule's plan before it has been bound."""

    def __init__(self, schedule_id: UUID) -> None:
        super().__init__(f"Schedule {schedule_id} is not bound to a plan")
        self.schedule_id = schedule_id


class ScheduleAssociationError(DomainError):
    """Raised when a schedule cannot be associated with a plan due to plan_id mismatch."""

    def __init__(self, *, schedule_id: UUID, expected_plan_id: UUID, actual_plan_id: UUID) -> None:
        super().__init__(
            f"Schedule {schedule_id} belongs to plan {expected_plan_id}, cannot associate with plan {actual_plan_id}"
        )
        self.schedule_id = schedule_id
        self.expected_plan_id = expected_plan_id
        self.actual_plan_id = actual_plan_id


class ScheduleNotFoundError(NotFoundError):
    def __init__(self, schedule_id: UUID | str) -> None:
        super().__init__(f"Schedule not found: {schedule_id}")
        self.schedule_id = schedule_id


class ProfileNotFoundError(NotFoundError):
    def __init__(self, user_id: UUID | str) -> None:
        super().__init__(f"Profile not found for user: {user_id}")
        self.user_id = user_id


class UnboundProfileError(DomainError):
    """Raised when accessing a profile's user before it has been bound."""

    def __init__(self, profile_id: UUID) -> None:
        super().__init__(f"Profile {profile_id} is not bound to a user")
        self.profile_id = profile_id


class ProfileAssociationError(DomainError):
    """Raised when a profile cannot be associated with a user due to user_id mismatch."""

    def __init__(self, *, profile_id: UUID, expected_user_id: UUID, actual_user_id: UUID) -> None:
        super().__init__(
            f"Profile {profile_id} belongs to user {expected_user_id}, cannot associate with user {actual_user_id}"
        )
        self.profile_id = profile_id
        self.expected_user_id = expected_user_id
        self.actual_user_id = actual_user_id


class DuplicateProfileError(DomainError):
    """Raised when adding a profile that already exists for a user."""

    def __init__(self, *, user_id: UUID) -> None:
        super().__init__(f"User {user_id} already has a profile")
        self.user_id = user_id


class InvalidTokenError(DomainError):
    """Raised when a token cannot be decoded or verified."""

    def __init__(self, message: str = "Invalid or malformed token") -> None:
        super().__init__(message)


class ExpiredTokenError(InvalidTokenError):
    """Raised when a token has expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired")
