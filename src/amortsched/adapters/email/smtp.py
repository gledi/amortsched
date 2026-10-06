import asyncio
import smtplib
import ssl
from email.message import EmailMessage as MimeMessage

from amortsched.app.ports import EmailMessage


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = False,
        use_ssl: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self._host: str = host
        self._port: int = port
        self._sender: str = sender
        self._username: str | None = username
        self._password: str | None = password
        self._starttls: bool = starttls
        self._use_ssl: bool = use_ssl
        self._timeout: float = timeout

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, self._to_mime(message))

    def _to_mime(self, message: EmailMessage) -> MimeMessage:
        mime = MimeMessage()
        mime["From"] = self._sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        if message.html is not None:
            mime.add_alternative(message.html, subtype="html")
        return mime

    def _send_sync(self, mime: MimeMessage) -> None:
        context = ssl.create_default_context()
        if self._use_ssl:
            client = smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context)
        else:
            client = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        with client:
            if self._starttls and not self._use_ssl:
                client.starttls(context=context)
            if self._username:
                client.login(self._username, self._password or "")
            client.send_message(mime)
