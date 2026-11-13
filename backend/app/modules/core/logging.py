import logging
import contextvars
import re
from typing import Optional

request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
user_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
booking_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("booking_id", default=None)
venue_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("venue_id", default=None)

class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get()
        user_id = user_id_ctx.get()
        booking_id = booking_id_ctx.get()
        venue_id = venue_id_ctx.get()

        extras = []
        if req_id:
            extras.append(f"req_id={req_id}")
        if user_id:
            extras.append(f"user_id={user_id}")
        if booking_id:
            extras.append(f"booking_id={booking_id}")
        if venue_id:
            extras.append(f"venue_id={venue_id}")

        record.structured_info = "[" + " ".join(extras) + "] " if extras else ""

        # Format time and message properly
        record.asctime = self.formatTime(record, self.datefmt)
        msg = record.getMessage()
        return f"{record.asctime} {record.name} {record.levelname} {record.structured_info}{msg}"

_SECRET_PATHS = [
    # Guest booking manage links are bearer credentials (DATA_MAP row 31).
    (re.compile(r"(/bookings/manage/)[^/\s?\"']+"), r"\1[redacted]"),
    (re.compile(r"(/reset-password\?token=|[?&]token=)[^&\s\"']+"), r"\1[redacted]"),
]


def redact(text: str) -> str:
    for pattern, repl in _SECRET_PATHS:
        text = pattern.sub(repl, text)
    return text


class RedactSecretsFilter(logging.Filter):
    """Strips credentials that travel in URLs before a log line is written."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in (record.args if isinstance(record.args, tuple) else (record.args,)))
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        return True


def setup_logging():
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    
    formatter = StructuredLogFormatter()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "groundkart"):
        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        for handler in logger.handlers:
            handler.setFormatter(formatter)
            if not any(isinstance(f, RedactSecretsFilter) for f in handler.filters):
                handler.addFilter(RedactSecretsFilter())
        logger.setLevel(logging.INFO)
        # Prevent double logging
        logger.propagate = False
