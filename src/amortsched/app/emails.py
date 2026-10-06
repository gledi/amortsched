from amortsched.app.ports import EmailMessage
from amortsched.core.entities import User


def _link(public_url: str, path: str, token: str) -> str:
    return f"{public_url.rstrip('/')}{path}?token={token}"


def verification_email(user: User, public_url: str, token: str) -> EmailMessage:
    link = _link(public_url, "/verify-email", token)
    return EmailMessage(
        to=user.email,
        subject="Confirm your email address",
        text=(
            "Hi,\n\n"
            f"Confirm your email address to finish setting up your account:\n\n{link}\n\n"
            "This link expires in 48 hours. If you did not create an account, ignore this email.\n"
        ),
        html=(
            "<p>Hi,</p>"
            "<p>Confirm your email address to finish setting up your account:</p>"
            f'<p><a href="{link}">Confirm email address</a></p>'
            "<p>This link expires in 48 hours. If you did not create an account, ignore this email.</p>"
        ),
    )


def password_reset_email(user: User, public_url: str, token: str) -> EmailMessage:
    link = _link(public_url, "/reset-password", token)
    return EmailMessage(
        to=user.email,
        subject="Reset your password",
        text=(
            "Hi,\n\n"
            f"Someone asked to reset the password for your account. Choose a new one here:\n\n{link}\n\n"
            "This link expires in 1 hour. If you did not ask for this, you can ignore this email.\n"
        ),
        html=(
            "<p>Hi,</p>"
            "<p>Someone asked to reset the password for your account. Choose a new one here:</p>"
            f'<p><a href="{link}">Reset password</a></p>'
            "<p>This link expires in 1 hour. If you did not ask for this, you can ignore this email.</p>"
        ),
    )
