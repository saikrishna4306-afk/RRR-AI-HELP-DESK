import React, { useEffect, useState } from "react";
import { getJSON, rupees } from "../lib/api.js";
import { MachineArt } from "./Catalog.jsx";

export default function Home() {
  const [products, setProducts] = useState([]);
  useEffect(() => { getJSON("/api/products").then((d) => setProducts(d.products.slice(0, 3))).catch(() => {}); }, []);
  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <h1>Machine stopped mid-design? Say what you see.</h1>
          <p className="lede">Ask RRR AI in Telugu, Hindi or English. Speak, type or show a photo. You get the fix on video, read aloud, step by step.</p>
          <div className="hero-actions">
            <a className="btn primary" href="#/help">Need help with your machine? Ask RRR AI</a>
            <a className="btn ghost" href="#/catalog">See machines</a>
          </div>
          <p className="hero-langs" lang="te">పై దారం తెగిపోతోందా? అడగండి.</p>
        </div>
        <div className="hero-hoop" aria-hidden="true">
          <svg viewBox="0 0 320 320">
            <circle cx="160" cy="160" r="140" fill="var(--card)" stroke="var(--hoop)" strokeWidth="18" />
            <circle cx="160" cy="160" r="120" fill="none" stroke="var(--zari)" strokeWidth="5" />
            <path className="run-stitch" d="M70 190 C 110 120, 150 230, 190 150 S 250 120, 260 170" fill="none" stroke="var(--thread)" strokeWidth="6" strokeLinecap="round" strokeDasharray="14 10" />
            <path d="M200 40 L206 150 L200 168 L194 150 Z" fill="var(--ink)" />
          </svg>
        </div>
      </section>
      <section className="section">
        <h2>Featured machines</h2>
        <div className="product-grid">
          {products.map((p) => (
            <article key={p.id} className="product">
              <MachineArt seed={p.id} />
              <h3>{p.name}</h3>
              <p className="price"><span className="sale">{p.price_from ? "From " : ""}{rupees(p.price)}</span> <s>{rupees(p.regular_price)}</s></p>
            </article>
          ))}
        </div>
        <a className="btn ghost" href="#/catalog">All 10 machines</a>
      </section>
    </>
  );
}
