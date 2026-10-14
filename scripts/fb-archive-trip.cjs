// Takes one trip out of a Facebook "Download your information" archive (JSON format) of a Page or profile:
// the posts' texts verbatim, their photos in the post order with the author's per-photo captions, EXIF data
// Facebook kept (time taken, camera, original size) and a fingerprint of every photo for matching originals.
// Nothing here is specific to this site: the output is plain JSON for the next steps
// (scripts/match-photos.cjs, scripts/archive-fb-trip.cjs).
//
// Usage: node scripts/fb-archive-trip.cjs <archive dir> <out dir> <post numbers>
//   <archive dir>: the unpacked archive (the folder that holds "this_profile's_activity_across_facebook"
//                  or "your_facebook_activity").
//   <post numbers>: positions of the posts in the archive sorted from oldest to newest, e.g. "1-9" or "24-33,35".
//                   `node scripts/fb-archive-trip.cjs <archive dir> --list` prints that numbered list.
// Writes in <out dir>: posts.json (feedOrder, date, text, sha256), media.json ({ media: { key: [items] }, sets }),
// published.json (fingerprints in the format scripts/match-photos.cjs reads).
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFile } = require("child_process");

const [root, outDir, spec] = process.argv.slice(2);

// Facebook writes UTF-8 text as if every byte were a Latin-1 character.
const fix = s => typeof s === "string" ? Buffer.from(s, "latin1").toString("utf8") : s;
const sha = t => crypto.createHash("sha256").update(t, "utf8").digest("hex");

const postsDir = ["this_profile's_activity_across_facebook/posts", "your_facebook_activity/posts"]
  .map(p => path.join(root, p)).find(p => fs.existsSync(p));
if (!postsDir) throw new Error(`No posts folder in ${root}`);
const all = fs.readdirSync(postsDir).filter(f => /^(profile_posts|your_posts)_\d+\.json$/.test(f))
  .flatMap(f => JSON.parse(fs.readFileSync(path.join(postsDir, f), "utf8")))
  .sort((a, b) => a.timestamp - b.timestamp);

const textOf = p => fix(((p.data || []).find(x => x.post) || {}).post || "");
const mediaOf = p => (p.attachments || []).flatMap(a => (a.data || []).map(x => x.media).filter(Boolean));
const day = t => new Date(t * 1000).toISOString().slice(0, 10);

if (outDir === "--list") {
  all.forEach((p, i) => console.log(`${i + 1}\t${day(p.timestamp)}\t${mediaOf(p).length}\t${textOf(p).replace(/\s+/g, " ").slice(0, 90)}`));
  process.exit(0);
}

const numbers = spec.split(",").flatMap(r => {
  const [a, b = a] = r.split("-").map(Number);
  return Array.from({ length: b - a + 1 }, (_, k) => a + k);
});

const gray = file => new Promise((resolve, reject) =>
  execFile("ffmpeg", ["-v", "error", "-i", file, "-vf", "scale=64:64:flags=area,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
    { encoding: "buffer", maxBuffer: 1 << 20 }, (err, stdout) => err ? reject(err) : resolve(stdout)));
const size = file => new Promise((resolve, reject) =>
  execFile("ffprobe", ["-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", file],
    (err, stdout) => err ? reject(err) : resolve(stdout.trim().split(",").map(Number))));

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const posts = [], media = { media: {}, sets: {} }, published = {};
  for (const n of numbers) {
    const p = all[n - 1];
    const key = `p${String(n).padStart(3, "0")}`;
    const text = textOf(p);
    posts.push({ feedOrder: n, key, date: day(p.timestamp), timestamp: p.timestamp, text, sha256: sha(text) });
    media.sets[key] = null;
    media.media[key] = [];
    published[key] = [];
    for (const [i, m] of mediaOf(p).entries()) {
      const file = path.join(root, m.uri);
      const exif = ((m.media_metadata || {}).photo_metadata || {}).exif_data?.[0] || {};
      const isVideo = /\.(mp4|mov)$/i.test(m.uri);
      const id = path.basename(m.uri).replace(/\.\w+$/, "");
      const item = {
        i, type: isVideo ? "video" : "photo", id: isVideo ? `v${id}` : id, copy: file,
        caption: fix(m.description || ""),
        taken: exif.taken_timestamp || null, camera: [exif.camera_make, exif.camera_model].filter(Boolean).join(" ") || null,
        original_size: exif.original_width ? [exif.original_width, exif.original_height] : null,
      };
      media.media[key].push(item);
      const pub = { i, type: item.type, caption: item.caption };
      if (!isVideo) {
        const [buf, [w, h]] = await Promise.all([gray(file), size(file)]);
        Object.assign(pub, { w, h, g: buf.toString("base64") });
      }
      published[key].push(pub);
    }
    console.log(`#${n} ${day(p.timestamp)}: ${media.media[key].length} items, ${text.length} chars`);
  }
  const write = (f, v) => fs.writeFileSync(path.join(outDir, f), JSON.stringify(v, null, 1) + "\n");
  write("posts.json", posts);
  write("media.json", media);
  write("published.json", published);
})();
