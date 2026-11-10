export async function getJSON(url, headers = {}) {
  const r = await fetch(url, { headers });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Request failed (${r.status})`);
  return r.json();
}

export async function ask({ text, language, sessionId, audio, media }) {
  const fd = new FormData();
  fd.append("text", text || "");
  fd.append("language", language || "auto");
  fd.append("session_id", sessionId);
  if (audio) fd.append("audio", audio, "speech.wav");
  if (media) fd.append("media", media, media.name);
  const r = await fetch("/api/ask", { method: "POST", body: fd });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `The help desk could not answer (${r.status}).`);
  return body;
}

export async function sendFeedback(sessionId, solved, requestId) {
  const r = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, solved, request_id: requestId || "" }),
  });
  return r.json();
}

export const rupees = (n) => "Rs. " + Number(n).toLocaleString("en-IN");
