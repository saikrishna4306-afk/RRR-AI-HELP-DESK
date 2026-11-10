import React, { useEffect, useState } from "react";
import { getJSON, rupees } from "../lib/api.js";

export function MachineArt({ seed }) {
  const n = parseInt(String(seed).replace(/\D/g, "")) || 1;
  const heads = n === 1 ? 4 : n === 7 ? 2 : 1;
  return (
    <svg className="machine-art" viewBox="0 0 200 120" role="img" aria-label="Neutral machine placeholder">
      <rect x="10" y="20" width="180" height="60" rx="8" fill="var(--hoop)" />
      {Array.from({ length: heads }).map((_, i) => {
        const x = 30 + i * (140 / Math.max(heads, 1)) + (heads === 1 ? 50 : 0);
        return <g key={i}><rect x={x} y="78" width="24" height="22" fill="var(--ink)" /><line x1={x + 12} y1="100" x2={x + 12} y2="110" stroke="var(--ink)" strokeWidth="2" /></g>;
      })}
      <rect x="10" y="108" width="180" height="6" fill="var(--zari)" />
      <line x1="20" y1="34" x2="180" y2="34" stroke="var(--thread)" strokeWidth="3" strokeDasharray="8 6" />
    </svg>
  );
}

export default function Catalog() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { getJSON("/api/products").then(setData).catch((e) => setErr(e.message)); }, []);
  return (
    <section className="section">
      <h1>Embroidery machines</h1>
      <p className="muted">All in stock. Sale prices shown with the regular price struck through. Product images are neutral placeholders.</p>
      {err && <p className="error" role="alert">{err}</p>}
      <div className="product-grid">
        {data?.products.map((p) => (
          <article key={p.id} className="product">
            <MachineArt seed={p.id} />
            <h2 className="h3">{p.name}</h2>
            <p className="price">
              <span className="sale">{p.price_from ? "From " : ""}{rupees(p.price)}</span> <s aria-label={`Regular price ${rupees(p.regular_price)}`}>{rupees(p.regular_price)}</s>
            </p>
            <p className="stock">In stock</p>
            <button type="button" className="btn small" disabled title="Coming soon">Ask AI about this machine</button>
          </article>
        ))}
      </div>
    </section>
  );
}
