// First draft of the photo layout of a trip imported from Facebook (layout.json for scripts/gen-fb-trip-pages.cjs).
// A post shows its text first and all photos after it, in the order of the story; here the photos are spread
// over the paragraphs in that order, in proportion to the length of each paragraph, then grouped into rows and
// mosaics (DESIGN_PHOTOS.md). A photo with a long caption of the author stands beside its caption.
// Runs of three or more short lines (a list or a table) are joined into one paragraph.
// The result is a starting point: covers and the placement of photos the text names are then checked by eye.
//
// Usage: node scripts/fb-auto-layout.cjs <trip-config.json> <out layout.json> [heroes.json]
//   heroes.json (optional): { "<chapter slug>": <photo number or "13a"> } — chapter covers chosen by eye.
// Without a chosen cover, a chapter's cover is its first horizontal photo.
const fs = require("fs");
const path = require("path");

const [cfgFile, outFile, heroesFile] = process.argv.slice(2);
const cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
const posts = JSON.parse(fs.readFileSync(cfg.posts, "utf8"));
const manifest = JSON.parse(fs.readFileSync(`media-manifests/${cfg.trip}.json`, "utf8"));
const sizes = JSON.parse(fs.readFileSync(`data/photos/${cfg.trip}.json`, "utf8"));
const heroes = heroesFile && fs.existsSync(heroesFile) ? JSON.parse(fs.readFileSync(heroesFile, "utf8")) : {};
const { fixText, fixCaption, sameText } = require("./fb-corrections.cjs")(cfg);
const old = fs.existsSync(outFile) ? JSON.parse(fs.readFileSync(outFile, "utf8")) : {};

const isTags = line => /^\s*(#\S+\s*)+$/.test(line);
const displayName = a => path.basename(a).replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");
const LONG_CAPTION = 150, SHORT_LINE = 40;

const layout = { draft: old.draft !== false, ...(old.cover ? { cover: old.cover } : {}), chapters: {} };
for (const ch of cfg.chapters) {
  const post = posts.find(p => p.feedOrder === ch.feedOrder);
  const paras = fixText(ch.key, post.text).split("\n").filter(l => l.trim() && !isTags(l));
  for (const ins of (ch.inserts || []).slice().sort((a, b) => b.after - a.after))
    paras.splice(ins.after + 1, 0, ...fs.readFileSync(ins.file, "utf8").replace(/\r/g, "").split("\n").filter(l => l.trim() && !isTags(l)));
  // runs of 3+ short lines → one paragraph with line breaks
  const joins = [];
  for (let i = 0; i < paras.length;) {
    let j = i;
    while (j < paras.length && paras[j].trim().length < SHORT_LINE) j++;
    if (j - i >= 3) { joins.push([i, j - 1]); i = j; } else i = Math.max(j, i + 1);
  }
  const joinEnd = i => (joins.find(([a, b]) => i >= a && i <= b) || [i, i])[1];
  const photos = manifest.photos.filter(p => p.chapter === ch.slug).map(p => {
    const s = sizes[`${ch.slug}/${displayName(p.archive_name)}`] || {};
    const caption = fixCaption(ch.key, p.source_position, p.caption || "");
    // a photo captioned with the words of a paragraph stands right after that paragraph
    const at = caption ? paras.findIndex(t => sameText(t, caption)) : -1;
    return { n: String(p.source_position), h: s.w > s.h, caption: at >= 0 ? "" : caption, at };
  });
  const hero = String(heroes[ch.slug] ?? (photos.find(p => p.h) || photos[0] || {}).n ?? "");
  const rest = photos.filter(p => p.n !== hero);
  // spread the photos over the paragraphs by the share of text before each paragraph's end
  const len = paras.map(p => p.length + 80);
  const total = len.reduce((a, b) => a + b, 0);
  const groups = {};
  rest.forEach((p, k) => {
    if (p.at >= 0) { (groups[joinEnd(p.at)] = groups[joinEnd(p.at)] || []).push(p); return; }
    const want = (k + 0.5) / rest.length * total;
    let acc = 0, i = 0;
    while (i < paras.length - 1 && acc + len[i] < want) acc += len[i++];
    i = joinEnd(i);
    (groups[i] = groups[i] || []).push(p);
  });
  const blocks = [];
  for (const [after, list] of Object.entries(groups).sort((x, y) => x[0] - y[0])) {
    let run = [];
    const flush = () => {
      for (let s = 0; s < run.length;) {
        const left = run.length - s;
        const take = left <= 3 ? left : left <= 6 ? left : left === 7 ? 4 : 5;
        const part = run.slice(s, s + take);
        s += take;
        if (part.length <= 3) blocks.push({ after: +after, kind: "row", items: part.map(p => p.n).join(" ") });
        else {
          const big = part.find(p => p.h) || part[0];
          blocks.push({ after: +after, kind: "mosaic", items: [big, ...part.filter(p => p !== big)].map(p => (p === big ? "L:" : "") + p.n).join(" ") });
        }
      }
      run = [];
    };
    for (const p of list) {
      if (p.caption.length > LONG_CAPTION) { flush(); blocks.push({ after: +after, kind: "beside", items: p.n }); }
      else run.push(p);
    }
    flush();
  }
  layout.chapters[ch.slug] = { ...(hero ? { hero } : {}), ...(joins.length ? { joins } : {}), blocks };
}
fs.writeFileSync(outFile, JSON.stringify(layout, null, 2) + "\n");
console.log(Object.entries(layout.chapters).map(([s, c]) => `${s}: cover ${c.hero}, ${c.blocks.length} blocks${c.joins ? `, joins ${JSON.stringify(c.joins)}` : ""}`).join("\n"));
