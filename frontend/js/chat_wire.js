// frontend/js/chat_wire.js
import { chat } from './session_api.js';

const form  = document.getElementById('chat-form');
const input = document.getElementById('chat-input');
const log   = document.getElementById('chat-log');
const statusEl = document.getElementById('api-status');

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `<strong>${role === 'player' ? 'You' : role === 'gm' ? 'GM' : 'System'}:</strong> ${escapeHtml(text)}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function escapeHtml(s='') {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

if (form && input && log) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMsg('player', text);
    input.value = '';
    try {
      const res = await chat({ role: 'player', message: text });
      const reply = res.reply || res.message || '…';
      addMsg('gm', reply);
      if (statusEl) statusEl.textContent = 'ok';
    } catch (err) {
      addMsg('system', 'Chat error: ' + (err?.message || err));
      if (statusEl) statusEl.textContent = 'error';
    }
  });
}
