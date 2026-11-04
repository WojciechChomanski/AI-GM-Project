// ===== Apply Damage (Breath and the Veil, knight v1) =====
// Target: your TARGETED token (T key), else your SELECTED token, else your assigned character.
const R = BreathRules;
// Called by the Breath Attack macro with scope.preset = {actorUuid, amount, type, mode, zone, armourApplied}:
// the engine already took armour off, so armour is NOT applied a second time here.
const PRE = (typeof scope !== 'undefined' && scope?.preset) || null;
const actor = (PRE?.actorUuid ? fromUuidSync(PRE.actorUuid) : null) ?? [...game.user.targets][0]?.actor ?? canvas.tokens?.controlled[0]?.actor ?? game.user.character;
if (!actor) return ui.notifications.warn('Apply Damage: select or target a token first.');
if (!game.user.isGM && !actor.isOwner) return ui.notifications.warn('Apply Damage: you do not own that actor.');
const P = actor.system.props ?? {};
const num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const mult = R.hpMultiplier(num(P.race_hp_bonus), num(P.class_hp_pct));
const maximum = R.scaledZones(mult);
const current = Object.fromEntries(R.ZONES.map((z) => [z, P[z + '_hp'] === undefined || P[z + '_hp'] === '' ? maximum[z] : num(P[z + '_hp'])]));
let wounds = []; try { wounds = JSON.parse(P.bleed_wounds || '[]'); } catch (e) { wounds = []; }
const wornKeys = String(P.armor_worn ?? '').split(',').map((s) => s.trim()).filter(Boolean);
const unknown = wornKeys.filter((k) => !ARMOR_CATALOG[k]);
const pieces = PRE?.armourApplied ? [] : wornKeys.filter((k) => ARMOR_CATALOG[k]).map((k) => ARMOR_CATALOG[k]);
const TYPES = ['slashing', 'piercing', 'blunt'];
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const zoneOpts = R.ZONES.map((z) => `<option value="${z}"${PRE?.zone === z ? ' selected' : ''}>${R.ZONE_LABEL[z]} (-${R.aimedPenalty(z)} to hit)</option>`).join('');
const content = `
<form class="bv-apply-damage">
  <p><b>${esc(actor.name)}</b> - ${R.totalHp(current)} / ${R.totalHp(maximum)} HP. Armour: ${esc(pieces.map((p) => p.name).join(', ') || 'none')}${unknown.length ? ` <span style="color:#b33">(unknown: ${esc(unknown.join(', '))})</span>` : ''}</p>
  <div class="form-group"><label>Damage</label><input type="number" name="amount" value="${PRE ? PRE.amount : 10}" min="0" step="1"></div>
  <div class="form-group"><label>Type</label><select name="type">${TYPES.map((t) => `<option value="${t}"${PRE?.type === t ? ' selected' : ''}>${t}</option>`).join('')}</select></div>
  <div class="form-group"><label>Hit</label>
    <label><input type="radio" name="mode" value="normal"${PRE?.mode === 'aimed' ? '' : ' checked'}> Normal (spread)</label>
    <label><input type="radio" name="mode" value="aimed"${PRE?.mode === 'aimed' ? ' checked' : ''}> Aimed</label></div>
  <div class="form-group bv-zone-row"><label>Aimed zone</label><select name="zone">${zoneOpts}</select></div>
  <div class="form-group"><label>Critical hit (x1.2)</label><input type="checkbox" name="critical"></div>
  <div class="form-group"><label>Crit cut an artery</label><input type="checkbox" name="artery"></div>
  ${PRE?.armourApplied ? '<p class="bv-note"><b>From Breath Attack: armour was already applied by the engine; it is not applied again.</b></p>' : ''}
  <p class="bv-note"><i>Only apply a hit that LANDED. An aimed miss does nothing. Aimed penalty: -40 head/throat/groin, -30 elsewhere.</i></p>
  <div class="bv-preview" style="border:1px solid #6b5a3e;padding:6px;margin-top:6px;background:rgba(0,0,0,.05)"></div>
</form>`;
function readForm(root) {
  const f = root.querySelector('form.bv-apply-damage');
  return { amount: Math.max(0, Math.trunc(num(f.amount.value))), type: f.type.value,
    mode: f.querySelector('input[name=mode]:checked').value, zone: f.zone.value,
    critical: f.critical.checked, artery: f.artery.checked };
}
function simulate(o) {
  const st = { current: { ...current }, maximum, wounds: structuredClone(wounds) };
  const rep = R.applyHit(st, { ...o, pieces });
  return { st, rep };
}
function previewHtml(o) {
  const { st, rep } = simulate(o);
  const a = rep.armor;
  const armourLine = !a ? 'No armour.' : o.mode === 'aimed'
    ? `Armour on ${R.ZONE_LABEL[o.zone]}: ${a.piece ?? 'none'} stops ${a.absorbed} (protection ${a.protection}).`
    : `Armour (weighted average over 11 zones ${a.average}) stops ${a.absorbed}.`;
  const split = Object.entries(rep.split).map(([z, d]) => `${R.ZONE_LABEL[z]} -${d} (${current[z]}&rarr;${st.current[z]})`).join(', ') || 'nothing';
  const w = rep.wound ? `Bleeding: new ${rep.wound.kind} wound on ${R.ZONE_LABEL[rep.wound.zone]} (${rep.wound.rate} HP/round).` : 'No new bleeding wound.';
  const state = rep.dead ? '<b style="color:#a00">DEAD</b>' : rep.collapsed ? '<b style="color:#a50">COLLAPSES (3+ zones at 0)</b>' : 'Standing';
  return `<b>Preview</b> (${o.mode}${o.mode === 'aimed' ? ', -' + R.aimedPenalty(o.zone) + ' to hit' : ''}): ${rep.incoming} ${o.type}${o.critical ? ' (crit)' : ''}<br>${armourLine} <b>${rep.through}</b> gets through.<br>Lands: ${split}.<br>${w}<br>Total HP ${R.totalHp(current)} &rarr; <b>${rep.total}</b>. Zones at 0: ${rep.zonesAtZero}. Bleeding ${rep.bleedRate}/round (cap ${R.BLEED_CAP}). ${state}${rep.destroyed.length ? '<br>Destroyed: ' + rep.destroyed.map((z) => R.ZONE_LABEL[z]).join(', ') + ' (use the crit tables / cripple rules).' : ''}`;
}
function armourLabels() {
  const out = {};
  for (const z of R.ZONES) {
    const best = TYPES.map((t) => R.bestPieceForZone(pieces, z, t));
    const p = best.find(([bp]) => bp)?.[0];
    out[`system.props.${z}_armor`] = p ? `${p.name} ${best.map(([, r]) => r).join('/')}` : '-';
  }
  return out;
}
const woundText = (ws) => ws.filter((w) => w.rate > 0).map((w) => `${R.ZONE_LABEL[w.zone] ?? w.zone}: ${w.kind} ${w.rate}/rd`).join('; ') || 'none';
async function write(st, extra = {}) {
  const upd = { ...armourLabels(), ...extra };
  for (const z of R.ZONES) upd[`system.props.${z}_hp`] = st.current[z];
  upd['system.props.bleed_wounds'] = JSON.stringify(st.wounds);
  upd['system.props.bleed_rate'] = R.currentRate(st.wounds);
  upd['system.props.bleed_list'] = woundText(st.wounds);
  await actor.update(upd);
}
const DialogV2 = foundry.applications.api.DialogV2;
const result = await DialogV2.wait({
  window: { title: `Apply Damage - ${actor.name}` },
  position: { width: 520 },
  content,
  rejectClose: false,
  render: (event, dialog) => {
    const root = dialog.element ?? event?.target?.element;
    const upd = () => {
      const o = readForm(root);
      root.querySelector('.bv-zone-row').style.display = o.mode === 'aimed' ? '' : 'none';
      root.querySelector('.bv-preview').innerHTML = previewHtml(o);
    };
    root.querySelector('form.bv-apply-damage').addEventListener('input', upd);
    root.querySelector('form.bv-apply-damage').addEventListener('change', upd);
    upd();
  },
  buttons: [
    { action: 'apply', label: 'Apply hit', default: true, callback: (event, button, dialog) => ({ action: 'apply', o: readForm(dialog.element ?? button.form) }) },
    { action: 'reset', label: 'Reset body to full', callback: () => ({ action: 'reset' }) },
    { action: 'cancel', label: 'Cancel', callback: () => null },
  ],
});
if (!result) return;
if (result.action === 'reset') {
  const ok = await DialogV2.confirm({ window: { title: 'Reset body' }, content: `<p>Set every zone of <b>${esc(actor.name)}</b> to its maximum and clear all bleeding?</p>` });
  if (!ok) return;
  await write({ current: { ...maximum }, wounds: [] });
  return ui.notifications.info(`${actor.name}: body reset to full (${R.totalHp(maximum)} HP).`);
}
const { st, rep } = simulate(result.o);
await write(st);
await ChatMessage.create({ speaker: ChatMessage.getSpeaker({ actor }), content: `<div class="bv-chat">${previewHtml(result.o).replace('<b>Preview</b>', '<b>Hit applied</b>')}</div>`, whisper: game.user.isGM ? ChatMessage.getWhisperRecipients('GM') : [] });
