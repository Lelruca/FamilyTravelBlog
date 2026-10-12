// Checks a built trip imported from Facebook against its sources:
// - every chapter shows the post's paragraphs verbatim and in order (hashtag-only lines are service tags, not shown);
// - every archived photo is shown exactly once in its chapter (cover included), each from R2, none from Drive;
// - the author's photo captions are on the page, verbatim.
//
// Usage: node scripts/verify-fb-trip.cjs <built site dir> <content trip dir> <fb-posts.json> <trip-config.json>
const fs = require("fs");
const path = require("path");

const [site, tripDir, postsFile, cfgFile] = process.argv.slice(2);
const cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
const posts = JSON.parse(fs.readFileSync(postsFile, "utf8"));
const manifest = JSON.parse(fs.readFileSync(path.join("media-manifests", cfg.trip + ".json"), "utf8"));
const base = (fs.readFileSync("hugo.prod.yaml", "utf8").match(/photoBase:\s*["']?([^"'\s]+)/) || [])[1];
const urlPath = tripDir.replace(/^content\//, "");
const decode = s => s.replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
  .replace(/&quot;/g, '"').replace(/&#34;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&nbsp;/g, " ");
const displayName = a => path.basename(a).replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");

let problems = 0, paragraphs = 0, photos = 0, captions = 0;
const fail = m => { problems++; console.log("  ✗ " + m); };
for (const ch of cfg.chapters) {
  const slug = manifest.chapters.find(c => c.originals_folder === ch.folder).slug;
  const html = fs.readFileSync(path.join(site, urlPath, slug, "index.html"), "utf8");
  const body = html.slice(html.indexOf('class="essay-body"'), html.indexOf('class="essay-navigation"'));
  // text
  const want = posts.find(p => p.feedOrder === ch.feedOrder).text.split("\n").filter(l => !/^\s*(#\S+\s*)+$/.test(l));
  const got = [...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m => decode(m[1]));
  if (got.length !== want.length) fail(`${slug}: ${got.length} paragraphs on the page, ${want.length} in the post`);
  want.forEach((p, i) => { if (got[i] !== p) fail(`${slug}: paragraph ${i + 1} differs:\n      post: ${JSON.stringify(p.slice(0, 80))}\n      page: ${JSON.stringify((got[i] || "").slice(0, 80))}`); });
  paragraphs += want.length;
  // photos: the cover and every photo link of the chapter
  const header = html.slice(html.indexOf('class="essay-header"'), html.indexOf('class="essay-body"'));
  const shown = [...(header + body).matchAll(/href="([^"]+\.jpg)"[^>]*data-photo-lightbox/g)].map(m => m[1]);
  const urls = [...(header + body).matchAll(/(?:src|href)="([^"]+)"/g)].map(m => m[1]);
  if (urls.some(u => /drive\.google|googleusercontent/.test(u))) fail(`${slug}: a Drive/Google photo URL on the page`);
  const notR2 = shown.filter(u => !u.startsWith(base)); if (notR2.length) fail(`${slug}: not from R2: ${notR2.slice(0, 3).join(" ")}`);
  const names = shown.map(u => decodeURIComponent(u.split("/").pop()));
  const expected = manifest.photos.filter(p => p.chapter === slug).map(p => displayName(p.archive_name));
  const missing = expected.filter(n => !names.includes(n)), extra = names.filter(n => !expected.includes(n));
  const twice = names.filter((n, i) => names.indexOf(n) !== i);
  if (missing.length) fail(`${slug}: photos not shown: ${missing.join(" ")}`);
  if (extra.length) fail(`${slug}: photos not in the archive: ${extra.join(" ")}`);
  if (twice.length) fail(`${slug}: photos shown twice: ${twice.join(" ")}`);
  photos += names.length;
  // captions
  for (const p of manifest.photos.filter(p => p.chapter === slug && p.caption)) {
    const attrs = [...html.matchAll(/data-caption="([^"]*)"/g)].map(m => decode(m[1]));
    if (!attrs.includes(p.caption)) fail(`${slug}: caption of ${displayName(p.archive_name)} missing or changed`);
    else captions++;
  }
}
console.log(`${paragraphs} paragraphs, ${photos} photos, ${captions} captions checked; ${problems} problems`);
process.exit(problems ? 1 : 0);
