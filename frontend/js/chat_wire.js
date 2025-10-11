// frontend/js/chat_wire.js (full file)
const form = document.querySelector('#chat-form');
const input = document.querySelector('#chat-input');
const log = document.querySelector('#chat-log');
const statusEl = document.querySelector('#api-status');

function append(role, text) {
  const div = document.createElement('div');
  div.className = role === 'you' ? 'msg you' : role === 'system' ? 'msg system' : 'msg gm';
  div.textContent = `${role === 'you' ? 'You' : role === 'system' ? 'System' : 'GM'}: ${text}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function detectMode() {
  try {
    const r = await fetch('/api/healthz');
    const j = await r.json();
    statusEl.textContent = j.mode || 'stub';
  } catch {
    statusEl.textContent = 'error';
  }
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = (input?.value || '').trim();
  if (!msg) return;
  append('you', msg);
  input.value = '';
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'player', message: msg })
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    statusEl.textContent = j.mode || 'stub';
    append('gm', j.reply || '(no reply)');
  } catch (err) {
    append('system', 'Chat error: ' + String(err.message || err));
    statusEl.textContent = 'error';
  }
});

// init
detectMode();

