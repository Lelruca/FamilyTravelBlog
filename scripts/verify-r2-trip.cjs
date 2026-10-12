// Checks every screen copy of a trip on the public R2 address (HTTP 200, image type, SHA-256 equal to the
// local copy in static/r2/<trip>/) and records the result in the trip's manifests: section "r2" in
// media-manifests/<trip>.json and in photo-manifest.json of the Drive archive, each copy linked to its original.
//
// Usage: node scripts/verify-r2-trip.cjs <trip-slug> "<Continent>/<Drive trip folder>"
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const [trip, driveRel] = process.argv.slice(2);
const base = (fs.readFileSync("hugo.prod.yaml", "utf8").match(/photoBase:\s*["']?([^"'\s]+)/) || [])[1];
if (!base) throw new Error("photoBase not found in hugo.prod.yaml");
const data = JSON.parse(fs.readFileSync(path.join("data", "photos", trip + ".json"), "utf8"));
const sha = buf => crypto.createHash("sha256").update(buf).digest("hex");

(async () => {
  const entries = Object.entries(data);
  const r2 = []; const bad = [];
  for (let i = 0; i < entries.length; i += 8) {
    await Promise.all(entries.slice(i, i + 8).map(async ([key, info]) => {
      const local = fs.readFileSync(path.join("static", "r2", trip, key));
      const url = `${base.replace(/\/$/, "")}/${trip}/${key.split("/").map(encodeURIComponent).join("/")}`;
      const res = await fetch(url);
      const body = Buffer.from(await res.arrayBuffer());
      const ok = res.status === 200 && /^image\//.test(res.headers.get("content-type") || "") && sha(body) === sha(local);
      if (!ok) bad.push(`${key}: ${res.status} ${res.headers.get("content-type")}`);
      r2.push({ key: `${trip}/${key}`, url, width: info.w, height: info.h, bytes: local.length, sha256: sha(local), archive_name: info.source, verified: ok });
    }));
  }
  r2.sort((a, b) => a.key.localeCompare(b.key));
  console.log(`${r2.length} copies checked on R2, ${bad.length} problems`);
  if (bad.length) { console.log(bad.join("\n")); process.exit(1); }
  const section = { checked: new Date().toISOString(), base, copies: r2 };
  for (const f of [path.join("media-manifests", trip + ".json"), path.join("G:/My Drive/Family Travel Blog Photos", driveRel, "photo-manifest.json")]) {
    const m = JSON.parse(fs.readFileSync(f, "utf8"));
    m.r2 = section; m.r2_verified = true;
    fs.writeFileSync(f, JSON.stringify(m, null, 2) + "\n");
  }
  console.log("Recorded in the project and Drive manifests.");
})();
