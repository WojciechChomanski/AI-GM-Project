// server/engine_bridge.js
const express = require('express');
const router = express.Router();

router.use(express.json());

// Extremely simple in-memory stub so routes always respond
let session = null;

router.get('/ping', (req, res) => {
  return res.json({ ok: true, active: !!session, sessionId: session?.id ?? null });
});

router.post('/start', (req, res) => {
  const character = String(req.body?.character || 'unknown');
  session = {
    id: 'sess_' + Date.now(),
    character,
    turn: 0,
    log: [{ t: new Date().toISOString(), msg: `Session started as ${character}` }],
  };
  return res.json({ ok: true, sessionId: session.id, character });
});

router.post('/choose', (req, res) => {
  if (!session) return res.status(400).json({ ok: false, error: 'no session' });
  session.log.push({ t: new Date().toISOString(), msg: `choice=${req.body?.choice}` });
  return res.json({ ok: true });
});

router.post('/turn', (req, res) => {
  if (!session) return res.status(400).json({ ok: false, error: 'no session' });
  session.turn++;
  session.log.push({ t: new Date().toISOString(), msg: `turn ${session.turn}`, input: req.body });
  return res.json({ ok: true, turn: session.turn });
});

router.get('/log', (req, res) => {
  return res.json({ ok: true, log: session?.log ?? [] });
});

router.post('/stop', (req, res) => {
  const sid = session?.id ?? null;
  session = null;
  return res.json({ ok: true, stopped: !!sid, sessionId: sid });
});

module.exports = router;







