"""Load guides / business docs from data/knowledge (md, txt, pdf) and chunk them by section."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

HEADER_KEYS = {"title", "fault_id", "machine_model", "language", "key_chapter"}


@dataclass
class Guide:
    path: str
    title: str
    fault_id: str
    machine_model: str
    language: str
    key_chapter: str
    body: str
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def steps(self) -> list[str]:
        txt = self.sections.get("steps", "")
        return [re.sub(r"^\d+[.)]\s*", "", ln).strip() for ln in txt.splitlines() if re.match(r"^\s*\d+[.)]", ln)]

    @property
    def safety_note(self) -> str:
        return self.sections.get("safety", "").strip()


SECTION_ALIASES = {
    "symptoms": "symptoms",
    "causes": "causes",
    "steps": "steps",
    "safety": "safety",
    "customers": "customers",
}


def _read_text(p: Path) -> str:
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    return p.read_text(encoding="utf-8")


def parse(p: Path) -> Guide:
    raw = _read_text(p)
    head, sep, body = raw.partition("\n---\n")
    meta = {}
    if sep:
        for ln in head.splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                if k.strip().lower() in HEADER_KEYS:
                    meta[k.strip().lower()] = v.strip()
    else:
        body = raw
    sections: dict[str, str] = {}
    current = "intro"
    for ln in body.splitlines():
        m = re.match(r"^##\s*\[?(\w+)\]?", ln)
        if m:
            current = SECTION_ALIASES.get(m.group(1).lower(), m.group(1).lower())
            continue
        sections[current] = sections.get(current, "") + ln + "\n"
    return Guide(
        path=p.name,
        title=meta.get("title", p.stem),
        fault_id=meta.get("fault_id", "general"),
        machine_model=meta.get("machine_model", "ALL"),
        language=meta.get("language", "en"),
        key_chapter=meta.get("key_chapter", ""),
        body=body,
        sections={k: v.strip() for k, v in sections.items() if v.strip()},
    )


def load_all(folder: Path) -> list[Guide]:
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in (".md", ".txt", ".pdf"))
    return [parse(p) for p in files]


def fingerprint(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.glob("*")):
        if p.suffix.lower() in (".md", ".txt", ".pdf"):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def chunks(guides: list[Guide]) -> list[dict]:
    out = []
    for g in guides:
        for sec, text in g.sections.items():
            if sec == "intro" and len(text) < 40:
                continue
            for i in range(0, len(text), 1200):
                out.append(
                    {
                        "id": f"{g.path}#{sec}{i // 1200}",
                        "path": g.path,
                        "title": g.title,
                        "fault_id": g.fault_id,
                        "machine_model": g.machine_model,
                        "language": g.language,
                        "section": sec,
                        "text": f"{g.title}\n{text[i:i + 1200]}",
                    }
                )
    return out
