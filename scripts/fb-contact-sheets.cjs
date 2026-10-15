// Numbered contact sheets of a trip's chapters (screen copies in static/r2/<trip>/<chapter>/), one image per
// chapter, photo numbers as in the post — to choose covers and check the layout by eye.
// Usage: node scripts/fb-contact-sheets.cjs <trip> <out dir>
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const [trip, out] = process.argv.slice(2);
const m = JSON.parse(fs.readFileSync(`media-manifests/${trip}.json`, "utf8"));
const dn = a => path.basename(a).replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");
fs.mkdirSync(out, { recursive: true });
const font = path.join(out, "f.ttf");
if (!fs.existsSync(font)) fs.copyFileSync("C:/Windows/Fonts/arialbd.ttf", font);
const fontArg = font.split(path.sep).join("/");
for (const ch of m.chapters) {
  const ps = m.photos.filter(p => p.chapter === ch.slug);
  const tiles = path.join(out, ch.slug);
  fs.rmSync(tiles, { recursive: true, force: true });
  fs.mkdirSync(tiles);
  ps.forEach((p, i) => execFileSync("ffmpeg", ["-v", "error", "-y", "-i", `static/r2/${trip}/${ch.slug}/${dn(p.archive_name)}`, "-vf",
    `scale=300:300:force_original_aspect_ratio=decrease,pad=300:300:(ow-iw)/2:(oh-ih)/2,drawtext=fontfile=${fontArg}:text=${p.source_position}:x=8:y=8:fontsize=40:fontcolor=yellow:box=1:boxcolor=black@0.6`,
    "-frames:v", "1", path.join(tiles, `${String(i).padStart(3, "0")}.jpg`)]));
  const files = ps.map((_, i) => path.join(tiles, `${String(i).padStart(3, "0")}.jpg`));
  const lay = files.map((_, i) => `${(i % 6) * 300}_${Math.floor(i / 6) * 300}`).join("|");
  execFileSync("ffmpeg", ["-v", "error", "-y", ...files.flatMap(f => ["-i", f]), "-filter_complex",
    files.length > 1 ? `${files.map((_, i) => `[${i}]`).join("")}xstack=inputs=${files.length}:layout=${lay}:fill=gray` : "[0]null",
    "-frames:v", "1", path.join(out, `${ch.slug}.jpg`)]);
  console.log(ch.slug, ps.length);
}
