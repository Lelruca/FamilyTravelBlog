// Types are assigned editorially in data/attractions.json, never inferred from the name.
// Rebuild ready-to-use search_terms after changing types or their vocabulary.
// --check validates the existing file without writing it.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = 'data/attractions.json';
const attractions = JSON.parse(fs.readFileSync(path, 'utf8'));
const types = JSON.parse(fs.readFileSync('data/attraction_types.json', 'utf8'));
for (const [id, attraction] of Object.entries(attractions)) {
  assert.ok(Array.isArray(attraction.types) && attraction.types.length, `${id}: missing types`);
  assert.equal(new Set(attraction.types).size, attraction.types.length, `${id}: duplicate types`);
  const terms = [...new Set(attraction.types.flatMap(type => {
    assert.ok(types[type], `${id}: unknown type ${type}`);
    return types[type].search_terms;
  }))];
  if (process.argv.includes('--check')) {
    assert.deepEqual(attraction.search_terms, terms, `${id}: stale search_terms`);
  } else {
    attraction.search_terms = terms;
  }
}
if (!process.argv.includes('--check')) fs.writeFileSync(path, JSON.stringify(attractions, null, 2) + '\n');
console.log(`Search vocabulary ${process.argv.includes('--check') ? 'checked' : 'updated'}: ${Object.keys(attractions).length} attractions.`);
