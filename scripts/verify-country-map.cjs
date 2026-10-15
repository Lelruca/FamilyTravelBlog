const fs = require('node:fs');
const assert = require('node:assert/strict');
const build = process.env.TRAVEL_VERIFY_BUILD_DIR || 'public';
const html = fs.readFileSync(`${build}/countries/index.html`, 'utf8');
const data = JSON.parse(html.match(/id="country-atlas-data">([\s\S]*?)<\/script>/)[1]);
const svg = fs.readFileSync('layouts/partials/travel-world-map.html', 'utf8');
const regions = { 'Европа':'europe', 'Северная Америка':'americas', 'Южная Америка':'south', 'Азия':'asia', 'Африка':'africa', 'Австралия и Океания':'oceania' };
let countries=0, trips=0;
for(const country of data.countries.filter(c=>c.trips.length)) {
  const paths=[...svg.matchAll(/<path\b([^>]*)>/g)].map(m=>m[1]).filter(a=>a.includes(`data-key="${country.key}"`));
  assert.ok(paths.length, `${country.key}: missing clickable map shape`);
  assert.ok(paths.every(a=>a.includes(`data-continent="${regions[country.region]}"`)), `${country.key}: map and directory regions differ`);
  for(const trip of country.trips) {
    assert.ok(fs.existsSync(`${build}/${trip.url.replace(/^\/FamilyTravelBlog\//,'')}index.html`), `Missing trip ${trip.url}`);
    trips++;
  }
  countries++;
}
console.log(`Verified ${countries} visited countries: clickable map shapes, regions and ${trips} trip links.`);
