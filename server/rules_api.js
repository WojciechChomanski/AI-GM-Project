// server/rules_api.js
const express = require('express');
const path = require('path');
const fs = require('fs/promises');

const router = express.Router();

// -------- helpers --------
async function readJson(relPath) {
  const full = path.join(process.cwd(), relPath.replace(/\\/g, '/'));
  const txt = await fs.readFile(full, 'utf8');
  const data = JSON.parse(txt);
  return { full, data };
}

async function replyJson(res, relPath) {
  try {
    const { data } = await readJson(relPath);
    return res.json({ ok: true, path: relPath, data });
  } catch (err) {
    return res.status(404).json({ ok: false, error: 'not found', path: relPath });
  }
}

// -------- routes: events / lore / relics --------
router.get('/rules/events/:id', async (req, res) => {
  const id = String(req.params.id).toLowerCase();
  return replyJson(res, `rules/events/${id}.json`);
});

router.get('/rules/lore/:id', async (req, res) => {
  const id = String(req.params.id).toLowerCase();
  return replyJson(res, `rules/lore/${id}.json`);
});

router.get('/rules/relics/:id', async (req, res) => {
  const id = String(req.params.id).toLowerCase();
  return replyJson(res, `rules/relics/${id}.json`);
});

// -------- routes: classes --------
// 1) Prefer per-class shim at rules/classes/<id>.json
// 2) Fallback: look inside rules/classes.json for a top-level key "Crusader_Knight"
// 3) Fallback: look for an object at .class where .id or .name matches the id
router.get('/rules/classes/:id', async (req, res) => {
  const id = String(req.params.id).toLowerCase();

  // Try shim first
  try {
    const { data } = await readJson(`rules/classes/${id}.json`);
    return res.json({ ok: true, path: `rules/classes/${id}.json`, data });
  } catch (_) {
    // fall through
  }

  // Try centralized classes.json
  try {
    const { data } = await readJson('rules/classes.json');

    // top-level (e.g., data.Crusader_Knight)
    const direct = Object.keys(data).find(k => k.toLowerCase() === id);
    if (direct) {
      return res.json({ ok: true, path: 'rules/classes.json#' + direct, data: data[direct] });
    }

    // or nested under "class"
    if (
      data.class &&
      (String(data.class.id).toLowerCase() === id || String(data.class.name).toLowerCase() === id)
    ) {
      return res.json({ ok: true, path: 'rules/classes.json#class', data: data.class });
    }

    return res.status(404).json({ ok: false, error: 'not found', path: 'rules/classes.json' });
  } catch (err) {
    return res.status(404).json({ ok: false, error: 'not found', path: 'rules/classes.json' });
  }
});

module.exports = router;

