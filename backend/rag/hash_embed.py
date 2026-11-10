"""Offline character n-gram hashing embedder (works for Telugu, Hindi, English)."""
from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np

DIM = 2048
MODEL_NAME = "hash:char3-5:v1"
_ws = re.compile(r"\s+")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    text = re.sub(r"[^\w\u0900-\u097F\u0C00-\u0C7F]+", " ", text)
    return _ws.sub(" ", text).strip()


def embed_one(text: str) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    for word in _norm(text).split():
        w = f" {word} "
        for n in (3, 4, 5):
            for i in range(max(1, len(w) - n + 1)):
                h = int.from_bytes(hashlib.blake2b(w[i : i + n].encode(), digest_size=8).digest(), "little")
                v[h % DIM] += 1.0 if (h >> 63) == 0 else -1.0
    nrm = np.linalg.norm(v)
    return v / nrm if nrm else v


class HashEmbedder:
    name = "hash"
    model_name = MODEL_NAME

    def available(self) -> bool:
        return True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [embed_one(t).tolist() for t in texts]


def tokenize(text: str) -> list[str]:
    toks = _norm(text).split()
    # add 4-char prefixes so agglutinative Telugu/Hindi word forms still overlap in BM25
    return toks + [t[:4] for t in toks if len(t) > 5]
