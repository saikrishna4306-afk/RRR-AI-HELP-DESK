import React, { useEffect, useState } from "react";
import Home from "./pages/Home.jsx";
import Catalog from "./pages/Catalog.jsx";
import Branches from "./pages/Branches.jsx";
import HelpDesk from "./pages/HelpDesk.jsx";
import Admin from "./pages/Admin.jsx";

const ROUTES = { "": Home, catalog: Catalog, branches: Branches, help: HelpDesk, admin: Admin };
const NAV = [["", "Home"], ["catalog", "Catalog"], ["branches", "Branches"], ["help", "Help Desk"]];
const ANNOUNCEMENTS = [
  "5 years warranty for embroidery machines and spare parts *Terms & Conditions apply",
  "Free delivery on orders above ₹2000",
  "Instant email delivery on all design purchases :)",
];

function useRoute() {
  const read = () => window.location.hash.replace(/^#\/?/, "").split(/[/?]/)[0];
  const [route, setRoute] = useState(read());
  useEffect(() => {
    const on = () => { setRoute(read()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export default function App() {
  const route = useRoute();
  const Page = ROUTES[route] || Home;
  const [ann, setAnn] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setAnn((a) => (a + 1) % ANNOUNCEMENTS.length), 5000);
    return () => clearInterval(t);
  }, []);
  return (
    <>
      <a className="skip" href="#main-content" onClick={(e) => { e.preventDefault(); document.getElementById("main-content")?.focus(); }}>Skip to content</a>
      <div className="announce" role="status" aria-live="polite">{ANNOUNCEMENTS[ann]}</div>
      <div className="demo-note">Demo prepared for RRR Group, not the official website</div>
      <header className="site-header">
        <a href="#/" className="brand" aria-label="RRR Group home">
          <svg viewBox="0 0 64 64" width="38" height="38" aria-hidden="true"><circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6"/><circle cx="32" cy="32" r="18" fill="none" stroke="var(--thread)" strokeWidth="3" strokeDasharray="5 4"/><path d="M32 8 L34 44 L32 50 L30 44 Z" fill="var(--ink)"/></svg>
          <span>RRR Group</span>
        </a>
        <nav aria-label="Main">
          {NAV.map(([r, label]) => (
            <a key={r} href={`#/${r}`} aria-current={route === r ? "page" : undefined}>{label}</a>
          ))}
        </nav>
        <div className="header-icons" aria-label="Account (demo placeholders)">
          <button type="button" className="icon-btn" aria-label="Search (demo)" disabled>⌕</button>
          <button type="button" className="icon-btn" aria-label="Log in (demo)" disabled>◯</button>
          <button type="button" className="icon-btn" aria-label="Cart (demo)" disabled>🛒</button>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}><Page /></main>
      <footer className="site-footer">
        <div className="stitch-rule" aria-hidden="true" />
        <div className="footer-grid">
          <div>
            <strong>RRR Group (demo)</strong>
            <p>Embroidery and sewing machines, Hyderabad. Prices in INR.</p>
          </div>
          <ul aria-label="Policies (placeholders)">
            {["Privacy policy", "Terms of service", "Shipping policy", "Refund policy", "Contact information"].map((x) => <li key={x}>{x}</li>)}
          </ul>
          <ul aria-label="Social">
            <li>Facebook</li><li>Instagram</li><li>YouTube @rrrembroidery-Hyderabad</li>
          </ul>
        </div>
        <p className="fineprint">Demo prepared for RRR Group, not the official website. Guides are sample content and need technician review. <a href="#/admin">Admin</a></p>
      </footer>
    </>
  );
}
