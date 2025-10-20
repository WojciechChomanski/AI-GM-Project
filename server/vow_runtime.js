// server/vow_runtime.js
// Minimal, non-breaking runtime for Crusader_Knight Tier-5 “No Retreat”.
// Applies start/end-of-round hooks, tracks state, logs ticks, and grants 1 random miracle on fulfill.
// NOTE: This does NOT change your damage math yet. If you later want x2 damage-taken while active,
// read session.combat.vow_effects.damage_taken_multiplier inside your existing damage calc.

function ensure(obj, key, seed) {
  if (obj[key] === undefined) obj[key] = seed;
  return obj[key];
}

function log(session, line) {
  ensure(session, 'log', []);
  session.log.push({ t: new Date().toISOString(), line });
}

function getVowState(session) {
  ensure(session, 'combat', {});
  ensure(session.combat, 'vows', {});
  return ensure(session.combat.vows, 'crusader_knight', {
    active: false,
    roundsLeft: 0,
    fulfilled: false,
    broken: false
  });
}

// Locate Tier-5 vow in a Crusader_Knight class block
function getCkTier5Vow(cls) {
  if (!cls?.progression) return null;
  const t5 = cls.progression.find(t => t.tier === 5 && t.vow?.name === 'No Retreat');
  return t5?.vow || null;
}

function check_vow_trigger(session, cls) {
  const vow = getCkTier5Vow(cls);
  if (!vow) return;

  const VS = getVowState(session);
  if (VS.active || VS.fulfilled || VS.broken) return;

  const hp  = session.actor?.hp_current ?? 0;
  const max = session.actor?.hp_max ?? 1;
  const hpPct = max > 0 ? Math.floor((hp / max) * 100) : 0;
  const enemyAlive = !!session.combat?.enemyAlive;

  const triggerPct = vow?.trigger?.value ?? 30;

  if (hpPct < triggerPct && enemyAlive) {
    VS.active = true;
    VS.roundsLeft = vow?.effects?.duration_rounds_max ?? 3;

    ensure(session, 'combat', {});
    session.combat.vow_effects = {
      damage_taken_multiplier: vow?.effects?.damage_taken_multiplier ?? 2.0,
      ally_aura: vow?.effects?.ally_auras ?? null
    };

    log(session, `🛡️ Vow activated: ${vow.name} (${VS.roundsLeft} rounds)`);
  }
}

function apply_vow_tick_and_miracle(session, cls) {
  const vow = getCkTier5Vow(cls);
  if (!vow) return;

  const VS = getVowState(session);
  if (!VS.active) return;

  // Sanity per round
  const sanityGain = vow?.effects?.sanity_per_round ?? 0;
  if (sanityGain) {
    ensure(session, 'actor', {});
    session.actor.sanity = (session.actor.sanity ?? 0) + sanityGain;
    log(session, `🕯️ Vow tick: +${sanityGain} Sanity`);
  }

  // Keep aura advertised for the round
  ensure(session, 'combat', {});
  session.combat.vow_effects ??= {};
  session.combat.vow_effects.ally_aura = vow?.effects?.ally_auras ?? null;

  // Duration bookkeeping
  VS.roundsLeft = Math.max(0, (VS.roundsLeft ?? 0) - 1);

  // Optional: break path (set session.combat.flags.vow_broken from your flee/withdraw logic)
  if (session.combat?.flags?.vow_broken) {
    VS.active = false; VS.broken = true;
    session.combat.vow_effects = null;

    const br = vow?.break_vow?.costs;
    if (br?.sanity_delta) {
      ensure(session, 'actor', {});
      session.actor.sanity = (session.actor.sanity ?? 0) + br.sanity_delta;
    }
    log(session, `⚠️ Vow broken: ${vow.name} (penalties applied)`);
    return;
  }

  // On expiry: fulfill + grant miracle intent
  if (VS.roundsLeft === 0) {
    VS.active = false; VS.fulfilled = true;
    session.combat.vow_effects = null;

    const pool = vow?.reward_on_fulfill?.miracle?.choose_one_random ?? [];
    if (pool.length) {
      const pick = pool[Math.floor(Math.random() * pool.length)];
      ensure(session, 'combat', {});
      ensure(session.combat, 'rewards', {});
      ensure(session.combat.rewards, 'miracles', []);
      session.combat.rewards.miracles.push(pick.id);
      log(session, `✨ Miracle granted: ${pick.label}`);
    } else {
      log(session, `✨ Miracle: (none configured)`);
    }
  }
}

module.exports = {
  check_vow_trigger,
  apply_vow_tick_and_miracle,
  getVowState
};
