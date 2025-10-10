export const ROUND_SECONDS = 6;

export const ACTIONS = {
  move:          { ap: 1, stamina: 0, distancePerAp: 5 },
  melee_attack:  { ap: 3, stamina: 1 },
  ranged_attack: { ap: 3, stamina: 1 },
  reload:        { ap: 2, stamina: 0 },
  guard:         { ap: 1, stamina: 0, grantsReaction: true },
  use_item:      { ap: 2, stamina: 0 },
  first_aid:     { ap: 4, stamina: 1 },
  ability:       { ap: 2, stamina: 1 },
  interact:      { ap: 1, stamina: 0 }
};

export function computeAPPerRound({ AGI = 8, encumbrance = 'light' } = {}) {
  const base = 6;
  const agiBonus = Math.floor((AGI - 8) / 3);
  const encPenalty = encumbrance === 'medium' ? 1 : encumbrance === 'heavy' ? 2 : 0;
  return Math.max(0, base + agiBonus - encPenalty);
}

export function canAfford(apLeft, actionId) {
  const a = ACTIONS[actionId];
  if (!a) return false;
  return apLeft >= a.ap;
}
