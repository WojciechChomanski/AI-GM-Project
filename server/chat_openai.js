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
    "If asked about out-of-scope topics, gently redirect back to the game."
  ].join(' ');
}

function validKey(k) {
  return !!k && k !== 'PASTE_YOUR_KEY_HERE' && /^sk-/.test(k);
}

function makeClient() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!validKey(apiKey)) return null;
  try { return new OpenAI({ apiKey }); } catch { return null; }
}

function stubReply(sessionNote, role, message) {
  return `[[stub]] ${role === 'player' ? 'You' : 'NPC'} said: "${message}". ` +
         `GM: The lantern sputters as a draft threads through the hall. ` +
         `Shadows pull long between cracked pillars. What do you do? (${sessionNote})`;
}

/** Chat entry point used by the Express route. Always resolves with a reply. */
async function chat(body = {}) {
  const message = (body.message || '').toString().trim();
  const role = (body.role || 'player').toString();
  const sessionNote = loadSessionSummary();

  const client = makeClient();
  if (!client) {
    return { reply: stubReply(sessionNote, role, message), model: 'stub' };
  }

  // Try live call; on any error, fall back to stub instead of throwing.
  try {
    const completion = await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: buildSystemPrompt() },
        { role: 'system', content: sessionNote },
        { role: 'user', content: message || 'Continue.' }
      ],
      temperature: 0.7,
      max_tokens: 400
    });

    const reply = completion.choices?.[0]?.message?.content?.trim() || '…';
    return { reply, model: completion.model, usage: completion.usage || null };
  } catch (e) {
    return {
      reply: stubReply(sessionNote, role, message),
      model: 'stub',
      // include a hint so we know why it fell back (not shown to the player UI)
      hint: `fallback: ${e?.message || e}`
    };
  }
}

module.exports = { chat };

