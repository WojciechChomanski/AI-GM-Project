require("dotenv").config();
const path = require("path");
const express = require("express");
const cors = require("cors");
const fs = require("fs");

const app = express();

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "..", "frontend"), { index: 'index.html' }));

// Health check
app.get("/api/healthz", (req, res) => {
  res.json({
    ok: true,
    mode: process.env.OPENAI_API_KEY ? "openai" : "stub",
    uptime_s: Math.round(process.uptime()),
  });
});

// Serve rules files
app.get("/api/rules/:file", (req, res) => {
  const file = req.params.file;
  const filePath = path.join(__dirname, "..", "rules", file);
  
  if (!filePath.startsWith(path.join(__dirname, "..", "rules"))) {
    return res.status(403).send("Forbidden");
  }

  fs.access(filePath, fs.constants.F_OK, (err) => {
    if (err) {
      console.warn(`[404] /api/rules/${file} — file not found`);
      return res.status(404).send("File not found");
    }
    res.sendFile(filePath);
  });
});

// Engine bridge stub
app.post("/api/engine/start", (req, res) => {
  res.json({started: true});
});
app.get("/api/engine/log", (req, res) => {
  res.send("");
});

// Chat stub (expand later)
app.post("/api/chat", (req, res) => {
  const {message} = req.body;
  res.json({ok: true, reply: `Stub: "${message}"`});
});

// SPA fallback: serve index.html for all non-API routes
app.get('*', (req, res) => {
  if (!req.url.startsWith('/api/')) {
    res.sendFile(path.join(__dirname, '..', 'frontend', 'index.html'));
  } else {
    res.status(404).send("Not found");
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Serving frontend from: ${path.join(__dirname, "..", "frontend")}`);
  console.log(`Serving rules from: ${path.join(__dirname, "..", "rules")}`);
});