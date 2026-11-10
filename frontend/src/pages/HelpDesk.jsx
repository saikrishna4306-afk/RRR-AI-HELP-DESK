import React, { useEffect, useRef, useState } from "react";
import { ask, getJSON, sendFeedback } from "../lib/api.js";
import { WavRecorder } from "../lib/recorder.js";

const LANGS = [["auto", "Auto"], ["te", "తెలుగు"], ["hi", "हिन्दी"], ["en", "English"]];
const SPEECH_LANG = { te: "te-IN", hi: "hi-IN", en: "en-IN" };
const UI = {
  listening: "Listening...",
  understanding: "Understanding your problem...",
  video: "Preparing the video...",
};
const sessionId = (() => {
  const k = "rrr_session";
  try {
    let v = sessionStorage.getItem(k);
    if (!v) { v = Math.random().toString(36).slice(2, 12); sessionStorage.setItem(k, v); }
    return v;
  } catch { return Math.random().toString(36).slice(2, 12); }
})();

function youtubeId(url) {
  const m = String(url).match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? m[1] : null;
}

function VideoPlayer({ video }) {
  const ref = useRef(null);
  const [muted, setMuted] = useState(true);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const [start, setStart] = useState(video.start_seconds || 0);
  const yt = youtubeId(video.url);
  useEffect(() => { setStart(video.start_seconds || 0); setMuted(true); setAutoplayBlocked(false); }, [video]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const go = () => {
      el.currentTime = start;
      el.muted = muted;
      el.play().then(() => setAutoplayBlocked(false)).catch(() => setAutoplayBlocked(true));
    };
    if (el.readyState >= 1) go(); else el.addEventListener("loadedmetadata", go, { once: true });
    return () => el.removeEventListener("loadedmetadata", go);
  }, [start, video, muted]);
  return (
    <div className="video-block">
      <h3 className="video-title">{video.title}</h3>
      <div className="video-frame">
        {yt ? (
          <iframe key={`${yt}-${start}-${muted}`} title={video.title}
            src={`https://www.youtube-nocookie.com/embed/${yt}?start=${Math.floor(start)}&autoplay=1&mute=${muted ? 1 : 0}&rel=0&playsinline=1`}
            allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen />
        ) : (
          <video ref={ref} src={video.url} muted={muted} autoPlay playsInline controls preload="auto" />
        )}
      </div>
      {(autoplayBlocked || yt) && <p className="hint">If your browser blocks autoplay with sound, press Play on the video to start it.</p>}
      <div className="chapters" role="group" aria-label="Video chapters">
        {video.chapters.map((c, i) => (
          <button key={c.t} type="button" className={`chapter ${c.t === start ? "on" : ""}`} onClick={() => setStart(c.t)} aria-pressed={c.t === start}>
            <span className="chapter-n">{i + 1}</span>{c.label}
          </button>
        ))}
        <button type="button" className="chapter unmute" onClick={() => setMuted((m) => !m)}>{muted ? "Unmute video" : "Mute video"}</button>
      </div>
    </div>
  );
}

function speakWithBrowser(text, lang) {
  if (!("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = SPEECH_LANG[lang] || "te-IN";
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith(u.lang.slice(0, 2)));
  if (voice) u.voice = voice;
  window.speechSynthesis.speak(u);
  return true;
}

function AnswerAudio({ result }) {
  const audioRef = useRef(null);
  const [blocked, setBlocked] = useState(false);
  const browserVoice = !result.audio || result.audio.provider === "mock";
  const play = () => {
    setBlocked(false);
    if (browserVoice) { if (!speakWithBrowser(result.answer.spoken_text, result.language)) setBlocked(true); return; }
    audioRef.current?.play().catch(() => setBlocked(true));
  };
  useEffect(() => {
    setBlocked(false);
    if (browserVoice) {
      audioRef.current = null;
      if (!speakWithBrowser(result.answer.spoken_text, result.language)) setBlocked(true);
      return () => window.speechSynthesis?.cancel();
    }
    const a = new Audio(`data:${result.audio.mime};base64,${result.audio.b64}`);
    audioRef.current = a;
    a.play().catch(() => setBlocked(true));
    return () => { a.pause(); audioRef.current = null; };
  }, [result, browserVoice]);
  return (
    <div className="spoken">
      <button type="button" className="btn play" onClick={play} aria-label="Play the spoken answer">▶ Play answer</button>
      <p lang={result.language}>{result.answer.spoken_text}</p>
      {blocked && <p className="hint">Your browser blocked autoplay. Tap “Play answer”.</p>}
      {browserVoice && <p className="hint">Voice: browser speech (server TTS not available).</p>}
    </div>
  );
}

function PoweredBy({ result }) {
  const order = ["stt", "vision", "llm", "tts"];
  const names = { stt: "STT", vision: "Vision", llm: "LLM", tts: "TTS" };
  const used = [...result.providers_used].sort((a, b) => order.indexOf(a.service) - order.indexOf(b.service));
  return (
    <div className="powered" aria-label="Providers used">
      <span className="powered-label">Powered by</span>
      {used.map((u, i) => (
        <span key={i} className={`chip ${u.provider === "mock" || u.provider === "none" ? "chip-mock" : ""}`} title={u.note || ""}>
          {names[u.service] || u.service}: {u.label} <em>{u.ms} ms</em>
        </span>
      ))}
      <span className="chip">Search: retrieve <em>{result.timings.retrieve ?? 0} ms</em></span>
    </div>
  );
}

export default function HelpDesk() {
  const [lang, setLang] = useState("auto");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [demo, setDemo] = useState(null);
  const [limits, setLimits] = useState(null);
  const [recording, setRecording] = useState(false);
  const [speechText, setSpeechText] = useState("");
  const [speechStatus, setSpeechStatus] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [showDebug, setShowDebug] = useState(false);
  const recRef = useRef(null);
  const speechRef = useRef(null);
  const speechTextRef = useRef("");
  const tickRef = useRef(null);
  const fileInput = useRef(null);
  const photoCaptureInput = useRef(null);
  const videoCaptureInput = useRef(null);

  useEffect(() => {
    getJSON("/api/demo-questions").then(setDemo).catch(() => {});
    getJSON("/api/config").then((c) => setLimits(c.limits)).catch(() => {});
  }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function submit({ audio = null, textOverride = null } = {}) {
    setError(""); setFeedback(""); setResult(null);
    window.speechSynthesis?.cancel();
    const q = audio
      ? [textOverride, text].filter((part) => part?.trim()).join("\n")
      : (textOverride ?? text);
    if (!audio && !q.trim() && !file) { setError("Speak, type a question, or add a photo or video first."); return; }
    setStage(audio ? "listening" : "understanding");
    const t1 = setTimeout(() => setStage("understanding"), 900);
    const t2 = setTimeout(() => setStage("video"), 2600);
    try {
      const r = await ask({ text: q, language: lang, sessionId, audio, media: file });
      setResult(r);
      setTimeout(() => document.getElementById("result")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }), 50);
    } catch (e) {
      setError(e.message || "Could not reach the help desk. Check that the server is running.");
    } finally {
      clearTimeout(t1); clearTimeout(t2); setStage("");
    }
  }

  async function toggleMic() {
    setError("");
    if (recording) {
      clearInterval(tickRef.current);
      setRecording(false);
      const recognition = speechRef.current;
      speechRef.current = null;
      if (recognition) {
        await new Promise((resolve) => {
          const timeout = setTimeout(resolve, 1000);
          recognition.addEventListener("end", () => { clearTimeout(timeout); resolve(); }, { once: true });
          try { recognition.stop(); } catch { clearTimeout(timeout); resolve(); }
        });
      }
      const wav = await recRef.current.stop();
      submit({ audio: wav, textOverride: speechTextRef.current });
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) { setError("This browser cannot record audio. Type your question instead."); return; }
    try {
      recRef.current = new WavRecorder(limits?.audio_seconds || 30);
      await recRef.current.start(() => toggleMicRef.current());
      speechTextRef.current = "";
      setSpeechText("");
      setSpeechStatus("Starting live speech recognition…");
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        if (lang !== "auto") recognition.lang = SPEECH_LANG[lang] || "te-IN";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.onstart = () => setSpeechStatus("Live transcription is on");
        recognition.onresult = (event) => {
          const finalWords = [];
          const partialWords = [];
          for (const item of event.results) {
            const words = item[0].transcript.trim();
            if (!words) continue;
            (item.isFinal ? finalWords : partialWords).push(words);
          }
          speechTextRef.current = [...finalWords, ...partialWords].join(" ");
          setSpeechText(speechTextRef.current);
        };
        recognition.onerror = (event) => {
          const messages = {
            "not-allowed": "Browser speech access was denied. You can still submit; server STT may transcribe it.",
            "service-not-allowed": "Browser speech recognition is blocked. You can still submit for server STT.",
            network: "Browser speech recognition needs a network connection. You can still submit for server STT.",
            "no-speech": "No speech detected yet. Keep speaking or check your microphone.",
          };
          setSpeechStatus(messages[event.error] || "Live transcription is unavailable; server STT may still work after submission.");
        };
        try { recognition.start(); speechRef.current = recognition; }
        catch { setSpeechStatus("Live transcription is unavailable; server STT may still work after submission."); }
      } else {
        setSpeechStatus("This browser does not support live transcription. Server STT may transcribe after submission.");
      }
      setRecording(true); setElapsed(0);
      tickRef.current = setInterval(() => setElapsed(recRef.current.elapsed()), 200);
    } catch (e) {
      setError(e?.name === "NotAllowedError" ? "Microphone permission was denied. Allow the microphone in your browser settings, or type your question." : "Could not start the microphone. Type your question instead.");
    }
  }
  const toggleMicRef = useRef(toggleMic);
  toggleMicRef.current = toggleMic;

  function onFile(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const isImg = f.type.startsWith("image/"), isVid = f.type.startsWith("video/");
    const mb = f.size / 1024 / 1024;
    if (!isImg && !isVid) { setError("Please choose a photo or a short video."); return; }
    if (isImg && mb > (limits?.image_mb || 5)) { setError(`Photo is too large. Maximum ${limits?.image_mb || 5} MB.`); return; }
    if (isVid && mb > (limits?.video_mb || 15)) { setError(`Video is too large. Maximum ${limits?.video_mb || 15} MB.`); return; }
    setError(""); setFile(f); setPreview(URL.createObjectURL(f));
  }

  async function onFeedback(solved) {
    const r = await sendFeedback(sessionId, solved, result?.request_id).catch(() => null);
    if (solved) setFeedback("Glad it worked. Happy stitching!");
    else if (r?.ticket_id) setFeedback(`We created ticket #${r.ticket_id}. A technician will follow up.`);
    else setFeedback("Sorry it is not fixed yet. Try the next step in the video, or tap “Not solved” again to reach a technician.");
  }

  const demoLang = lang === "auto" ? "te" : lang;
  const busy = Boolean(stage);

  return (
    <section className="section helpdesk">
      <h1>RRR AI Help Desk</h1>
      <p className="muted">Tell us the machine problem in Telugu, Hindi or English. You will see the fix on video and hear it explained.</p>

      <div className="desk-grid">
        <div className="ask-panel stitched-panel">
          <div className="lang-row" role="radiogroup" aria-label="Language">
            {LANGS.map(([v, label]) => (
              <button key={v} type="button" role="radio" aria-checked={lang === v} className={`seg ${lang === v ? "on" : ""}`} onClick={() => setLang(v)}>{label}</button>
            ))}
          </div>

          <div className="mic-wrap">
            <button type="button" className={`mic ${recording ? "rec" : ""}`} onClick={toggleMic} disabled={busy} aria-pressed={recording}
              aria-label={recording ? "Stop recording and send" : "Start recording your question"}>
              <svg viewBox="0 0 120 120" aria-hidden="true">
                <circle cx="60" cy="60" r="54" className="mic-hoop" />
                <circle cx="60" cy="60" r="44" className="mic-stitch" />
                <rect x="50" y="30" width="20" height="38" rx="10" className="mic-body" />
                <path d="M40 58 a20 20 0 0 0 40 0 M60 78 v12 M48 92 h24" className="mic-stand" />
              </svg>
            </button>
            <p className="mic-label" aria-live="polite">{recording ? `Recording ${elapsed.toFixed(0)}s / ${limits?.audio_seconds || 30}s. Tap to send your voice with the selected text and photo/video.` : "Tap the hoop and speak"}</p>
            {(recording || speechText || speechStatus) && <div className="live-transcript" aria-live="polite">
              <strong>What you’re saying</strong>
              <p>{speechText || (recording ? speechStatus || "Listening for words…" : "No browser transcript captured.")}</p>
              {speechText && recording && <span className="hint">{speechStatus}</span>}
            </div>}
          </div>

          <label className="field">
            <span>Or type your question</span>
            <textarea value={text} maxLength={limits?.text_chars || 1000} rows={3} onChange={(e) => setText(e.target.value)}
              placeholder="ఉదా: పై దారం పదే పదే తెగిపోతోంది" lang={lang === "auto" ? undefined : lang} />
          </label>

          <div className="upload-row">
            <input ref={fileInput} type="file" accept="image/*,video/*" onChange={onFile} hidden />
            <input ref={photoCaptureInput} type="file" accept="image/*" capture="environment" onChange={onFile} hidden />
            <input ref={videoCaptureInput} type="file" accept="video/*" capture="environment" onChange={onFile} hidden />
            <button type="button" className="btn ghost" onClick={() => photoCaptureInput.current?.click()}>Take photo</button>
            <button type="button" className="btn ghost" onClick={() => videoCaptureInput.current?.click()}>Record video</button>
            <button type="button" className="btn ghost" onClick={() => fileInput.current?.click()}>Choose photo or video</button>
            <span className="hint">Photo up to {limits?.image_mb || 5} MB, video up to {limits?.video_seconds || 20}s / {limits?.video_mb || 15} MB</span>
          </div>
          {file && (
            <div className="preview">
              {file.type.startsWith("image/") ? <img src={preview} alt="Your upload preview" /> : <video src={preview} muted controls playsInline />}
              <button type="button" className="btn small" onClick={() => { setFile(null); setPreview(""); }}>Remove</button>
            </div>
          )}

          <button type="button" className="btn primary wide" onClick={() => submit()} disabled={busy || recording}>Ask RRR AI</button>

          {demo && (
            <div className="demo-qs">
              <h2 className="h4">Try a demo question</h2>
              <ol>
                {demo.faults.map((f) => (
                  <li key={f.fault_id}>
                    <button type="button" className="demo-q" disabled={busy} lang={demoLang} onClick={() => { setText(f[demoLang]); submit({ textOverride: f[demoLang] }); }}>{f[demoLang]}</button>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>

        <div id="result" className="result-panel" aria-live="polite" aria-busy={busy}>
          {busy && (
            <div className="loading">
              <div className="thread-loader" aria-hidden="true" />
              <p>{UI[stage]}</p>
            </div>
          )}
          {error && <p className="error" role="alert">{error}</p>}
          {!busy && !result && !error && (
            <div className="empty">
              <p>Your answer appears here: what we heard, the repair video, the spoken fix and the steps.</p>
            </div>
          )}
          {result && (
            <>
              <div className="heard"><span className="label">I heard</span><p lang={result.language}>{result.transcript || (result.providers_used.some((u) => u.service === "stt") ? "Speech could not be transcribed. Use typed text or configure a real STT provider." : "(photo or video only)")}</p></div>
              {result.handoff ? (
                <div className="handoff stitched-panel">
                  <h2 className="h3">Passed to a technician</h2>
                  <AnswerAudio result={result} />
                  {result.ticket_id && <p>Ticket <strong>#{result.ticket_id}</strong></p>}
                </div>
              ) : result.answer_path === "welcome" || result.answer_path === "out_of_scope" ? (
                <div className="handoff stitched-panel">
                  <h2 className="h3">{result.answer_path === "welcome" ? "How I can help" : "Outside my help library"}</h2>
                  <AnswerAudio result={result} />
                </div>
              ) : (
                <>
                  {result.video && <VideoPlayer video={result.video} />}
                  <AnswerAudio result={result} />
                  <ol className="steps" lang={result.language}>
                    {result.answer.steps.map((s, i) => <li key={i}>{s}</li>)}
                  </ol>
                  {result.answer.safety_note && <p className="safety" lang={result.language}><strong>Safety</strong> {result.answer.safety_note}</p>}
                  <p className="source">Source guide: {result.sources.map((s) => s.title).join(", ")} <span className="muted">(sample content, technician review required)</span></p>
                  <div className="feedback">
                    <button type="button" className="btn small" onClick={() => onFeedback(true)}>Solved</button>
                    <button type="button" className="btn small ghost" onClick={() => onFeedback(false)}>Not solved</button>
                    {feedback && <p role="status">{feedback}</p>}
                  </div>
                </>
              )}
              <PoweredBy result={result} />
              <details className="debug" open={showDebug} onToggle={(e) => setShowDebug(e.target.open)}>
                <summary>Debug details</summary>
                <dl>
                  <dt>Request</dt><dd>{result.request_id}</dd>
                  <dt>Fault</dt><dd>{result.fault_id} (confidence {result.confidence})</dd>
                  <dt>Decision</dt><dd>{result.fusion_reason} / answer path: {result.answer_path}</dd>
                  <dt>Timings</dt><dd>{Object.entries(result.timings).map(([k, v]) => `${k} ${v} ms`).join(", ") || "-"}</dd>
                  <dt>Notes</dt><dd>{result.providers_used.filter((u) => u.note).map((u) => `${u.service}: ${u.note}`).join(" | ") || "-"}</dd>
                </dl>
              </details>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
