// server/rules_api.js
// Read-only endpoints to serve JSON rule files from /rules/*
// Safe: no combat/engine wiring changed.

const fs = require('fs');
const path = require('path');

module.exports = function rulesApi(app) {
  const ROOT = path.resolve(__dirname, '..');
  const RULES = path.join(ROOT, 'rules');

  const ALLOWED_DIRS = new Set([
    'lore', 'relics', 'vendors', 'events', 'characters', 'classes', 'items'
  ]);

  function stripBOM(s) {
    if (typeof s !== 'string') return s;
    return s.replace(/^\uFEFF/, '');
  }

  function readJsonSafe(fp) {
    const text = stripBOM(fs.readFileSync(fp, 'utf8'));
    return JSON.parse(text);
  }

  function safeJoin(dir, file) {
    const base = path.join(RULES, dir);
    const target = path.normalize(path.join(base, file));
    if (!target.startsWith(base)) throw new Error('Path escape blocked');
    return target;
  }

  // List simple index of available JSON files
  app.get('/api/rules/index', (_req, res) => {
    try {
      const out = {};
      for (const d of fs.readdirSync(RULES, { withFileTypes: true })) {
        if (!d.isDirectory()) continue;
        if (!ALLOWED_DIRS.has(d.name)) continue;
        const dirPath = path.join(RULES, d.name);
        const files = fs.readdirSync(dirPath)
          .filter(f => f.toLowerCase().endsWith('.json'));
        out[d.name] = files;
      }
      res.json({ ok: true, index: out });
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e) });
    }
  });

  // Generic fetch: /api/rules/<dir>/<file(.json)>
  app.get('/api/rules/:dir/:file', (req, res) => {
    try {
      const dir = String(req.params.dir || '').toLowerCase();
      if (!ALLOWED_DIRS.has(dir)) {
        return res.status(400).json({ ok: false, error: 'dir not allowed' });
      }
      let file = String(req.params.file || '');
      if (!file.toLowerCase().endsWith('.json')) file += '.json';
      const fp = safeJoin(dir, file);
      if (!fs.existsSync(fp)) return res.status(404).json({ ok: false, error: 'not found' });
      const data = readJsonSafe(fp);
      res.json({ ok: true, path: `rules/${dir}/${file}`, data });
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e) });
    }
  });
};
