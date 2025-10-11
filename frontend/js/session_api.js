// frontend/js/session_api.js
export async function getSession() {
  const r = await fetch('/api/session', { cache: 'no-store' });
  if (!r.ok) throw new Error('Failed to load session');
  const { state } = await r.json();
  return state || {};
}
export async function resetSession() {
  const r = await fetch('/api/session/reset', { method: 'POST' });
  if (!r.ok) throw new Error('Reset failed');
}
export async function initSession() {
  const r = await fetch('/api/session/init', { method: 'POST' });
  if (!r.ok) throw new Error('Init failed');
}
export async function resolveEvent(eventId, outcome, bonusObjectives = []) {
  const r = await fetch('/api/session/resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ eventId, outcome, bonusObjectives })
  });
  if (!r.ok) throw new Error('Resolve failed');
}
export async function chat({ role = 'player', message = '' }) {
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, message })
  });
  if (!r.ok) throw new Error('Chat failed');
  return r.json();
}

