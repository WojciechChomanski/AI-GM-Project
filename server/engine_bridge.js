// server/engine_bridge.js
// Minimal, rule-agnostic engine stub so /api/engine/* routes exist.
// This DOES NOT change your d100 rules or Python files. It only gives
// the frontend & your PowerShell scripts something stable to talk to.

const crypto = require('crypto');

function makeId() {
  return crypto.randomBytes(6).toString('hex');
}

module.exports = function mountEngineRoutes(app) {
  // ---- in-memory state (dev only; reset on server restart) ----
  const state = {
    active: false,
    sessionId: null,
    character: null,     // "torvald", etc. (free-form)
    pathChoice: null,    // 1..n
    turn: 0,
    log: [],
  };

  function push(line) {
    state.log.push({ t: new Date().toISOString(), line });
    if (state.log.length > 300) state.log.shift();
  }

  function reset() {
    state.active = false;
    state.sessionId = null;
    state.character = null;
    state.pathChoice = null;
    state.turn = 0;
    state.log = [];
  }

  // ---- routes ----
  app.get('/api/engine/ping', (_req, res) => {
    res.json({ ok: true, active: state.active, sessionId: state.sessionId });
  });

  app.post('/api/engine/start', (req, res) => {
    const { character } = req.body || {};
    reset();
    state.active = true;
    state.sessionId = makeId();
    state.character = character || 'torvald';
    push(`⚔️ Session ${state.sessionId} started; character=${state.character}`);
    return res.json({
      ok: true,
      sessionId: state.sessionId,
      character: state.character,
      msg: 'Session started',
    });
  });

  app.post('/api/engine/choose', (req, res) => {
    if (!state.active) return res.status(400).json({ ok: false, error: 'No active session' });
    const { choice } = req.body || {};
    state.pathChoice = Number(choice) || 1;
    push(`📜 Choice set: ${state.pathChoice}`);
    return res.json({ ok: true, pathChoice: state.pathChoice });
  });

  app.post('/api/engine/turn', (req, res) => {
    if (!state.active) return res.status(400).json({ ok: false, error: 'No active session' });

    const { stance, attack_type, ability, aimed_zone } = req.body || {};
    state.turn += 1;

    // Produce a harmless deterministic-ish result so tooling “works”.
    const roll = Math.floor(Math.random() * 100) + 1;
    const hit = roll >= 50;
    const summary =
      attack_type === 2 && aimed_zone
        ? `Turn ${state.turn}: stance=${stance || 'n/a'}, aimed attack at ${aimed_zone}, ability=${ability || 'none'} ➜ roll=${roll} ➜ ${hit ? 'HIT' : 'MISS'}`
        : `Turn ${state.turn}: stance=${stance || 'n/a'}, normal attack, ability=${ability || 'none'} ➜ roll=${roll} ➜ ${hit ? 'HIT' : 'MISS'}`;

    push(summary);

    return res.json({
      ok: true,
      turn: state.turn,
      result: {
        roll,
        hit,
        stance: stance ?? null,
        attack_type: attack_type ?? 1,
        ability: ability ?? null,
        aimed_zone: aimed_zone ?? null,
      },
    });
  });

  app.get('/api/engine/log', (_req, res) => {
    return res.json({ ok: true, log: state.log.slice(-100) });
  });

  app.post('/api/engine/stop', (_req, res) => {
    push('⏹️ Session stopped');
    reset();
    return res.json({ ok: true, msg: 'Session stopped' });
  });
};





