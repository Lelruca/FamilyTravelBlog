// Converts a chapter's old photo strips ({{< photoscroller >}}) into the photo-story layout
// ({{< row >}} / {{< mosaic >}}, DESIGN_PHOTOS.md), keeping every photo where its strip was.
// The author's text is not touched; the script checks that every paragraph stays identical.
//
// Usage: node scripts/compose-chapter.cjs <chapter dir> [picks.json]
//   picks.json (optional): { "big": ["IMG_1.jpg", ...], "exclude": [...] }
//     big  — photos to show as large mosaic tiles (or alone in a row);  exclude — photos to drop.
// Needs: screen copies + sizes from scripts/make-display-copies.cjs, and the Google Drive for desktop DB.
const fs = require("fs");
const path = require("path");
const os = require("os");
const { DatabaseSync } = require("node:sqlite");

const [chapterDir, picksFile] = process.argv.slice(2);
const picks = picksFile ? JSON.parse(fs.readFileSync(picksFile, "utf8")) : {};
const big = new Set(picks.big || []), exclude = new Set(picks.exclude || []);
const chapter = path.basename(chapterDir);
const trip = path.basename(path.dirname(chapterDir));
const sizes = JSON.parse(fs.readFileSync(path.join("data", "photos", trip + ".json"), "utf8"));

// Drive file ID -> file name, from a copy of the DriveFS database.
const fsRoot = path.join(process.env.LOCALAPPDATA, "Google", "DriveFS");
const acct = fs.readdirSync(fsRoot).find(d => fs.existsSync(path.join(fsRoot, d, "metadata_sqlite_db")));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "drivefs-"));
for (const ext of ["", "-wal"]) {
  const src = path.join(fsRoot, acct, "metadata_sqlite_db" + ext);
  if (fs.existsSync(src)) fs.copyFileSync(src, path.join(tmp, "db" + ext));
}
const db = new DatabaseSync(path.join(tmp, "db"));
const titleOf = id => (db.prepare("SELECT local_title FROM items WHERE id = ? AND trashed = 0").get(id) || {}).local_title;
const displayName = f => f.replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");
const nameOfUrl = u => {
  const id = (u.match(/[?&]id=([\w-]+)/) || [])[1];
  const t = id && titleOf(id);
  if (!t) throw new Error("Unknown Drive photo: " + u);
  return displayName(t);
};
const ratio = n => {
  const s = sizes[`${chapter}/${n}`];
  if (!s) throw new Error(`No copy for ${chapter}/${n} — run make-display-copies`);
  return s.w / s.h;
};

const isSquare = r => r > 0.9 && r < 1.1;

// Lay out one strip: squares in groups of five become mosaics (one large tile + four small),
// everything else goes into rows of equal height (2–4 photos, total ratio about 2.3–4.2).
function compose(names) {
  const blocks = [];
  const squares = names.filter(n => isSquare(ratio(n)));
  const used = new Set();
  let side = "L";
  const chunks = [];
  while (squares.filter(n => !used.has(n)).length >= 5) {
    const free = squares.filter(n => !used.has(n));
    const lead = free.find(n => big.has(n)) || free[0];
    const rest = free.filter(n => n !== lead).slice(0, 4);
    [lead, ...rest].forEach(n => used.add(n));
    chunks.push({ at: names.indexOf(lead), text: `{{< mosaic "${side}:${lead} ${rest.join(" ")}" >}}` });
    side = side === "L" ? "R" : "L";
  }
  // Rows from the remaining photos, in their order. A "big" photo gets a row of its own if it is horizontal.
  const rest = names.filter(n => !used.has(n));
  const rows = [];
  let cur = [];
  const sum = r => r.reduce((s, n) => s + ratio(n), 0);
  for (const n of rest) {
    if (big.has(n) && ratio(n) > 1.3) { if (cur.length) rows.push(cur); rows.push([n]); cur = []; continue; }
    cur.push(n);
    if (sum(cur) >= 2.3 || cur.length === 4) { rows.push(cur); cur = []; }
  }
  if (cur.length) {
    const last = rows[rows.length - 1];
    if (last && last.length < 4 && sum(last) + sum(cur) <= 4.6 && !(last.length === 1 && big.has(last[0]))) rows[rows.length - 1] = last.concat(cur);
    else rows.push(cur);
  }
  for (const r of rows) chunks.push({ at: names.indexOf(r[0]), text: `{{< row "${r.join(" ")}" >}}` });
  return chunks.sort((a, b) => a.at - b.at).map(c => c.text);
}

const file = path.join(chapterDir, "index.md");
const src = fs.readFileSync(file, "utf8");
const [, fm, body] = src.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
// The chapter cover is shown at the top, so it is not repeated in the text.
const heroUrl = (fm.match(/^hero_image: "(.*)"$/m) || [])[1];
if (heroUrl) exclude.add(heroUrl.includes("drive.google.com") ? nameOfUrl(heroUrl) : heroUrl);
const isPhotoHtml = b => /^<div class="essay-(group|mosaic)/.test(b);
const blocks = body.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
const out = [];
const seen = new Set();
for (const b of blocks) {
  // old strips, or photo blocks of the earlier per-trip layouts (<div class="essay-group">…)
  const m = b.match(/^\{\{< photoscroller items="([^"]+)" >\}\}$/);
  const html = isPhotoHtml(b) ? [...new Set([...b.matchAll(/[?&]id=([\w-]{20,})/g)].map(x => x[1]))] : null;
  if (!m && !html) { out.push(b); continue; }
  const names = (m ? m[1].split(",") : html.map(id => `?id=${id}`)).map(nameOfUrl).filter(n => !exclude.has(n) && !seen.has(n));
  names.forEach(n => seen.add(n));
  if (names.length) out.push(...compose(names));
}
let fm2 = fm;
const hero = (fm.match(/^hero_image: "(.*)"$/m) || [])[1];
if (hero && hero.includes("drive.google.com")) fm2 = fm2.replace(/^hero_image: .*$/m, `hero_image: "${nameOfUrl(hero)}"`);
if (/^layout:/m.test(fm2)) fm2 = fm2.replace(/^layout: .*$/m, 'layout: "photo-story"');
else fm2 = fm2.replace(/^weight:/m, 'layout: "photo-story"\nweight:');
const result = "---\n" + fm2 + "\n---\n" + out.join("\n\n") + "\n";

// The text must be exactly the same, paragraph by paragraph.
const text = s => s.split(/^---$/m).slice(2).join("---").split(/\n\s*\n/).map(x => x.trim()).filter(x => x && !x.startsWith("{{<") && !isPhotoHtml(x));
if (JSON.stringify(text(src)) !== JSON.stringify(text(result))) throw new Error("Text changed — aborting");
fs.writeFileSync(file, result);
console.log(`${chapter}: ${seen.size} photos, ${out.length - text(src).length} photo blocks; text unchanged.`);
db.close();
try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
