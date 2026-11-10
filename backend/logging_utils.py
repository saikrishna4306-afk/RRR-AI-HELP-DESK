"""JSON logs with request ids and phone-number redaction."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import time

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
PHONE_RE = re.compile(r"(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")


def redact(text: str) -> str:
    return PHONE_RE.sub("[phone-redacted]", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "msg": redact(record.getMessage()),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update({k: redact(str(v)) if isinstance(v, str) else v for k, v in extra.items()})
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def log(logger: logging.Logger, msg: str, **fields) -> None:
    logger.info(msg, extra={"extra_fields": fields})


class Timer:
    """Collects per-stage timings in milliseconds."""

    def __init__(self) -> None:
        self.timings: dict[str, int] = {}

    def stage(self, name: str):
        timer = self

        class _Ctx:
            def __enter__(self):
                self.t = time.perf_counter()

            def __exit__(self, *exc):
                timer.timings[name] = timer.timings.get(name, 0) + int((time.perf_counter() - self.t) * 1000)

        return _Ctx()
