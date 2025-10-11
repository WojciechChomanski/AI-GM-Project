// server/dev.js
const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PS_SCRIPT = path.join(ROOT, 'tools', 'session_runner.ps1');
const STATE_PATH = path.join(ROOT, 'sessions', 'session_state.json');

const app = express();
app.use(express.json());

// --- helpers ---
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

// --- API ---
app.get('/api/healthz', (_req, res) => res.json({ ok: true }));

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

// Placeholder chat endpoint (wire your LLM later)
app.post('/api/chat', async (req, res) => {
  const { role, message } = req.body || {};
  res.json({
    ok: true,
    echo: { role: role || 'player', message: message || '' },
    reply: "Chat endpoint stub: connect your model here."
  });
});

// --- static ---
app.use('/sessions', express.static(path.join(ROOT, 'sessions')));
app.use('/debug', express.static(path.join(ROOT, 'web', 'debug')));
app.use('/frontend', express.static(path.join(ROOT, 'frontend')));
app.use(express.static(path.join(ROOT, 'frontend'))); // serve index.html by default

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Dev server on http://localhost:${PORT}`);
  console.log(`Root: ${ROOT}`);
});

