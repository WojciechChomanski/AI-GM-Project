// server/dev.js  (full file)
const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv').config(); // loads .env if present

const app = express();
app.use(express.json());

// ---- Paths ----
const ROOT = path.resolve(__dirname, '..');
const PS_SCRIPT = path.join(ROOT, 'tools', 'session_runner.ps1');
const STATE_PATH = path.join(ROOT, 'sessions', 'session_state.json');

// ---- Helpers ----
function runPS(args = []) {
  return new Promise((resolve, reject) => {
    const ps = spawn(
      'powershell',
      ['-ExecutionPolicy', 'Bypass', '-File', PS_SCRIPT, ...args],
      { shell: true }
    );

    let stdout = '';
    let stderr = '';
    ps.stdout.on('data', d => (stdout += d.toString()));
    ps.stderr.on('data', d => (stderr += d.toString()));

    ps.on('close', code => {
      if (code === 0) return resolve({ stdout, stderr });
      reject(new Error(`PS exited ${code}\n${stderr || stdout}`));
    });
  });
}

function readState() {
  if (!fs.existsSync(STATE_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
  } catch {
    return null;
  }
}

// ---- Static files ----
// Frontend is the root
app.use(express.static(path.join(ROOT, 'frontend')));
// Debug page
app.use('/debug', express.static(path.join(ROOT, 'web', 'debug')));
// Current session JSON (dev-only)
app.use('/sessions', express.static(path.join(ROOT, 'sessions')));

// ---- Health ----
app.get('/api/healthz', (_req, res) => {
  res.json({ ok: true, mode: process.env.OPENAI_API_KEY ? 'openai' : 'stub' });
});

// ---- Session API ----
app.get('/api/session', (_req, res) => {
  const state = readState();
  res.json({ ok: true, state });
});

app.post('/api/session/reset', async (_req, res) => {
  try {
    await runPS(['-Reset']);
    res.json({ ok: true, state: readState() });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post('/api/session/init', async (_req, res) => {
  try {
    await runPS(['-Init']);
    res.json({ ok: true, state: readState() });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

app.post('/api/session/resolve', async (req, res) => {
  const { eventId, outcome, bonusObjectives } = req.body || {};
  if (!eventId || !outcome) {
    return res.status(400).json({ ok: false, error: 'Missing eventId or outcome' });
  }
  try {
    const args = ['-Resolve', '-EventId', eventId, '-Outcome', outcome];
    if (Array.isArray(bonusObjectives) && bonusObjectives.length > 0) {
      args.push('-BonusObjectives', ...bonusObjectives);
    }
    await runPS(args);
    res.json({ ok: true, state: readState() });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

// ---- Chat API ----
const { sendChat } = require('./chat_openai'); // uses stub if no OPENAI_API_KEY

app.post('/api/chat', async (req, res) => {
  const { role = 'player', message = '' } = req.body || {};
  if (!message) return res.status(400).json({ ok: false, error: 'Missing message' });
  try {
    const reply = await sendChat({ role, message });
    const mode = process.env.OPENAI_API_KEY ? 'openai' : 'stub';
    res.json({ ok: true, reply, mode });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

// ---- Start with auto-port fallback ----
const basePort = parseInt(process.env.PORT, 10) || 3000;

function listenOn(port, triesLeft = 10) {
  const server = app.listen(port, () => {
    console.log(`Dev server on http://localhost:${port}`);
    console.log(`Root: ${ROOT}`);
  });

  server.on('error', (err) => {
    if (err && err.code === 'EADDRINUSE' && triesLeft > 0) {
      console.log(`[dev] Port ${port} in use, trying ${port + 1}...`);
      listenOn(port + 1, triesLeft - 1);
    } else {
      console.error(err);
      process.exit(1);
    }
  });
}

listenOn(basePort);





