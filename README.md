# Multilingual AI Diagnostic Assistant for Industrial Embroidery Machines

## 1. Problem
Over 80% of embroidery machine operators and small apparel workshops in India face daily machine breakdowns (thread snapping, needle breakage, tension issues). Technical manuals are mostly in complex English, and technicians take hours to arrive, resulting in expensive factory downtime.

## 2. Solution
An intuitive, multilingual AI assistant powered by Gnani.ai. Operators can ask troubleshooting questions in their regional language (Telugu, Hindi, English) and receive step-by-step mechanical fixes in seconds.

## 3. Key Features
- **Regional Language Support:** Tested across Telugu, Hindi, and English.
- **Accurate Domain Knowledge:** Understands textile terms like bobbin tension, thread path, needle deflection, and hoop stabilization.
- **Fast & Lightweight:** Delivers low-latency answers suitable for real workshop floors.

## 4. Built With
- Gnani.ai Language & Speech APIs
- Web Interface (Fast and mobile-friendly)
# RRR AI Help Desk (demo)

A demo website for RRR Group (embroidery and sewing machines, Hyderabad) with an AI Help Desk: ask about a machine problem in Telugu, Hindi or English by voice, text, photo or video, and get the repair video, a spoken answer and numbered steps. Built as a Gnani.ai internship showcase: multilingual voice, multimodal diagnosis, grounded hybrid RAG, cost control and evaluation.

> Demo prepared for RRR Group, not the official website. All guides are **sample content and need technician review**.

## 1. Install
1. Install **Python 3.11 or newer** from https://www.python.org/downloads/ (Windows: tick "Add python.exe to PATH").
2. Unzip `rrr-ai-helpdesk.zip` and open the folder in VS Code. Node.js is **not** needed (the website is prebuilt in `frontend/dist`).

## 2. Run
Windows Command Prompt, inside the folder:
```
start.bat
```
Mac/Linux: `./start.sh`. The first run creates `venv`, installs packages, copies `.env.example` to `.env` and starts **http://localhost:8000**. With no keys it runs fully in demo (mock) mode.

## 3. Paste your keys into `.env`
| Key | Where to get it | If empty |
|---|---|---|
| `GNANI_API_KEY` | Gnani/Vachana dashboard → API keys (docs.gnani.ai) | Gnani STT/TTS skipped; falls back to Gemini/edge/mock |
| `GNANI_TTS_VOICE_TE` | Pick a Telugu voice at https://docs.gnani.ai/api/TTS/available-voices | Telugu speech uses free edge-tts `te-IN-ShrutiNeural` |
| `GNANI_LLM_BASE_URL`, `GNANI_LLM_MODEL`, `GNANI_LLM_API_KEY` | Your internship LLM access: look in the Gnani dashboard/docs for an "OpenAI-compatible" endpoint (the base URL is the part before `/chat/completions`) and the model id. Key defaults to `GNANI_API_KEY` | Gnani LLM skipped; uses Gemini, then the built-in template |
| `GNANI_*_CREDITS_PER_*` | Your Gnani pricing page | Ledger counts units but estimates 0 credits |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey (free tier) | Gemini skipped |
| `GEMINI_LLM_MODEL`, `GEMINI_VISION_MODEL`, `GEMINI_STT_MODEL`, `GEMINI_EMBED_MODEL` | Run `venv\Scripts\python scripts\list_gemini_models.py` and copy names | That Gemini feature is skipped |
| `ADMIN_TOKEN` | Choose any password | Default `change-me` (change it before deploying) |

Then set the providers you want, for example:
```
LLM_PROVIDER=gnani   LLM_FALLBACK=gemini
STT_PROVIDER=gnani   STT_FALLBACK=gemini
TTS_PROVIDER=gnani   TTS_FALLBACK=edge
VISION_PROVIDER=gemini
```
Check Gnani once with `venv\Scripts\python scripts\smoke_gnani.py` (prints status codes and bodies; saves `smoke_tts.wav`).

## 4. Restart
Press Ctrl+C in the window and run `start.bat` again.

## 5. Confirm which providers are live
Open http://localhost:8000/#/help, ask a question, and read the **Powered by** strip under the answer (for example *STT: Gnani Prisma, LLM: Gnani LLM, TTS: Gnani Timbre*, with timings). Yellow chips mean a mock/fallback was used; hover a chip to see why. `#/admin` (token = `ADMIN_TOKEN`) shows provider status, usage and credits.

## 6. The demo: ask these 4 questions in order (Telugu)
1. నా ఎంబ్రాయిడరీ మెషిన్‌లో పై దారం పదే పదే తెగిపోతోంది, ఏం చేయాలి?
2. మెషిన్ నడుస్తున్నప్పుడు సూది విరిగిపోతోంది, దీన్ని ఎలా సరిచేయాలి?
3. డిజైన్ అవుట్‌లైన్ ఫిల్‌తో సరిపోవడం లేదు, మధ్యలో ఖాళీలు వస్తున్నాయి, ఏం చేయాలి?
4. బట్ట కింద దారం చిక్కులు చిక్కులుగా వస్తోంది, ఎందుకు ఇలా అవుతోంది?

For each: "I heard" shows the transcript, the repair video starts at the relevant chapter and requests autoplay with sound, the spoken answer is available from its play button, then the numbered steps, safety note and source guide appear. Browser autoplay settings may require a tap on Play. The same questions in Hindi and English are the "Try a demo question" buttons (switch the language selector).
Second flow: tap **Upload photo or video** and add text context if helpful. With Gemini vision configured, the image or short video and sanitized customer description are analyzed together with the text retrieval result; the app uses the matching guide/video only when evidence is strong enough. In mock mode vision uses filename hints (`needle`, `thread`, `outline`, `nest`). Unsupported repair issues or unrecognized uploads are handed to a technician. A first general greeting/help question gets a short capability reply; repeated out-of-library questions get a brief scope reply without creating a ticket. Two "Not solved" taps also create a ticket.

In mock mode the mock STT does not invent a transcript. The help desk uses browser speech recognition when your browser supports it; otherwise use typed text or configure Gnani/Gemini STT. Demo questions are available separately through the buttons below the form.

## 7. Add RRR's real documents, problems and videos later
- **Documents/guides:** drop `.md`, `.txt` or `.pdf` files into `data/knowledge/`. Guide format: header lines `title:`, `fault_id:`, `machine_model:` (`ALL` or a model name), `language:` (`te|hi|en`), `key_chapter:`, then `---`, then sections `## symptoms`, `## causes`, `## steps` (numbered), `## safety`, `## customers` (how customers describe the problem, in all three languages). The index rebuilds automatically on restart, or run `venv\Scripts\python -m backend.ingest`.
- **New problem:** add guides with a new `fault_id`, add an entry to `data/videos.json`, add it to the vision list in `backend/schemas.py` (`FAULTS`, `FaultOrUnknown`) and `VISION_PROMPT` in `backend/pipeline.py`, add demo/golden questions.
- **Videos:** put an MP4 in `data/videos/` and set `"video": "/media/videos/<file>.mp4"`, or use an unlisted YouTube link `"https://youtu.be/<id>"`. Set `chapters` to `[{"t": seconds, "label": "..."}]`; chapter labels should match `key_chapter` in the guides.

## 8. Deploy free (one container)
Render: New → Web Service → connect your GitHub repo → Runtime **Docker** → add environment variables from `.env` (never commit `.env`) → deploy. Fly.io: `fly launch` (uses the Dockerfile) then `fly secrets set GNANI_API_KEY=...`. Add your public URL to `ALLOWED_ORIGINS`. SQLite resets on free hosts when they restart; set `DATABASE_URL` to a free Postgres for persistent tickets (install `psycopg[binary]`).

## 9. Troubleshooting
- **Mic does not work:** the browser needs microphone permission; on phones use the deployed `https://` URL (mic is blocked on plain http except `localhost`).
- **No sound:** browsers block autoplay; tap **Play answer**. If the Powered-by chip says *Mock TTS*, the browser's own voice is used and may lack Telugu; set edge or Gnani TTS.
- **Telugu shows as boxes:** the page loads Noto fonts from Google Fonts; offline, Windows uses Nirmala UI.
- **401 / 403 from a provider:** wrong key or key without access; it falls back automatically. Run `scripts/smoke_gnani.py` to see the body.
- **Gemini does nothing:** model names in `.env` are blank on purpose; run `scripts/list_gemini_models.py` and fill them.
- **Changed `EMBED_PROVIDER`:** delete the `data/index` folder and restart (the app also refuses mismatched indexes and rebuilds).
- **Port 8000 busy:** close the other program, or run `venv\Scripts\python -m uvicorn backend.main:app --port 8001`.

## 10. What is mocked vs real
| Part | Real implementation | Mock (no keys) | Verified |
|---|---|---|---|
| STT | Gnani Prisma `/stt/v3`, Gemini audio; browser speech recognition when supported | No fabricated transcript | Mock only. Live calls **not verified** |
| TTS | Gnani Timbre, edge-tts | Chime + browser speech | Mock only. Live calls **not verified** |
| LLM | Gnani (OpenAI-compatible), Gemini | Deterministic template from the guide | Mock only. Live calls **not verified** |
| Vision | Gemini (image/short video) | Filename hints | Mock only |
| Retrieval | Hybrid BM25 + dense + RRF; Gemini or offline hash embeddings | Hash embeddings | Yes (tests + eval) |
| Videos | Your MP4s or YouTube | Generated demo explainers | Yes |

## For developers
- Tests (offline): `venv\Scripts\python -m pytest -q`. Lint: `ruff check backend tests scripts eval`.
- Evaluation: `python -m eval.run --mode mock` (or `real` with your keys) writes `docs/EVAL.md`.
- Frontend dev: `cd frontend && npm install && npm run dev` (needs Node 18+), then `npm run build` to refresh `frontend/dist`.
- API: `POST /api/ask` (multipart: `audio` WAV, `media`, `text`, `language`, `session_id`), `POST /api/feedback`, `GET /api/products`, `GET /api/demo-questions`, `GET /health`, `GET /metrics`, `GET /admin/{tickets,unanswered,usage,providers}` with header `X-Admin-Token`.
- Design notes: `docs/ADR.md`.
