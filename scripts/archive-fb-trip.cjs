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
const ownerOf = f => [...owner].find(([k]) => path.resolve(k) === path.resolve(f))?.[1];

const manifest = {
  trip: cfg.trip, title: cfg.title, source: cfg.source,
  archive_root: `${cfg.continent}/${cfg.archiveFolder}`,
  created: new Date().toISOString(),
  match_threshold: SURE,
  chapters: [], photos: [], videos: [], skipped: [],
};

for (const ch of cfg.chapters) {
  const dir = path.join(tripDir, ch.folder);
  fs.mkdirSync(dir, { recursive: true });
  // A chapter without a post (trip-config "originals": [paths]) — photos the owner chose for a part of the trip
  // she has not written about yet; the text is added later. Photos are numbered 1, 2, … in the given order.
  if (ch.originals) {
    ch.originals.forEach((src, k) => {
      const name = `${String(k + 1).padStart(2, "0")}_${path.basename(src)}`;
      const dst = path.join(dir, name);
      const srcSha = sha(src);
      if (!fs.existsSync(dst) || sha(dst) !== srcSha) fs.copyFileSync(src, dst);
      if (sha(dst) !== srcSha) throw new Error(`Checksum mismatch after copy: ${dst}`);
      // an original that is also one of a post's Facebook photos keeps that link
      const o = ownerOf(src), item = o && media.media[o.key][o.i];
      manifest.photos.push({
        chapter: ch.slug, position: k + 1, source_position: k + 1, facebook_id: item ? item.id : null,
        caption: item ? fps[o.key][o.i].caption || "" : "",
        ...(item ? { facebook_post: o.key, facebook_position: o.i + 1 } : {}),
        archive_name: `${ch.folder}/${name}`, kind: "original",
        original_relative_path: path.relative(cfg.originalsRoot, src).split(path.sep).join("/"),
        match_score: o ? o.score : null, bytes: fs.statSync(dst).size, sha256: srcSha,
      });
    });
    // trip-config "post": { key, feedOrder, paras } — this chapter shows paragraphs of a post (see gen-fb-trip-pages.cjs)
    manifest.chapters.push({ slug: ch.slug, title: ch.folder.replace(/^\d+ - /, ""), originals_folder: ch.folder,
      without_post: !ch.post, ...(ch.post ? { post: ch.post.key, post_paragraphs: ch.post.paras } : {}),
      photo_count: ch.originals.length, original_count: ch.originals.length });
    continue;
  }
  const post = posts.find(p => p.feedOrder === ch.feedOrder);
  const items = media.media[ch.key];
  let n = 0;
  for (const item of items) {
    // trip-config "skip": { "<photo number>": "why" } — e.g. the same photo posted twice in one post
    const skip = (ch.skip || {})[item.i + 1];
    if (skip) { manifest.skipped.push({ chapter: ch.slug, source_position: item.i + 1, facebook_id: item.id, reason: skip }); continue; }
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
  // trip-config "extra": [paths] — originals the owner asked to add to a post that has too few photos of its own
  // (e.g. only a video); numbered after the post's media, as kind "original" without a Facebook id
  for (const [k, src] of (ch.extra || []).entries()) {
    const nn = String(++n).padStart(2, "0");
    const name = `${nn}_${path.basename(src)}`;
    const dst = path.join(dir, name);
    const srcSha = sha(src);
    if (!fs.existsSync(dst) || sha(dst) !== srcSha) fs.copyFileSync(src, dst);
    if (sha(dst) !== srcSha) throw new Error(`Checksum mismatch after copy: ${dst}`);
    manifest.photos.push({
      chapter: ch.slug, position: n, source_position: items.length + k + 1, facebook_id: null, caption: "",
      archive_name: `${ch.folder}/${name}`, kind: "original", added_by_owner_request: true,
      original_relative_path: path.relative(cfg.originalsRoot, src).split(path.sep).join("/"),
      match_score: null, bytes: fs.statSync(dst).size, sha256: srcSha,
    });
  }
  manifest.chapters.push({
    slug: ch.slug, title: post.text.split("\n")[0].slice(0, 80), originals_folder: ch.folder,
    facebook_set: media.sets[ch.key], post_date: post.date, text_sha256: textSha(post.text),
    photo_count: n, original_count: manifest.photos.filter(p => p.chapter === ch.slug && p.kind === "original").length,
  });
}

// trip-config "cover": { original, note } — a trip cover the owner chose that is not one of the chapters' photos:
// archived in "00 - Обложка" (not a chapter) as manifest.cover.shown, the way north-ontario-2020 keeps its cover.
// Its screen copy and R2 key (<trip>/cover/<name>) are added to manifest.cover.shown.r2 after upload.
if (cfg.cover) {
  const dir = path.join(tripDir, "00 - Обложка"), src = cfg.cover.original;
  fs.mkdirSync(dir, { recursive: true });
  const name = `01_${path.basename(src)}`, dst = path.join(dir, name), srcSha = sha(src);
  if (!fs.existsSync(dst) || sha(dst) !== srcSha) fs.copyFileSync(src, dst);
  if (sha(dst) !== srcSha) throw new Error(`Checksum mismatch after copy: ${dst}`);
  manifest.cover = { shown: { archive_name: `00 - Обложка/${name}`, kind: "original",
    original_relative_path: path.relative(cfg.originalsRoot, src).split(path.sep).join("/"),
    note: cfg.cover.note || "", bytes: fs.statSync(dst).size, sha256: srcSha } };
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
