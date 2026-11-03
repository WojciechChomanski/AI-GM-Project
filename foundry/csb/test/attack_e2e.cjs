// End-to-end check of macros/breath-attack.macro.js against a RUNNING bridge, with Foundry mocked.
//   python scripts/combat_engine.py            (BREATH_PORT=8765 for this test)
//   node foundry/csb/test/attack_e2e.cjs [url]
const fs = require('fs'), path = require('path');
const url = process.argv[2] || 'http://127.0.0.1:8765/combat/attack';
const items = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'weapons_items.json'), 'utf8'));
const weapon = (id) => ({ system: { props: items.find((i) => i.system.props.weapon_id === id).system.props } });
function actor(name, props, weapons) {
  return { name, uuid: 'Actor.' + name, isOwner: true, system: { props: { ...props } }, items: weapons,
    updates: [], async update(u) { this.updates.push(u); for (const [k, v] of Object.entries(u)) this.system.props[k.replace('system.props.', '')] = v; } };
}
const knight = actor('Konrad', { weapon_in_hand: 'longsword', stamina: 100, stamina_max: 100, total_hp_max: 115, strength: 40,
  weapon_skill: 40, armor_worn: 'Heavy_Light', current_guard: 'vom_tag', race: 'Human', gender: 'Male', class_name: 'Crusader_Knight',
  virtue: 75, piety: 30, fight_state_json: '{}', conditions_json: '[]', mastery_json: '{}' }, [weapon('longsword')]);
const bandit = actor('Bandit', { total_hp_max: 100, stamina_max: 100, armor_worn: 'Heavy_Medium', race: 'Human' }, [weapon('battle_axe')]);
const chat = [], executed = [];
let FORM = { guard: 'half_sword', trigger: 'always', maneuver: 'Half-Sword Thrust', zone: '', dtype: '', trick: false };
Object.assign(globalThis, {
  canvas: { tokens: { controlled: [{ actor: knight }] } },
  game: { user: { isGM: true, targets: new Set([{ actor: bandit }]), character: null },
    macros: { getName: (n) => (n === 'Apply Damage' ? { execute: async (s) => executed.push(s) } : null) } },
  ui: { notifications: { warn: (m) => { throw new Error('warn ' + m); }, error: (m) => { throw new Error('error ' + m); }, info: () => {} } },
  foundry: { applications: { api: { DialogV2: { wait: async () => FORM } } } },
  ChatMessage: { create: async (m) => chat.push(m), getSpeaker: () => ({}), getWhisperRecipients: () => [] },
});
let src = fs.readFileSync(path.join(__dirname, '..', 'macros', 'breath-attack.macro.js'), 'utf8')
  .replace(/const BREATH_BRIDGE = \{[^}]*\};/, `const BREATH_BRIDGE = { url: '${url}', user: process.env.API_USERNAME || 'admin', password: process.env.API_PASSWORD || 'secret' };`);
const run = new Function('scope', `return (async () => {${src}\n})();`);
(async () => {
  const assert = (c, m) => { if (!c) { console.error('FAIL', m); process.exit(1); } };
  await run({});
  const p = knight.system.props;
  assert(p.current_guard === 'half_sword', 'guard stored: ' + p.current_guard);
  assert(p.previous_guard === 'vom_tag', 'previous guard stored');
  assert(p.stamina < 100, 'stamina spent stored: ' + p.stamina);
  assert(JSON.parse(p.fight_state_json), 'fight_state stored');
  assert(chat.length === 1 && /Half-Sword Thrust/.test(chat[0].content), 'chat names the maneuver');
  console.log(chat[0].content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' '));
  if (/HIT/.test(chat[0].content)) assert(executed.length === 1 && executed[0].preset.armourApplied, 'Apply Damage preset');
  // second swing: aimed, forced piercing, no maneuver, one hand
  knight.system.props.grip = 'one_hand';
  FORM = { guard: 'vom_tag', trigger: 'always', maneuver: '__none', zone: 'head', dtype: 'piercing', trick: false };
  await run({});
  assert(/Maneuver: <b>none/.test(chat[1].content), 'no maneuver');
  console.log(chat[1].content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' '));
  console.log('E2E OK: attack macro -> bridge -> engine -> sheet state + chat + Apply Damage preset');
})().catch((e) => { console.error(e); process.exit(1); });
