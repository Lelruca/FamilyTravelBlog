// Takes a small grayscale "fingerprint" (64×64, aspect ignored) of every photo in the given folders,
// so photos published elsewhere (Facebook copies without names) can be matched to their originals.
// Rotation is not applied here; the matcher compares all four rotations.
//
// Usage: node scripts/fingerprint-photos.cjs <out.json> [--from YYYYMMDD] [--to YYYYMMDD] <folder|file> ...
//   --from/--to keep only files whose name starts with a date (20251209_162909.jpg) in that range.
// Re-running resumes: files already in <out.json> are skipped.
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const args = process.argv.slice(2);
const out = args.shift();
let from = null, to = null;
const inputs = [];
while (args.length) {
  const a = args.shift();
  if (a === "--from") from = args.shift();
  else if (a === "--to") to = args.shift();
  else inputs.push(a);
}

const IMAGE = /\.(jpe?g|png|heic|webp)$/i;
const inRange = f => {
  const d = (path.basename(f).match(/^(\d{8})_/) || [])[1];
  if (!d) return !from && !to;
  return (!from || d >= from) && (!to || d <= to);
};
const files = inputs.flatMap(p => fs.statSync(p).isDirectory()
  ? fs.readdirSync(p).filter(f => IMAGE.test(f)).map(f => path.join(p, f))
  : [p]).filter(inRange);

const done = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : {};
const todo = files.filter(f => !done[f]);
console.log(`${files.length} photos, ${todo.length} to fingerprint`);

const gray = file => new Promise((resolve, reject) =>
  execFile("ffmpeg", ["-v", "error", "-i", file, "-vf", "scale=64:64:flags=area,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
    { encoding: "buffer", maxBuffer: 1 << 20 }, (err, stdout) => err ? reject(err) : resolve(stdout)));
const size = file => new Promise((resolve, reject) =>
  execFile("ffprobe", ["-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", file],
    (err, stdout) => err ? reject(err) : resolve(stdout.trim().split(",").map(Number))));

let n = 0, failed = 0;
const save = () => fs.writeFileSync(out, JSON.stringify(done));
async function worker() {
  while (todo.length) {
    const f = todo.shift();
    try {
      const [buf, [w, h]] = await Promise.all([gray(f), size(f)]);
      if (buf.length !== 4096) throw new Error(`got ${buf.length} bytes`);
      done[f] = { w, h, g: buf.toString("base64") };
    } catch (e) {
      failed++;
      console.error(`FAILED ${f}: ${e.message.split("\n")[0]}`);
    }
    if (++n % 50 === 0) { save(); console.log(`${n} done`); }
  }
}
Promise.all(Array.from({ length: 4 }, worker)).then(() => {
  save();
  console.log(`finished: ${Object.keys(done).length} fingerprints, ${failed} failed`);
});
