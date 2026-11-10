import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: `npm run dev` proxies API calls to the FastAPI server on :8000
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000", "/admin": "http://localhost:8000", "/media": "http://localhost:8000", "/health": "http://localhost:8000" },
  },
});
