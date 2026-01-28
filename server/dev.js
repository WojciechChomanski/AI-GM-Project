require("dotenv").config();
const path = require("path");
const express = require("express");
const cors = require("cors");
const fs = require("fs");

const app = express();

app.use(cors({
  origin: "http://localhost:3000",
  credentials: true
}));

app.use(express.json());
app.use(express.static(path.join(__dirname, "..", "frontend"), { index: 'index.html' }));

app.use((req, res, next) => {
  res.setHeader(
    "Content-Security-Policy",
    "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://127.0.0.1:8000; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
  );
  next();
});

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

// SPA fallback
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















