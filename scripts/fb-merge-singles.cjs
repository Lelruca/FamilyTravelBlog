// A photo alone in a row is an exception (DESIGN_PHOTOS.md «Фотоблоки»): only a strong frame or one the text asks
// for stands alone. This joins every single-photo row of a layout (layout.json of scripts/gen-fb-trip-pages.cjs)
// to the nearest photo block of the same chapter — the next one if it stands after the same or the following
// paragraph, otherwise the previous one — so a lone vertical photo does not hang next to text about something else.
// A row of more than 4 photos becomes a mosaic. Photos beside their text ("beside") are left as they are.
//
// Usage: node scripts/fb-merge-singles.cjs <layout.json> [slug:photo,…]   (photos to keep alone, e.g. forillon:4)
const fs = require("fs");

const merge = (layout, keep = []) => {
  let moved = 0;
  for (const [slug, ch] of Object.entries(layout.chapters)) {
    const blocks = ch.blocks;
    const isPhotoBlock = b => b && (b.kind === "row" || b.kind === "mosaic");
    for (let i = 0; i < blocks.length; i++) {
      const b = blocks[i];
      if (b.kind !== "row" || String(b.items).trim().split(/\s+/).length !== 1) continue;
      if (keep.includes(`${slug}:${String(b.items).trim()}`)) continue;
      const next = blocks.slice(i + 1).find(isPhotoBlock);
      const prev = blocks.slice(0, i).reverse().find(isPhotoBlock);
      const target = next && next.after <= b.after + 1 ? next : prev || next;
      if (!target) continue;
      const items = String(target.items).split(/\s+/);
      if (target === next) items.splice(target.kind === "mosaic" ? 1 : 0, 0, String(b.items).trim());
      else items.push(String(b.items).trim());
      target.items = items.join(" ");
      if (target.kind === "row" && items.length > 4) { target.kind = "mosaic"; target.items = "L:" + items.join(" "); }
      blocks.splice(i--, 1);
      moved++;
    }
  }
  return moved;
};

module.exports = merge;
if (require.main === module) {
  const [file, keepArg] = process.argv.slice(2);
  const layout = JSON.parse(fs.readFileSync(file, "utf8"));
  const moved = merge(layout, keepArg ? keepArg.split(",") : []);
  fs.writeFileSync(file, JSON.stringify(layout, null, 2) + "\n");
  console.log(`${moved} single photos joined to their neighbours`);
}
