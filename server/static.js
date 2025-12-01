// File: server/static.js
// Dev server that serves both /frontend and /api with a permissive dev CSP.

require('dotenv').config();
const path = require('path');
const express = require('express');

const app = express();
app.use(express.json());

// ---- DEV CSP (permissive for your current inline usage) ----
const DEV_CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "media-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self' http://localhost:3000",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'"
].join('; ');

app.use((req, res, next) => {
  res.setHeader('Content-Security-Policy', DEV_CSP);
  next();
});

// ---- API Routers (reuse your existing ones) ----
try {
  const rulesApi = require('./rules_api');          // mounts under /rules
  app.use('/api', rulesApi);
} catch (e) {
  console.warn('rules_api not mounted:', e.message);
}
try {
  const engineBridge = require('./engine_bridge');  // mounts ping/start/etc.
  app.use('/api/engine', engineBridge);
} catch (e) {
  console.warn('engine_bridge not mounted:', e.message);
}

// ---- Static frontend ----
const FRONTEND_DIR = path.join(__dirname, '..', 'frontend');
app.use(express.static(FRONTEND_DIR, {
  setHeaders: (res) => { res.setHeader('Content-Security-Policy', DEV_CSP); } // ensure index.html also gets CSP
}));

// Legacy path fix: /debug/session.html -> /dev/session.html
app.get('/debug/session.html', (_req, res) => {
  res.redirect(302, '/dev/session.html');
});

// SPA fallback to /index.html if needed
app.get('*', (_req, res) => {
  res.sendFile(path.join(FRONTEND_DIR, 'index.html'));
});

const PORT = Number(process.env.PORT || 3000);
app.listen(PORT, () => {
  console.log(`Dev server ready on http://localhost:${PORT}`);
});