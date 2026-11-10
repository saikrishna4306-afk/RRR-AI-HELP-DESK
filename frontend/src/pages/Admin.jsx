import React, { useState } from "react";
import { getJSON } from "../lib/api.js";

const TABS = [["tickets", "Tickets"], ["unanswered", "Unanswered"], ["usage", "Usage"], ["providers", "Providers"]];

export default function Admin() {
  const [token, setToken] = useState("");
  const [tab, setTab] = useState("tickets");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  async function load(t = tab) {
    setErr(""); setData(null); setTab(t);
    try { setData(await getJSON(`/admin/${t}`, { "X-Admin-Token": token })); }
    catch (e) { setErr(e.message === "Admin token required" ? "Wrong admin token. Check ADMIN_TOKEN in .env." : e.message); }
  }

  return (
    <section className="section">
      <h1>Admin</h1>
      <form className="admin-login" onSubmit={(e) => { e.preventDefault(); load(); }}>
        <label className="field inline"><span>Admin token</span>
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="current-password" />
        </label>
        <button className="btn primary" type="submit">Open</button>
      </form>
      <div className="lang-row" role="tablist">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={`seg ${tab === k ? "on" : ""}`} onClick={() => load(k)} type="button">{l}</button>)}
      </div>
      {err && <p className="error" role="alert">{err}</p>}
      {data && Array.isArray(data) && (
        data.length === 0 ? <p className="muted">Nothing here yet.</p> :
        <div className="table-wrap"><table>
          <thead><tr>{Object.keys(data[0]).filter((k) => k !== "media").map((k) => <th key={k}>{k}</th>)}</tr></thead>
          <tbody>{data.map((row) => <tr key={row.id}>{Object.entries(row).filter(([k]) => k !== "media").map(([k, v]) => <td key={k} className={k === "summary" ? "pre" : ""}>{String(v)}</td>)}</tr>)}</tbody>
        </table></div>
      )}
      {data && !Array.isArray(data) && <pre className="json">{JSON.stringify(data, null, 2)}</pre>}
    </section>
  );
}
