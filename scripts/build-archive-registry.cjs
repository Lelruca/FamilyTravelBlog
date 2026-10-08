// Builds the archive registry of a trip that is already on R2 (NEW_TRIPS_WORKFLOW.md, «Обязательная последовательность»):
//   archive — every image in the trip's Drive folder: path, bytes, SHA-256, size, which site photos use it;
//   r2      — every screen copy the site shows: R2 key, size, bytes, SHA-256 of the public file, the archive original it
//             was made from (with its SHA-256), plus a verification baseline for scripts/verify-r2-migration.cjs.
// Writes both to media-manifests/<trip>.json and to photo-manifest.json in the trip's Drive folder, keeping what
// those files already hold (older sections are left untouched; a top-level array is kept as `photos`).
//
// Usage: node scripts/build-archive-registry.cjs <content trip dir> "<Drive trip folder, relative to the archive root>"
//   e.g. node scripts/build-archive-registry.cjs content/europe/portugal/portugal-spain-2016 "Europe/2016 - Португалия-Испания"
// Needs: Google Drive for desktop on G:, ffprobe, and a fresh production build in public/ (npm run build).
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

const [tripDir, driveRel] = process.argv.slice(2);
if (!tripDir || !driveRel) { console.error("Usage: node scripts/build-archive-registry.cjs <content trip dir> \"<Drive trip folder>\""); process.exit(1); }
const DRIVE_ROOT = "G:/My Drive/Family Travel Blog Photos";
const PUBLIC_BASE = "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/";
const LONG_SIDE = 2000;
const slug = path.basename(tripDir);
const driveDir = path.join(DRIVE_ROOT, driveRel);
const IMAGE = /\.(jpe?g|png|heic|webp|gif|tiff?)$/i;

const sha256 = buf => crypto.createHash("sha256").update(buf).digest("hex");
const hashFile = file => new Promise((resolve, reject) => {
  const h = crypto.createHash("sha256");
  fs.createReadStream(file).on("data", d => h.update(d)).on("error", reject).on("end", () => resolve(h.digest("hex")));
});
const dims = input => {
  const args = ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0"];
  const out = typeof input === "string"
    ? execFileSync("ffprobe", [...args, input])
    : execFileSync("ffprobe", [...args, "-i", "pipe:0"], { input });
  const [w, h] = out.toString().trim().split(/\r?\n/)[0].split(",").map(Number);
  return { w, h };
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const mapLimit = async (items, n, fn) => {
  const queue = items.slice(); const out = [];
  await Promise.all(Array.from({ length: n }, async () => { while (queue.length) { const it = queue.shift(); out.push(await fn(it)); } }));
  return out;
};

(async () => {
  const registry = JSON.parse(fs.readFileSync(path.join("data", "photos", slug + ".json"), "utf8"));
  const siteKeys = Object.keys(registry);
  // Where `source` is not an archive path (e.g. "owner-selected: …" or an old URL), take the archive file recorded
  // for that copy in the existing project registry.
  const projectFile = path.join("media-manifests", slug + ".json");
  const known = new Map(((fs.existsSync(projectFile) && JSON.parse(fs.readFileSync(projectFile, "utf8")).r2 || {}).photos || [])
    .map(p => [p.key.replace(`${slug}/`, ""), p.archiveFile]));
  for (const k of siteKeys) {
    const src = registry[k].source || "";
    if ((/^https?:|^[a-z-]+: /i.test(src) || !src.includes("/")) && known.get(k)) registry[k] = { ...registry[k], source: known.get(k) };
  }
  const bySource = new Map();
  for (const k of siteKeys) {
    const src = registry[k].source;
    if (!bySource.has(src)) bySource.set(src, []);
    bySource.get(src).push(k);
  }

  // 1. archive: every image in the chapter folders, plus a separate trip cover kept at the trip folder root
  const files = fs.readdirSync(driveDir).filter(f => IMAGE.test(f) && fs.statSync(path.join(driveDir, f)).isFile()).sort();
  for (const ch of fs.readdirSync(driveDir, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name).sort())
    for (const f of fs.readdirSync(path.join(driveDir, ch)).sort())
      if (IMAGE.test(f)) files.push(`${ch}/${f}`);
  let n = 0;
  const archive = await mapLimit(files, 4, async rel => {
    const full = path.join(driveDir, rel);
    const entry = { archiveFile: rel, bytes: fs.statSync(full).size, sha256: await hashFile(full), ...dims(full) };
    entry.width = entry.w; entry.height = entry.h; delete entry.w; delete entry.h;
    if (/^zz_/.test(path.basename(rel))) entry.unused = true;
    const used = bySource.get(rel); if (used) entry.siteKeys = used;
    if (++n % 50 === 0) console.log(`  archive ${n}/${files.length}`);
    return entry;
  });
  archive.sort((a, b) => a.archiveFile.localeCompare(b.archiveFile));
  const archiveBy = new Map(archive.map(a => [a.archiveFile, a]));
  const missingOriginals = siteKeys.filter(k => !archiveBy.has(registry[k].source));
  console.log(`archive: ${archive.length} images, ${archive.filter(a => a.unused).length} unused, missing originals for site photos: ${missingOriginals.length}`);

  // 2. r2: download every public copy, hash it, check its size against the site registry
  const r2 = [], problems = [];
  n = 0;
  for (const key of siteKeys) {
    const url = PUBLIC_BASE + slug + "/" + key.split("/").map(encodeURIComponent).join("/");
    let res;
    for (let attempt = 0; attempt < 8; attempt++) {
      res = await fetch(url).catch(() => null);
      if (res && res.status === 429) { await sleep(1500 * (attempt + 1)); continue; }
      break;
    }
    if (!res || !res.ok || !/^image\//.test(res.headers.get("content-type") || "")) { problems.push(`${res ? res.status : "ERR"} ${key}`); continue; }
    const buf = Buffer.from(await res.arrayBuffer());
    const { w, h } = dims(buf);
    const info = registry[key];
    if (w !== info.w || h !== info.h) problems.push(`size ${w}x${h} vs registry ${info.w}x${info.h}: ${key}`);
    if (Math.max(w, h) > LONG_SIDE) problems.push(`over ${LONG_SIDE} px: ${key}`);
    const [chapter, ...rest] = key.split("/");
    const orig = archiveBy.get(info.source);
    r2.push({ key: `${slug}/${key}`, slug: chapter, filename: rest.join("/"), archiveFile: info.source, originalSha256: orig ? orig.sha256 : null,
      w, h, bytes: buf.length, sha256: sha256(buf), url, ...(info.rotate ? { rotate: info.rotate } : {}) });
    if (++n % 50 === 0) console.log(`  r2 ${n}/${siteKeys.length}`);
    await sleep(40);
  }
  console.log(`r2: ${r2.length} copies verified, problems: ${problems.length}`);

  // 3. verification baseline from the production build (same rules as scripts/verify-r2-migration.cjs)
  const visibleText = t => t.replace(/<[^>]*>/g, "").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&nbsp;/g, "\u00a0").replace(/&hellip;/g, "…").replace(/[ \t\r\n\f]+/g, " ").trim();
  const imgs = html => [...html.matchAll(/<img\b[^>]*\bsrc=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m => m[1] || m[2] || m[3]);
  const route = tripDir.replace(/^content\//, "").replace(/\\/g, "/");
  const chapters = [];
  for (const ch of fs.readdirSync(tripDir).filter(d => fs.existsSync(path.join(tripDir, d, "index.md"))).sort()) {
    const file = `content/${route}/${ch}/index.md`;
    const html = fs.readFileSync(path.join("public", route, ch, "index.html"), "utf8");
    const article = html.match(/<article class=(?:"photo-essay"|photo-essay)>([\s\S]*?)<\/article>/)?.[1];
    const body = html.match(/<div class=(?:"essay-body"|essay-body)>([\s\S]*?)<\/div>\s*<nav/)?.[1];
    if (!article || !body) { problems.push(`no photo-story layout in build: ${ch}`); continue; }
    const prefix = PUBLIC_BASE + slug + "/";
    const srcs = imgs(article);
    const notR2 = srcs.filter(s => !s.startsWith(prefix));
    if (notR2.length) problems.push(`not on R2 in ${ch}: ${notR2.join(", ")}`);
    chapters.push({ slug: ch, file, route: `${route}/${ch}`,
      mdSha256: sha256(fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n")),
      keys: srcs.filter(s => s.startsWith(prefix)).map(s => s.slice(prefix.length)),
      paragraphHashes: [...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m => sha256(visibleText(m[1]))) });
  }
  const cover = (fs.readFileSync(path.join(tripDir, "_index.md"), "utf8").match(/^cover_image:\s*"([^"]+)"/m) || [])[1] || "";
  const coverKey = cover.startsWith(PUBLIC_BASE + slug + "/") ? cover.slice((PUBLIC_BASE + slug + "/").length) : null;
  if (!coverKey) problems.push(`trip cover is not an R2 copy of this trip: ${cover}`);

  if (missingOriginals.length || problems.length) {
    console.error("NOT WRITTEN — fix first:\n" + [...missingOriginals.map(k => `no archive original: ${k}`), ...problems].join("\n"));
    process.exit(1);
  }

  const now = new Date().toISOString();
  const archiveSection = { folder: driveRel, scannedAt: now, images: archive.length, unused: archive.filter(a => a.unused).length,
    bytes: archive.reduce((s, a) => s + a.bytes, 0), files: archive };
  const r2Section = { bucket: "family-travel-photos", publicBase: PUBLIC_BASE, longSideLimit: LONG_SIDE,
    preparedFrom: "Archived originals (archiveFile); EXIF rotation applied; no upscaling.", verifiedAt: now,
    // coverKey is compared with photo.key ("<trip>/<chapter>/<file>") by verify-r2-migration.cjs
    photos: r2, verification: { tripRoute: route, coverKey: `${slug}/${coverKey}`, chapters } };

  const merge = (file, title) => {
    let doc = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : { trip: title };
    if (Array.isArray(doc)) doc = { trip: title, photos: doc };
    // fields of an older r2 section that this run does not produce are kept
    doc.archive = archiveSection; doc.r2 = { ...(doc.r2 || {}), ...r2Section };
    fs.writeFileSync(file, JSON.stringify(doc, null, 2) + "\n");
  };
  const title = (fs.readFileSync(path.join(tripDir, "_index.md"), "utf8").match(/^title:\s*"(.*)"\s*$/m) || [])[1] || slug;
  merge(path.join("media-manifests", slug + ".json"), title);
  merge(path.join(driveDir, "photo-manifest.json"), title);
  console.log(`written: media-manifests/${slug}.json and ${driveRel}/photo-manifest.json — ${archive.length} originals, ${r2.length} R2 copies, ${chapters.length} chapters`);
})().catch(e => { console.error(e); process.exit(1); });
