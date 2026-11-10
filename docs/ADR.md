# Architecture decision notes

**ADR-1 One process, one container.** FastAPI serves the API and the prebuilt React app so the demo deploys to a 512 MB free host. No torch or local models.

**ADR-2 Providers chosen by env, with fallback chains.** Each service (LLM, STT, TTS, vision, embeddings) has an async interface. A chain tries primary → fallback → mock with timeouts and tenacity retries; missing keys or an exhausted Gnani credit budget skip a provider silently. Every response lists which provider actually ran (the "Powered by" strip), so a showcase never silently pretends.

**ADR-3 Hybrid retrieval over a tiny corpus.** BM25 + dense vectors fused with Reciprocal Rank Fusion. An offline character n-gram hash embedder always exists, so search works with no network; Gemini embeddings are optional. Each guide carries a trilingual "how customers describe this" section (document expansion), which is what makes Telugu questions match even with the hash embedder. The index stores the embedding model name and refuses to load on mismatch.

**ADR-4 Grounded structured output with a deterministic floor.** The LLM must return JSON validated by Pydantic plus checks: language/script, no invented numbers or prices, every step must overlap a guide step, chapter must exist, safety note is always the guide's. One repair retry, then a template built from the guide. Worst case is a correct but plainer answer, never an invented one.

**ADR-5 Closed-set vision fused with retrieval.** Vision picks from the 4 known faults or "unknown" (strict JSON). It runs in parallel with retrieval; agreement raises confidence, disagreement or weak signals hand off to a human ticket.

**ADR-6 Untrusted text.** Transcripts, guides and text in media are data. Instruction-like lines are stripped before prompting, the system prompt says so, and output validation catches what slips through (tested).

**ADR-7 Cost control.** Ledger of units per call (audio seconds, characters, tokens) with credit rates from `.env`; Gnani is skipped once `GNANI_CREDIT_BUDGET` is reached. TTS audio is cached on disk by hash(text, voice, language, provider), and answers are cached per (fault, language) for text-only questions.
