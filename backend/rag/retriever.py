"""Hybrid retrieval: dense + BM25 fused with Reciprocal Rank Fusion, plus metadata filters."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from ..config import DATA, get_settings
from . import docs as docs_mod
from .hash_embed import HashEmbedder, tokenize
from .store import IndexMismatch, NumpyStore

logger = logging.getLogger("retriever")
INDEX_DIR = DATA / "index"
KNOWLEDGE_DIR = DATA / "knowledge"
RRF_K = 60


@dataclass
class RetrievalResult:
    fault_id: str
    confidence: float
    cosine: float
    embed_model: str
    hits: list[dict]


class Retriever:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR, index_dir: Path = INDEX_DIR) -> None:
        self.knowledge_dir = knowledge_dir
        self.index_dir = index_dir
        self.guides: list[docs_mod.Guide] = []
        self.chunks: list[dict] = []
        self.stores: dict[str, NumpyStore] = {}
        self.bm25: BM25Okapi | None = None
        self.hash_embedder = HashEmbedder()
        self.primary = None  # optional remote embedder (Gemini)

    # ---------- build / load ----------
    async def ensure(self, primary_embedder=None, force: bool = False) -> None:
        self.primary = primary_embedder
        self.guides = docs_mod.load_all(self.knowledge_dir)
        self.chunks = docs_mod.chunks(self.guides)
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks]) if self.chunks else None
        fp = docs_mod.fingerprint(self.knowledge_dir)
        embedders = [self.hash_embedder] + ([primary_embedder] if primary_embedder and primary_embedder.available() else [])
        for emb in embedders:
            name = emb.model_name
            store = None
            if not force:
                try:
                    store = NumpyStore.load(self.index_dir, name)
                    if store.fingerprint != fp:
                        logger.info(f"index for {name} is stale; rebuilding")
                        store = None
                except (FileNotFoundError, IndexMismatch) as e:
                    logger.info(f"rebuilding index for {name}: {e}")
            if store is None:
                try:
                    vecs = await emb.embed([c["text"] for c in self.chunks])
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"could not build {name} index: {e!r}")
                    continue
                store = NumpyStore(name)
                store.fingerprint = fp
                if self.chunks:
                    store.add(np.array(vecs), self.chunks)
                store.save(self.index_dir)
            self.stores[name] = store

    # ---------- query ----------
    async def _dense(self, query: str, where: dict | None) -> tuple[list[tuple[float, dict]], str]:
        if self.primary is not None and self.primary.model_name in self.stores:
            try:
                q = (await self.primary.embed([query]))[0]
                return self.stores[self.primary.model_name].search(np.array(q), 20, where), self.primary.model_name
            except Exception as e:  # noqa: BLE001
                logger.warning(f"primary embedder failed at query time, using hash: {e!r}")
        name = self.hash_embedder.model_name
        q = (await self.hash_embedder.embed([query]))[0]
        return self.stores[name].search(np.array(q), 20, where), name

    async def search(self, query: str, machine_model: str | None = None) -> RetrievalResult:
        where = {"machine_model": ["ALL", machine_model]} if machine_model else None
        dense, model = await self._dense(query, where)
        dense_rank = {m["id"]: r for r, (_, m) in enumerate(dense)}
        cos_by_id = {m["id"]: s for s, m in dense}
        bm_rank: dict[str, int] = {}
        if self.bm25 is not None:
            scores = self.bm25.get_scores(tokenize(query))
            order = np.argsort(-scores)
            r = 0
            for i in order[:20]:
                c = self.chunks[int(i)]
                if scores[i] <= 0:
                    break
                if where and c["machine_model"] not in where["machine_model"]:
                    continue
                bm_rank[c["id"]] = r
                r += 1
        fused: dict[str, float] = {}
        for cid, r in dense_rank.items():
            fused[cid] = fused.get(cid, 0) + 1 / (RRF_K + r + 1)
        for cid, r in bm_rank.items():
            fused[cid] = fused.get(cid, 0) + 1 / (RRF_K + r + 1)
        by_id = {c["id"]: c for c in self.chunks}
        ranked = sorted(fused.items(), key=lambda x: -x[1])
        hits = [{**by_id[cid], "rrf": round(sc, 5), "cosine": round(cos_by_id.get(cid, 0.0), 4)} for cid, sc in ranked[:8]]
        if not hits:
            return RetrievalResult("unknown", 0.0, 0.0, model, [])
        # aggregate per fault (sum of fused scores)
        per_fault: dict[str, float] = {}
        for h in hits:
            per_fault[h["fault_id"]] = per_fault.get(h["fault_id"], 0) + h["rrf"]
        best = max(per_fault, key=per_fault.get)
        best_cos = max((h["cosine"] for h in hits if h["fault_id"] == best), default=0.0)
        has_bm = any(by_id[cid]["fault_id"] == best for cid in bm_rank)
        thr = get_settings().threshold_for(model)
        conf = 0.5 + 0.5 * (best_cos - thr) / max(1e-6, 1 - thr) if best_cos >= thr else 0.5 * best_cos / max(thr, 1e-6)
        if not has_bm:
            conf *= 0.8  # keyword evidence missing
        return RetrievalResult(best, round(float(min(max(conf, 0.0), 1.0)), 3), round(best_cos, 4), model, hits)

    def guide(self, fault_id: str, language: str) -> docs_mod.Guide | None:
        cands = [g for g in self.guides if g.fault_id == fault_id]
        for lang in (language, "en"):
            for g in cands:
                if g.language == lang:
                    return g
        return cands[0] if cands else None

    def fault_ids(self) -> list[str]:
        return sorted({g.fault_id for g in self.guides if g.fault_id != "general"})
