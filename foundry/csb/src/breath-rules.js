// Breath and the Veil - zone damage rules, ported 1:1 from the repo (main):
//   scripts/zone_hp.py, scripts/armor_system.py (option B), scripts/bleeding.py,
//   scripts/combat_health.py (distribute_damage / take_damage_to_zone / add_bleeding_wound).
// ALL NUMBERS ARE PLACEHOLDERS (same as the Python). Armour durability/wear is NOT tracked here yet.
const BreathRules = (() => {
  const BASE_ZONES = { chest: 20, left_upper_leg: 13, right_upper_leg: 13, stomach: 11, head: 7,
    left_upper_arm: 6, right_upper_arm: 6, left_lower_leg: 6, right_lower_leg: 6,
    left_lower_arm: 3, right_lower_arm: 3, throat: 3, groin: 3 };
  const ZONES = Object.keys(BASE_ZONES);
  const ZONE_LABEL = { chest: 'Chest', left_upper_leg: 'Left thigh', right_upper_leg: 'Right thigh', stomach: 'Stomach',
    head: 'Head', left_upper_arm: 'Left upper arm', right_upper_arm: 'Right upper arm', left_lower_leg: 'Left shin',
    right_lower_leg: 'Right shin', left_lower_arm: 'Left forearm', right_lower_arm: 'Right forearm', throat: 'Throat', groin: 'Groin' };
  const VITAL = ['head', 'throat', 'chest'];
  const SPREAD_EXCLUDED = ['throat', 'groin'];
  const SPREAD_FLOOR = { head: 1 };
  const BLEED_FLOOR = Object.fromEntries(ZONES.map((z) => [z, 1]));
  const COLLAPSE_ZONES_AT_ZERO = 3;
  const aimedPenalty = (zone) => (['head', 'throat', 'groin', 'neck'].includes(zone) ? 40 : 30);

  // Python round(): banker's rounding (half to even)
  const pyRound = (x) => { const f = Math.floor(x), d = x - f; if (Math.abs(d - 0.5) < 1e-12) return f % 2 === 0 ? f : f + 1; return Math.round(x); };
  const hpMultiplier = (raceBonus = 0, classPct = 0) => (1 + (raceBonus || 0) / 100) * (1 + (classPct || 0) / 100);
  function scaledZones(m = 1) {
    const target = pyRound(100 * m);
    const z = {}; for (const k of ZONES) z[k] = Math.max(1, pyRound(BASE_ZONES[k] * m));
    z.chest += target - Object.values(z).reduce((a, b) => a + b, 0);
    return z;
  }
  const totalHp = (cur) => Object.values(cur).reduce((a, v) => a + Math.max(0, v), 0);
  const zonesAtZero = (cur) => ZONES.filter((z) => cur[z] <= 0);

  // zone_hp.spread_damage (largest remainder; ties -> bigger zone, then fixed order)
  function spreadDamage(current, maximum, damage, excluded = SPREAD_EXCLUDED, floor = SPREAD_FLOOR) {
    excluded = excluded || []; floor = floor || {};
    const keys = Object.keys(current);
    const taken = Object.fromEntries(keys.map((z) => [z, 0]));
    let remaining = Math.trunc(Math.max(0, damage));
    while (remaining > 0) {
      const alive = keys.filter((z) => !excluded.includes(z) && current[z] - taken[z] > (floor[z] || 0));
      if (!alive.length) break;
      const mx = (z) => (maximum[z] ?? 1);
      const weight = alive.reduce((a, z) => a + mx(z), 0);
      const shares = {}, alloc = {};
      for (const z of alive) { shares[z] = remaining * mx(z) / weight; alloc[z] = Math.trunc(shares[z]); }
      const leftover = remaining - alive.reduce((a, z) => a + alloc[z], 0);
      const order = [...alive].sort((a, b) => {
        const ra = shares[a] - alloc[a], rb = shares[b] - alloc[b];
        if (ra !== rb) return rb - ra;
        if (mx(a) !== mx(b)) return mx(b) - mx(a);
        return keys.indexOf(a) - keys.indexOf(b);
      });
      for (const z of order.slice(0, leftover)) alloc[z] += 1;
      let spent = 0;
      for (const z of alive) { const room = current[z] - taken[z] - (floor[z] || 0); const hit = Math.min(room, alloc[z]); taken[z] += hit; spent += hit; }
      remaining -= spent;
      remaining = Math.ceil(remaining - 1e-9);
      if (spent === 0) break;
    }
    return Object.fromEntries(Object.entries(taken).filter(([, d]) => d > 0));
  }

  // ---- armour (option B). pieces: [{name, coverage:[...], armor_rating:{slashing,piercing,blunt}}], full condition
  const SPREAD_WEIGHTS = Object.fromEntries(ZONES.filter((z) => !SPREAD_EXCLUDED.includes(z)).map((z) => [z, BASE_ZONES[z]]));
  const SPREAD_WEIGHT_TOTAL = Object.values(SPREAD_WEIGHTS).reduce((a, b) => a + b, 0); // 94
  const roundProtection = (v) => Math.trunc(v + 0.5);
  function bestPieceForZone(pieces, zone, type) {
    let best = null, prot = 0;
    for (const p of pieces || []) { if (!p.coverage.includes(zone)) continue; const r = Number(p.armor_rating[type] || 0); if (r > prot) { best = p; prot = r; } }
    return [best, prot];
  }
  function averageProtection(pieces, type) {
    let s = 0; for (const [z, w] of Object.entries(SPREAD_WEIGHTS)) s += bestPieceForZone(pieces, z, type)[1] * w;
    return s / SPREAD_WEIGHT_TOTAL;
  }
  function armorVsSpread(pieces, damage, type) {
    damage = Math.max(0, Math.trunc(damage));
    const avg = averageProtection(pieces, type), protection = roundProtection(avg), absorbed = Math.min(damage, protection);
    return { incoming: damage, protection, average: Math.round(avg * 100) / 100, absorbed, remainder: damage - absorbed };
  }
  function armorVsAimed(pieces, zone, damage, type) {
    damage = Math.max(0, Math.trunc(damage));
    const [p, prot] = bestPieceForZone(pieces, zone, type);
    const protection = roundProtection(prot), absorbed = Math.min(damage, protection);
    return { incoming: damage, protection, piece: p ? p.name : null, absorbed, remainder: damage - absorbed };
  }

  // ---- bleeding (scripts/bleeding.py)
  const BLEED_CAP = 5, CUT_MAX_DAMAGE = 5;
  const RATE_TABLE = { base: [1, 2, 3], thigh_groin: [2, 3, 4], throat: [3, 4, 5] };
  const KIND_INDEX = { cut: 0, deep: 1, artery: 2 };
  const zoneGroup = (z) => (z === 'throat' || z === 'neck' ? 'throat' : z === 'groin' || z.includes('upper_leg') ? 'thigh_groin' : 'base');
  function makeWound(zone, damage, type, critical = false, artery = false, rateMult = 1) {
    if (damage == null || damage <= 0) return null;
    const blunt = type === 'blunt';
    if (blunt && !critical) return null;
    const kind = artery && !blunt ? 'artery' : critical || damage > CUT_MAX_DAMAGE ? 'deep' : 'cut';
    const g = zoneGroup(zone);
    let rate = RATE_TABLE[g][KIND_INDEX[kind]];
    if (rateMult !== 1) rate = Math.max(1, Math.ceil(rate * rateMult - 1e-9));
    return { zone, kind, rate: Math.trunc(rate), age: 0, noclot: g === 'throat' || kind === 'artery' };
  }
  const currentRate = (wounds, cap = BLEED_CAP) => Math.min(cap, wounds.reduce((a, w) => a + Math.max(0, Math.trunc(w.rate)), 0));
  // CombatHealthManager.add_bleeding_wound (mutates wounds; returns the new wound or null)
  function addBleedingWound(wounds, zone, damage, type, critical = false, artery = false, rateMult = 1) {
    if (!artery && wounds.some((w) => w.zone === zone && w.kind === 'artery' && w.age === 0)) return null;
    if (artery && wounds.some((w) => w.zone === zone && w.kind === 'artery')) { artery = false; critical = true; }
    const w = makeWound(zone, damage, type, critical, artery, rateMult);
    if (w) { wounds.push(w); const keep = wounds.filter((x) => x.rate > 0); wounds.length = 0; wounds.push(...keep); }
    return w;
  }

  // ---- one hit. state = {current:{zone:hp}, maximum:{zone:hp}, wounds:[...]}; returns a report, mutates state.
  // opts: {amount, type, mode:'normal'|'aimed', zone, critical, artery, pieces, bleedRateMult}
  function applyHit(state, opts) {
    const { type, mode = 'normal', zone, critical = false, artery = false, pieces = [], bleedRateMult = 1 } = opts;
    let damage = Math.trunc(opts.amount * (critical ? 1.2 : 1.0));
    const rep = { mode, type, critical, incoming: damage, armor: null, split: {}, wound: null, destroyed: [], dead: false };
    const cur = state.current;
    if (mode === 'aimed') {
      if (pieces.length) { rep.armor = armorVsAimed(pieces, zone, damage, type); damage = rep.armor.remainder; }
      rep.through = damage;
      if (damage > 0) {
        const before = cur[zone];
        cur[zone] = Math.max(0, cur[zone] - damage);
        rep.split = { [zone]: damage };
        rep.overflow = Math.max(0, damage - before);
        rep.wound = addBleedingWound(state.wounds, zone, damage, type, critical, artery, bleedRateMult);
      }
    } else {
      if (pieces.length) { rep.armor = armorVsSpread(pieces, damage, type); damage = rep.armor.remainder; }
      rep.through = damage;
      const split = spreadDamage(cur, state.maximum, damage, SPREAD_EXCLUDED, SPREAD_FLOOR);
      for (const [z, d] of Object.entries(split)) cur[z] -= d;
      rep.split = split;
      if (damage > 0 && Object.keys(split).length) {
        const keys = Object.keys(cur);
        const wz = Object.keys(split).reduce((a, b) => (split[b] > split[a] || (split[b] === split[a] && keys.indexOf(b) < keys.indexOf(a)) ? b : a));
        rep.wound = addBleedingWound(state.wounds, wz, damage, type, critical, artery, bleedRateMult);
      }
    }
    rep.destroyed = Object.keys(rep.split).filter((z) => cur[z] <= 0);
    rep.total = totalHp(cur);
    rep.zonesAtZero = zonesAtZero(cur).length;
    rep.collapsed = rep.zonesAtZero >= COLLAPSE_ZONES_AT_ZERO;
    rep.dead = VITAL.some((z) => cur[z] <= 0) || rep.total <= 0;
    rep.bleedRate = currentRate(state.wounds);
    return rep;
  }

  return { BASE_ZONES, ZONES, ZONE_LABEL, VITAL, SPREAD_EXCLUDED, SPREAD_FLOOR, BLEED_FLOOR, BLEED_CAP, aimedPenalty, pyRound,
    hpMultiplier, scaledZones, totalHp, zonesAtZero, spreadDamage, averageProtection, armorVsSpread, armorVsAimed,
    bestPieceForZone, makeWound, currentRate, addBleedingWound, applyHit };
})();
if (typeof module !== 'undefined') module.exports = BreathRules;
