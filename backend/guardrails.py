"""Language detection, untrusted-text sanitising, handoff triggers and grounding checks."""
from __future__ import annotations

import re

TE = re.compile(r"[\u0C00-\u0C7F]")
DEV = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier)? ?(instructions|rules|prompts?)",
    r"disregard (all |the )?(previous|above|prior)",
    r"system prompt",
    r"you are now",
    r"act as (an?|the)",
    r"new instructions?:",
    r"developer mode",
    r"reveal (your|the) (prompt|instructions|keys?)",
    r"api[_ ]?key",
]
INJ_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

HUMAN_RE = re.compile(
    r"\b(human|real person|agent|talk to (someone|a person)|call me|customer care)\b"
    r"|మనిషి|మనిషితో|టెక్నీషియన్‌తో మాట్లాడ|కాల్ చేయండి|ఎవరితోనైనా మాట్లాడ"
    r"|इंसान|एजेंट|किसी से बात|कॉल करें|किसी व्यक्ति",
    re.IGNORECASE,
)
UNSAFE_RE = re.compile(
    r"bypass (the )?(safety|guard|sensor)|remove (the )?(safety )?guard|disable (the )?(sensor|safety)"
    r"|open (the )?(electrical|power) (panel|board)|run without (the )?cover|rewire",
    re.IGNORECASE,
)
MONEY_RE = re.compile(r"(₹|\brs\.?\s?\d|\binr\b|rupees?|रुपये|रुपए|రూపాయ)", re.IGNORECASE)
LONGNUM_RE = re.compile(r"\d[\d,]{2,}")


def detect_language(text: str, default: str = "te") -> str:
    te, dev, lat = len(TE.findall(text)), len(DEV.findall(text)), len(LATIN.findall(text))
    if te == dev == lat == 0:
        return default
    return max((te, "te"), (dev, "hi"), (lat, "en"))[1]


def script_ok(text: str, language: str) -> bool:
    te, dev, lat = len(TE.findall(text)), len(DEV.findall(text)), len(LATIN.findall(text))
    total = te + dev + lat
    if total == 0:
        return False
    share = {"te": te, "hi": dev, "en": lat}.get(language, 0) / total
    return share >= (0.5 if language == "en" else 0.4)


def sanitize_untrusted(text: str) -> tuple[str, bool]:
    """Drop lines that look like instructions to the model. Returns (clean_text, injection_found)."""
    found = False
    keep = []
    for ln in (text or "").splitlines():
        if INJ_RE.search(ln):
            found = True
            continue
        keep.append(ln)
    return "\n".join(keep).strip(), found


def wants_human(text: str) -> bool:
    return bool(HUMAN_RE.search(text or ""))


def unsafe_request(text: str) -> bool:
    return bool(UNSAFE_RE.search(text or ""))


def _grams(s: str, n: int = 3) -> set[str]:
    s = re.sub(r"\s+", " ", s.lower())
    return {s[i : i + n] for i in range(max(0, len(s) - n + 1))}


def grounded(sentence: str, sources: list[str], min_overlap: float = 0.4) -> bool:
    g = _grams(sentence)
    if not g:
        return False
    return max((len(g & _grams(src)) / len(g) for src in sources), default=0.0) >= min_overlap


def invented_numbers(text: str, guide_text: str) -> list[str]:
    bad = []
    if MONEY_RE.search(text) and not MONEY_RE.search(guide_text):
        bad.append("price/currency")
    for num in LONGNUM_RE.findall(text):
        if num not in guide_text:
            bad.append(num)
    return bad
