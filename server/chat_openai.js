// server/chat_openai.js
const fs = require('fs');
const path = require('path');
const OpenAI = require('openai');

const ROOT = path.resolve(__dirname, '..');
const STATE_PATH = path.join(ROOT, 'sessions', 'session_state.json');

function loadSessionSummary() {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    const s = JSON.parse(raw);
    const flags = Object.entries(s.flags || {}).map(([k, v]) => `${k}=${v?.value}`).join(', ');
    const notes = (s.journal || []).slice(-3).join(' | ');
    return `Session flags: ${flags || 'none'} • Recent: ${notes || '—'}`;
  } catch {
    return 'No active session.';
  }
}

function buildSystemPrompt() {
  return [
    "You are the AI Game Master for ‘The Breath & The Veil’.",
    "Tone: grounded, cinematic, helpful. Keep replies 2–6 sentences unless asked for more.",
    "Rating: keep it PG-13. No explicit sexual content, graphic gore, hate speech, or instructions for real harm.",
    "Stay in-world; describe with concise sensory detail; summarize mechanics without rules lawyering.",
    "If asked about out-of-scope topics, redirect back to the game.",
  ].join(' ');
}

function makeClient() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return null;
  return new OpenAI({ apiKey });
}

/** Chat entry point used by the Express route. */
async function chat(body = {}) {
  const message = (body.message || '').toString().trim();
  const role = (body.role || 'player').toString();

  const sessionNote = loadSessionSummary();

  // Stub fallback if no API key
  const client = makeClient();
  if (!client) {
    const reply =
      `[[stub]] ${role === 'player' ? 'You' : 'NPC'} said: "${message}". ` +
      `GM replies: The lantern sputters as the wind curls through the hall. ` +
      `What do you do next? (${sessionNote})`;
    return { reply, model: 'stub' };
  }

  // OpenAI call (non-stream)
  const system = buildSystemPrompt();
  const prompt = [
    { role: 'system', content: system },
    { role: 'system', content: sessionNote },
    { role: 'user', content: message || 'Continue.' },
  ];

  const completion = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: prompt,
    temperature: 0.7,
    max_tokens: 400,
  });

  const reply = completion.choices?.[0]?.message?.content?.trim() || '…';
  return {
    reply,
    model: completion.model,
    usage: completion.usage || null,
  };
}

module.exports = { chat };
