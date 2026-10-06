// Uploads screen-quality photo copies from static/r2/ to Cloudflare R2 (bucket family-travel-photos),
// the place the published site shows photos from. Needs a one-time `npx wrangler login` on this PC.
//
// Usage: node scripts/upload-to-r2.cjs <trip-slug> [chapter-slug ...]
//   e.g. node scripts/upload-to-r2.cjs portugal-spain-2016 sintra
// Only files that are new or changed since the last upload are sent (tracked in static/r2/.uploaded.json).
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const BUCKET = "family-travel-photos";
const PARALLEL = 8;
const [trip, ...chapters] = process.argv.slice(2);
if (!trip) { console.error("Usage: node scripts/upload-to-r2.cjs <trip-slug> [chapter-slug ...]"); process.exit(1); }

const root = path.join("static", "r2");
const stateFile = path.join(root, ".uploaded.json");
const state = fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, "utf8")) : {};
const keys = [];
for (const ch of chapters.length ? chapters : fs.readdirSync(path.join(root, trip))) {
  const dir = path.join(root, trip, ch);
  for (const f of fs.readdirSync(dir)) {
    const key = `${trip}/${ch}/${f}`;
    const st = fs.statSync(path.join(dir, f));
    if (state[key] !== `${st.size}:${Math.round(st.mtimeMs)}`) keys.push(key);
  }
}
const type = k => /\.mp4$/i.test(k) ? "video/mp4" : "image/jpeg";
let done = 0, failed = [];
const put = key => new Promise(resolve => {
  // shell: true (npx on Windows) joins arguments unescaped, so values with spaces or brackets are quoted
  execFile("npx", ["-y", "wrangler@4", "r2", "object", "put", `"${BUCKET}/${key}"`, "--file", `"${path.join(root, key)}"`,
    "--content-type", type(key), "--cache-control", '"public, max-age=31536000, immutable"', "--remote"],
    { shell: true }, err => {
      if (err) failed.push(key);
      else { const st = fs.statSync(path.join(root, key)); state[key] = `${st.size}:${Math.round(st.mtimeMs)}`; done++; }
      resolve();
    });
});
(async () => {
  const queue = keys.slice();
  await Promise.all(Array.from({ length: PARALLEL }, async () => { while (queue.length) await put(queue.shift()); }));
  fs.writeFileSync(stateFile, JSON.stringify(state, null, 1) + "\n");
  console.log(`Uploaded ${done}, failed ${failed.length}, unchanged ${Object.keys(state).length - done}.`);
  if (failed.length) { console.log(failed.join("\n")); process.exit(1); }
})();
