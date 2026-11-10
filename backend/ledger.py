"""Usage ledger with Gnani credit budget."""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from .config import get_settings
from .db import Usage, session

logger = logging.getLogger("ledger")


def record(provider: str, service: str, unit: str, units: float, note: str = "") -> float:
    s = get_settings()
    credits = 0.0
    if provider == "gnani":
        rate = {
            "audio_sec": s.gnani_stt_credits_per_sec,
            "chars": s.gnani_tts_credits_per_1k_chars / 1000.0,
            "tokens": s.gnani_llm_credits_per_1k_tokens / 1000.0,
        }.get(unit, 0.0)
        credits = units * rate
    with session() as db:
        db.add(Usage(provider=provider, service=service, unit=unit, units=units, est_credits=credits, note=note[:200]))
        db.commit()
    return credits


def gnani_credits_used() -> float:
    with session() as db:
        val = db.scalar(select(func.coalesce(func.sum(Usage.est_credits), 0.0)).where(Usage.provider == "gnani"))
    return float(val or 0.0)


def gnani_budget_ok() -> bool:
    used = gnani_credits_used()
    ok = used < get_settings().gnani_credit_budget
    if not ok:
        logger.warning("gnani credit budget reached; using free providers", extra={"extra_fields": {"used": used}})
    return ok


def summary() -> dict:
    with session() as db:
        rows = db.execute(
            select(Usage.provider, Usage.service, Usage.unit, func.count(), func.sum(Usage.units), func.sum(Usage.est_credits))
            .group_by(Usage.provider, Usage.service, Usage.unit)
        ).all()
    s = get_settings()
    return {
        "gnani_budget": s.gnani_credit_budget,
        "gnani_used": round(gnani_credits_used(), 3),
        "rows": [
            {"provider": p, "service": sv, "unit": u, "calls": c, "units": round(un or 0, 2), "est_credits": round(cr or 0, 3)}
            for p, sv, u, c, un, cr in rows
        ],
    }
