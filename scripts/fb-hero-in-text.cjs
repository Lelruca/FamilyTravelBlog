// The owner's rule: a photo chosen as a chapter cover is added to the cover, it does not leave the story.
// For every chapter of a layout (layout.json of scripts/gen-fb-trip-pages.cjs) whose cover is one of its own
// photos and is not placed in the text, this puts it back next to its neighbour in the post's order
// (the block holding photo n-1 or n+1, the nearest one), so it returns to the episode it belongs to.
// A row of more than 5 photos becomes a mosaic. Prints what it did, to be checked by eye.
//
// Usage: node scripts/fb-hero-in-text.cjs <layout.json>
const fs = require("fs");

const file = process.argv[2];
const layout = JSON.parse(fs.readFileSync(file, "utf8"));
const num = s => String(s).replace(/^[LRT]:/, "");
for (const [slug, ch] of Object.entries(layout.chapters)) {
  const hero = ch.hero == null ? "" : String(ch.hero);
  if (!/^\d+[a-z]?$/.test(hero)) continue;
  const placed = ch.blocks.flatMap(b => String(b.items || "").split(/\s+/).map(num));
  if (placed.includes(hero)) continue;
  const h = parseInt(hero, 10);
  let best = null;
  for (const b of ch.blocks) {
    if (b.kind !== "row" && b.kind !== "mosaic") continue;
    const items = String(b.items).split(/\s+/);
    items.forEach((it, i) => {
      const d = parseInt(num(it), 10) - h;
      if (Number.isNaN(d)) return;
      if (!best || Math.abs(d) < Math.abs(best.d) || (Math.abs(d) === Math.abs(best.d) && d < 0)) best = { b, i, d };
    });
  }
  if (!best) { ch.blocks.push({ after: -1, kind: "row", items: hero }); console.log(`${slug}: cover ${hero} — no block, put first`); continue; }
  const items = String(best.b.items).split(/\s+/);
  items.splice(best.d < 0 ? best.i + 1 : best.i, 0, hero);
  if (best.b.kind === "row" && items.length > 5) { best.b.kind = "mosaic"; best.b.items = "L:" + items.join(" "); }
  else best.b.items = items.join(" ");
  console.log(`${slug}: cover ${hero} → ${best.b.kind} "${best.b.items}" (after paragraph ${best.b.after})`);
}
fs.writeFileSync(file, JSON.stringify(layout, null, 2) + "\n");
