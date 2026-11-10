"""VectorStore interface and a brute-force NumpyStore persisted as .npz + meta.json."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class IndexMismatch(Exception):
    pass


class VectorStore(ABC):
    @abstractmethod
    def add(self, vectors: np.ndarray, metas: list[dict]) -> None: ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int, where: dict | None = None) -> list[tuple[float, dict]]: ...


class NumpyStore(VectorStore):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.vectors = np.zeros((0, 0), dtype=np.float32)
        self.metas: list[dict] = []
        self.fingerprint = ""

    def add(self, vectors: np.ndarray, metas: list[dict]) -> None:
        v = np.asarray(vectors, dtype=np.float32)
        v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        self.vectors = v if self.vectors.size == 0 else np.vstack([self.vectors, v])
        self.metas.extend(metas)

    def search(self, query: np.ndarray, k: int, where: dict | None = None) -> list[tuple[float, dict]]:
        if not self.metas:
            return []
        q = np.asarray(query, dtype=np.float32)
        q = q / max(float(np.linalg.norm(q)), 1e-9)
        sims = self.vectors @ q
        order = np.argsort(-sims)
        out = []
        for i in order:
            m = self.metas[int(i)]
            if where and any(m.get(key) not in (val if isinstance(val, (list, set, tuple)) else [val]) for key, val in where.items()):
                continue
            out.append((float(sims[i]), m))
            if len(out) >= k:
                break
        return out

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        safe = self.model_name.replace(":", "_").replace("/", "_")
        np.savez_compressed(folder / f"{safe}.npz", vectors=self.vectors)
        (folder / f"{safe}.meta.json").write_text(
            json.dumps({"model": self.model_name, "fingerprint": self.fingerprint, "metas": self.metas}, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, folder: Path, model_name: str, file_model: str | None = None) -> "NumpyStore":
        """Load index saved for `file_model` (default model_name); refuse if recorded model differs."""
        safe = (file_model or model_name).replace(":", "_").replace("/", "_")
        meta_p, vec_p = folder / f"{safe}.meta.json", folder / f"{safe}.npz"
        if not meta_p.exists() or not vec_p.exists():
            raise FileNotFoundError(str(meta_p))
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        if meta.get("model") != model_name:
            raise IndexMismatch(f"index built with {meta.get('model')!r}, expected {model_name!r}")
        st = cls(model_name)
        st.vectors = np.load(vec_p)["vectors"]
        st.metas = meta["metas"]
        st.fingerprint = meta.get("fingerprint", "")
        return st
