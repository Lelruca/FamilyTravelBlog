// Makes the screen-quality copies the site shows (layer 3 in DESIGN_PHOTOS / photo storage plan):
// originals stay on Google Drive; copies (2000 px on the long side, correct rotation) go to
// static/r2/<trip>/<chapter>/<original name>.jpg — the same paths they will have on Cloudflare R2.
// Also writes data/photos/<trip>.json with each photo's size, so rows are laid out at build time.
//
// Usage: node scripts/make-display-copies.cjs <content trip dir> "<Drive trip folder>" [chapter-slug ...]
//   e.g. node scripts/make-display-copies.cjs content/europe/portugal/portugal-spain-2016 "2016 - Португалия-Испания" belem
// Drive chapter folders "NN - Name" are matched to chapters by their order (weight).
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const [tripDir, driveTrip, ...only] = process.argv.slice(2);
const DRIVE_ROOT = "G:/My Drive/Family Travel Blog Photos";
const LONG_SIDE = 2000;

const tripSlug = path.basename(tripDir);
const continent = fs.readdirSync(DRIVE_ROOT).find(c => fs.existsSync(path.join(DRIVE_ROOT, c, driveTrip)));
const driveDir = path.join(DRIVE_ROOT, continent, driveTrip);

// Chapters in reading order.
const chapters = fs.readdirSync(tripDir)
  .filter(d => fs.existsSync(path.join(tripDir, d, "index.md")))
  .map(d => ({ slug: d, weight: +((fs.readFileSync(path.join(tripDir, d, "index.md"), "utf8").match(/^weight:\s*(\d+)/m) || [])[1] || 0) }))
  .sort((a, b) => a.weight - b.weight)
  // chapters without any photo (e.g. a short conclusion) have no Drive folder
  .filter(c => /(?:[?&]id=[\w-]{20}|\.jpg\b|photoscroller|essay-photo)/i.test(fs.readFileSync(path.join(tripDir, c.slug, "index.md"), "utf8")));
const folders = fs.readdirSync(driveDir).filter(d => /^\d+ - /.test(d)).sort();
if (folders.length !== chapters.length) {
  console.error(`Folders (${folders.length}) and chapters (${chapters.length}) do not match`);
  process.exit(1);
}

// Our archive prefixes (NN_, NNa_) are not part of the photo's name on the site.
const displayName = f => f.replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");
const probe = file => execFileSync("ffprobe", ["-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", file]).toString().trim().split(",").map(Number);

const dataFile = path.join("data", "photos", tripSlug + ".json");
// Scans without rotation info: data/photos/<trip>.rotate.json, e.g. { "virginia-beach-2/We.jpg": 90 } (degrees clockwise)
const rotateFile = path.join("data", "photos", tripSlug + ".rotate.json");
const rotate = fs.existsSync(rotateFile) ? JSON.parse(fs.readFileSync(rotateFile, "utf8")) : {};
const turn = { 90: ",transpose=1", 180: ",transpose=1,transpose=1", 270: ",transpose=2" };
const data = fs.existsSync(dataFile) ? JSON.parse(fs.readFileSync(dataFile, "utf8")) : {};
let made = 0, kept = 0;
folders.forEach((folder, i) => {
  const ch = chapters[i].slug;
  if (only.length && !only.includes(ch)) return;
  const outDir = path.join("static", "r2", tripSlug, ch);
  fs.mkdirSync(outDir, { recursive: true });
  for (const f of fs.readdirSync(path.join(driveDir, folder))) {
    if (!/\.(jpe?g|png|heic|webp)$/i.test(f) || /^zz_/.test(f)) continue;
    const src = path.join(driveDir, folder, f);
    const name = displayName(f);
    const out = path.join(outDir, name);
    const rot = rotate[`${ch}/${name}`] || 0;
    const stale = !fs.existsSync(out) || fs.statSync(out).mtimeMs < fs.statSync(src).mtimeMs || (data[`${ch}/${name}`] || {}).rotate !== (rot || undefined);
    if (stale) {
      // ffmpeg applies the EXIF rotation; scale the long side down to 2000 px (never up)
      execFileSync("ffmpeg", ["-v", "error", "-y", "-i", src, "-vf",
        `scale='if(gt(iw,ih),min(${LONG_SIDE},iw),-2)':'if(gt(iw,ih),-2,min(${LONG_SIDE},ih))'${turn[rot] || ""}`, "-q:v", "3", out]);
      made++;
    } else kept++;
    const [w, h] = probe(out);
    data[`${ch}/${name}`] = { w, h, source: `${folder}/${f}`, ...(rot ? { rotate: rot } : {}) };
  }
});
fs.mkdirSync(path.dirname(dataFile), { recursive: true });
fs.writeFileSync(dataFile, JSON.stringify(Object.fromEntries(Object.entries(data).sort()), null, 1) + "\n");
console.log(`Copies made: ${made}, already up to date: ${kept}. Sizes: ${dataFile}`);
