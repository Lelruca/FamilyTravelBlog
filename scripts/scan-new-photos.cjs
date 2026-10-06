// Finds photos the owner added to a trip's Google Drive folder that are not on the site yet,
// and duplicates (same photo twice). Read-only: changes nothing on Drive or in the site.
//
// Usage: node scripts/scan-new-photos.cjs <content trip dir> "<Drive trip folder name>"
//   e.g. node scripts/scan-new-photos.cjs content/europe/portugal/portugal-spain-2016 "2016 - Португалия-Испания"
//
// Drive file IDs come from the local Google Drive for desktop database (DriveFS).
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const { DatabaseSync } = require("node:sqlite");

const [tripDir, driveTrip] = process.argv.slice(2);
if (!tripDir || !driveTrip) {
  console.error('Usage: node scripts/scan-new-photos.cjs <content trip dir> "<Drive trip folder name>"');
  process.exit(1);
}
const DRIVE_ROOT = "G:/My Drive/Family Travel Blog Photos";

// Copy the live DB (and its WAL) so DriveFS keeps working undisturbed.
const fsRoot = path.join(process.env.LOCALAPPDATA, "Google", "DriveFS");
const acct = fs.readdirSync(fsRoot).find(d => fs.existsSync(path.join(fsRoot, d, "metadata_sqlite_db")));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "drivefs-"));
for (const ext of ["", "-wal"]) {
  const src = path.join(fsRoot, acct, "metadata_sqlite_db" + ext);
  if (fs.existsSync(src)) fs.copyFileSync(src, path.join(tmp, "db" + ext));
}
const db = new DatabaseSync(path.join(tmp, "db"));

const children = db.prepare(
  "SELECT i.stable_id, i.id, i.local_title AS title, i.is_folder, i.file_size AS size, i.mime_type AS mime " +
  "FROM items i JOIN stable_parents p ON p.item_stable_id = i.stable_id " +
  "WHERE p.parent_stable_id = ? AND i.trashed = 0 AND i.is_tombstone = 0");
const byTitle = db.prepare("SELECT stable_id FROM items WHERE local_title = ? AND is_folder = 1 AND trashed = 0");

// Locate the trip folder under "Family Travel Blog Photos".
const tripFolder = byTitle.all(driveTrip).find(f => {
  const parents = db.prepare("SELECT parent_stable_id FROM stable_parents WHERE item_stable_id = ?").all(f.stable_id);
  return parents.some(p => {
    const gp = db.prepare("SELECT parent_stable_id FROM stable_parents WHERE item_stable_id = ?").all(p.parent_stable_id);
    return gp.some(g => (db.prepare("SELECT local_title FROM items WHERE stable_id = ?").get(g.parent_stable_id) || {}).local_title === "Family Travel Blog Photos");
  });
});
if (!tripFolder) { console.error("Drive folder not found: " + driveTrip); process.exit(1); }

// All image files, with the chapter folder and any subfolder they sit in.
const files = [];
const walk = (stableId, rel) => {
  for (const it of children.all(stableId)) {
    const r = rel ? rel + "/" + it.title : it.title;
    if (it.is_folder) walk(it.stable_id, r);
    else if (/^image\//.test(it.mime || "") || /\.(jpe?g|png|heic|webp)$/i.test(it.title)) files.push({ ...it, rel: r });
  }
};
walk(tripFolder.stable_id, "");

// Photo IDs used on the site, per chapter page; photo-story chapters name their photos instead.
const used = new Map(); // id -> chapter dir
const namesUsed = new Map(); // chapter dir -> Set of photo base names
for (const dir of fs.readdirSync(tripDir)) {
  const md = path.join(tripDir, dir, "index.md");
  const src = fs.existsSync(md) ? fs.readFileSync(md, "utf8") : (dir === "_index.md" ? fs.readFileSync(path.join(tripDir, dir), "utf8") : "");
  for (const m of src.matchAll(/(?:[?&]id=|\/d\/)([A-Za-z0-9_-]{20,})/g)) if (!used.has(m[1])) used.set(m[1], dir === "_index.md" ? "(обложка поездки)" : dir);
  if (dir !== "_index.md") namesUsed.set(dir, new Set([...src.matchAll(/([\w+-]+)\.jpe?g\b/gi)].map(m => m[1].toLowerCase())));
}

// Duplicates: same original name (ignoring our NN_/NNa_/zz_ prefixes) or identical bytes.
const baseName = t => t.replace(/^zz_не использовано_/, "").replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, "").toLowerCase();
// A photo-story chapter names its photos: a file whose name appears there, in its own chapter folder, is used.
const chapterDirs = fs.readdirSync(tripDir).filter(d => fs.existsSync(path.join(tripDir, d, "index.md")))
  .map(d => ({ d, w: +((fs.readFileSync(path.join(tripDir, d, "index.md"), "utf8").match(/^weight:\s*(\d+)/m) || [])[1] || 0) }))
  .sort((a, b) => a.w - b.w).map(x => x.d);
const chapterFolders = [...new Set(files.map(f => f.rel.split("/")[0]))].filter(n => /^\d+ - /.test(n)).sort();
for (const f of files) {
  const dir = chapterDirs[chapterFolders.indexOf(f.rel.split("/")[0])];
  if (!used.has(f.id) && f.rel.split("/").length === 2 && dir && (namesUsed.get(dir) || new Set()).has(baseName(f.title))) used.set(f.id, dir);
}
const hashOf = f => crypto.createHash("sha256").update(fs.readFileSync(path.join(DRIVE_ROOT, path.dirname(path.join(tripRel(), f.rel)), f.title))).digest("hex");
function tripRel() {
  for (const cont of fs.readdirSync(DRIVE_ROOT)) if (fs.existsSync(path.join(DRIVE_ROOT, cont, driveTrip))) return path.join(cont, driveTrip);
  return driveTrip;
}
const groups = new Map();
for (const f of files) {
  const k = baseName(f.title);
  if (!groups.has(k)) groups.set(k, []);
  groups.get(k).push(f);
}
const bySize = new Map();
for (const f of files) { if (!bySize.has(f.size)) bySize.set(f.size, []); bySize.get(f.size).push(f); }
for (const same of bySize.values()) {
  if (same.length < 2) continue;
  const byHash = new Map();
  for (const f of same) { const h = hashOf(f); if (!byHash.has(h)) byHash.set(h, []); byHash.get(h).push(f); }
  for (const g of byHash.values()) if (g.length > 1 && new Set(g.map(f => baseName(f.title))).size > 1) groups.set("bytes:" + g[0].id, g);
}

// Report.
const chapterOf = f => f.rel.split("/")[0];
// zz_не использовано_ files were set aside on purpose earlier, they are not new
const fresh = files.filter(f => !used.has(f.id) && !/^zz_/.test(f.title));
const report = {};
for (const f of fresh) (report[chapterOf(f)] = report[chapterOf(f)] || []).push(f);

console.log(`Поездка: ${driveTrip}. Фото на Диске: ${files.length}, на сайте: ${files.filter(f => used.has(f.id)).length}, отложено (zz_): ${files.filter(f => /^zz_/.test(f.title)).length}, новых: ${fresh.length}.`);
for (const [ch, list] of Object.entries(report).sort()) {
  console.log(`\n== ${ch}: новых ${list.length}`);
  for (const f of list) {
    const dupOf = (groups.get(baseName(f.title)) || []).concat([...groups.values()].filter(g => g.includes(f)).flat())
      .filter(g => g.id !== f.id);
    const sub = f.rel.split("/").length > 2 ? "  [подпапка " + path.dirname(f.rel).split("/").slice(1).join("/") + "]" : "";
    const dupText = dupOf.length ? "  ДУБЛЬ: " + [...new Set(dupOf.map(d => d.rel + (used.has(d.id) ? " (на сайте: " + used.get(d.id) + ")" : "")))].join("; ") : "";
    console.log(`  ${f.title}  ${f.id}${sub}${dupText}`);
  }
}
const dupUsed = [...groups.values()].filter(g => g.length > 1 && g.filter(f => used.has(f.id)).length > 1);
if (dupUsed.length) {
  console.log("\n== Одно и то же фото стоит на сайте дважды:");
  for (const g of dupUsed) console.log("  " + g.filter(f => used.has(f.id)).map(f => f.rel + " → " + used.get(f.id)).join("  |  "));
}
db.close();
try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
