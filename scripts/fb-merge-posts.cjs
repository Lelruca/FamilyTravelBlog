// Joins several posts of scripts/fb-archive-trip.cjs output into one chapter post: a short post about the same
// place or day (one photo, or text only) is told together with its neighbour instead of standing alone.
// The texts follow each other verbatim in the given order, the photos too (numbered on through all of them);
// the first post's date and feed order stay, and "merged_from" keeps every post's key, date and text checksum.
//
// Usage: node scripts/fb-merge-posts.cjs <fb dir> <target key>=<key>,<key>,… …   (e.g. p008=p008,p011)
//   <fb dir>: the folder with posts.json, media.json and published.json; the files are rewritten in place.
const fs = require("fs");
const path = require("path");

const [dir, ...specs] = process.argv.slice(2);
const file = n => path.join(dir, n);
const posts = JSON.parse(fs.readFileSync(file("posts.json"), "utf8"));
const media = JSON.parse(fs.readFileSync(file("media.json"), "utf8"));
const published = JSON.parse(fs.readFileSync(file("published.json"), "utf8"));

for (const spec of specs) {
  const [target, list] = spec.split("=");
  const keys = list.split(",");
  if (!keys.includes(target)) throw new Error(`${spec}: the target must be one of the joined posts`);
  const parts = keys.map(k => posts.find(p => p.key === k) || (() => { throw new Error(`No post ${k}`); })());
  if (parts.some(p => p.merged_from)) throw new Error(`${spec}: already merged`);
  const first = parts[0];
  const merged = { ...posts.find(p => p.key === target), date: first.date, timestamp: first.timestamp,
    text: parts.map(p => p.text.trimEnd()).join("\n"),
    merged_from: parts.map(p => ({ key: p.key, feedOrder: p.feedOrder, date: p.date, sha256: p.sha256 })) };
  let i = 0;
  const items = [], fps = [];
  for (const k of keys) {
    for (const [n, m] of (media.media[k] || []).entries()) {
      items.push({ ...m, i, from_post: k, from_position: m.i + 1 });
      fps.push({ ...(published[k] || [])[n], i });
      i++;
    }
  }
  for (const k of keys) if (k !== target) {
    posts.splice(posts.findIndex(p => p.key === k), 1);
    delete media.media[k]; delete published[k];
  }
  posts[posts.findIndex(p => p.key === target)] = merged;
  media.media[target] = items;
  published[target] = fps;
  if (!media.sets[target]) media.sets[target] = keys.map(k => media.sets[k]).find(Boolean) || null;
  console.log(`${target}: ${keys.join(" + ")} → ${merged.text.split("\n").filter(l => l.trim()).length} paragraphs, ${items.length} items`);
}
fs.writeFileSync(file("posts.json"), JSON.stringify(posts, null, 1));
fs.writeFileSync(file("media.json"), JSON.stringify(media, null, 1));
fs.writeFileSync(file("published.json"), JSON.stringify(published, null, 1));
