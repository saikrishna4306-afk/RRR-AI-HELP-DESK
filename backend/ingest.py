"""Rebuild the search index from data/knowledge.  Usage:  python -m backend.ingest"""
from __future__ import annotations

import asyncio

from .providers.registry import embedder
from .rag.retriever import Retriever


async def main() -> None:
    r = Retriever()
    await r.ensure(embedder(), force=True)
    print(f"indexed {len(r.guides)} documents, {len(r.chunks)} chunks; stores: {list(r.stores)}")


if __name__ == "__main__":
    asyncio.run(main())
