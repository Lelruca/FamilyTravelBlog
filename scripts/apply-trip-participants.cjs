// The reviewed participant register is authoritative. Reapply after regenerating trip pages.
// --check verifies coverage and front matter without writing; --require-reviewed also rejects open questions.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const people = JSON.parse(read('data/people.json'));
const families = JSON.parse(read('data/participant_families.json'));
const register = JSON.parse(read('data/trip_participants.json'));
const check = process.argv.includes('--check');
const trips = [];
const familyMembers = Object.fromEntries(Object.keys(families).map(id => [id, []]));
for (const [id, person] of Object.entries(people)) {
  if (person.family !== undefined) {
    assert(families[person.family], `${id}: unknown family ${person.family}`);
    familyMembers[person.family].push(id);
  }
}
for (const id of ['oma', 'babushka', 'seryozha', 'lelya', 'natasha', 'mitya'])
  assert.equal(people[id].family, undefined, `${id}: main family must retain individual profiles`);
function scan(dir) {
  for (const entry of fs.readdirSync(path.join(root, dir), {withFileTypes: true})) {
    const file = `${dir}/${entry.name}`;
    if (entry.isDirectory()) scan(file);
    else if (entry.name === '_index.md' && /^trip_year:/m.test(read(file).match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] || ''))
      trips.push(file.slice('content/'.length, -'/_index.md'.length));
  }
}
scan('content');
assert.deepEqual(Object.keys(register).sort(), trips.sort(), 'Participant register must cover every trip and contain no orphan trips');
for (const [id, family] of Object.entries(families)) {
  assert(family.title && familyMembers[id].length, `Invalid or empty family ${id}`);
}
let changed = 0;
const pending = [];
for (const [trip, record] of Object.entries(register)) {
  assert(Array.isArray(record.people) && record.people.length, `${trip}: missing participants`);
  assert.equal(new Set(record.people).size, record.people.length, `${trip}: duplicate participants`);
  for (const id of record.people) assert(people[id], `${trip}: unknown person ${id}`);
  assert(Array.isArray(record.families), `${trip}: missing family list`);
  assert.equal(new Set(record.families).size, record.families.length, `${trip}: duplicate families`);
  for (const id of record.families) {
    assert(families[id], `${trip}: unknown family ${id}`);
    assert(familyMembers[id].some(member => record.people.includes(member)), `${trip}: family has no confirmed participant`);
  }
  assert(record.label && !/Сережа|Сергей|Ольга/u.test(record.label), `${trip}: noncanonical participant label`);
  assert(['reviewed', 'needs-owner'].includes(record.status), `${trip}: invalid review status`);
  assert(Array.isArray(record.evidence) && record.evidence.length, `${trip}: missing evidence`);
  if (record.status === 'needs-owner') {
    assert(record.questions?.length, `${trip}: missing open question`);
    pending.push(trip);
  }
  const file = `content/${trip}/_index.md`;
  const before = read(file);
  const after = before.replace(/^(---\r?\n)([\s\S]*?)(\r?\n---)/, (_, open, front, close) => {
    const newline = before.includes('\r\n') ? '\r\n' : '\n';
    front = front.replace(/^participants:[^\r\n]*(?:\r?\n[ \t]+-[^\r\n]*)*\r?\n?/m, '');
    for (const [key, value] of Object.entries({people: record.people, participant_families: record.families, cover_who: record.label})) {
      const field = `${key}: ${JSON.stringify(value)}`;
      const existing = new RegExp(`^${key}:[^\\r\\n]*(?:\\r?\\n[ \\t]+-[^\\r\\n]*)*`, 'm');
      front = existing.test(front) ? front.replace(existing, field) : front + newline + field;
    }
    return open + front + close;
  });
  if (before !== after) {
    changed++;
    if (!check) fs.writeFileSync(path.join(root, file), after);
    else console.error(`Out of sync: ${file}`);
  }
}
console.log(`${trips.length} trips; ${Object.keys(people).length} people; ${Object.keys(families).length} families; ${changed} ${check ? 'out of sync' : 'updated'}; ${pending.length} awaiting owner clarification.`);
if (check && changed) process.exitCode = 1;
if (process.argv.includes('--require-reviewed') && pending.length) {
  console.error('Unresolved: ' + pending.join(', '));
  process.exitCode = 1;
}
