// Regenerating photo layouts must retain reviewed links used by the city search.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');

fs.mkdirSync('.tmp', {recursive: true});
const fixture = fs.mkdtempSync(path.resolve('.tmp/fb-attractions-'));
const write = (file, data) => {
  const target = path.join(fixture, file);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, typeof data === 'string' ? data : JSON.stringify(data));
};
const cases = {
  inline: {before: 'attractions: ["reviewed-museum"]', after: 'attractions: ["reviewed-museum"]'},
  block: {before: 'attractions:\n  - reviewed-museum\n  - reviewed-park', after: 'attractions:\n  - reviewed-museum\n  - reviewed-park'},
  configured: {tags: ['new-museum'], after: 'attractions: ["new-museum"]'},
  cleared: {before: 'attractions: ["old-museum"]', tags: [], after: 'attractions: []'},
  empty: {before: 'attractions: []', after: 'attractions: []'},
  unreviewed: {after: null},
};
const chapters = {};
for (const [slug, c] of Object.entries(cases)) {
  chapters[slug] = {title: slug, city: 'Москва', places: ['moscow'],
    ...(c.tags !== undefined ? {attractions: c.tags} : {})};
  if (c.before) write(`content/trip/${slug}/index.md`, `---\r\ntitle: "Old title"\r\n${c.before.replaceAll('\n', '\r\n')}\r\n---\r\nOld layout.\r\n`);
}
write('posts.json', [{feedOrder: 1, text: 'Авторский текст.', date: '2021-10-20'}]);
write('trip-config.json', {trip: 'fixture', posts: 'posts.json', chapters: Object.keys(cases).map(slug => ({slug, feedOrder: 1}))});
write('pages.json', {dir: 'content/trip', trip: {title: 'Fixture'}, chapters});
write('media-manifests/fixture.json', {photos: []});
execFileSync(process.execPath, [path.resolve(__dirname, 'gen-fb-trip-pages.cjs'), 'trip-config.json', 'pages.json'], {cwd: fixture});
for (const [slug, c] of Object.entries(cases)) {
  const raw = fs.readFileSync(path.join(fixture, `content/trip/${slug}/index.md`), 'utf8').replaceAll('\r\n', '\n');
  const tags = raw.match(/^attractions:[^\n]*(?:\n[ \t]+-[^\n]*)*/m)?.[0] || null;
  assert.equal(tags, c.after, slug);
  assert.ok(raw.includes('<p>Авторский текст.</p>'), slug + ': generation did not finish');
}
console.log('Facebook regeneration: existing tags retained, explicit tags applied, empty arrays respected; unreviewed chapters stay untagged.');
