// Matches published photos (e.g. Facebook copies, fingerprinted in the browser) to originals
// fingerprinted by scripts/fingerprint-photos.cjs. Both fingerprints are 64×64 grayscale with the
// aspect ratio ignored; originals are tried in all four rotations because EXIF rotation may or may
// not have been applied. Similarity is the correlation of 16×16 block averages.
//
// Usage: node scripts/match-photos.cjs <published.json> <originals-fp.json> <out.json>
//   published.json: { "<post key>": [ { i, type: "photo"|"video", w, h, g (base64), caption }, ... ], ... }
// Writes, per post, every published item with its best original, score and runner-up, and prints a summary.
const fs = require("fs");
const path = require("path");

const [pubFile, origFile, outFile] = process.argv.slice(2);
const published = JSON.parse(fs.readFileSync(pubFile, "utf8"));
const originals = JSON.parse(fs.readFileSync(origFile, "utf8"));

const N = 64, B = 16, S = N / B;
const decode = b64 => Uint8Array.from(Buffer.from(b64, "base64"));
const rotate = g => { const r = new Uint8Array(N * N); for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) r[x * N + (N - 1 - y)] = g[y * N + x]; return r; };
const blocks = g => {
  const v = new Float64Array(B * B);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) v[((y / S) | 0) * B + ((x / S) | 0)] += g[y * N + x];
  let m = 0; for (const a of v) m += a; m /= v.length;
  let s = 0; for (let i = 0; i < v.length; i++) { v[i] -= m; s += v[i] * v[i]; }
  s = Math.sqrt(s) || 1; for (let i = 0; i < v.length; i++) v[i] /= s;
  return v;
};
const corr = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };

// Each original in four rotations. ffmpeg applies EXIF rotation to the pixels but ffprobe reports
// the stored size, so the aspect ratio is compared without regard to orientation (long/short side).
const shape = (w, h) => Math.max(w, h) / Math.min(w, h);
const orig = Object.entries(originals).map(([file, o]) => {
  let g = decode(o.g); const rots = [];
  for (let r = 0; r < 4; r++) { rots.push({ r: r * 90, v: blocks(g), aspect: shape(o.w, o.h) }); g = rotate(g); }
  return { file, rots };
});

const out = {}; const used = new Map();
for (const [post, items] of Object.entries(published)) {
  out[post] = items.map(item => {
    if (item.type !== "photo" || !item.g) return { i: item.i, type: item.type, caption: item.caption || "", err: item.err };
    const v = blocks(decode(item.g)); const aspect = shape(item.w, item.h);
    const scored = orig.map(o => {
      let best = { s: -2 };
      for (const rot of o.rots) {
        const s = corr(v, rot.v) - (Math.abs(Math.log(rot.aspect / aspect)) > 0.03 ? 0.15 : 0);  // aspect mismatch: likely a different shot
        if (s > best.s) best = { s, r: rot.r };
      }
      return { file: o.file, ...best };
    }).sort((a, b) => b.s - a.s);
    const [m, second] = scored;
    const res = { i: item.i, type: "photo", caption: item.caption || "", w: item.w, h: item.h,
      file: m.file, score: +m.s.toFixed(4), rotation: m.r, runnerUp: second.file, runnerUpScore: +second.s.toFixed(4) };
    (used.get(m.file) || used.set(m.file, []).get(m.file)).push(`${post}#${item.i}`);
    return res;
  });
}
for (const list of Object.values(out)) for (const r of list)
  if (r.file && used.get(r.file).length > 1) r.sharedWith = used.get(r.file);
fs.writeFileSync(outFile, JSON.stringify(out, null, 1));

for (const [post, list] of Object.entries(out)) {
  const photos = list.filter(r => r.type === "photo");
  const sure = photos.filter(r => r.score >= 0.9 && r.score - r.runnerUpScore >= 0.03 && !r.sharedWith).length;
  console.log(`${post}: ${list.length} items, ${photos.length} photos, ${sure} sure, ${photos.length - sure} to check, ` +
    `${list.length - photos.length} video, captions: ${list.filter(r => r.caption && r.caption !== "?").length}`);
}
