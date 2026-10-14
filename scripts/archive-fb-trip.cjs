// Builds the Drive archive of a trip imported from Facebook: one folder per chapter (one post),
// files named NN_<original name> in the post's photo order. Each photo is the matched full original
// from OneDrive (scripts/match-photos.cjs); where no original exists, the Facebook copy is archived
// as NN_facebook_<photo id>.jpg and marked as a copy in the manifest (taken from item.copy when the media list
// gives its path, as scripts/fb-archive-trip.cjs does, otherwise from cfg.copiesDir). Copies are verified by SHA-256.
// Writes photo-manifest.json in the trip folder and media-manifests/<trip>.json.
// Re-running is safe: files already archived with the same checksum are left as they are.
//
// Usage: node scripts/archive-fb-trip.cjs <trip-config.json>
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const cfg = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const DRIVE_ROOT = "G:/My Drive/Family Travel Blog Photos";
const tripDir = path.join(DRIVE_ROOT, cfg.continent, cfg.archiveFolder);
const SURE = 0.95;  // fingerprint correlation above which a match is the same photo (see match-photos.cjs)

const read = f => JSON.parse(fs.readFileSync(f, "utf8"));
const posts = read(cfg.posts), media = read(cfg.media), fps = read(cfg.fingerprints), matches = read(cfg.matches);
const sha = f => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
const textSha = t => crypto.createHash("sha256").update(t, "utf8").digest("hex");

// An original belongs to the published photo that matches it best (bursts give near-twins).
const owner = new Map();
for (const [key, list] of Object.entries(matches))
  for (const r of list) if (r.type === "photo" && r.score >= SURE) {
    const o = owner.get(r.file);
    if (!o || r.score > o.score) owner.set(r.file, { key, i: r.i, score: r.score });
  }

const manifest = {
  trip: cfg.trip, title: cfg.title, source: cfg.source,
  archive_root: `${cfg.continent}/${cfg.archiveFolder}`,
  created: new Date().toISOString(),
  match_threshold: SURE,
  chapters: [], photos: [], videos: [],
};

for (const ch of cfg.chapters) {
  const post = posts.find(p => p.feedOrder === ch.feedOrder);
  const items = media.media[ch.key];
  const dir = path.join(tripDir, ch.folder);
  fs.mkdirSync(dir, { recursive: true });
  let n = 0;
  for (const item of items) {
    if (item.type !== "photo") {
      manifest.videos.push({ chapter: ch.slug, source_position: item.i + 1, facebook_id: item.id.replace(/^v/, "") });
      continue;
    }
    const nn = String(++n).padStart(2, "0");
    const m = matches[ch.key][item.i];
    const o = m.file && owner.get(m.file);
    const isOriginal = m.score >= SURE && o && o.key === ch.key && o.i === item.i;
    const src = isOriginal ? m.file
      : item.copy || path.join(cfg.copiesDir, fs.readdirSync(cfg.copiesDir).find(f => f.includes(`_${item.id}.`)) || "missing");
    if (!fs.existsSync(src)) throw new Error(`No source for ${ch.key} #${item.i + 1} (${item.id})`);
    const name = `${nn}_${isOriginal ? path.basename(src) : `facebook_${item.id}.jpg`}`;
    const dst = path.join(dir, name);
    const srcSha = sha(src);
    if (!fs.existsSync(dst) || sha(dst) !== srcSha) fs.copyFileSync(src, dst);
    const dstSha = sha(dst);
    if (dstSha !== srcSha) throw new Error(`Checksum mismatch after copy: ${dst}`);
    manifest.photos.push({
      chapter: ch.slug, position: n, source_position: item.i + 1, facebook_id: item.id,
      caption: fps[ch.key][item.i].caption || "",
      archive_name: `${ch.folder}/${name}`,
      kind: isOriginal ? "original" : "facebook-copy",
      original_relative_path: isOriginal ? path.relative(cfg.originalsRoot, src).split(path.sep).join("/") : null,
      match_score: isOriginal ? m.score : null,
      bytes: fs.statSync(dst).size, sha256: dstSha,
    });
  }
  manifest.chapters.push({
    slug: ch.slug, title: post.text.split("\n")[0].slice(0, 80), originals_folder: ch.folder,
    facebook_set: media.sets[ch.key], post_date: post.date, text_sha256: textSha(post.text),
    photo_count: n, original_count: manifest.photos.filter(p => p.chapter === ch.slug && p.kind === "original").length,
  });
}

// Files in the chapter folders that this run did not place (e.g. the owner's additions) are reported, not touched.
const placed = new Set(manifest.photos.map(p => p.archive_name));
manifest.other_files = cfg.chapters.flatMap(ch =>
  fs.readdirSync(path.join(tripDir, ch.folder)).map(f => `${ch.folder}/${f}`).filter(f => !placed.has(f) && !/desktop\.ini$/i.test(f)));
manifest.archive_verified = true;
manifest.drive_sync_verified = false;

const json = JSON.stringify(manifest, null, 2) + "\n";
fs.writeFileSync(path.join(tripDir, "photo-manifest.json"), json);
fs.writeFileSync(path.join("media-manifests", cfg.trip + ".json"), json);
const copies = manifest.photos.filter(p => p.kind === "facebook-copy").length;
console.log(`${manifest.photos.length} photos archived in ${tripDir}: ${manifest.photos.length - copies} originals, ${copies} Facebook copies; ${manifest.videos.length} videos listed`);
for (const c of manifest.chapters) console.log(`  ${c.originals_folder}: ${c.photo_count} (${c.original_count} originals)`);
if (manifest.other_files.length) console.log("Other files left as they are:", manifest.other_files);
