// server/dev.js
// Minimal dev server: serves frontend, mounts engine routes if present, and read-only rules API.

require('dotenv').config();
const path = require('path');
const express = require('express');

const PORT = Number(process.env.PORT || 3000);
const app = express();

app.use(express.json({ limit: '1mb' }));

// Health
app.get('/api/healthz', (_req, res) => res.json({ ok: true }));

// Mount engine bridge if present (your existing engine endpoints)
try {
  const engine = require('./engine_bridge');
  if (typeof engine === 'function') engine(app);
  else if (engine && typeof engine.mount === 'function') engine.mount(app);
} catch (_) {
  // engine bridge not present — fine
}

// Mount read-only rules API (new)
try {
  const rulesApi = require('./rules_api');
  if (typeof rulesApi === 'function') rulesApi(app);
} catch (_) {
  // no rules API — fine
}

// Optional chat stub if you had it
try {
  const chatRoutes = require('./chat_openai');
  if (typeof chatRoutes === 'function') chatRoutes(app);
} catch (_) {
  // ignore
}

// Serve debug if you have it
const debugDir = path.join(__dirname, '..', 'web', 'debug');
app.use('/debug', express.static(debugDir, { fallthrough: true }));

// Serve frontend
const frontDir = path.join(__dirname, '..', 'frontend');
app.use(express.static(frontDir));

// SPA-style fallback only for non-API GETs
app.use((req, res, next) => {
  if (
    req.method === 'GET' &&
    !req.path.startsWith('/api') &&
    !req.path.startsWith('/debug') &&
    !req.path.startsWith('/sessions')
  ) {
    return res.sendFile(path.join(frontDir, 'index.html'));
  }
  return next();
});

app.listen(PORT, () => {
  console.log(`Dev server on http://localhost:${PORT}`);
  console.log(`Root: ${path.resolve(path.join(__dirname, '..'))}`);
});













