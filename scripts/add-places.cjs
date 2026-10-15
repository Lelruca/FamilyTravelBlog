// Adds reviewed places: content/places/<slug>/_index.md and an entry in data/place_coordinates.json
// (static/maps/PLACES.md). Coordinates are looked up beforehand and checked against the country, region
// and the story; an existing place is never overwritten.
// Usage: node scripts/add-places.cjs <places.json>
//   places.json: [ [slug, "Local - Русское, Страна", lat, lon, "relation/123", "query", "OSM name", "CA"], ... ]
const fs = require("fs");
const list = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const file = "data/place_coordinates.json";
const coords = JSON.parse(fs.readFileSync(file, "utf8"));
let added = 0;
for (const [slug, title, lat, lon, osm, query, name, cc] of list) {
  if (coords[slug] || fs.existsSync(`content/places/${slug}`)) { console.log(`exists, kept: ${slug}`); continue; }
  fs.mkdirSync(`content/places/${slug}`, { recursive: true });
  fs.writeFileSync(`content/places/${slug}/_index.md`, `---\ntitle: ${JSON.stringify(title)}\n---\n`);
  coords[slug] = { lat, lon, name, country_code: cc, source: `https://www.openstreetmap.org/${osm}`, query };
  added++;
}
fs.writeFileSync(file, JSON.stringify(coords, null, 2) + "\n");
console.log(`${added} places added`);
