import structlog

from amortsched.app.ports import EmailMessage

logger = structlog.get_logger()  # pyright: ignore[reportAny]


class ConsoleEmailSender:
    async def send(self, message: EmailMessage) -> None:
        await logger.ainfo("email_sent", to=message.to, subject=message.subject, body=message.text)  # pyright: ignore[reportAny]
