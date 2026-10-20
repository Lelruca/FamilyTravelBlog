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
  .replace(/&quot;/g, '"').replace(/&#34;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&nbsp;/g, " ")
  .replace(/&#(\d+);/g, (m, n) => String.fromCodePoint(+n)).replace(/&#x([\da-f]+);/gi, (m, n) => String.fromCodePoint(parseInt(n, 16)));
const displayName = a => path.basename(a).replace(/^\d{2}[a-z]?_/, "").replace(/\.(jpe?g|png|heic|webp)$/i, ".jpg").replace(/\s+/g, "_");

const { fixText, fixCaption, sameText } = require("./fb-corrections.cjs")(cfg);
let problems = 0, paragraphs = 0, photos = 0, captions = 0;
const fail = m => { problems++; console.log("  ✗ " + m); };
for (const ch of cfg.chapters) {
  const slug = ch.slug || manifest.chapters.find(c => c.originals_folder === ch.folder).slug;
  const html = fs.readFileSync(path.join(site, urlPath, slug, "index.html"), "utf8");
  const body = html.slice(html.indexOf('class="essay-body"'), html.indexOf('class="essay-navigation"'));
  // text
  const src = ch.post || ch;
  const all = (ch.text ? fixText(ch.slug, fs.readFileSync(ch.text, "utf8").split(String.fromCharCode(13)).join("").trimEnd()) : ch.originals && !ch.post ? "" : fixText(src.key, posts.find(p => p.feedOrder === src.feedOrder).text)).split("\n").filter(l => l.trim() && !/^\s*(#\S+\s*)+$/.test(l));
  // trip-config "post": paragraphs a…b of a post shown in this chapter (see gen-fb-trip-pages.cjs)
  const want = ch.post ? all.slice(ch.post.paras[0], ch.post.paras[1] + 1) : all;
  // another post of the author inserted into this chapter (trip-config "inserts")
  for (const ins of (ch.inserts || []).slice().sort((a, b) => b.after - a.after))
    want.splice(ins.after + 1, 0, ...fs.readFileSync(ins.file, "utf8").replace(/\r/g, "").split("\n").filter(l => l.trim()));
  // a paragraph may hold several lines of the post joined by <br> (a list or table)
  const got = [...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].flatMap(m => decode(m[1].replace(/<br\s*\/?>/g, "\n")).split("\n"));
  if (got.length !== want.length) fail(`${slug}: ${got.length} paragraphs on the page, ${want.length} in the post`);
  want.forEach((p, i) => { if (got[i] !== p) fail(`${slug}: paragraph ${i + 1} differs:\n      post: ${JSON.stringify(p.slice(0, 80))}\n      page: ${JSON.stringify((got[i] || "").slice(0, 80))}`); });
  paragraphs += want.length;
  // photos: the cover and every photo link of the chapter
  const header = html.slice(html.indexOf('class="essay-header"'), html.indexOf('class="essay-body"'));
  const shown = [...(header + body).matchAll(/href="([^"]+\.jpg)"[^>]*data-photo-lightbox/g)].map(m => m[1]);
  const urls = [...(header + body).matchAll(/(?:src|href)="([^"]+)"/g)].map(m => m[1]);
  if (urls.some(u => /drive\.google|googleusercontent/.test(u))) fail(`${slug}: a Drive/Google photo URL on the page`);
  const notR2 = shown.filter(u => !u.startsWith(base)); if (notR2.length) fail(`${slug}: not from R2: ${notR2.slice(0, 3).join(" ")}`);
  // a photo of another chapter of the trip used as this chapter's cover (key "chapter/name") is counted there
  const names = shown.filter(u => u.includes(`/${slug}/`)).map(u => decodeURIComponent(u.split("/").pop()));
  const expected = manifest.photos.filter(p => p.chapter === slug).map(p => displayName(p.archive_name));
  const missing = expected.filter(n => !names.includes(n)), extra = names.filter(n => !expected.includes(n));
  // the chapter cover stays in the story too (the owner's rule): once in the header and once in the text is right
  const cover = [...header.matchAll(/href="([^"]+\.jpg)"[^>]*data-photo-lightbox/g)].map(m => decodeURIComponent(m[1].split("/").pop()));
  const inBody = [...body.matchAll(/href="([^"]+\.jpg)"[^>]*data-photo-lightbox/g)].map(m => m[1]).filter(u => u.includes(`/${slug}/`)).map(u => decodeURIComponent(u.split("/").pop()));
  const twice = inBody.filter((n, i) => inBody.indexOf(n) !== i);
  // except where the owner asked not to repeat it (trip-config "cover_only")
  for (const n of cover) if (expected.includes(n) && !inBody.includes(n) && !(ch.cover_only || []).includes(n)) fail(`${slug}: cover ${n} is not in the story`);
  if (missing.length) fail(`${slug}: photos not shown: ${missing.join(" ")}`);
  if (extra.length) fail(`${slug}: photos not in the archive: ${extra.join(" ")}`);
  if (twice.length) fail(`${slug}: photos shown twice: ${twice.join(" ")}`);
  photos += names.length;
  // captions
  for (const p of manifest.photos.filter(p => p.chapter === slug && p.caption)) {
    const attrs = [...html.matchAll(/data-caption="([^"]*)"/g)].map(m => decode(m[1]));
    // a long caption may be shown as a paragraph next to its photo instead (class photo-note)
    const notes = [...body.matchAll(/<p class="photo-note">([\s\S]*?)<\/p>/g)].map(m => decode(m[1].replace(/<br>/g, "\n")));
    const cap = fixCaption(ch.key, p.source_position, p.caption);
    if (!attrs.includes(cap) && !notes.some(n => n.includes(cap)) && !want.some(t => sameText(t, cap))) fail(`${slug}: caption of ${displayName(p.archive_name)} missing or changed`);
    else captions++;
  }
}
console.log(`${paragraphs} paragraphs, ${photos} photos, ${captions} captions checked; ${problems} problems`);
process.exit(problems ? 1 : 0);
