// Checks that every file of a Drive archive folder has reached the cloud: Google Drive for desktop
// gives a file its real Drive ID once uploaded ("local…" IDs are still pending). Reads a copy of the
// local DriveFS database; changes nothing. With --write, records the IDs in the trip's photo-manifest.json
// and media-manifests/<trip>.json.
//
// Usage: node scripts/check-drive-sync.cjs "<Continent>/<trip folder>" [--write]
const fs = require("fs");
const path = require("path");
const os = require("os");
const { DatabaseSync } = require("node:sqlite");

const [rel, flag] = process.argv.slice(2);
const DRIVE_ROOT = "G:/My Drive/Family Travel Blog Photos";
const fsRoot = path.join(process.env.LOCALAPPDATA, "Google", "DriveFS");
const acct = fs.readdirSync(fsRoot).find(d => fs.existsSync(path.join(fsRoot, d, "metadata_sqlite_db")));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "drivefs-"));
for (const ext of ["", "-wal"]) {
  const src = path.join(fsRoot, acct, "metadata_sqlite_db" + ext);
  if (fs.existsSync(src)) fs.copyFileSync(src, path.join(tmp, "db" + ext));
}
const db = new DatabaseSync(path.join(tmp, "db"));
const children = db.prepare(
  "SELECT i.stable_id, i.id, i.local_title AS title, i.is_folder, i.file_size AS size " +
  "FROM items i JOIN stable_parents p ON p.item_stable_id = i.stable_id " +
  "WHERE p.parent_stable_id = ? AND i.trashed = 0 AND i.is_tombstone = 0");
const root = db.prepare("SELECT stable_id FROM items WHERE local_title = 'Family Travel Blog Photos' AND is_folder = 1 AND trashed = 0").get();

// Walk down the path from "Family Travel Blog Photos".
let node = root;
for (const part of rel.split("/")) {
  node = children.all(node.stable_id).find(c => c.is_folder && c.title === part);
  if (!node) { console.error("Not in DriveFS yet: " + part); process.exit(1); }
}
const ids = {}; let pending = 0, total = 0;
const walk = (stableId, prefix) => {
  for (const it of children.all(stableId)) {
    const r = prefix ? `${prefix}/${it.title}` : it.title;
    if (it.is_folder) { walk(it.stable_id, r); continue; }
    total++; ids[r] = it.id;
    if (String(it.id).startsWith("local")) pending++;
  }
};
walk(node.stable_id, "");

// Every file on disk must be known to DriveFS.
const onDisk = [];
const scan = (d, prefix) => { for (const f of fs.readdirSync(d)) { const p = path.join(d, f), r = prefix ? `${prefix}/${f}` : f;
  if (fs.statSync(p).isDirectory()) scan(p, r); else if (!/desktop\.ini$/i.test(f)) onDisk.push(r); } };
scan(path.join(DRIVE_ROOT, rel), "");
const unknown = onDisk.filter(r => !ids[r]);
console.log(`${total} files in DriveFS, ${pending} still uploading, ${unknown.length} on disk but unknown to DriveFS`);
if (unknown.length) console.log(unknown.slice(0, 10));

if (flag === "--write" && !pending && !unknown.length) {
  const mf = path.join(DRIVE_ROOT, rel, "photo-manifest.json");
  const m = JSON.parse(fs.readFileSync(mf, "utf8"));
  for (const p of m.photos) p.drive_id = ids[p.archive_name];
  m.drive_sync_verified = true;
  m.drive_sync_checked = new Date().toISOString();
  m.drive_trip_folder_id = node.id;
  const json = JSON.stringify(m, null, 2) + "\n";
  fs.writeFileSync(mf, json);
  fs.writeFileSync(path.join("media-manifests", m.trip + ".json"), json);
  console.log("Drive IDs recorded in " + mf);
}
db.close();
fs.rmSync(tmp, { recursive: true, force: true });
