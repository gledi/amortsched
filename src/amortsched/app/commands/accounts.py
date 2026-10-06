import asyncio
import datetime
import uuid
from dataclasses import dataclass

from amortsched.app.emails import password_reset_email, verification_email
from amortsched.app.ports import EmailSender, Settings, TokenService
from amortsched.core.entities import AccountToken, User
from amortsched.core.errors import IncorrectPasswordError, InvalidAccountTokenError, UserNotFoundError
from amortsched.core.repositories import AccountTokenRepository, AsyncRepository, RefreshTokenRepository
from amortsched.core.security import PasswordHasher
from amortsched.core.specifications import Eq, Id
from amortsched.core.utils import now

VERIFICATION_TOKEN_TTL = datetime.timedelta(hours=48)
PASSWORD_RESET_TOKEN_TTL = datetime.timedelta(hours=1)


async def _issue_account_token(
    repo: AccountTokenRepository,
    token_service: TokenService,
    user_id: uuid.UUID,
    purpose: AccountToken.Purpose,
    ttl: datetime.timedelta,
) -> str:
    _ = await repo.invalidate_unused(user_id, purpose.value)
    raw_token = token_service.create_refresh_token()
    token = AccountToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_service.hash_refresh_token(raw_token),
        expires_at=now() + ttl,
    )
    _ = await repo.add(token)
    return raw_token


async def _consume_account_token(
    repo: AccountTokenRepository,
    token_service: TokenService,
    raw_token: str,
    purpose: AccountToken.Purpose,
) -> AccountToken:
    token = await repo.get_by_token_hash(token_service.hash_refresh_token(raw_token))
    if token is None or token.purpose != purpose or not token.is_usable(now()):
        raise InvalidAccountTokenError()
    if not await repo.mark_used(token.id):
        raise InvalidAccountTokenError()
    return token


async def _get_user(user_repo: AsyncRepository[User], user_id: uuid.UUID) -> User:
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


@dataclass(frozen=True, slots=True)
class SendVerificationEmailCommand:
    user_id: uuid.UUID


class SendVerificationEmailHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        account_token_repo: AccountTokenRepository,
        token_service: TokenService,
        email_sender: EmailSender,
        settings: Settings,
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._account_token_repo: AccountTokenRepository = account_token_repo
        self._token_service: TokenService = token_service
        self._email_sender: EmailSender = email_sender
        self._settings: Settings = settings

    async def handle(self, command: SendVerificationEmailCommand) -> None:
        user = await _get_user(self._user_repo, command.user_id)
        if user.email_verified:
            return
        raw_token = await _issue_account_token(
            self._account_token_repo,
            self._token_service,
            user.id,
            AccountToken.Purpose.EmailVerification,
            VERIFICATION_TOKEN_TTL,
        )
        await self._email_sender.send(verification_email(user, self._settings.public_url, raw_token))


@dataclass(frozen=True, slots=True)
class VerifyEmailCommand:
    token: str


class VerifyEmailHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        account_token_repo: AccountTokenRepository,
        token_service: TokenService,
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._account_token_repo: AccountTokenRepository = account_token_repo
        self._token_service: TokenService = token_service

    async def handle(self, command: VerifyEmailCommand) -> User:
        token = await _consume_account_token(
            self._account_token_repo,
            self._token_service,
            command.token,
            AccountToken.Purpose.EmailVerification,
        )
        user = await _get_user(self._user_repo, token.user_id)
        if not user.email_verified:
            user.email_verified_at = now()
            user.touch()
            _ = await self._user_repo.update(user)
        return user


@dataclass(frozen=True, slots=True)
class RequestPasswordResetCommand:
    email: str


class RequestPasswordResetHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        account_token_repo: AccountTokenRepository,
        token_service: TokenService,
        email_sender: EmailSender,
        settings: Settings,
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._account_token_repo: AccountTokenRepository = account_token_repo
        self._token_service: TokenService = token_service
        self._email_sender: EmailSender = email_sender
        self._settings: Settings = settings

    async def handle(self, command: RequestPasswordResetCommand) -> None:
        user = await self._user_repo.get_one_or_none(Eq("email", command.email.casefold()))
        if user is None or not user.is_active:
            return
        raw_token = await _issue_account_token(
            self._account_token_repo,
            self._token_service,
            user.id,
            AccountToken.Purpose.PasswordReset,
            PASSWORD_RESET_TOKEN_TTL,
        )
        await self._email_sender.send(password_reset_email(user, self._settings.public_url, raw_token))


@dataclass(frozen=True, slots=True)
class ResetPasswordCommand:
    token: str
    password: str


class ResetPasswordHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        account_token_repo: AccountTokenRepository,
        refresh_token_repo: RefreshTokenRepository,
        token_service: TokenService,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._account_token_repo: AccountTokenRepository = account_token_repo
        self._refresh_token_repo: RefreshTokenRepository = refresh_token_repo
        self._token_service: TokenService = token_service
        self._password_hasher: PasswordHasher = password_hasher

    async def handle(self, command: ResetPasswordCommand) -> User:
        token = await _consume_account_token(
            self._account_token_repo,
            self._token_service,
            command.token,
            AccountToken.Purpose.PasswordReset,
        )
        user = await _get_user(self._user_repo, token.user_id)
        user.password_hash = await asyncio.to_thread(self._password_hasher.hash, command.password)
        if not user.email_verified:
            user.email_verified_at = now()
        user.touch()
        _ = await self._user_repo.update(user)
        _ = await self._refresh_token_repo.revoke_all_for_user(user.id)
        return user


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    user_id: uuid.UUID
    current_password: str
    new_password: str


class ChangePasswordHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        refresh_token_repo: RefreshTokenRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._refresh_token_repo: RefreshTokenRepository = refresh_token_repo
        self._password_hasher: PasswordHasher = password_hasher

    async def handle(self, command: ChangePasswordCommand) -> User:
        user = await _get_user(self._user_repo, command.user_id)
        if not await asyncio.to_thread(self._password_hasher.verify, command.current_password, user.password_hash):
            raise IncorrectPasswordError()
        user.password_hash = await asyncio.to_thread(self._password_hasher.hash, command.new_password)
        user.touch()
        _ = await self._user_repo.update(user)
        _ = await self._refresh_token_repo.revoke_all_for_user(user.id)
        return user


@dataclass(frozen=True, slots=True)
class UpdateAccountCommand:
    user_id: uuid.UUID
    name: str


class UpdateAccountHandler:
    def __init__(self, user_repo: AsyncRepository[User]) -> None:
        self._user_repo: AsyncRepository[User] = user_repo

    async def handle(self, command: UpdateAccountCommand) -> User:
        user = await _get_user(self._user_repo, command.user_id)
        user.name = command.name
        user.touch()
        _ = await self._user_repo.update(user)
        return user


@dataclass(frozen=True, slots=True)
class RevokeAllSessionsCommand:
    user_id: uuid.UUID


class RevokeAllSessionsHandler:
    def __init__(self, refresh_token_repo: RefreshTokenRepository) -> None:
        self._refresh_token_repo: RefreshTokenRepository = refresh_token_repo

    async def handle(self, command: RevokeAllSessionsCommand) -> None:
        _ = await self._refresh_token_repo.revoke_all_for_user(command.user_id)


@dataclass(frozen=True, slots=True)
class DeleteAccountCommand:
    user_id: uuid.UUID
    password: str


class DeleteAccountHandler:
    def __init__(self, user_repo: AsyncRepository[User], password_hasher: PasswordHasher) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._password_hasher: PasswordHasher = password_hasher

    async def handle(self, command: DeleteAccountCommand) -> None:
        user = await _get_user(self._user_repo, command.user_id)
        if not await asyncio.to_thread(self._password_hasher.verify, command.password, user.password_hash):
            raise IncorrectPasswordError()
        _ = await self._user_repo.purge(Id(user.id))
