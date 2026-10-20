// Writes the Hugo pages of a trip imported from Facebook: the trip page and one chapter per post, the post's
// paragraphs verbatim (hashtag-only lines are service tags, like LJ's lj-cut, and are not shown), photos placed
// as the layout file says, and the author's per-photo captions added to data/photos/<trip>.json.
// Photos not placed by the layout go after the last paragraph, so none is lost while the layout is in progress.
//
// Usage: node scripts/gen-fb-trip-pages.cjs <trip-config.json> <pages.json> [layout.json]
//   pages.json: { dir, trip: { front matter of _index.md }, chapters: { <slug>: { title, city, places, kind? } } }
//   layout.json: { draft, cover, cover_position, chapters: { <slug>: { hero, hero_crop, card (the photo of the chapter tile
//                  on the trip page when it should differ from the cover), joins: [[from, to]], blocks: [
//                  { after: <paragraph index, -1 = before the first>, kind: "row"|"mosaic", items: "L:3 5 7" },
//                  { after, kind: "beside", items: "4", side, paras: [0, 1] }, { after, kind: "text", captions: "8 9", join },
//                  { after, kind: "heading", text: "<place>" } ] } } }
//   Photos are given by their number in the post; "18a" is an addition of the owner next to photo 18.
// Spelling corrections the owner asked for (trip-config "corrections": a JSON file of { key, caption?, from, to })
// are applied to the shown text only; the archive text and the manifest keep the original words.
const fs = require("fs");
const path = require("path");

const [cfgFile, pagesFile, layoutFile] = process.argv.slice(2);
const cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
const pages = JSON.parse(fs.readFileSync(pagesFile, "utf8"));
const layout = layoutFile && fs.existsSync(layoutFile) ? JSON.parse(fs.readFileSync(layoutFile, "utf8")) : { chapters: {} };
const posts = JSON.parse(fs.readFileSync(cfg.posts, "utf8"));
const manifest = JSON.parse(fs.readFileSync(`media-manifests/${cfg.trip}.json`, "utf8"));
const tripDir = pages.dir;
const { fixText, fixCaption, sameText } = require("./fb-corrections.cjs")(cfg);
const draft = layout.draft === false ? "false" : "true";

const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const yaml = v => Array.isArray(v) ? "\n" + v.map(x => `  - ${x}`).join("\n") : JSON.stringify(v);
const isTags = line => /^\s*(#\S+\s*)+$/.test(line);
const displayName = a => path.basename(a).replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");

const front = Object.entries({ ...pages.trip, ...(layout.cover ? { cover_image: layout.cover } : {}),
  ...(layout.cover_position ? { cover_position: layout.cover_position } : {}), source_url: cfg.source })
  .map(([k, v]) => `${k}: ${yaml(v)}`).join("\n");
fs.mkdirSync(tripDir, { recursive: true });
fs.writeFileSync(`${tripDir}/_index.md`, `---\n${front}\ndraft: ${draft}\n---\n`);

// The chapter's day: the most common capture date among its originals (file names 20200627_122955.jpg).
const chapterDate = (slug, post) => {
  const days = manifest.photos.filter(p => p.chapter === slug && p.original_relative_path)
    .map(p => (path.basename(p.original_relative_path).match(/^(\d{4})(\d{2})(\d{2})_/) || []).slice(1).join("-")).filter(Boolean);
  const count = {}; days.forEach(d => count[d] = (count[d] || 0) + 1);
  const top = Object.entries(count).sort((a, b) => b[1] - a[1])[0];
  return top ? top[0] : post.date;
};

const report = [];
const textCaps = new Set();
cfg.chapters.forEach((ch, n) => {
  // a chapter without a post (trip-config "originals") has photos only, its text is written later
  // trip-config "post": { key, feedOrder, paras: [a, b] } — a chapter of chosen originals that shows paragraphs a…b
  // of a post (one long post told over several chapters, e.g. one chapter per day)
  const src = ch.post || ch;
  const post = posts.find(p => p.feedOrder === src.feedOrder) || { text: "", date: "" };
  // trip-config "text": a file with the owner's own words for a chapter that has no post (one line = one paragraph);
  // spelling corrections for it use the chapter slug as their key
  const own = ch.text && fixText(ch.slug, fs.readFileSync(ch.text, "utf8").replace(/\r/g, "").trimEnd());
  const all = (own || (ch.originals && !ch.post ? "" : fixText(src.key, post.text))).split("\n").filter(l => l.trim() && !isTags(l));
  const paras = ch.post ? all.slice(ch.post.paras[0], ch.post.paras[1] + 1) : all;
  // another short post of the author about the same day, inserted after a paragraph (trip-config "inserts":
  // [{ after, file }], the file holding that post's text); later "after" indexes count the inserted lines
  for (const ins of (ch.inserts || []).slice().sort((a, b) => b.after - a.after))
    paras.splice(ins.after + 1, 0, ...fs.readFileSync(ins.file, "utf8").replace(/\r/g, "").split("\n").filter(l => l.trim() && !isTags(l)));
  const mine = manifest.photos.filter(p => p.chapter === ch.slug);
  const photos = mine.map(p => displayName(p.archive_name));
  const byPos = Object.fromEntries(mine.map(p => [String(p.source_position), displayName(p.archive_name)]));
  const capByPos = Object.fromEntries(mine.map(p => [String(p.source_position), fixCaption(ch.key, p.source_position, p.caption || "")]));
  // a caption repeating a paragraph is already on the page as text: not written over the photo again
  for (const p of mine) if (p.caption && paras.some(t => sameText(t, fixCaption(ch.key, p.source_position, p.caption)))) textCaps.add(`${ch.slug}/${displayName(p.archive_name)}`);
  const name = t => t.replace(/^([LRT]:)?(\d+[a-z]?)$/, (all, k, num) => (k || "") + (byPos[num] || "MISSING" + num));
  const raw = layout.chapters[ch.slug] || { blocks: [] };
  const hero = raw.hero && name(String(raw.hero));
  const used = hero ? [hero] : [];
  const after = {};
  for (const b of raw.blocks) {
    const items = b.kind === "text" || b.kind === "heading" ? "" : String(b.items).split(/\s+/).filter(Boolean).map(name).join(" ");
    (after[b.after] = after[b.after] || []).push({ ...b, names: items });
    if (b.kind !== "text" && b.kind !== "heading") used.push(...items.split(" ").map(x => x.replace(/^[LRT]:/, "")));
    if (b.kind === "text" || b.kind === "beside") for (const num of String(b.captions || b.items).split(/\s+/)) textCaps.add(`${ch.slug}/${byPos[num]}`);
  }
  const missing = photos.filter(p => !used.includes(p));
  const unknown = used.filter(p => !photos.includes(p));
  // the cover is also in the text (the owner's rule): counted once
  const twice = used.filter((p, i) => used.indexOf(p) !== i && !(p === hero && used.indexOf(p) === 0 && used.indexOf(p, 1) === i));
  report.push(`${ch.slug}: ${paras.length} paragraphs, ${photos.length} photos, placed ${used.length}` +
    (missing.length ? `, NOT PLACED ${missing.length}` : "") + (unknown.length ? `, UNKNOWN ${unknown.join(" ")}` : "") + (twice.length ? `, TWICE ${twice.join(" ")}` : ""));
  const last = paras.length - 1;
  for (let i = 0; i < missing.length; i += 3) (after[last] = after[last] || []).push({ kind: "row", names: missing.slice(i, i + 3).join(" ") });

  // a photo's own caption shown as a paragraph of text next to it (lines stay lines)
  const note = num => `<p class="photo-note">${esc(capByPos[num]).replace(/\n/g, "<br>")}</p>`;
  const render = b => {
    // { after, kind: "heading", text } — the place the next photos show (a section of a long chapter)
    if (b.kind === "heading") return `<h3 class="essay-section">${esc(b.text)}</h3>`;
    if (b.kind === "text") {
      const ns = String(b.captions).split(/\s+/);
      return b.join ? `<p class="photo-note">${ns.map(x => esc(capByPos[x]).replace(/\n/g, "<br>")).join("<br>")}</p>` : ns.map(note).join("\n\n");
    }
    // "paras": [a, b] — the post's paragraphs a…b stand inside, next to the photo (its caption, if any, after them)
    if (b.kind === "beside") {
      const inner = (b.paras ? paras.slice(b.paras[0], b.paras[1] + 1).map(t => `<p>${esc(t)}</p>`) : [])
        .concat(capByPos[String(b.items)] || !b.paras ? [note(String(b.items))] : []);
      return `{{< beside photo="${b.names}"${b.side ? ` side="${b.side}"` : ""} >}}\n${inner.join("\n")}\n{{< /beside >}}`;
    }
    return `{{< ${b.kind} "${b.names}" >}}`;
  };
  const body = [];
  (after[-1] || []).forEach(b => body.push(render(b)));
  // "joins": [[3, 9]] — short lines of one list or table (lines 3–9) shown as one paragraph with line breaks
  const joinOf = i => (raw.joins || []).find(([a, b]) => i >= a && i <= b);
  const inBeside = i => raw.blocks.some(b => b.kind === "beside" && b.paras && i >= b.paras[0] && i <= b.paras[1]);
  paras.forEach((p, i) => {
    const j = joinOf(i);
    if (inBeside(i)) { (after[i] || []).forEach(b => body.push(render(b))); return; }
    if (!j || i === j[0]) body.push(`<p>${(j ? paras.slice(j[0], j[1] + 1) : [p]).map(esc).join("<br>")}</p>`);
    if (!j || i === j[1]) for (let k = j ? j[0] : i; k <= i; k++) (after[k] || []).forEach(b => body.push(render(b)));
  });

  const m = pages.chapters[ch.slug];
  const dir = `${tripDir}/${ch.slug}`;
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(`${dir}/index.md`, `---
title: ${yaml(m.title)}
chapter_kind: "${m.kind || "part"}"
layout: "photo-story"
weight: ${(n + 1) * 10}
city: ${yaml(m.city)}
places:${yaml(m.places)}
${hero ? `hero_image: ${yaml(hero)}\n` : ""}${raw.hero_crop ? `hero_crop: ${yaml(raw.hero_crop)}\n` : ""}${raw.card ? `hero_card_image: ${yaml(name(String(raw.card)))}\n` : ""}${raw.hero_card_position ? `hero_card_position: ${yaml(raw.hero_card_position)}\n` : ""}date: "${chapterDate(ch.slug, post)}"
auto_gallery: false
draft: ${draft}
---
${body.join("\n\n")}
`);
});

// The author's captions of single photos, verbatim, next to each photo's size.
const dataFile = `data/photos/${cfg.trip}.json`;
if (fs.existsSync(dataFile)) {
  const data = JSON.parse(fs.readFileSync(dataFile, "utf8"));
  let caps = 0;
  for (const p of manifest.photos) {
    const key = `${p.chapter}/${displayName(p.archive_name)}`;
    if (!data[key]) continue;
    delete data[key].caption; delete data[key].caption_in_text;
    if (p.caption) { data[key][textCaps.has(key) ? "caption_in_text" : "caption"] = fixCaption(cfg.chapters.find(c => c.slug === p.chapter).key, p.source_position, p.caption); caps++; }
  }
  fs.writeFileSync(dataFile, JSON.stringify(data, null, 1) + "\n");
  report.push(`captions: ${caps}`);
}
console.log(report.join("\n"));
