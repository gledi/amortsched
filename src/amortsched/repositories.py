from uuid import UUID

from amortsched.entities import Plan, User
from amortsched.errors import DuplicateEmailError, PlanNotFoundError, UserNotFoundError


class UserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._email_index: dict[str, UUID] = {}

    def add(self, user: User) -> User:
        if user.email in self._email_index:
            raise DuplicateEmailError(user.email)
        self._users[user.id] = user
        self._email_index[user.email] = user.id
        return user

    def get_by_id(self, user_id: UUID) -> User:
        try:
            return self._users[user_id]
        except KeyError:
            raise UserNotFoundError(user_id) from None

    def get_by_email(self, email: str) -> User:
        try:
            user_id = self._email_index[email]
        except KeyError:
            raise UserNotFoundError(email) from None
        return self._users[user_id]

    def remove(self, user_id: UUID) -> None:
        user = self.get_by_id(user_id)
        del self._email_index[user.email]
        del self._users[user_id]

    def list_all(self) -> list[User]:
        return list(self._users.values())


class PlanRepository:
    def __init__(self) -> None:
        self._plans: dict[UUID, Plan] = {}

    def add(self, plan: Plan) -> Plan:
        self._plans[plan.id] = plan
        return plan

    def get_by_id(self, plan_id: UUID) -> Plan:
        try:
            return self._plans[plan_id]
        except KeyError:
            raise PlanNotFoundError(plan_id) from None

    def update(self, plan: Plan) -> Plan:
        if plan.id not in self._plans:
            raise PlanNotFoundError(plan.id)
        self._plans[plan.id] = plan
        return plan

    def remove(self, plan_id: UUID) -> None:
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        del self._plans[plan_id]

    def list_by_user(self, user_id: UUID) -> list[Plan]:
        return [p for p in self._plans.values() if p.user_id == user_id]
