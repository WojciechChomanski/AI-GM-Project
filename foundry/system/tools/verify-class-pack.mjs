// Shared check: the classes pack must never again ship Paladin or the "integration" metadata block,
// and must include the worldly Knight. Used by compile-packs.mjs and node tests.
export function verifyClassPack(docs) {
  const labels = new Set(docs.flatMap((d) => [
    String(d.source_id || d.system?.source_id || "").toLowerCase(),
    String(d.name || "").toLowerCase(),
  ]));
  const errors = [];
  if (labels.has("paladin")) errors.push("classes pack still contains Paladin (retired honour title, not a class)");
  if (labels.has("integration")) errors.push("classes pack contains the 'integration' metadata block as a class");
  if (!labels.has("knight")) errors.push("classes pack is missing the worldly Knight");
  return errors;
}
