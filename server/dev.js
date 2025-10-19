// server/dev.js  — minimal, mounts /api (rules) and /api/engine (engine)
require('dotenv').config();
const path = require('path');
const express = require('express');

const app = express();
app.use(express.json());

// Health
app.get('/api/healthz', (_req, res) => res.json({ ok: true }));

// Routers (must exist: server/rules_api.js and server/engine_bridge.js exporting an Express.Router)
const rulesApi = require('./rules_api');         // defines routes starting with '/rules/...'
const engineBridge = require('./engine_bridge'); // defines routes starting with '/ping', '/start', etc.

// Mount routers
app.use('/api', rulesApi);          // yields: /api/rules/...
app.use('/api/engine', engineBridge); // yields: /api/engine/ping, /api/engine/start, ...

// Static (optional)
app.use('/', express.static(path.join(process.cwd())));

// Start
const PORT = Number(process.env.PORT || 3000);
app.listen(PORT, () => {
  console.log(`Dev server on http://localhost:${PORT}`);
  console.log(`Root: ${process.cwd()}`);
  console.log('Mounted: /api (rules), /api/engine (engine)');
});















